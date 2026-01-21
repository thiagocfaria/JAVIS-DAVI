from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

from .grounding import JarvisACI
from .local_env import build_env_controller
from .worker import Worker
from ..cerebro.actions import Action, ActionPlan
from ..validacao.plano import validar_plano

logger = logging.getLogger("jarvis.agent_s3")


@dataclass
class S3Config:
    worker_engine_type: str
    worker_base_url: str | None
    worker_api_key: str | None
    worker_model: str
    grounding_engine_type: str
    grounding_base_url: str | None
    grounding_api_key: str | None
    grounding_model: str
    grounding_width: int
    grounding_height: int
    max_steps: int
    max_trajectory: int
    enable_reflection: bool
    enable_code_agent: bool
    code_agent_budget: int
    code_workdir: str | None
    max_image_dim: int


class JarvisS3Agent:
    def __init__(
        self,
        config: S3Config,
        platform: str,
        approval_callback: Callable[[], bool] | None = None,
    ):
        self.config = config
        self.platform = platform
        self.approval_callback = approval_callback
        self.worker = None
        self.grounding_agent = None

    def _build_engine_params(
        self, engine_type: str, base_url: str | None, api_key: str | None, model: str
    ) -> dict:
        params = {
            "engine_type": engine_type,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        }
        return params

    def ensure_agent(self, width: int, height: int) -> None:
        worker_params = self._build_engine_params(
            self.config.worker_engine_type,
            self.config.worker_base_url,
            self.config.worker_api_key,
            self.config.worker_model,
        )
        grounding_params = self._build_engine_params(
            self.config.grounding_engine_type,
            self.config.grounding_base_url,
            self.config.grounding_api_key,
            self.config.grounding_model,
        )
        grounding_params["grounding_width"] = width
        grounding_params["grounding_height"] = height

        env_controller = build_env_controller(self.config.code_workdir)

        self.grounding_agent = JarvisACI(
            env_controller=env_controller,
            platform=self.platform,
            engine_params_for_generation=worker_params,
            engine_params_for_grounding=grounding_params,
            width=width,
            height=height,
            enable_code_agent=self.config.enable_code_agent,
            code_agent_budget=self.config.code_agent_budget,
            approval_callback=self.approval_callback,
        )
        skipped_actions = ["set_cell_values"]
        self.worker = Worker(
            worker_engine_params=worker_params,
            grounding_agent=self.grounding_agent,
            platform=self.platform,
            max_trajectory_length=self.config.max_trajectory,
            enable_reflection=self.config.enable_reflection,
            skipped_actions=skipped_actions,
        )

    def predict(self, instruction: str, obs: dict) -> tuple[dict, list]:
        if self.worker is None or self.grounding_agent is None:
            raise RuntimeError("s3_agent_not_initialized")
        return self.worker.generate_next_action(instruction, obs)


class S3Runner:
    def __init__(
        self,
        config: S3Config,
        platform: str,
        policy,
        executor,
        validator,
        telemetry,
        say: Callable[[str], None],
        request_approval: Callable[[], bool],
        require_approval: bool,
        dry_run: bool = False,
    ):
        self.config = config
        self.platform = platform
        self.policy = policy
        self.executor = executor
        self.validator = validator
        self.telemetry = telemetry
        self.say = say
        self.request_approval = request_approval
        self.require_approval = require_approval
        self.dry_run = dry_run
        self.agent = JarvisS3Agent(config, platform, approval_callback=request_approval)

    def _scale_image(self, image: "Image.Image") -> "Image.Image":
        max_dim = int(self.config.max_image_dim or 0)
        if max_dim <= 0:
            return image
        width, height = image.size
        if max(width, height) <= max_dim:
            return image
        from PIL import Image as PilImage

        scale = max_dim / float(max(width, height))
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        # Use Resampling enum for newer PIL, fallback to LANCZOS constant
        resampling = getattr(PilImage, "Resampling", None)
        if resampling:
            lanczos = resampling.LANCZOS
        else:
            # Fallback: try LANCZOS constant, or use 1 (nearest) as last resort
            lanczos = getattr(PilImage, "LANCZOS", 1)
        return image.resize(new_size, lanczos)

    def _image_to_bytes(self, image: "Image.Image") -> bytes:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _prepare_obs(self) -> tuple[dict, int, int]:
        screenshot = self.validator.take_screenshot()
        if screenshot is None:
            raise RuntimeError("s3_screenshot_failed")

        if getattr(self.validator, "get_masked_screenshot_for_ai", None):
            try:
                masked = self.validator.get_masked_screenshot_for_ai()
                if masked is not None:
                    screenshot = masked
            except Exception:
                pass
        elif getattr(self.validator, "_mask_for_export", None):
            try:
                screenshot = self.validator._mask_for_export(screenshot)
            except Exception:
                pass

        screenshot = self._scale_image(screenshot)
        width, height = screenshot.size
        png_bytes = self._image_to_bytes(screenshot)
        return {"screenshot": png_bytes}, width, height

    def _execute_action(self, action: Action) -> bool:
        plan = ActionPlan(
            actions=[action], risk_level="low", notes="agent_s3", confidence=0.0
        )
        quality = validar_plano(plan)
        if quality.errors:
            self.telemetry.log_event("s3_plan_invalid", {"errors": quality.errors})
            self.say("Plano invalido no modo S3.")
            return False

        decision = self.policy.check_actions(plan.actions)
        if not decision.allowed:
            self.telemetry.log_event("s3_policy_block", {"reason": decision.reason})
            self.say(f"Bloqueado: {decision.reason}")
            return False

        if decision.requires_human:
            self.say("Acao requer intervencao humana.")
            return False

        if self.request_approval and (
            self.require_approval or decision.requires_confirmation
        ):
            if not self.request_approval():
                self.say("Aprovacao negada.")
                return False

        if self.dry_run:
            logger.info("S3 DRY_RUN: %s", action)
            return True

        error = self.executor.execute(action.action_type, action.params or {})
        if error:
            self.telemetry.log_event(
                "s3_action_error", {"action": action.to_dict(), "error": error}
            )
            self.say(f"Erro ao executar: {error}")
            return False

        validation = self.validator.validate(action)
        self.telemetry.log_event(
            "s3_action_done", {"action": action.to_dict(), "validation": validation}
        )

        if validation.get("status") == "requires_human":
            self.say("Detectado CAPTCHA ou 2FA. Por favor, complete manualmente.")
            return False
        if validation.get("status") == "failed":
            self.say("A validacao falhou. Parando para evitar erro.")
            return False

        return True

    def run(self, instruction: str) -> bool:
        for step in range(self.config.max_steps):
            obs, width, height = self._prepare_obs()
            if self.agent.worker is None:
                self.agent.ensure_agent(width, height)
            else:
                if self.agent.grounding_agent is None:
                    self.agent.ensure_agent(width, height)
                else:
                    self.agent.grounding_agent.width = width
                    self.agent.grounding_agent.height = height
                    if self.agent.grounding_agent.engine_params_for_grounding is not None:
                        self.agent.grounding_agent.engine_params_for_grounding[
                            "grounding_width"
                        ] = width
                        self.agent.grounding_agent.engine_params_for_grounding[
                            "grounding_height"
                        ] = height

            info, actions = self.agent.predict(instruction, obs)
            if not actions:
                self.say("S3 nao retornou acao.")
                return False

            action = actions[0]
            if isinstance(action, str):
                if action.upper() == "DONE":
                    self.say("S3 concluiu a tarefa.")
                    return True
                if action.upper() == "FAIL":
                    self.say("S3 indicou falha na tarefa.")
                    return False
                if action.upper() == "WAIT":
                    continue

            if not isinstance(action, Action):
                self.say("Acao invalida retornada pelo S3.")
                return False

            ok = self._execute_action(action)
            if not ok:
                return False

        self.say("S3 atingiu o limite de passos.")
        return False


def build_s3_agent(config) -> S3Config:
    return S3Config(
        worker_engine_type=getattr(config, "s3_worker_engine_type", "openai_compat"),
        worker_base_url=getattr(
            config, "s3_worker_base_url", config.local_llm_base_url
        ),
        worker_api_key=getattr(config, "s3_worker_api_key", config.local_llm_api_key),
        worker_model=getattr(config, "s3_worker_model", config.local_llm_model),
        grounding_engine_type=getattr(
            config, "s3_grounding_engine_type", "openai_compat"
        ),
        grounding_base_url=getattr(
            config, "s3_grounding_base_url", config.local_llm_base_url
        ),
        grounding_api_key=getattr(
            config, "s3_grounding_api_key", config.local_llm_api_key
        ),
        grounding_model=getattr(config, "s3_grounding_model", "ui-tars-1.5-7b"),
        grounding_width=getattr(config, "s3_grounding_width", 1920),
        grounding_height=getattr(config, "s3_grounding_height", 1080),
        max_steps=getattr(config, "s3_max_steps", 15),
        max_trajectory=getattr(config, "s3_max_trajectory", 8),
        enable_reflection=getattr(config, "s3_enable_reflection", True),
        enable_code_agent=getattr(config, "s3_enable_code_agent", False),
        code_agent_budget=getattr(config, "s3_code_agent_budget", 20),
        code_workdir=getattr(config, "s3_code_workdir", None),
        max_image_dim=getattr(config, "s3_max_image_dim", 1920),
    )
