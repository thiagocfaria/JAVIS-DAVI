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
import re
import time
import uuid
from typing import Callable

from ..comunicacao.chat_log import ChatLog
from ..entrada.stt import SpeechToText
from ..memoria.memory import (
    HybridMemoryStore,
    LocalMemoryCache,
    build_memory_store,
)
from ..memoria.procedures import ProcedureStore
from ..seguranca.kill_switch import stop_requested
from ..seguranca.policy import PolicyKernel
from ..seguranca.policy_usuario import PolicyUsuarioStore
from ..seguranca.sanitizacao import (
    classify_text,
    redact_text,
    sanitize_external_text,
)
from ..telemetria.telemetry import Telemetry
from ..validacao.plano import validar_plano
from ..validacao.validator import Validator
from ..voz.tts import TextToSpeech
from .actions import Action, ActionPlan
from .config import Config
from .llm import BudgetedLLMClient, LLMClient, _safe_json_loads, build_local_llm_client
from .orcamento import OrcamentoDiario

# Try to import new automation module
try:
    from ..acoes import AutomationRouter

    HAS_NEW_AUTOMATION = True
except ImportError:
    HAS_NEW_AUTOMATION = False
    try:
        from ..acoes.legacy import AutomationDriver
    except ImportError:
        AutomationDriver = None


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
            self.executor = AutomationRouter(
                session_type=config.session_type,
                enable_web=True,
            )
        elif AutomationDriver:
            self.executor = LegacyAutomationWrapper(AutomationDriver(config.session_type))
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
        self._demo_recorder = None
        self._demo_recording_name: str | None = None

    def handle_text(self, text: str) -> None:
        """Handle a text command."""
        if not text.strip():
            return

        if self._stop_active():
            return

        command_id = uuid.uuid4().hex
        command_start_ts = time.time()

        def _log_command_event(event_type: str, extra: dict[str, object] | None = None) -> None:
            payload: dict[str, object] = {
                "command_id": command_id,
                "text": text,
                "timestamp": command_start_ts,
            }
            if extra:
                payload.update(extra)
            self.telemetry.log_event(event_type, payload)

        def _log_command_end(status: str, duration: float, error: str | None = None) -> None:
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

        try:
            status, success = self._process_command_flow(text, _log_command_event)
        except Exception as exc:
            self.last_error = str(exc)
            raise
        finally:
            duration = time.time() - command_start_ts
            final_status = "success" if success else status
            _log_command_end(final_status, duration, self.last_error)

    def run_s3_loop(self, instruction: str) -> bool:
        """Run Agent-S S3 loop for a GUI task."""
        if not instruction.strip():
            return False
        from ..agent_s3.runner import S3Runner, build_s3_agent
        import platform as _platform

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
            return self.config.max_failures_per_command > 0 and failures >= self.config.max_failures_per_command

        failures = 0
        attempts: list[dict[str, object]] = []

        def try_plan(
            plan: ActionPlan,
            source: str,
            guidance: str | None = None,
            count_failure: bool = True,
        ) -> bool:
            nonlocal failures, command_status, command_success
            plan = self._validate_plan(plan, source)
            if plan is None:
                self._record_attempt(attempts, source, False, self.last_error, None)
                if count_failure:
                    failures += 1
                log_event("plan.invalid", {"source": source})
                return False

            log_event(
                "plan.validated",
                {
                    "source": source,
                    "actions": len(plan.actions),
                    "risk_level": plan.risk_level,
                },
            )
            self.telemetry.log_event("plan", plan.to_dict())
            plan_start = time.perf_counter()
            executed = self._run_plan(plan)
            plan_duration = time.perf_counter() - plan_start
            log_event(
                "plan.executed",
                {
                    "source": source,
                    "success": executed,
                    "duration": plan_duration,
                    "actions": len(plan.actions),
                    "risk_level": plan.risk_level,
                },
            )
            if not executed:
                self._record_attempt(attempts, source, False, self.last_error, plan)
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

        procedure_match = self.procedures.match(text)
        if procedure_match:
            plan, _values = procedure_match
            self.telemetry.log_event("plan_source", {"source": "procedure"})
            if try_plan(plan, "procedure", count_failure=False):
                return command_status, command_success
            self.telemetry.log_event("procedure_failed", {"command": text})

        plan = self._plan_with_llm(text, self.llm_local, source="local")
        if plan is None:
            self._record_attempt(attempts, "local", False, self.last_error, None)
        if plan and self._is_mock_fallback(plan) and not self._allow_mock_fallback(text):
            self.telemetry.log_event("local_fallback_skip", {"reason": "mock_fallback"})
            self.last_error = "mock_fallback_skipped"
            self._record_attempt(attempts, "local", False, self.last_error, plan)
            plan = None
        if plan:
            self.telemetry.log_event("plan_source", {"source": "local"})
            if try_plan(plan, "local", count_failure=False):
                return command_status, command_success

        external_allowed = (
            self._external_allowed(text) if self.config.browser_ai_enabled else False
        )
        guidance = self._collect_external_guidance(text, attempts) if external_allowed else None
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

        self._handle_guidance_loop(text, try_plan, planner=self.llm_local, attempts=attempts)
        return command_status, command_success

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
            self._say("Esta ação requer intervenção humana. Por favor, complete manualmente.")
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

        if self.config.require_approval or decision.requires_confirmation:
            approved = self._request_approval()
            if not approved:
                self.last_error = "approval_denied"
                self._say("Aprovação negada.")
                self.telemetry.log_event("approval_denied", {})
                self._log_pause("approval_denied", plan=plan, actions_executed=[])
                return False

        return self._execute_plan(plan)

    def _record_success(self, text: str, plan: ActionPlan, guidance: str | None = None) -> None:
        self.last_plan = plan
        self.last_command = text
        self.last_success = True
        self.last_error = None
        payload = {"plan": plan.to_dict()}
        if guidance:
            payload["guidance"] = guidance
        with contextlib.suppress(Exception):
            redacted_text, mem_meta = self._redact_for_memory(text, "episode")
            sanitized_payload, payload_redactions = self._redact_payload_for_memory(payload)
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
                spoken = self.stt.transcribe_once(seconds=3)
                if voice_phrase:
                    spoken_ok = normalize_text(spoken) == normalize_text(voice_phrase)
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
        self.tts.speak(text)

    def transcribe_and_handle(self) -> None:
        """Capture voice and handle as command."""
        try:
            # Use VAD if available
            text = self.stt.transcribe_once(seconds=5)
            self.handle_text(text)
        except Exception as e:
            self._say(f"Erro no reconhecimento de voz: {e}")

    def _plan_with_llm(
        self,
        text: str,
        llm_client: LLMClient,
        source: str,
    ) -> ActionPlan | None:
        """Generate action plan using a specific LLM client."""
        try:
            prompt_text = text
            return llm_client.plan(prompt_text)
        except Exception as exc:
            self.telemetry.log_event("plan_error", {"error": str(exc), "source": source})
            self.last_error = f"{source}_plan_error"
            if source == "browser":
                self._say("Nao consegui entender a resposta da IA. Pode tentar de novo?")
            elif source == "guidance":
                self._say("Nao consegui transformar a explicacao em passos.")
            else:
                self._say("Nao consegui gerar um plano local. Vou tentar outra forma.")
            return None

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
            actions = int(actions_raw) if isinstance(actions_raw, (int, float, str)) else 0
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
            r"^(digitar|digite|escrever|escreva|type|write|colar|paste)\b", stripped, re.IGNORECASE
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

    def _store_procedure_memory(self, command: str, plan: ActionPlan, source: str) -> None:
        with contextlib.suppress(Exception):
            redacted_command, mem_meta = self._redact_for_memory(command, f"procedure:{source}")
            payload = {"source": source, "plan": plan.to_dict()}
            sanitized_payload, payload_redactions = self._redact_payload_for_memory(payload)
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
                return self.stt.transcribe_once(seconds=5)
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
            self._say("A resposta ficou vazia apos sanitizacao. Pode explicar de outro jeito?")
            return None
        return result.text

    def _redact_for_memory(self, text: str, source: str) -> tuple[str, dict[str, object]]:
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
                return {key: scrub(val) for key, val in value.items()}
            if isinstance(value, list):
                return [scrub(val) for val in value]
            return value

        sanitized = scrub(payload)
        return sanitized, sorted(redactions)

    @staticmethod
    def _safe_filename(text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
        return cleaned.strip("_") or "demo"

    def _start_demo_recording(self, name: str) -> None:
        if self._demo_recorder is not None:
            self._say("Ja estou gravando uma demonstracao. Diga 'parar demonstracao' para finalizar.")
            return
        try:
            from ..aprendizado.recorder import DemonstrationRecorder
        except Exception as exc:
            self.last_error = f"demo_recorder_import_failed:{exc}"
            self._say("Recorder nao disponivel. Instale o pynput para gravar demonstracoes.")
            return
        try:
            recordings_dir = self.config.data_dir / "recordings"
            self._demo_recorder = DemonstrationRecorder(recordings_dir=recordings_dir)
            self._demo_recorder.start_recording(name)
            self._demo_recording_name = name
            self.telemetry.log_event("demo_start", {"name": name})
            self._say(f"Gravando demonstracao '{name}'. Diga 'parar demonstracao' para finalizar.")
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
            procedure_path = procedures_dir / f"{safe_name}_{int(recording.start_time)}.json"
            learner.save_procedure(procedure, procedure_path)
            self.procedures.add_from_command(procedure.name, procedure.to_action_plan())
            self._store_procedure_memory(procedure.name, procedure.to_action_plan(), "demo_learned")
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
                self._store_procedure_memory(self.last_command, self.last_plan, "user_approved")
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
            r"^(fixar|memorizar|lembrar)\s+(?:memoria|memória)\s+(.+)$", text.strip(), re.IGNORECASE
        )
        if fixar_match:
            memory_text = fixar_match.group(2).strip()
            if not memory_text:
                self._say("Nada para fixar.")
                return True
            redacted_text, mem_meta = self._redact_for_memory(memory_text, "fixed_knowledge")
            item_id = self.memory.add_fixed_knowledge(
                redacted_text,
                {"source": "user", "memory_meta": mem_meta},
            )
            self.telemetry.log_event("memory_pinned", {"id": item_id})
            self._say("Memoria fixada.")
            return True

        esquecer_match = re.match(
            r"^(esquecer|apagar)\s+(?:memoria|memória)\s+(.+)$", text.strip(), re.IGNORECASE
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
                self._log_pause("kill_switch", details={"path": str(self.config.stop_file_path)})
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
        message = ("Parei. Motivo: {reason}. Feito ate aqui: {done}. Plano: {plan}.").format(
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
        local_clients = []
        if hasattr(self.llm_local, "get_available_clients"):
            local_clients = self.llm_local.get_available_clients()
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
