from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from ..acoes.desktop import DesktopAutomation
from ..acoes.web import check_playwright_deps
from ..aprendizado.recorder import check_recorder_deps
from ..cerebro.config import Config
from ..entrada.shortcut import check_shortcut_deps
from ..entrada.stt import check_stt_deps
from ..validacao.validator import check_validator_deps
from ..voz.tts import check_tts_deps


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str  # OK | WARN | FAIL
    detail: str
    hint: str = ""


@dataclass(frozen=True)
class PreflightReport:
    checks: list[CheckResult]

    @property
    def has_failures(self) -> bool:
        return any(check.status == "FAIL" for check in self.checks)

    @property
    def counts(self) -> dict:
        return {
            "ok": sum(1 for c in self.checks if c.status == "OK"),
            "warn": sum(1 for c in self.checks if c.status == "WARN"),
            "fail": sum(1 for c in self.checks if c.status == "FAIL"),
        }


def run_preflight(config: Config) -> PreflightReport:
    checks: list[CheckResult] = []

    # Python version
    ver = sys.version_info
    if ver < (3, 10):
        checks.append(
            CheckResult(
                name="Python",
                status="FAIL",
                detail=f"{ver.major}.{ver.minor} detectado (minimo 3.10)",
                hint="Instale Python 3.11+.",
            )
        )
    elif ver < (3, 11):
        checks.append(
            CheckResult(
                name="Python",
                status="WARN",
                detail=f"{ver.major}.{ver.minor} detectado (recomendado 3.11+)",
                hint="Funciona, mas nao e o alvo principal.",
            )
        )
    else:
        checks.append(CheckResult(name="Python", status="OK", detail="3.11+ detectado"))

    # Data dir writable
    checks.append(_check_data_dir(config.data_dir))
    checks.append(_check_stop_file(config))

    # LLM (local only)
    checks.append(_check_local_llm(config))

    # STT deps
    checks.append(_check_stt(config))

    # TTS deps
    checks.append(_check_tts(config))

    # Desktop automation drivers
    checks.append(_check_desktop_drivers(config))

    # Web automation
    checks.append(_check_web_automation())

    # OCR / validator
    checks.append(_check_validator())

    # Recorder deps (optional)
    checks.append(_check_recorder())

    # Chat UI (optional)
    checks.append(_check_chat_ui())

    # Chat shortcut (optional)
    checks.append(_check_chat_shortcut())

    return PreflightReport(checks=checks)


def format_report(report: PreflightReport) -> str:
    lines = ["Preflight check (estado atual):"]
    for check in report.checks:
        lines.append(f"- [{check.status}] {check.name}: {check.detail}")
        if check.hint:
            lines.append(f"  dica: {check.hint}")
    counts = report.counts
    lines.append(
        f"Resumo: {counts['ok']} OK, {counts['warn']} aviso(s), {counts['fail']} falha(s)"
    )
    return "\n".join(lines)


def _check_data_dir(data_dir: Path) -> CheckResult:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return CheckResult(name="Data dir", status="OK", detail=str(data_dir))
    except Exception as exc:
        return CheckResult(
            name="Data dir",
            status="FAIL",
            detail=f"sem acesso em {data_dir}",
            hint=str(exc),
        )


def _check_stop_file(config: Config) -> CheckResult:
    if config.stop_file_path.exists():
        return CheckResult(
            name="Kill switch",
            status="WARN",
            detail=f"STOP ativo em {config.stop_file_path}",
            hint="Remova o arquivo para liberar a execucao.",
        )
    return CheckResult(
        name="Kill switch",
        status="OK",
        detail="STOP nao encontrado",
    )


def _check_local_llm(config: Config) -> CheckResult:
    if config.local_llm_base_url:
        return CheckResult(
            name="LLM local",
            status="OK",
            detail="servidor local configurado",
        )
    return CheckResult(
        name="LLM local",
        status="WARN",
        detail="nao configurado",
        hint="Defina JARVIS_LOCAL_LLM_BASE_URL para usar o cerebro local.",
    )


def _check_stt(config: Config) -> CheckResult:
    deps = check_stt_deps()
    mode = config.stt_mode

    has_audio = deps.get("sounddevice") and deps.get("numpy")
    has_local = has_audio and deps.get("faster_whisper")

    if mode == "none":
        return CheckResult(
            name="STT",
            status="WARN",
            detail="voz desativada",
            hint="Defina JARVIS_STT_MODE para usar voz.",
        )

    if not has_audio:
        return CheckResult(
            name="STT",
            status="FAIL",
            detail="sem captura de audio (sounddevice/numpy)",
            hint="pip install sounddevice numpy",
        )

    if mode == "local":
        if not has_local:
            return CheckResult(
                name="STT",
                status="FAIL",
                detail="local sem faster-whisper",
                hint="pip install faster-whisper",
            )
        return CheckResult(name="STT", status="OK", detail="local ativo")

    if mode == "auto":
        if has_local:
            return CheckResult(name="STT", status="OK", detail="auto (local)")
        return CheckResult(
            name="STT",
            status="FAIL",
            detail="auto sem local",
            hint="Instale faster-whisper.",
        )

    return CheckResult(name="STT", status="WARN", detail=f"modo desconhecido: {mode}")


def _check_tts(config: Config) -> CheckResult:
    deps = check_tts_deps()
    mode = config.tts_mode

    if mode == "none":
        return CheckResult(
            name="TTS",
            status="WARN",
            detail="voz desativada",
            hint="Defina JARVIS_TTS_MODE=local para voz.",
        )

    has_engine = deps.get("piper") or deps.get("espeak-ng")
    if not has_engine:
        return CheckResult(
            name="TTS",
            status="WARN",
            detail="nenhum engine instalado",
            hint="Instale piper ou espeak-ng.",
        )

    return CheckResult(name="TTS", status="OK", detail="engine local disponivel")


def _check_desktop_drivers(config: Config) -> CheckResult:
    tools = DesktopAutomation(session_type=config.session_type).check_available_tools()
    has_any = tools["xdotool"] or tools["wtype"] or tools["ydotool"] or tools["pyautogui"]
    ydotool_socket = tools.get("ydotool_socket")
    headless = _is_headless_env(tools)

    if not has_any and headless:
        return CheckResult(
            name="Acoes desktop",
            status="WARN",
            detail="ambiente headless (sem drivers)",
            hint="Instale xdotool (X11) ou wtype/ydotool (Wayland) quando for usar GUI.",
        )

    if not has_any:
        return CheckResult(
            name="Acoes desktop",
            status="FAIL",
            detail="nenhum driver de input encontrado",
            hint="Instale xdotool (X11) ou wtype/ydotool (Wayland).",
        )

    if tools["is_wayland"] and tools["ydotool"] and not ydotool_socket:
        return CheckResult(
            name="Acoes desktop",
            status="WARN",
            detail="Wayland: ydotool sem daemon (click/scroll podem falhar)",
            hint="Inicie ydotoold e exporte YDTOOL_SOCKET se necessario.",
        )

    if tools["is_wayland"] and not (tools["wtype"] or tools["ydotool"] or tools["pyautogui"]):
        return CheckResult(
            name="Acoes desktop",
            status="WARN",
            detail="Wayland sem wtype/ydotool",
            hint="Instale wtype ou ydotool.",
        )

    detail = "ok (drivers disponiveis)"
    return CheckResult(name="Acoes desktop", status="OK", detail=detail)


def _is_headless_env(tools: dict) -> bool:
    flag = os.environ.get("JARVIS_HEADLESS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if flag:
        return True

    session_type = str(tools.get("session_type") or "").strip().lower()
    if session_type in {"tty", "headless"}:
        return True

    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if not has_display and session_type in {"", "unknown"}:
        return True

    return False


def _check_web_automation() -> CheckResult:
    deps = check_playwright_deps()
    if not deps.get("playwright_installed"):
        return CheckResult(
            name="Acoes web",
            status="WARN",
            detail="Playwright nao instalado",
            hint="pip install playwright && playwright install chromium",
        )
    if not deps.get("browsers_installed"):
        return CheckResult(
            name="Acoes web",
            status="WARN",
            detail="Playwright sem browsers",
            hint="playwright install chromium",
        )
    return CheckResult(name="Acoes web", status="OK", detail="Playwright pronto")


def _check_validator() -> CheckResult:
    deps = check_validator_deps()
    force_rust = os.environ.get("JARVIS_FORCE_RUST_VISION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if force_rust and not deps.get("rust_vision"):
        return CheckResult(
            name="Validacao (OCR)",
            status="FAIL",
            detail="Rust vision requerido, mas nao instalado",
            hint="Use scripts/build_rust_vision.sh para compilar.",
        )
    if not deps.get("pillow"):
        return CheckResult(
            name="Validacao (OCR)",
            status="WARN",
            detail="Pillow nao instalado",
            hint="pip install Pillow",
        )
    if not deps.get("pytesseract") and not deps.get("rust_vision"):
        return CheckResult(
            name="Validacao (OCR)",
            status="WARN",
            detail="pytesseract nao instalado",
            hint="pip install pytesseract && sudo apt install tesseract-ocr",
        )
    return CheckResult(name="Validacao (OCR)", status="OK", detail="OCR disponivel")


def _check_recorder() -> CheckResult:
    deps = check_recorder_deps()
    if not deps.get("pynput"):
        return CheckResult(
            name="Aprendizado",
            status="WARN",
            detail="pynput nao instalado",
            hint="pip install pynput",
        )
    return CheckResult(name="Aprendizado", status="OK", detail="gravacao disponivel")


def _check_chat_ui() -> CheckResult:
    try:
        import tkinter  # noqa: F401
    except Exception:
        return CheckResult(
            name="Chat UI",
            status="WARN",
            detail="tkinter nao instalado",
            hint="Instale python3-tk para usar o chat UI.",
        )
    return CheckResult(name="Chat UI", status="OK", detail="tkinter disponivel")


def _check_chat_shortcut() -> CheckResult:
    """Check if dependencies for global keyboard shortcut are available."""
    deps = check_shortcut_deps()
    if not deps.get("pynput"):
        return CheckResult(
            name="Atalho chat",
            status="WARN",
            detail="pynput nao instalado (atalho desabilitado)",
            hint="pip install pynput para ativar atalho Ctrl+Shift+J.",
        )
    return CheckResult(
        name="Atalho chat",
        status="OK",
        detail="atalho global disponivel (Ctrl+Shift+J)",
    )
