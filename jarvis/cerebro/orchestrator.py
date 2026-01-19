"""
Orchestrator - Core logic that integrates all Jarvis modules.

This module:
- Receives commands (text or voice)
- Plans actions (using procedures or LLM)
- Checks policies (security rules)
- Requests approval (voice + key)
- Executes actions (desktop/web automation)
- Validates results (OCR/screenshots)
- Logs telemetry
"""

from __future__ import annotations

import contextlib
import os
import re
import threading
import time
import uuid
import traceback
from typing import Any, Callable, Union, cast

from jarvis.interface.infra.chat_log import ChatLog
from jarvis.interface.audio.audio_utils import BYTES_PER_SAMPLE, SAMPLE_RATE
from jarvis.interface.entrada.followup import FollowUpSession
from jarvis.interface.entrada.stt import SpeechToText
from ..memoria.memory import build_memory_store
from ..memoria.procedures import ProcedureStore
from ..seguranca.kill_switch import stop_requested
from ..seguranca.policy import PolicyKernel
from ..seguranca.policy_usuario import PolicyUsuarioStore
from ..seguranca.sanitizacao import (
    classify_text,
    redact_text,
    sanitize_external_text,
)
from ..telemetria.latency import RollingPercentiles
from ..telemetria.telemetry import Telemetry
from ..validacao.plano import validar_plano
from ..validacao.validator import Validator
from ..voz.adapters.speaker_resemblyzer import ResemblyzerSpeakerVerifier
from ..voz.tts import TextToSpeech
from .actions import Action, ActionPlan
from .config import Config
from .llm import BudgetedLLMClient, LLMClient, _safe_json_loads, build_local_llm_client
from .orcamento import OrcamentoDiario


# Config helpers (keep local to orchestrator).
def _env_int_clamped(key: str, default: int, min_value: int, max_value: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(value, max_value))


# Try to import new automation module
try:
    from ..acoes import AutomationRouter

    HAS_NEW_AUTOMATION = True
except ImportError:
    HAS_NEW_AUTOMATION = False
    try:
        from ..acoes.legacy import AutomationDriver
    except ImportError:
        AutomationDriver = None  # type: ignore[assignment, misc]


class LegacyAutomationWrapper:
    """Wrapper to make legacy AutomationDriver compatible with new interface."""

    def __init__(self, driver) -> None:
        self._driver = driver

    def execute(self, action_type: str, params: dict):
        """Execute action using legacy driver."""
        from .actions import Action

        action = Action(action_type=action_type, params=params)
        return self._driver.execute(action)


class Orchestrator:
    """
    Main orchestrator for Jarvis.

    Integrates all modules and manages the command execution flow.
    """

    def __init__(self, config: Config) -> None:
        self.config = config

        # Initialize policy kernel (immutable security core)
        self.policy = PolicyKernel(
            allow_open_app=config.allow_open_app,
            user_policy_path=config.policy_user_path,
        )
        self.policy_user_store = PolicyUsuarioStore(config.policy_user_path)

        # Initialize telemetry (local only)
        self.telemetry = Telemetry(config.log_path)
        self.budget = OrcamentoDiario(
            config.budget_path, config.budget_max_calls, config.budget_max_chars
        )
        self.chat = ChatLog(
            config.chat_log_path,
            auto_open=config.chat_auto_open,
            open_command=config.chat_open_command,
            open_cooldown_s=config.chat_open_cooldown_s,
        )

        # Initialize memory (local-first)
        self.memory = build_memory_store(
            db_path=config.memory_db,
        )

        # Initialize local brain (no paid API)
        self.llm_local = BudgetedLLMClient(
            build_local_llm_client(
                config.local_llm_base_url,
                config.local_llm_api_key,
                config.local_llm_model,
                config.local_llm_timeout_s,
                config.llm_confidence_min,
                config.local_llm_cooldown_s,
            ),
            budget=self.budget,
            telemetry=self.telemetry,
            name="local",
        )

        # Initialize automation (separated desktop/web)
        if HAS_NEW_AUTOMATION:
            self.executor: Union[AutomationRouter, LegacyAutomationWrapper] = (
                AutomationRouter(
                    session_type=config.session_type,
                    enable_web=True,
                )
            )
        elif AutomationDriver:
            self.executor = LegacyAutomationWrapper(
                AutomationDriver(config.session_type)
            )
        else:
            raise RuntimeError("No automation driver available")

        # Initialize validator (with OCR)
        self.validator = Validator(
            enable_ocr=True,
            save_screenshots=False,
            mask_screenshots=config.mask_screenshots,
        )

        # Initialize TTS (Piper with espeak fallback)
        self.tts = TextToSpeech(config)

        # Initialize STT (local)
        self.stt = SpeechToText(config)
        self._followup = FollowUpSession()
        self._debug_enabled = os.environ.get("JARVIS_DEBUG", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._speaker_verifier = ResemblyzerSpeakerVerifier()
        self._stage_percentiles = RollingPercentiles()
        self._voice_metrics_active = False
        self._voice_eos_perf_ts: float | None = None
        self._voice_first_audio_perf_ts: float | None = None
        self._voice_ack_perf_ts: float | None = None
        self._voice_phase1_perf_ts: float | None = None
        self._voice_metrics_totals: dict[str, float] = {
            "llm_ms": 0.0,
            "tts_ms": 0.0,
            "play_ms": 0.0,
            "tts_first_audio_ms": 0.0,
            "tts_ack_ms": 0.0,
        }
        self._voice_metrics_counts: dict[str, int] = {
            "llm": 0,
            "tts": 0,
            "play": 0,
            "tts_first_audio": 0,
            "tts_ack": 0,
        }
        self._voice_overlap_lock = threading.Lock()
        self._voice_overlap_timer: threading.Timer | None = None
        self._voice_overlap_plan: ActionPlan | None = None
        self._voice_overlap_norm: str | None = None

        # Initialize procedures store
        self.procedures = ProcedureStore(
            config.procedures_path,
            max_total=config.procedures_max_total,
            max_per_tag=config.procedures_max_per_tag,
            ttl_days=config.procedures_ttl_days,
        )

        # State tracking
        self.last_plan: ActionPlan | None = None
        self.last_command: str | None = None
        self.last_success: bool = False
        self.last_error: str | None = None
        self._stop_notified: bool = False
        self._demo_recorder: Any = (
            None  # DemonstrationRecorder | None, but imported conditionally
        )
        self._demo_recording_name: str | None = None

    def _debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"[orchestrator] {message}")

    def _reset_voice_metrics(self) -> None:
        self._voice_metrics_active = True
        self._voice_eos_perf_ts = None
        self._voice_first_audio_perf_ts = None
        self._voice_ack_perf_ts = None
        self._voice_phase1_perf_ts = None
        self._voice_metrics_totals = {
            "llm_ms": 0.0,
            "tts_ms": 0.0,
            "play_ms": 0.0,
            "tts_first_audio_ms": 0.0,
            "tts_ack_ms": 0.0,
        }
        self._voice_metrics_counts = {
            "llm": 0,
            "tts": 0,
            "play": 0,
            "tts_first_audio": 0,
            "tts_ack": 0,
        }

    def _log_voice_stage_metrics(
        self, stt_metrics: dict[str, float | None] | None
    ) -> None:
        llm_ms = (
            self._voice_metrics_totals["llm_ms"]
            if self._voice_metrics_counts["llm"] > 0
            else None
        )
        tts_ms = (
            self._voice_metrics_totals["tts_ms"]
            if self._voice_metrics_counts["tts"] > 0
            else None
        )
        play_ms = (
            self._voice_metrics_totals["play_ms"]
            if self._voice_metrics_counts["play"] > 0
            else None
        )
        tts_first_audio_ms = (
            self._voice_metrics_totals["tts_first_audio_ms"]
            if self._voice_metrics_counts["tts_first_audio"] > 0
            else None
        )
        tts_ack_ms = (
            self._voice_metrics_totals["tts_ack_ms"]
            if self._voice_metrics_counts["tts_ack"] > 0
            else None
        )
        if stt_metrics is None:
            stt_metrics = {}
        eos_to_first_audio_ms: float | None = None
        eos_to_ack_ms: float | None = None
        eos_to_phase1_ms: float | None = None
        eos_perf_ts = stt_metrics.get("eos_perf_ts") if isinstance(stt_metrics, dict) else None
        first_audio_perf_ts = self._voice_first_audio_perf_ts
        ack_perf_ts = self._voice_ack_perf_ts
        phase1_perf_ts = self._voice_phase1_perf_ts
        if isinstance(eos_perf_ts, (int, float)) and isinstance(
            first_audio_perf_ts, (int, float)
        ):
            delta_ms = (float(first_audio_perf_ts) - float(eos_perf_ts)) * 1000.0
            if delta_ms >= 0:
                eos_to_first_audio_ms = float(delta_ms)
        if isinstance(eos_perf_ts, (int, float)) and isinstance(ack_perf_ts, (int, float)):
            delta_ms = (float(ack_perf_ts) - float(eos_perf_ts)) * 1000.0
            if delta_ms >= 0:
                eos_to_ack_ms = float(delta_ms)
        if isinstance(eos_perf_ts, (int, float)) and isinstance(phase1_perf_ts, (int, float)):
            delta_ms = (float(phase1_perf_ts) - float(eos_perf_ts)) * 1000.0
            if delta_ms >= 0:
                eos_to_phase1_ms = float(delta_ms)
        stage_values = {
            "capture_ms": stt_metrics.get("capture_ms") if isinstance(stt_metrics, dict) else None,
            "vad_ms": stt_metrics.get("vad_ms") if isinstance(stt_metrics, dict) else None,
            "endpoint_ms": stt_metrics.get("endpoint_ms") if isinstance(stt_metrics, dict) else None,
            "stt_ms": stt_metrics.get("stt_ms") if isinstance(stt_metrics, dict) else None,
            "llm_ms": llm_ms,
            "tts_ms": tts_ms,
            "play_ms": play_ms,
            "tts_first_audio_ms": tts_first_audio_ms,
            "eos_to_first_audio_ms": eos_to_first_audio_ms,
            "tts_ack_ms": tts_ack_ms,
            "eos_to_ack_ms": eos_to_ack_ms,
            "eos_to_phase1_ms": eos_to_phase1_ms,
        }
        for stage, value in stage_values.items():
            self._stage_percentiles.record(stage, value)
        payload: dict[str, float | None | dict[str, float | None]] = dict(stage_values)
        payload["p95"] = self._stage_percentiles.snapshot(stage_values.keys())
        self.telemetry.log_event("voice_stage_metrics", payload)

    def handle_text(self, text: str) -> tuple[str, bool]:
        """Handle a text command."""
        if not text.strip():
            return "empty", False

        if self._stop_active():
            return "stopped", False

        command_id = uuid.uuid4().hex
        command_start_ts = time.time()

        def _log_command_event(
            event_type: str, extra: dict[str, object] | None = None
        ) -> None:
            payload: dict[str, object] = {
                "command_id": command_id,
                "text": text,
                "timestamp": command_start_ts,
            }
            if extra:
                payload.update(extra)
            self.telemetry.log_event(event_type, payload)

        def _log_command_end(
            status: str, duration: float, error: str | None = None
        ) -> None:
            self.telemetry.log_event(
                "command.end",
                {
                    "command_id": command_id,
                    "text": text,
                    "timestamp": command_start_ts,
                    "status": status,
                    "duration": duration,
                    "error": error or "",
                },
            )

        _log_command_event("command.start", {"source": "text", "session": "local"})

        status = "failed"
        success = False
        try:
            status, success = self._process_command_flow(text, _log_command_event)
        except Exception as exc:
            self.last_error = str(exc)
            raise
        finally:
            duration = time.time() - command_start_ts
            final_status = "success" if success else status
            _log_command_end(final_status, duration, self.last_error)
        return status, success

    def run_s3_loop(self, instruction: str) -> bool:
        """Run Agent-S S3 loop for a GUI task."""
        if not instruction.strip():
            return False
        import platform as _platform

        from ..agent_s3.runner import S3Runner, build_s3_agent

        s3_config = build_s3_agent(self.config)
        runner = S3Runner(
            config=s3_config,
            platform=_platform.system().lower(),
            policy=self.policy,
            executor=self.executor,
            validator=self.validator,
            telemetry=self.telemetry,
            say=self._say,
            request_approval=self._request_approval,
            require_approval=self.config.require_approval,
            dry_run=self.config.dry_run,
        )
        return runner.run(instruction)

    def _process_command_flow(
        self,
        text: str,
        log_event: Callable[[str, dict[str, object] | None], None],
    ) -> tuple[str, bool]:
        """Core command logic moved out for instrumentation."""
        command_status = "failed"
        command_success = False

        def should_stop() -> bool:
            return (
                self.config.max_failures_per_command > 0
                and failures >= self.config.max_failures_per_command
            )

        failures = 0
        attempts: list[dict[str, object]] = []

        def try_plan(
            plan: ActionPlan,
            source: str,
            guidance: str | None = None,
            count_failure: bool = True,
        ) -> bool:
            nonlocal failures, command_status, command_success
            validated_plan = self._validate_plan(plan, source)
            if validated_plan is None:
                self._record_attempt(attempts, source, False, self.last_error, None)
                if count_failure:
                    failures += 1
                log_event("plan.invalid", {"source": source})
                return False

            log_event(
                "plan.validated",
                {
                    "source": source,
                    "actions": len(validated_plan.actions),
                    "risk_level": validated_plan.risk_level,
                },
            )
            self.telemetry.log_event("plan", validated_plan.to_dict())
            plan_start = time.perf_counter()
            executed = self._run_plan(validated_plan)
            plan_duration = time.perf_counter() - plan_start
            log_event(
                "plan.executed",
                {
                    "source": source,
                    "success": executed,
                    "duration": plan_duration,
                    "actions": len(validated_plan.actions),
                    "risk_level": validated_plan.risk_level,
                },
            )
            if not executed:
                self._record_attempt(attempts, source, False, self.last_error, validated_plan)
                if count_failure:
                    failures += 1
                return False

            self._record_attempt(attempts, source, True, None, plan)
            self._record_success(text, plan, guidance)
            self._maybe_learn_procedure(text, plan, guidance)
            command_success = True
            command_status = "success"
            return True

        # Check for meta commands first
        if self._handle_meta_command(text):
            command_status = "meta"
            return command_status, command_success

        self.telemetry.log_event("command", {"text": text})
        if self._route_intent(text):
            command_status = "smalltalk"
            command_success = True
            return command_status, command_success

        # If the local LLM is not configured, avoid a confusing "Não consegui completar"
        # for natural-language questions that the mock planner can't handle.
        if not self.config.local_llm_base_url:
            from .utils import normalize_text

            normalized = normalize_text(text)
            if normalized and not self._contains_action_verb(normalized):
                # Keep it conservative: only trigger for longer free-form requests.
                if len(normalized.split()) > 2:
                    self._say(
                        "Ainda não tenho o cérebro (LLM) configurado aqui, então só consigo executar comandos bem simples no modo voz.\n"
                        "Exemplos: “abrir firefox”, “digitar oi”, “esperar 2”."
                    )
                    command_status = "no_llm_help"
                    command_success = True
                    return command_status, command_success

        procedure_match = self.procedures.match(text)
        if procedure_match:
            plan, _values = procedure_match
            self.telemetry.log_event("plan_source", {"source": "procedure"})
            if try_plan(plan, "procedure", count_failure=False):
                return command_status, command_success
            self.telemetry.log_event("procedure_failed", {"command": text})

        rule_plan = self._rule_based_plan(text)
        if rule_plan:
            self.telemetry.log_event("plan_source", {"source": "rule"})
            if try_plan(rule_plan, "rule", count_failure=False):
                return command_status, command_success

        consume_overlap = getattr(self, "_consume_overlap_plan", None)
        prefetched: ActionPlan | None = None
        if callable(consume_overlap):
            consume_overlap_typed = cast(
                Callable[[str], ActionPlan | None],
                consume_overlap,
            )
            prefetched = consume_overlap_typed(text)

        plan = prefetched or self._plan_with_llm(text, self.llm_local, source="local")

        if plan is None:
            self._record_attempt(attempts, "local", False, self.last_error, None)
        elif not isinstance(plan, ActionPlan):
            self.last_error = "invalid_plan_type"
            self._record_attempt(attempts, "local", False, self.last_error, None)
            plan = None
        elif self._is_mock_fallback(plan) and not self._allow_mock_fallback(text):
            self.telemetry.log_event("local_fallback_skip", {"reason": "mock_fallback"})
            self.last_error = "mock_fallback_skipped"
            self._record_attempt(attempts, "local", False, self.last_error, plan)
            plan = None
        else:
            self.telemetry.log_event("plan_source", {"source": "local"})
            if try_plan(plan, "local", count_failure=False):
                return command_status, command_success

        external_allowed = (
            self._external_allowed(text) if self.config.browser_ai_enabled else False
        )
        guidance = (
            self._collect_external_guidance(text, attempts)
            if external_allowed
            else None
        )
        if guidance:
            plan = self._try_parse_plan_from_text(guidance)
            if not plan:
                plan = self._plan_with_llm(guidance, self.llm_local, source="browser")
            if plan:
                self.telemetry.log_event("plan_source", {"source": "browser"})
                if try_plan(plan, "browser", guidance=guidance, count_failure=False):
                    return command_status, command_success
            else:
                self._record_attempt(attempts, "browser", False, self.last_error, None)

        if should_stop():
            self._say("Falhou varias vezes. Vou pedir sua ajuda para economizar.")
            self._log_pause("falhas_maximas", plan=self.last_plan, actions_executed=[])

        self._handle_guidance_loop(
            text, try_plan, planner=self.llm_local, attempts=attempts
        )
        return command_status, command_success

    def _route_intent(self, text: str) -> bool:
        from .utils import normalize_text

        normalized = normalize_text(text)
        if not normalized:
            return False
        if self._contains_action_verb(normalized):
            return False
        if not self._looks_like_smalltalk(normalized):
            return False

        response = "Oi! Como posso ajudar?"
        self._say(response)
        try:
            self.chat.append("jarvis", response, {"source": "intent_router"})
        except Exception:
            pass
        return True

    @staticmethod
    def _contains_action_verb(text: str) -> bool:
        verbs = {
            "abrir",
            "abre",
            "abrindo",
            "fechar",
            "feche",
            "clicar",
            "clique",
            "digitar",
            "digite",
            "escrever",
            "escreva",
            "pesquisar",
            "pesquise",
            "buscar",
            "busque",
            "procurar",
            "procure",
            "mostrar",
            "mostre",
            "criar",
            "crie",
            "apagar",
            "apague",
            "remover",
            "remova",
            "enviar",
            "envie",
            "baixar",
            "baixe",
            "instalar",
            "instale",
            "navegar",
            "navegue",
            "entrar",
            "entre",
            "abrir",
            "open",
            "click",
            "type",
            "search",
            "scroll",
        }
        for verb in verbs:
            if re.search(rf"\b{re.escape(verb)}\b", text):
                return True
        return False

    @staticmethod
    def _looks_like_smalltalk(text: str) -> bool:
        greetings = {
            "oi",
            "ola",
            "olá",
            "e ai",
            "e aí",
            "eai",
            "bom dia",
            "boa tarde",
            "boa noite",
            "tudo bem",
            "como vai",
            "como voce ta",
            "como voce esta",
            "como você ta",
            "como você está",
            "fala",
            "salve",
        }
        for phrase in greetings:
            if phrase in text:
                return True
        if text in {"jarvis", "oi jarvis", "ola jarvis", "olá jarvis"}:
            return True
        return False

    @staticmethod
    def _has_any(text: str, words: set[str] | list[str]) -> bool:
        for word in words:
            if re.search(rf"\b{re.escape(word)}\b", text):
                return True
        return False

    def _rule_based_plan(self, text: str) -> ActionPlan | None:
        from .utils import normalize_text

        t = normalize_text(text)

        def has(*parts: str) -> bool:
            return all(p in t for p in parts)

        def has_any_prefix(prefixes: list[str]) -> bool:
            return any(tok.startswith(pref) for tok in t.split() for pref in prefixes)

        verb = any(v in t.split() for v in ["abrir", "abre", "abriu", "open"])

        if verb and has_any_prefix(["naveg", "browser"]):
            actions = [
                Action(action_type="open_url", params={"url": "https://www.google.com"})
            ]
            return ActionPlan(
                actions=actions, risk_level="low", notes="rule_based:browser"
            )

        if verb and has_any_prefix(["youtub", "yt"]):
            actions = [
                Action(
                    action_type="open_url", params={"url": "https://www.youtube.com"}
                )
            ]
            return ActionPlan(
                actions=actions, risk_level="low", notes="rule_based:youtube"
            )

        if verb and ("chatgpt" in t or has("chat", "gpt")):
            actions = [
                Action(action_type="open_url", params={"url": "https://chatgpt.com"})
            ]
            return ActionPlan(
                actions=actions, risk_level="low", notes="rule_based:chatgpt"
            )

        return None

    def _execute_plan(self, plan: ActionPlan) -> bool:
        """Execute an action plan."""
        executed: list[Action] = []
        for action in plan.actions:
            if self._stop_active():
                self._log_pause("kill_switch", plan=plan, actions_executed=executed)
                return False
            # Dry run mode
            if self.config.dry_run:
                print(f"DRY_RUN: {action}")
                continue

            # Execute action
            error = self.executor.execute(action.action_type, action.params or {})

            if error:
                self.telemetry.log_event(
                    "action_error",
                    {
                        "action": action.to_dict(),
                        "error": error,
                    },
                )
                self.last_error = str(error)
                self._say(f"Erro ao executar: {error}")
                self._log_pause(
                    "action_error",
                    details={"error": str(error), "action": action.to_dict()},
                    plan=plan,
                    actions_executed=executed,
                )
                self.last_success = False
                return False

            # Validate action result
            validation = self.validator.validate(action)

            self.telemetry.log_event(
                "action_done",
                {
                    "action": action.to_dict(),
                    "validation": validation,
                },
            )

            # Check if validation requires human
            if validation.get("status") == "requires_human":
                self.last_error = "requires_human"
                self._say("Detectado CAPTCHA ou 2FA. Por favor, complete manualmente.")
                self._log_pause(
                    "requires_human",
                    details={"validation": validation},
                    plan=plan,
                    actions_executed=executed,
                )
                return False
            if validation.get("status") == "failed":
                self.last_error = "validation_failed"
                self._say("A validação falhou. Parando para evitar erro.")
                self._log_pause(
                    "validation_failed",
                    details={"validation": validation},
                    plan=plan,
                    actions_executed=executed,
                )
                return False
            executed.append(action)

        return True

    def _validate_plan(self, plan: ActionPlan, source: str) -> ActionPlan | None:
        qualidade = validar_plano(plan)
        plan.confidence = qualidade.confidence
        if qualidade.errors:
            first_error = qualidade.errors[0] if qualidade.errors else "plan_invalid"
            self.last_error = f"plan_invalid:{first_error}"
            self.telemetry.log_event(
                "plan_invalid",
                {
                    "errors": qualidade.errors,
                    "warnings": qualidade.warnings,
                    "source": source,
                },
            )
            self._say("Plano invalido.")
            self._log_pause(
                "plan_invalid",
                details={
                    "errors": qualidade.errors,
                    "warnings": qualidade.warnings,
                    "source": source,
                },
                plan=plan,
                actions_executed=[],
            )
            return None
        return plan

    def _run_plan(self, plan: ActionPlan) -> bool:
        if not plan.actions:
            self.last_error = "plan_empty"
            self._say("Não encontrei ações para esse comando.")
            self.telemetry.log_event("plan_empty", {})
            self._log_pause("plan_empty", plan=plan, actions_executed=[])
            return False

        decision = self.policy.check_actions(plan.actions)
        if not decision.allowed:
            self.last_error = f"policy_blocked:{decision.reason}"
            self._say(f"Bloqueado: {decision.reason}")
            self.telemetry.log_event(
                "policy_block",
                {
                    "reason": decision.reason,
                    "blocked_by": decision.blocked_by,
                },
            )
            self._log_pause(
                "policy_blocked",
                details={"reason": decision.reason, "blocked_by": decision.blocked_by},
                plan=plan,
                actions_executed=[],
            )
            return False

        if decision.requires_human:
            self.last_error = "requires_human"
            self._say(
                "Esta ação requer intervenção humana. Por favor, complete manualmente."
            )
            self.telemetry.log_event("requires_human", {"reason": "2fa_captcha"})
            self._log_pause(
                "requires_human",
                details={"reason": "2fa_captcha"},
                plan=plan,
                actions_executed=[],
            )
            return False

        if plan.risk_level != "low":
            decision = decision.__class__(
                allowed=decision.allowed,
                reason=decision.reason,
                requires_confirmation=True,
                requires_human=decision.requires_human,
                blocked_by=decision.blocked_by,
            )

        skip_approval = (
            plan.risk_level == "low"
            and isinstance(plan.notes, str)
            and plan.notes.startswith("rule_based")
        )
        needs_approval = decision.requires_confirmation or (
            self.config.require_approval and not skip_approval
        )
        if needs_approval:
            approved = self._request_approval()
            if not approved:
                self.last_error = "approval_denied"
                self._say("Aprovação negada.")
                self.telemetry.log_event("approval_denied", {})
                self._log_pause("approval_denied", plan=plan, actions_executed=[])
                return False

        return self._execute_plan(plan)

    def _record_success(
        self, text: str, plan: ActionPlan, guidance: str | None = None
    ) -> None:
        self.last_plan = plan
        self.last_command = text
        self.last_success = True
        self.last_error = None
        payload_dict: dict[str, Any] = {"plan": plan.to_dict()}
        if guidance:
            payload_dict["guidance"] = guidance
        payload: dict[str, object] = cast(dict[str, object], payload_dict)
        with contextlib.suppress(Exception):
            redacted_text, mem_meta = self._redact_for_memory(text, "episode")
            sanitized_payload, payload_redactions = self._redact_payload_for_memory(
                cast(dict[str, object], payload)
            )
            memory_meta = dict(mem_meta)
            if payload_redactions:
                memory_meta["payload_redactions"] = payload_redactions
            if isinstance(sanitized_payload, dict):
                sanitized_payload["memory_meta"] = memory_meta
            self.memory.add_episode(redacted_text, sanitized_payload)

    def _handle_guidance_loop(
        self,
        text: str,
        try_plan,
        planner: LLMClient,
        attempts: list[dict[str, object]],
    ) -> None:
        max_attempts = self.config.max_guidance_attempts
        if max_attempts <= 0:
            self._say("Não consegui completar.")
            self._log_pause(
                "guidance_disabled",
                details={"reason": "max_guidance_attempts=0"},
                plan=None,
                actions_executed=[],
            )
            return

        for attempt in range(max_attempts):
            self._say("Não consegui completar. Pode me explicar como fazer?")
            summary = self._summarize_attempts(attempts)
            if summary:
                self._say(f"Tentei: {summary}")
            guidance = self._prompt_user("Explique os passos ou cole a resposta da IA:")
            if not guidance:
                self._log_pause(
                    "guidance_aborted",
                    details={"reason": "empty_guidance"},
                    plan=None,
                    actions_executed=[],
                )
                return
            guidance = self._sanitize_guidance(guidance, source="usuario")
            if not guidance:
                return
            plan = self._try_parse_plan_from_text(guidance)
            if not plan:
                plan = self._plan_with_llm(guidance, planner, source="guidance")
            if not plan:
                self._say("Não consegui gerar um plano. Vamos tentar de outra forma?")
                continue
            if try_plan(plan, "llm_guidance", guidance=guidance, count_failure=False):
                return
            if attempt < max_attempts - 1:
                self._say("Ainda não deu certo. Pode explicar de outro jeito?")
        self._say("Não consegui completar com as tentativas atuais.")
        self._log_pause(
            "guidance_failed",
            details={"attempts": self._summarize_attempts(attempts)},
            plan=None,
            actions_executed=[],
        )

    def _request_approval(self) -> bool:
        """Request user approval for action execution."""
        voice_phrase = self.config.approval_voice_passphrase
        key_phrase = self.config.approval_key_passphrase

        if not voice_phrase and not key_phrase:
            from .utils import normalize_text

            print("Aprovação necessária. Digite 'ok' e pressione Enter: ")
            return normalize_text(input()) == "ok"

        print("Aprovação necessária. Fale a frase-senha e confirme digitando-a.")

        spoken_ok = False
        typed_ok = False

        # Try voice recognition
        from .utils import normalize_text

        if self.config.stt_mode != "none":
            try:
                if voice_phrase and self._speaker_verifier.is_enabled():
                    result = self.stt.transcribe_with_vad(
                        max_seconds=4,
                        return_audio=True,
                        require_wake_word=False,
                    )
                    if isinstance(result, tuple):
                        spoken, audio_bytes, speech_detected = result
                    else:
                        spoken, audio_bytes, speech_detected = result, b"", None
                    if not audio_bytes or speech_detected is False:
                        spoken_ok = False
                    else:
                        score, ok = self._speaker_verifier.verify_ok(
                            audio_bytes, SAMPLE_RATE
                        )
                        if not ok:
                            self._debug(
                                f"voice approval speaker verification failed (score={score:.3f})"
                            )
                            spoken_ok = False
                        else:
                            spoken_ok = normalize_text(spoken) == normalize_text(
                                voice_phrase
                            )
                            if spoken_ok:
                                self.telemetry.log_event(
                                    "voice_approval", {"match": True}
                                )
                else:
                    spoken = self.stt.transcribe_once(
                        seconds=3, require_wake_word=False
                    )
                    if voice_phrase:
                        spoken_ok = normalize_text(spoken) == normalize_text(
                            voice_phrase
                        )
                        if spoken_ok:
                            self.telemetry.log_event("voice_approval", {"match": True})
            except Exception as e:
                self.telemetry.log_event("voice_approval_error", {"error": str(e)})
                spoken_ok = False

        # Get typed confirmation
        typed = input().strip()
        if key_phrase:
            typed_ok = normalize_text(typed) == normalize_text(key_phrase)

        # Evaluate based on approval mode
        mode = self.config.approval_mode

        if mode == "voice_and_key":
            if self.config.stt_mode == "none":
                # Fallback: require typed twice if voice unavailable
                if not key_phrase:
                    return False
                typed2 = normalize_text(input("Repita a frase-senha para confirmar: "))
                return typed_ok and typed2 == normalize_text(key_phrase)
            return spoken_ok and typed_ok

        if mode == "voice_or_key":
            return spoken_ok or typed_ok

        if mode == "key_only":
            return typed_ok

        # Default: require both
        return spoken_ok and typed_ok

    def _say(self, text: str) -> None:
        """Output text via TTS and console."""
        print(text)
        tts_async = os.environ.get("JARVIS_TTS_ASYNC", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if tts_async and hasattr(self.tts, "speak_async"):
            self.tts.speak_async(text)
        else:
            self.tts.speak(text)
        if not self._voice_metrics_active:
            return
        metrics = self.tts.get_last_metrics()
        first_audio_perf_ts = metrics.get("tts_first_audio_perf_ts")
        ack_perf_ts = metrics.get("tts_ack_perf_ts")
        if (
            self._voice_first_audio_perf_ts is None
            and isinstance(first_audio_perf_ts, (int, float))
        ):
            self._voice_first_audio_perf_ts = float(first_audio_perf_ts)
        if self._voice_ack_perf_ts is None and isinstance(ack_perf_ts, (int, float)):
            self._voice_ack_perf_ts = float(ack_perf_ts)
        tts_ms = metrics.get("tts_ms")
        if tts_ms is not None:
            self._voice_metrics_totals["tts_ms"] += float(tts_ms)
            self._voice_metrics_counts["tts"] += 1
        play_ms = metrics.get("play_ms")
        if play_ms is not None:
            self._voice_metrics_totals["play_ms"] += float(play_ms)
            self._voice_metrics_counts["play"] += 1
        tts_first_audio_ms = metrics.get("tts_first_audio_ms")
        if tts_first_audio_ms is not None:
            self._voice_metrics_totals["tts_first_audio_ms"] += float(
                tts_first_audio_ms
            )
            self._voice_metrics_counts["tts_first_audio"] += 1
        tts_ack_ms = metrics.get("tts_ack_ms")
        if tts_ack_ms is not None:
            self._voice_metrics_totals["tts_ack_ms"] += float(tts_ack_ms)
            self._voice_metrics_counts["tts_ack"] += 1

    def transcribe_and_handle(self) -> None:
        """Capture voice and handle as command."""
        stt_metrics: dict[str, float | None] = {}
        overlap_enabled = os.environ.get("JARVIS_VOICE_OVERLAP_PLAN", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        phase1_enabled = os.environ.get("JARVIS_VOICE_PHASE1", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        overlap_min_chars = _env_int_clamped("JARVIS_VOICE_OVERLAP_MIN_CHARS", 12, 0, 9999)
        overlap_stable_ms = _env_int_clamped("JARVIS_VOICE_OVERLAP_STABLE_MS", 350, 50, 3000)
        partials_log = os.environ.get(
            "JARVIS_STT_PARTIALS_LOG", ""
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        partials_stdout = os.environ.get(
            "JARVIS_STT_PARTIALS_STDOUT", ""
        ).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        partials_enabled = partials_log or partials_stdout or overlap_enabled or phase1_enabled
        latest_partial: dict[str, object] = {"text": "", "ts": 0.0}
        phase1_started = threading.Event()
        overlap_lock = getattr(self, "_voice_overlap_lock", None)
        if overlap_lock is None:
            overlap_lock = threading.Lock()
            try:
                setattr(self, "_voice_overlap_lock", overlap_lock)
            except Exception:
                pass
        overlap_timer: threading.Timer | None = None

        def _on_partial(text: str) -> None:
            nonlocal overlap_timer
            if partials_stdout:
                preview = (text or "").replace("\n", " ").strip()
                if len(preview) > 160:
                    preview = preview[:160] + "…"
                print(f"[stt-partial] {preview}")
            if partials_log:
                try:
                    self.chat.append("jarvis", text, {"type": "stt_partial"})
                except Exception:
                    pass
            if not (overlap_enabled or phase1_enabled):
                return
            now = time.perf_counter()
            with overlap_lock:
                latest_partial["text"] = text
                latest_partial["ts"] = now
                if overlap_timer is not None:
                    try:
                        overlap_timer.cancel()
                    except Exception:
                        pass
                    overlap_timer = None

                def _stable_fire() -> None:
                    try:
                        with overlap_lock:
                            current_text = str(latest_partial.get("text") or "")
                        # Avoid phase1 false positives when a wake word is required.
                        # When wake-word gating is on, only speak after final transcription produced text.
                        if phase1_enabled and not phase1_started.is_set():
                            # Speaking during recording can cause echo and confuse the STT.
                            # If a wake word is required, only speak after the recording ended (on_eos).
                            if not require_wake:
                                self._try_voice_phase1_ack()
                                phase1_started.set()
                        if overlap_enabled and len(current_text.strip()) >= overlap_min_chars:
                            self._prefetch_overlap_plan(current_text)
                    except Exception:
                        return

                overlap_timer = threading.Timer(overlap_stable_ms / 1000.0, _stable_fire)
                overlap_timer.daemon = True
                overlap_timer.start()

        reset_metrics = getattr(self, "_reset_voice_metrics", None)
        if callable(reset_metrics):
            reset_metrics()
        try:
            # Use VAD if available
            require_wake = self._followup.should_require_wake_word(
                self.stt.requires_wake_word()
            )
            voice_seconds = _env_int_clamped("JARVIS_VOICE_MAX_SECONDS", 30, 3, 120)
            def _on_eos() -> None:
                # Avoid phase1 false positives when a wake word is required.
                if phase1_enabled and not phase1_started.is_set() and not require_wake:
                    self._try_voice_phase1_ack()
                    phase1_started.set()

            try:
                result = self.stt.transcribe_with_vad(
                    max_seconds=voice_seconds,
                    return_audio=True,
                    require_wake_word=require_wake,
                    on_partial=(
                        _on_partial if partials_enabled else None
                    ),
                    on_eos=_on_eos if phase1_enabled else None,
                )
            except TypeError:
                result = self.stt.transcribe_with_vad(
                    max_seconds=voice_seconds,
                    return_audio=True,
                    require_wake_word=require_wake,
                )
            get_stt_metrics = getattr(self.stt, "get_last_metrics", None)
            if callable(get_stt_metrics):
                stt_metrics_result = get_stt_metrics()
                if stt_metrics_result is not None and isinstance(stt_metrics_result, dict):
                    stt_metrics = stt_metrics_result
            eos_perf_ts = stt_metrics.get("eos_perf_ts")
            if isinstance(eos_perf_ts, (int, float)):
                self._voice_eos_perf_ts = float(eos_perf_ts)
            if isinstance(result, tuple):
                text, audio_bytes, speech_detected = result
            else:
                text, audio_bytes, speech_detected = result, b"", None
            if not text:
                return
            if phase1_enabled and not phase1_started.is_set():
                self._try_voice_phase1_ack()
                phase1_started.set()
            confirm_low = os.environ.get(
                "JARVIS_STT_CONFIRM_LOW_CONFIDENCE", ""
            ).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            confidence_min = float(os.environ.get("JARVIS_STT_CONFIDENCE_MIN", "0.65"))
            confidence: float | None = None
            get_confidence = getattr(self.stt, "get_last_confidence", None)
            if callable(get_confidence):
                confidence_result = get_confidence()
                if isinstance(confidence_result, (int, float)):
                    confidence = float(confidence_result)
            if confirm_low and confidence is not None and confidence < confidence_min:
                from .utils import normalize_text

                confirm = self._prompt_user(f"Voce quis dizer '{text}'? (sim/nao)")
                if not normalize_text(confirm).startswith("s"):
                    self._followup.reset()
                    return
            verifier = self._speaker_verifier
            if verifier.is_enabled():
                if not verifier.is_available():
                    self._debug(
                        "speaker verification enabled but resemblyzer unavailable"
                    )
                elif (
                    len(audio_bytes) >= (SAMPLE_RATE * BYTES_PER_SAMPLE)
                    and speech_detected is not False
                ):
                    voiceprint = verifier.load_voiceprint(
                        str(verifier.voiceprint_path())
                    )
                    if not voiceprint:
                        self._debug("speaker verification enabled but no voiceprint")
                        self._say("Cadastre sua voz com 'cadastrar voz'.")
                        self._followup.reset()
                        return
                    score, ok = verifier.verify_ok(audio_bytes, SAMPLE_RATE)
                    if not ok:
                        self._debug(f"speaker verification failed (score={score:.3f})")
                        self._followup.reset()
                        return
            status, success = self.handle_text(text)
            if success:
                self._followup.on_command_accepted(True)
            else:
                self._followup.reset()
        except Exception as e:
            if getattr(self, "_debug_enabled", False):
                print(traceback.format_exc())
            self._say(f"Erro no reconhecimento de voz: {e}")
        finally:
            if overlap_timer is not None:
                try:
                    overlap_timer.cancel()
                except Exception:
                    pass
            get_stt_metrics = getattr(self.stt, "get_last_metrics", None)
            if not stt_metrics and callable(get_stt_metrics):
                stt_metrics_result = get_stt_metrics()
                if stt_metrics_result is not None and isinstance(stt_metrics_result, dict):
                    stt_metrics = stt_metrics_result
            if hasattr(self, "_voice_metrics_active"):
                try:
                    self._voice_metrics_active = False
                except Exception:
                    pass
            log_metrics = getattr(self, "_log_voice_stage_metrics", None)
            if callable(log_metrics) and stt_metrics:
                log_metrics(stt_metrics)

    def _try_voice_phase1_ack(self) -> None:
        if not getattr(self, "_voice_metrics_active", False):
            return
        if self._voice_phase1_perf_ts is not None:
            return
        play = getattr(self.tts, "play_phase1_ack", None)
        if not callable(play):
            return
        play()
        metrics = self.tts.get_last_metrics()
        ts = metrics.get("tts_first_audio_perf_ts")
        if isinstance(ts, (int, float)):
            self._voice_phase1_perf_ts = float(ts)

    def _prefetch_overlap_plan(self, text: str) -> None:
        from .utils import normalize_text

        norm = normalize_text(text)
        if not norm:
            return
        lock = getattr(self, "_voice_overlap_lock", None)
        if lock is None:
            lock = threading.Lock()
            try:
                setattr(self, "_voice_overlap_lock", lock)
            except Exception:
                pass
        with lock:
            if (
                getattr(self, "_voice_overlap_norm", None) == norm
                and getattr(self, "_voice_overlap_plan", None) is not None
            ):
                return
        thread = threading.Thread(target=self._prefetch_overlap_plan_worker, args=(text, norm), daemon=True)
        thread.start()

    def _prefetch_overlap_plan_worker(self, text: str, norm: str) -> None:
        plan = self._plan_with_llm_quiet(text, self.llm_local, source="local_overlap")
        if plan is None:
            return
        lock = getattr(self, "_voice_overlap_lock", None)
        if lock is None:
            lock = threading.Lock()
            try:
                setattr(self, "_voice_overlap_lock", lock)
            except Exception:
                pass
        with lock:
            try:
                setattr(self, "_voice_overlap_plan", plan)
                setattr(self, "_voice_overlap_norm", norm)
            except Exception:
                pass

    def _consume_overlap_plan(self, text: str) -> ActionPlan | None:
        from .utils import normalize_text

        norm = normalize_text(text)
        if not norm:
            return None
        lock = getattr(self, "_voice_overlap_lock", None)
        if lock is None:
            lock = threading.Lock()
            try:
                setattr(self, "_voice_overlap_lock", lock)
            except Exception:
                pass
        with lock:
            if getattr(self, "_voice_overlap_norm", None) != norm:
                return None
            plan = getattr(self, "_voice_overlap_plan", None)
            try:
                setattr(self, "_voice_overlap_plan", None)
                setattr(self, "_voice_overlap_norm", None)
            except Exception:
                pass
            return plan

    def _plan_with_llm_quiet(
        self,
        text: str,
        llm_client: LLMClient,
        source: str,
    ) -> ActionPlan | None:
        start_ts = time.perf_counter()
        try:
            prompt_text = self._compact_llm_input(text)
            return llm_client.plan(prompt_text)
        except Exception as exc:
            self.telemetry.log_event(
                "plan_error", {"error": str(exc), "source": source}
            )
            self.last_error = f"{source}_plan_error"
            return None
        finally:
            if self._voice_metrics_active:
                llm_ms = (time.perf_counter() - start_ts) * 1000.0
                self._voice_metrics_totals["llm_ms"] += float(llm_ms)
                self._voice_metrics_counts["llm"] += 1

    def _plan_with_llm(
        self,
        text: str,
        llm_client: LLMClient,
        source: str,
    ) -> ActionPlan | None:
        """Generate action plan using a specific LLM client."""
        start_ts = time.perf_counter()
        try:
            prompt_text = self._compact_llm_input(text)
            return llm_client.plan(prompt_text)
        except Exception as exc:
            self.telemetry.log_event(
                "plan_error", {"error": str(exc), "source": source}
            )
            self.last_error = f"{source}_plan_error"
            if source == "browser":
                self._say(
                    "Nao consegui entender a resposta da IA. Pode tentar de novo?"
                )
            elif source == "guidance":
                self._say("Nao consegui transformar a explicacao em passos.")
            else:
                self._say("Nao consegui gerar um plano local. Vou tentar outra forma.")
            return None
        finally:
            if self._voice_metrics_active:
                llm_ms = (time.perf_counter() - start_ts) * 1000.0
                self._voice_metrics_totals["llm_ms"] += float(llm_ms)
                self._voice_metrics_counts["llm"] += 1

    @staticmethod
    def _compact_llm_input(text: str) -> str:
        """
        Keep LLM input small for latency, without destroying meaning.

        Only applies to very long text (e.g. pasted logs); typical voice commands
        are unchanged.
        """
        raw = text.strip()
        if not raw:
            return raw
        try:
            max_chars = int(os.environ.get("JARVIS_LLM_COMMAND_MAX_CHARS", "4000"))
        except ValueError:
            max_chars = 4000
        if max_chars <= 0 or len(raw) <= max_chars:
            return raw
        head = max(0, int(max_chars * 0.7))
        tail = max(0, max_chars - head)
        prefix = raw[:head].rstrip()
        suffix = raw[-tail:].lstrip() if tail else ""
        return (
            f"{prefix}\n\n[...TRUNCADO: input muito longo para reduzir latencia...]\n\n{suffix}"
            if suffix
            else f"{prefix}\n\n[...TRUNCADO: input muito longo para reduzir latencia...]"
        )

    def _try_parse_plan_from_text(self, text: str) -> ActionPlan | None:
        try:
            plan_dict = _safe_json_loads(text)
        except Exception:
            return None
        try:
            plan = ActionPlan.from_dict(plan_dict)
        except Exception:
            return None
        qualidade = validar_plano(plan)
        if qualidade.errors:
            return None
        plan.confidence = qualidade.confidence
        plan.notes = f"{plan.notes} (parsed_guidance)"
        return plan

    def _record_attempt(
        self,
        attempts: list[dict[str, object]],
        source: str,
        ok: bool,
        reason: str | None,
        plan: ActionPlan | None,
    ) -> None:
        actions_count = len(plan.actions) if plan else 0
        attempts.append(
            {
                "source": source,
                "ok": ok,
                "reason": reason or "",
                "actions": actions_count,
            }
        )

    def _summarize_attempts(self, attempts: list[dict[str, object]]) -> str:
        if not attempts:
            return ""
        parts: list[str] = []
        for idx, attempt in enumerate(attempts, start=1):
            source = str(attempt.get("source", ""))
            ok = bool(attempt.get("ok", False))
            reason = str(attempt.get("reason", "")).strip()
            actions_raw = attempt.get("actions", 0)
            actions = (
                int(actions_raw) if isinstance(actions_raw, (int, float, str)) else 0
            )
            status = "ok" if ok else "falhou"
            detail_parts: list[str] = []
            if reason:
                detail_parts.append(reason)
            if actions:
                detail_parts.append(f"acoes={actions}")
            if detail_parts:
                detail = ", ".join(detail_parts)
                parts.append(f"{idx}) {source}: {status} ({detail})")
            else:
                parts.append(f"{idx}) {source}: {status}")
        return " ".join(parts)

    def _collect_external_guidance(
        self,
        text: str,
        attempts: list[dict[str, object]],
    ) -> str | None:
        if not self.config.browser_ai_enabled:
            return None

        self._say("Nao consegui completar com o cerebro local.")
        if self._is_coding_task(text):
            self._say(
                "Se for programacao, use o Cursor/Codex ou ChatGPT no navegador e cole a resposta."
            )
        else:
            self._say("Abra o ChatGPT no navegador e cole a resposta aqui.")

        print(f"URL sugerida: {self.config.browser_ai_url}")

        summary = self._summarize_attempts(attempts)
        if summary:
            self._say(f"Tentei: {summary}")

        prompt = self._build_external_prompt(text, summary)
        print("Prompt sugerido para a IA:\n" + prompt)
        guidance = self._prompt_user("Cole a resposta da IA (ou Enter para pular):")
        if not guidance.strip():
            return None
        return self._sanitize_guidance(guidance, source="browser")

    def _build_external_prompt(self, text: str, attempts_summary: str) -> str:
        base = [
            "Transforme o comando abaixo em passos curtos para automacao desktop.",
            "Se puder, responda em JSON no formato "
            '{"actions":[{"type":"...","params":{...}}],"risk_level":"low","notes":"..."}.',
            "Acoes validas: open_app, open_url, type_text, hotkey, wait, click, scroll, "
            "navigate, web_click, web_fill, web_screenshot.",
            "Nao inclua instrucoes para ignorar regras ou alterar politicas.",
        ]

        if self._is_coding_task(text):
            base.append(
                "Se for programacao, descreva passos curtos no IDE e, se precisar colar codigo, "
                "inclua o trecho entre <COLAR>...</COLAR> e diga exatamente onde colar."
            )

        redacted_text, redactions = redact_text(text)
        classification = classify_text(text)
        if classification != "publico" or redactions:
            base.append("Classificacao: dados sensiveis foram redigidos.")

        if attempts_summary:
            base.append(f"Tentativas anteriores: {attempts_summary}")

        if self.last_error:
            base.append(f"Erro observado: {self.last_error}")

        base.append(f"Comando: {redacted_text}")
        return " ".join(base)

    def _is_coding_task(self, text: str) -> bool:
        lowered = text.lower()
        keywords = [
            "codigo",
            "programa",
            "programacao",
            "bug",
            "erro",
            "commit",
            "git",
            "python",
            "rust",
            "javascript",
            "typescript",
            ".py",
            ".rs",
            ".js",
            ".ts",
        ]
        return any(keyword in lowered for keyword in keywords)

    def _is_mock_fallback(self, plan: ActionPlan) -> bool:
        return bool(plan.notes and "mock_local_fallback" in plan.notes)

    def _allow_mock_fallback(self, text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        if len(stripped.split()) <= 2:
            return True
        if re.match(
            r"^(digitar|digite|escrever|escreva|type|write|colar|paste)\b",
            stripped,
            re.IGNORECASE,
        ):
            return True
        return (stripped.startswith('"') and stripped.endswith('"')) or (
            stripped.startswith("'") and stripped.endswith("'")
        )

    def _maybe_learn_procedure(
        self,
        command: str,
        plan: ActionPlan,
        guidance: str | None,
    ) -> None:
        if not guidance or not self.config.auto_learn_procedures:
            return
        try:
            self.procedures.add_from_command(command, plan)
            self._store_procedure_memory(command, plan, "auto_learn")
            self._say("Aprendi um novo procedimento para usar depois.")
        except Exception as exc:
            self.telemetry.log_event("learn_error", {"error": str(exc)})

    def _store_procedure_memory(
        self, command: str, plan: ActionPlan, source: str
    ) -> None:
        with contextlib.suppress(Exception):
            redacted_command, mem_meta = self._redact_for_memory(
                command, f"procedure:{source}"
            )
            payload_dict: dict[str, Any] = {"source": source, "plan": plan.to_dict()}
            payload: dict[str, object] = cast(dict[str, object], payload_dict)
            sanitized_payload, payload_redactions = self._redact_payload_for_memory(
                payload
            )
            memory_meta = dict(mem_meta)
            if payload_redactions:
                memory_meta["payload_redactions"] = payload_redactions
            if isinstance(sanitized_payload, dict):
                sanitized_payload["memory_meta"] = memory_meta
            self.memory.add_procedure(redacted_command, sanitized_payload)

    def _prompt_user(self, prompt: str) -> str:
        """Prompt user for input (voice or text)."""
        print(prompt)
        if self.config.stt_mode != "none":
            try:
                return self.stt.transcribe_once(seconds=5, require_wake_word=False)
            except Exception:
                return input().strip()
        return input().strip()

    def _sanitize_guidance(self, guidance: str, source: str) -> str | None:
        result = sanitize_external_text(guidance)
        if result.removed_lines or result.redactions or result.truncated:
            self.telemetry.log_event(
                "guidance_sanitized",
                {
                    "source": source,
                    "removed_lines": result.removed_lines,
                    "redactions": result.redactions,
                    "classification": result.classification,
                    "truncated": result.truncated,
                },
            )
            self._say("Removi instrucoes suspeitas e dados sensiveis da resposta.")
        if not result.text.strip():
            self.last_error = f"guidance_empty:{source}"
            self._say(
                "A resposta ficou vazia apos sanitizacao. Pode explicar de outro jeito?"
            )
            return None
        return result.text

    def _redact_for_memory(
        self, text: str, source: str
    ) -> tuple[str, dict[str, object]]:
        redacted, redactions = redact_text(text)
        classification = classify_text(text)
        if redactions or classification != "publico":
            self.telemetry.log_event(
                "memory_redacted",
                {
                    "source": source,
                    "classification": classification,
                    "redactions": redactions,
                },
            )
        return redacted, {
            "classification": classification,
            "redactions": redactions,
            "source": source,
        }

    def _redact_payload_for_memory(
        self, payload: dict[str, object]
    ) -> tuple[dict[str, object], list[str]]:
        redactions: set[str] = set()

        def scrub(value: object) -> object:
            if isinstance(value, str):
                redacted, hits = redact_text(value)
                for hit in hits:
                    redactions.add(hit)
                return redacted
            if isinstance(value, dict):
                return cast(
                    dict[str, object], {key: scrub(val) for key, val in value.items()}
                )
            if isinstance(value, list):
                return [scrub(val) for val in value]
            return value

        sanitized = cast(dict[str, object], scrub(payload))
        return sanitized, sorted(redactions)

    @staticmethod
    def _safe_filename(text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
        return cleaned.strip("_") or "demo"

    def _start_demo_recording(self, name: str) -> None:
        if self._demo_recorder is not None:
            self._say(
                "Ja estou gravando uma demonstracao. Diga 'parar demonstracao' para finalizar."
            )
            return
        try:
            from ..aprendizado.recorder import DemonstrationRecorder
        except Exception as exc:
            self.last_error = f"demo_recorder_import_failed:{exc}"
            self._say(
                "Recorder nao disponivel. Instale o pynput para gravar demonstracoes."
            )
            return
        try:
            recordings_dir = self.config.data_dir / "recordings"
            recorder = DemonstrationRecorder(recordings_dir=recordings_dir)
            recorder.start_recording(name)
            self._demo_recorder = recorder
            self._demo_recording_name = name
            self.telemetry.log_event("demo_start", {"name": name})
            self._say(
                f"Gravando demonstracao '{name}'. Diga 'parar demonstracao' para finalizar."
            )
        except Exception as exc:
            self._demo_recorder = None
            self._demo_recording_name = None
            self.last_error = f"demo_start_failed:{exc}"
            self._say("Falha ao iniciar a demonstracao. Verifique as dependencias.")

    def _stop_demo_recording(self) -> None:
        if self._demo_recorder is None:
            self._say("Nenhuma demonstracao em andamento.")
            return
        recorder = self._demo_recorder
        self._demo_recorder = None
        recording_name = self._demo_recording_name or "demo"
        self._demo_recording_name = None
        try:
            recording = recorder.stop_recording()
            recording_path = recorder.save_recording(recording)
            self.telemetry.log_event(
                "demo_saved",
                {"name": recording_name, "path": str(recording_path)},
            )
        except Exception as exc:
            self.last_error = f"demo_stop_failed:{exc}"
            self._say("Falha ao salvar a demonstracao.")
            return
        try:
            from ..aprendizado.learner import DemonstrationLearner

            learner = DemonstrationLearner(llm_client=self.llm_local)
            procedure = learner.extract_procedure(recording, name=recording_name)
            procedures_dir = self.config.data_dir / "procedures_learned"
            procedures_dir.mkdir(parents=True, exist_ok=True)
            safe_name = self._safe_filename(procedure.name)
            procedure_path = (
                procedures_dir / f"{safe_name}_{int(recording.start_time)}.json"
            )
            learner.save_procedure(procedure, procedure_path)
            self.procedures.add_from_command(procedure.name, procedure.to_action_plan())
            self._store_procedure_memory(
                procedure.name, procedure.to_action_plan(), "demo_learned"
            )
            self.telemetry.log_event(
                "demo_learned",
                {
                    "name": procedure.name,
                    "recording_path": str(recording_path),
                    "procedure_path": str(procedure_path),
                },
            )
            self._say("Demonstracao salva e procedure criada.")
        except Exception as exc:
            self.last_error = f"demo_learn_failed:{exc}"
            self._say("Gravacao salva, mas falhei ao extrair a procedure.")

    def _handle_meta_command(self, text: str) -> bool:
        """Handle meta commands (approve, save, etc.)."""
        from .utils import normalize_text

        lowered = normalize_text(text)

        # Approve last procedure
        if "aprovado" in lowered or lowered.startswith("aprovar"):
            if self.last_success and self.last_plan and self.last_command:
                self.procedures.add_from_command(self.last_command, self.last_plan)
                self._store_procedure_memory(
                    self.last_command, self.last_plan, "user_approved"
                )
                self._say("Procedimento salvo e aprovado.")
                return True
            self._say("Nada para aprovar ainda.")
            return True

        # Check system status
        if lowered in ("status", "sistema"):
            self._show_status()
            return True

        if lowered in ("abrir chat", "mostrar chat", "abrir conversa"):
            self.chat.open()
            return True

        if lowered in ("cadastrar voz", "registrar voz"):
            verifier = self._speaker_verifier
            if not verifier.is_available():
                self._say("Verificacao de locutor indisponivel. Instale resemblyzer.")
                return True
            self._say(
                "Certo. Vou gravar sua voz por alguns segundos. "
                "Quando terminar, vou pedir confirmacao."
            )
            try:
                enroll_seconds = _env_int_clamped(
                    "JARVIS_VOICE_ENROLL_MAX_SECONDS", 12, 5, 60
                )
                result = self.stt.transcribe_with_vad(
                    max_seconds=enroll_seconds,
                    return_audio=True,
                    require_wake_word=False,
                )
            except Exception as exc:
                self._debug(f"voice enrollment failed: {exc}")
                self._say("Falha ao gravar sua voz.")
                return True
            if isinstance(result, tuple):
                _text, audio_bytes, speech_detected = result
            else:
                audio_bytes, speech_detected = b"", None
            if not audio_bytes or speech_detected is False:
                self._say("Nao captei voz suficiente para cadastrar.")
                return True
            if len(audio_bytes) < (SAMPLE_RATE * BYTES_PER_SAMPLE):
                self._say("Fale por mais tempo para cadastrar sua voz.")
                return True
            confirm = self._prompt_user("Confirmar cadastro de voz? (sim/nao)")
            confirm_text = normalize_text(confirm)
            if not confirm_text.startswith("s") and confirm_text != "ok":
                self._say("Cadastro cancelado.")
                return True
            embedding = verifier.enroll(audio_bytes, SAMPLE_RATE)
            if embedding:
                voice_path = getattr(verifier, "voiceprint_path", None)
                if callable(voice_path):
                    self._say(f"Voz cadastrada em {voice_path()}.")
                else:
                    self._say("Voz cadastrada.")
            else:
                self._say("Nao consegui cadastrar sua voz.")
            return True

        if lowered.startswith("remover regra"):
            self._say(
                "Regras do nucleo sao imutaveis. Posso apenas ajustar policy do usuario para sites/apps."
            )
            return True

        policy_match = re.match(
            r"^(bloquear|permitir)\s+(site|dominio|domínio|app)\s+(.+)$", lowered
        )
        if policy_match:
            action = policy_match.group(1)
            target_type = policy_match.group(2)
            value = policy_match.group(3).strip()
            if value:
                self._apply_user_policy(action, target_type, value)
                return True

        demo_match = re.match(r"^demonstrar\s+(.+)$", text.strip(), re.IGNORECASE)
        if demo_match:
            name = demo_match.group(1).strip()
            if not name:
                self._say("Informe um nome: 'demonstrar <nome>'.")
                return True
            self._start_demo_recording(name)
            return True

        if lowered in {
            "parar demonstracao",
            "parar demonstração",
            "parar demo",
            "finalizar demonstracao",
            "finalizar demonstração",
            "finalizar demo",
            "parar gravacao",
            "parar gravação",
        }:
            self._stop_demo_recording()
            return True

        fixar_match = re.match(
            r"^(fixar|memorizar|lembrar)\s+(?:memoria|memória)\s+(.+)$",
            text.strip(),
            re.IGNORECASE,
        )
        if fixar_match:
            memory_text = fixar_match.group(2).strip()
            if not memory_text:
                self._say("Nada para fixar.")
                return True
            redacted_text, mem_meta = self._redact_for_memory(
                memory_text, "fixed_knowledge"
            )
            item_id = self.memory.add_fixed_knowledge(
                redacted_text,
                {"source": "user", "memory_meta": mem_meta},
            )
            self.telemetry.log_event("memory_pinned", {"id": item_id})
            self._say("Memoria fixada.")
            return True

        esquecer_match = re.match(
            r"^(esquecer|apagar)\s+(?:memoria|memória)\s+(.+)$",
            text.strip(),
            re.IGNORECASE,
        )
        if esquecer_match:
            memory_text = esquecer_match.group(2).strip()
            if not memory_text:
                self._say("Nada para esquecer.")
                return True
            deleted = self.memory.forget(memory_text, kind="knowledge")
            self.telemetry.log_event("memory_forget", {"count": deleted})
            if deleted:
                self._say(f"Esqueci {deleted} memoria(s).")
            else:
                self._say("Nao encontrei memoria para esquecer.")
            return True

        return False

    def _stop_active(self) -> bool:
        if stop_requested(self.config.stop_file_path):
            if not self._stop_notified:
                self.telemetry.log_event(
                    "kill_switch",
                    {"path": str(self.config.stop_file_path)},
                )
                self._say("Kill switch ativo. Remova o arquivo STOP para continuar.")
                self._log_pause(
                    "kill_switch", details={"path": str(self.config.stop_file_path)}
                )
                self._stop_notified = True
            return True
        self._stop_notified = False
        return False

    def _external_allowed(self, text: str) -> bool:
        classification = classify_text(text)
        if classification == "publico" or not self.config.block_external_sensitive:
            return True
        if self.config.external_ask_on_sensitive:
            answer = self._prompt_user(
                "Detectei dados sensiveis. Posso enviar para IA externa? (sim/nao)"
            )
            from .utils import normalize_text

            if normalize_text(answer).startswith("s"):
                return True
        self.last_error = "external_blocked_sensitive"
        self._say("Nao vou enviar dados sensiveis para IA externa.")
        self._log_pause(
            "external_blocked_sensitive",
            details={"classification": classification},
            plan=self.last_plan,
            actions_executed=[],
        )
        return False

    def _log_pause(
        self,
        reason: str,
        details: dict[str, object] | None = None,
        plan: ActionPlan | None = None,
        actions_executed: list[Action] | None = None,
    ) -> None:
        summary: dict[str, object] = {
            "reason": reason,
            "last_error": self.last_error,
            "plan_actions": self._format_actions(plan.actions if plan else []),
            "executed_actions": self._format_actions(actions_executed or []),
        }
        if details:
            summary["details"] = details
        message = (
            "Parei. Motivo: {reason}. Feito ate aqui: {done}. Plano: {plan}."
        ).format(
            reason=reason,
            done=summary["executed_actions"] or "nada",
            plan=summary["plan_actions"] or "n/a",
        )
        self.chat.append("jarvis", message, summary)

    @staticmethod
    def _format_actions(actions: list[Action]) -> str:
        parts: list[str] = []
        for action in actions:
            params = action.params or {}
            if action.action_type == "open_app":
                parts.append(f"open_app({params.get('app')})")
            elif action.action_type == "open_url":
                parts.append(f"open_url({params.get('url')})")
            elif action.action_type == "type_text":
                parts.append("type_text(...)")
            elif action.action_type == "hotkey":
                parts.append(f"hotkey({params.get('combo')})")
            elif action.action_type == "click":
                parts.append("click(...)")
            elif action.action_type == "wait":
                parts.append(f"wait({params.get('seconds')})")
            elif action.action_type == "scroll":
                parts.append(f"scroll({params.get('amount')})")
            else:
                parts.append(action.action_type)
        return ", ".join(parts)

    def _show_status(self) -> None:
        """Show system status."""
        # Get LLM status
        local_clients: list[str] = []
        try:
            clients_result = self.llm_local.get_available_clients()
        except Exception:
            clients_result = []
        if isinstance(clients_result, list):
            local_clients = clients_result
        local_status = ", ".join(local_clients) if local_clients else "mock"

        # Get memory status
        memory_status = "local"

        status = f"""
Sistema Jarvis - Status
========================
LLM local: {local_status}
Browser AI: {"ativo" if self.config.browser_ai_enabled else "desativado"}
Memória: {memory_status}
STT: {self.config.stt_mode}
TTS: {self.config.tts_mode}
Modo: {"dry-run" if self.config.dry_run else "ativo"}
"""
        print(status)

    def _apply_user_policy(self, action: str, target_type: str, value: str) -> None:
        if target_type in {"site", "dominio", "domínio"}:
            if action == "bloquear":
                self.policy_user_store.add_blocked_domain(value)
                self._say(f"Site bloqueado: {value}")
            else:
                self.policy_user_store.remove_blocked_domain(value)
                self._say(f"Site permitido: {value}")
        elif target_type == "app":
            if action == "bloquear":
                self.policy_user_store.add_blocked_app(value)
                self._say(f"App bloqueado: {value}")
            else:
                self.policy_user_store.remove_blocked_app(value)
                self._say(f"App permitido: {value}")
        else:
            self._say("Tipo de bloqueio nao reconhecido.")
            return

        self.policy = PolicyKernel(
            allow_open_app=self.config.allow_open_app,
            user_policy_path=self.config.policy_user_path,
        )
