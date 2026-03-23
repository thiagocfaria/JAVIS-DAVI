from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jarvis.acoes.desktop import DesktopAutomation
from jarvis.acoes.web import check_playwright_deps
from jarvis.aprendizado.recorder import check_recorder_deps
from jarvis.cerebro.config import Config
from .shortcut import check_shortcut_deps
from . import stt as stt_module
from .stt import check_stt_deps
from jarvis.validacao.validator import check_validator_deps
from jarvis.interface.entrada.adapters import vad_silero, wakeword_openwakeword, wakeword_porcupine
from jarvis.interface.saida.tts import TextToSpeech, check_tts_deps


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


def run_preflight(config: Config, profile: str | None = None) -> PreflightReport:
    profiles = _resolve_profiles(profile)
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

    if "voice" in profiles:
        # STT deps
        checks.append(_check_stt(config))

        wake_check = _check_wake_word_audio()
        if wake_check is not None:
            checks.append(wake_check)
        silero_check = _check_silero_deactivity()
        if silero_check is not None:
            checks.append(silero_check)
        audio_calib_check = _check_audio_calibration()
        if audio_calib_check is not None:
            checks.append(audio_calib_check)

        # TTS deps
        checks.append(_check_tts(config))

    if "desktop" in profiles:
        # Desktop automation drivers
        checks.append(_check_desktop_drivers(config))

        # Web automation
        checks.append(_check_web_automation())

        # OCR / validator
        checks.append(_check_validator())

        # Recorder deps (optional)
        checks.append(_check_recorder())

    if "ui" in profiles:
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


def _resolve_profiles(profile: str | None = None) -> set[str]:
    raw = profile
    if raw is None:
        raw = os.environ.get("JARVIS_PREFLIGHT_PROFILE", "")
    raw = str(raw or "").strip().lower()

    valid = {"voice", "ui", "desktop"}
    if not raw or raw in {"full", "all", "default"}:
        return set(valid)

    parts: list[str] = []
    for chunk in raw.split(","):
        parts.extend(piece for piece in chunk.split() if piece)

    selected = {part for part in parts if part in valid}
    return selected or set(valid)


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int_optional(key: str) -> int | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _probe_stt_capture(seconds: float) -> tuple[bool, str, int | None]:
    sd = stt_module.sd
    if sd is None:
        return False, "indisponivel", None
    device = _env_int_optional("JARVIS_AUDIO_DEVICE")
    capture_sr = _env_int_optional("JARVIS_AUDIO_CAPTURE_SR")
    device_label = "default"
    device_name = ""
    if capture_sr is None:
        try:
            info: dict[str, Any] = sd.query_devices(device, "input")  # type: ignore
            default_sr = info.get("default_samplerate")
            capture_sr = int(default_sr) if default_sr else stt_module.SAMPLE_RATE
            device_name = str(info.get("name") or "").strip()
        except Exception:
            capture_sr = stt_module.SAMPLE_RATE
    else:
        try:
            info: dict[str, Any] = sd.query_devices(device, "input")  # type: ignore
            device_name = str(info.get("name") or "").strip()
        except Exception:
            device_name = ""

    if device is not None:
        device_label = f"{device} ({device_name})" if device_name else str(device)
    else:
        device_label = f"default ({device_name})" if device_name else "default"
    samplerate = int(capture_sr)
    try:
        frames = max(1, int(seconds * samplerate))
        audio = sd.rec(
            frames,
            samplerate=samplerate,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd.wait()
        size = int(getattr(audio, "size", 0))
        if size == 0 and hasattr(audio, "__len__"):
            size = len(audio)
        return size > 0, device_label, samplerate
    except Exception:
        return False, device_label, samplerate


def _check_audio_calibration() -> CheckResult | None:
    sd = stt_module.sd
    np = stt_module.np
    if sd is None or np is None:
        return CheckResult(
            name="Audio calib",
            status="WARN",
            detail="sounddevice/numpy indisponiveis; não foi possível medir RMS/peak",
            hint="Instale sounddevice/numpy para calibração automática.",
        )
    device = _env_int_optional("JARVIS_AUDIO_DEVICE")
    try:
        info: dict[str, Any] = sd.query_devices(device, "input")  # type: ignore
        sr = int(info.get("default_samplerate") or 44100)
        name = str(info.get("name") or device or "default")
    except Exception:
        sr = 44100
        name = str(device or "default")
    sr = max(8000, min(192000, sr))
    try:
        audio = sd.rec(
            int(sr * 0.3),
            samplerate=sr,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd.wait()
        rms = float(np.sqrt(np.mean(audio**2)))
        peak = float(np.max(np.abs(audio)))
    except Exception as exc:
        return CheckResult(
            name="Audio calib",
            status="WARN",
            detail=f"falha ao medir RMS/peak ({exc})",
            hint="Verifique permissões e device de áudio.",
        )
    if peak >= 0.98 or rms >= 0.2:
        return CheckResult(
            name="Audio calib",
            status="WARN",
            detail=f"entrada clipando (rms={rms:.3f}, peak={peak:.3f}) no device {name}",
            hint="Reduza ganho (JARVIS_AUDIO_INPUT_GAIN_DB=-6) ou troque device.",
        )
    if rms < 1e-4:
        return CheckResult(
            name="Audio calib",
            status="WARN",
            detail=f"entrada muito baixa (rms={rms:.6f}, peak={peak:.6f}) no device {name}",
            hint="Verifique cabos/mic, aumente ganho ou escolha outro device.",
        )
    return CheckResult(
        name="Audio calib",
        status="OK",
        detail=f"RMS/peak ok (rms={rms:.4f}, peak={peak:.3f}) no device {name}",
    )


def _probe_tts_play(config: Config) -> bool:
    try:
        TextToSpeech(config).speak("teste de audio")
        return True
    except Exception:
        return False


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
    try:
        stop_exists = config.stop_file_path.exists()
    except PermissionError as exc:
        return CheckResult(
            name="Kill switch",
            status="WARN",
            detail=f"sem permissao para checar STOP em {config.stop_file_path}",
            hint=str(exc),
        )
    except OSError as exc:
        return CheckResult(
            name="Kill switch",
            status="WARN",
            detail=f"falha ao checar STOP em {config.stop_file_path}",
            hint=str(exc),
        )
    if stop_exists:
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
    has_resample = bool(deps.get("scipy"))
    probe_enabled = _env_bool("JARVIS_PREFLIGHT_PROBE", False)
    probe_seconds = max(0.05, _env_float("JARVIS_PREFLIGHT_PROBE_SECONDS", 0.2))

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
        if not has_resample:
            result = CheckResult(
                name="STT",
                status="WARN",
                detail="scipy ausente; reamostragem pode falhar em devices != 16 kHz",
                hint="pip install scipy",
            )
        else:
            result = CheckResult(name="STT", status="OK", detail="local ativo")
    elif mode == "auto":
        if has_local:
            if not has_resample:
                result = CheckResult(
                    name="STT",
                    status="WARN",
                    detail="scipy ausente; reamostragem pode falhar em devices != 16 kHz",
                    hint="pip install scipy",
                )
            else:
                result = CheckResult(name="STT", status="OK", detail="auto (local)")
        else:
            result = CheckResult(
                name="STT",
                status="FAIL",
                detail="auto sem local",
                hint="Instale faster-whisper.",
            )
    else:
        result = CheckResult(
            name="STT", status="WARN", detail=f"modo desconhecido: {mode}"
        )

    streaming_enabled = _env_bool("JARVIS_STT_STREAMING", False)
    if streaming_enabled and result.status != "FAIL":
        if not deps.get("realtimestt"):
            return CheckResult(
                name="STT",
                status="WARN",
                detail=f"{result.detail}; streaming ativo, RealtimeSTT ausente",
                hint="pip install RealtimeSTT ou use JARVIS_STT_STREAMING=0",
            )
        if not deps.get("pyaudio"):
            return CheckResult(
                name="STT",
                status="WARN",
                detail=f"{result.detail}; streaming ativo, pyaudio ausente",
                hint="pip install pyaudio ou use JARVIS_STT_STREAMING=0",
            )

    if not probe_enabled or result.status == "FAIL":
        return result

    probe_ok, device_label, capture_sr = _probe_stt_capture(probe_seconds)
    sr_label = f"{capture_sr}Hz" if capture_sr else "desconhecido"
    probe_detail = f"device={device_label}, sr={sr_label}"

    if not probe_ok:
        detail = f"{result.detail}; captura falhou no preflight ({probe_detail})"
        hint = (
            result.hint
            or "Verifique microfone/dispositivo ou desative JARVIS_PREFLIGHT_PROBE."
        )
        return CheckResult(name="STT", status="WARN", detail=detail, hint=hint)

    if result.status == "OK":
        return CheckResult(
            name="STT",
            status="OK",
            detail=f"{result.detail} (captura ok; {probe_detail})",
        )

    return CheckResult(
        name="STT",
        status=result.status,
        detail=f"{result.detail} (captura ok; {probe_detail})",
        hint=result.hint,
    )


def _check_wake_word_audio() -> CheckResult | None:
    if not _env_bool("JARVIS_WAKE_WORD_AUDIO", False):
        return None
    backend = (
        os.environ.get("JARVIS_WAKE_WORD_AUDIO_BACKEND", "pvporcupine").strip().lower()
    )
    if backend in {"oww", "openwakeword", "openwakewords"}:
        if not wakeword_openwakeword.is_available():
            return CheckResult(
                name="Wake word (audio)",
                status="WARN",
                detail="wake word por audio ativo, mas openwakeword ausente",
                hint="pip install openwakeword e configure JARVIS_OPENWAKEWORD_MODEL_PATHS",
            )
        model_paths = os.environ.get("JARVIS_OPENWAKEWORD_MODEL_PATHS", "").strip()
        auto_download = _env_bool("JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD", False)
        if not model_paths and not auto_download:
            return CheckResult(
                name="Wake word (audio)",
                status="WARN",
                detail="openwakeword disponivel, mas sem modelos configurados",
                hint="Defina JARVIS_OPENWAKEWORD_MODEL_PATHS ou JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD=1",
            )
        return CheckResult(
            name="Wake word (audio)",
            status="OK",
            detail="openwakeword disponivel",
        )

    if not wakeword_porcupine.is_available():
        return CheckResult(
            name="Wake word (audio)",
            status="WARN",
            detail="wake word por audio ativo, mas pvporcupine ausente",
            hint="pip install pvporcupine e configure JARVIS_PORCUPINE_ACCESS_KEY",
        )
    return CheckResult(
        name="Wake word (audio)",
        status="OK",
        detail="pvporcupine disponivel",
    )


def _check_silero_deactivity() -> CheckResult | None:
    if not _env_bool("JARVIS_SILERO_DEACTIVITY", False):
        return None
    if not vad_silero.is_available():
        return CheckResult(
            name="Silero deactivity",
            status="WARN",
            detail="silero deactivity ativo, mas torch/numpy ausentes",
            hint="Instale torch e numpy, ou desative JARVIS_SILERO_DEACTIVITY.",
        )
    auto_download = _env_bool("JARVIS_SILERO_AUTO_DOWNLOAD", False)
    if not auto_download and not vad_silero.has_cached_model():
        return CheckResult(
            name="Silero deactivity",
            status="WARN",
            detail="silero ativo, mas modelo nao encontrado no cache",
            hint="Defina JARVIS_SILERO_AUTO_DOWNLOAD=1 para baixar o modelo.",
        )
    return CheckResult(
        name="Silero deactivity",
        status="OK",
        detail="silero disponivel",
    )


def _check_tts(config: Config) -> CheckResult:
    deps = check_tts_deps()
    mode = config.tts_mode
    probe_enabled = _env_bool("JARVIS_PREFLIGHT_PROBE", False)
    engine_pref = (os.environ.get("JARVIS_TTS_ENGINE", "auto") or "auto").strip().lower()

    if mode == "none":
        return CheckResult(
            name="TTS",
            status="WARN",
            detail="voz desativada",
            hint="Defina JARVIS_TTS_MODE=local para voz.",
        )

    has_piper = bool(deps.get("piper"))
    has_espeak = bool(deps.get("espeak-ng"))
    has_engine = has_piper or has_espeak
    if not has_engine:
        return CheckResult(
            name="TTS",
            status="WARN",
            detail="nenhum engine instalado",
            hint="Instale piper ou espeak-ng.",
        )

    result: CheckResult
    if engine_pref in {"piper"} and not has_piper:
        result = CheckResult(
            name="TTS",
            status="WARN",
            detail="JARVIS_TTS_ENGINE=piper, mas piper nao esta instalado",
            hint="Instale o binario piper + modelo local, ou use JARVIS_TTS_ENGINE=auto/espeak-ng.",
        )
        return result
    if engine_pref in {"espeak", "espeak-ng"} and not has_espeak:
        result = CheckResult(
            name="TTS",
            status="WARN",
            detail="JARVIS_TTS_ENGINE=espeak-ng, mas espeak-ng nao esta instalado",
            hint="Instale espeak-ng, ou use JARVIS_TTS_ENGINE=auto/piper.",
        )
        return result

    if has_piper:
        try:
            piper_ok = TextToSpeech(config)._find_piper_model() is not None
        except Exception:
            piper_ok = False
        if not piper_ok:
            detail = "piper instalado, mas sem modelo local"
            if has_espeak:
                detail += " (espeak disponivel)"
            result = CheckResult(
                name="TTS",
                status="WARN",
                detail=detail,
                hint="Baixe um modelo Piper ou use espeak-ng.",
            )
        else:
            result = CheckResult(
                name="TTS", status="OK", detail="engine local disponivel"
            )
    else:
        result = CheckResult(name="TTS", status="OK", detail="engine local disponivel")

    if not probe_enabled or not has_engine:
        return result

    if not _probe_tts_play(config):
        detail = f"{result.detail}; falha ao tocar audio no preflight"
        hint = result.hint or "Verifique TTS/alsa ou desative JARVIS_PREFLIGHT_PROBE."
        return CheckResult(name="TTS", status="WARN", detail=detail, hint=hint)

    if result.status == "OK":
        return CheckResult(
            name="TTS",
            status="OK",
            detail=f"{result.detail} (audio ok)",
        )

    return result


def _check_desktop_drivers(config: Config) -> CheckResult:
    tools = DesktopAutomation(session_type=config.session_type).check_available_tools()
    has_any = (
        tools["xdotool"] or tools["wtype"] or tools["ydotool"] or tools["pyautogui"]
    )
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

    if tools["is_wayland"] and not (
        tools["wtype"] or tools["ydotool"] or tools["pyautogui"]
    ):
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
    if session_type in {"", "unknown"}:
        env_session = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
        if env_session:
            session_type = env_session
    if session_type in {"tty", "headless"}:
        return True

    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if os.environ.get("CI") and not has_display:
        return True
    if not has_display and session_type in {"", "unknown"}:
        return True
    if session_type in {"x11", "wayland"} and not has_display:
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
    file_trigger = bool(deps.get("file_trigger"))
    if not deps.get("pynput"):
        if file_trigger:
            return CheckResult(
                name="Atalho chat",
                status="OK",
                detail="atalho via arquivo configurado (pynput ausente)",
                hint=(
                    "Configure um atalho do sistema para executar: "
                    "touch $JARVIS_CHAT_SHORTCUT_FILE"
                ),
            )
        return CheckResult(
            name="Atalho chat",
            status="WARN",
            detail="pynput nao instalado (atalho desabilitado)",
            hint="pip install pynput para ativar atalho Ctrl+Shift+J.",
        )
    # Wayland costuma bloquear captura global de teclado; XWayland (DISPLAY) às vezes funciona.
    if deps.get("wayland") and not deps.get("x11"):
        if file_trigger:
            return CheckResult(
                name="Atalho chat",
                status="OK",
                detail="Wayland detectado; usando atalho via arquivo",
                hint=(
                    "Configure um atalho do sistema para executar: "
                    "touch $JARVIS_CHAT_SHORTCUT_FILE"
                ),
            )
        return CheckResult(
            name="Atalho chat",
            status="WARN",
            detail="Wayland detectado: atalhos globais via pynput podem falhar",
            hint=(
                "Use X11/XWayland (DISPLAY) ou configure o atalho no seu ambiente (GNOME/KDE) para chamar: "
                "python -m jarvis.interface.entrada.chat_ui"
            ),
        )
    return CheckResult(
        name="Atalho chat",
        status="OK",
        detail="atalho global disponivel (Ctrl+Shift+J)",
    )
