from __future__ import annotations

import os
from typing import Any
from pathlib import Path


def _env_is_set(key: str) -> bool:
    value = os.environ.get(key)
    return value is not None and value != ""


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _set_default_env(key: str, value: str) -> None:
    if not _env_is_set(key):
        os.environ[key] = value


def _set_env(key: str, value: str) -> None:
    os.environ[key] = value


def _auto_select_audio_input_device() -> None:
    """
    Auto-select a better input device for voice mode.

    Rationale:
    - Some ALSA "hw" devices can appear as valid inputs but be effectively unusable
      (clipping at peak=1.0 even in silence). That breaks VAD and makes STT slow/noisy.
    - Pulse/PipeWire virtual devices often apply better routing and AEC/NS at the OS level.

    Behavior:
    - Runs when `JARVIS_AUTO_AUDIO_DEVICE=1` (default).
    - If `JARVIS_AUDIO_DEVICE` is already set, it is only overridden when the chosen
      device looks clearly unusable (ex.: clipping in silence), unless
      `JARVIS_AUDIO_DEVICE_STRICT=1`.
    - Records a tiny "silence probe" (<= 0.25s) on a small set of candidate devices.
    - Picks the device with lowest noise/clipping score.
    """
    if not _env_bool("JARVIS_AUTO_AUDIO_DEVICE", True):
        return
    if _env_bool("JARVIS_AUDIO_DEVICE_STRICT", False) and _env_is_set(
        "JARVIS_AUDIO_DEVICE"
    ):
        return

    try:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
    except Exception:
        return

    try:
        devices_raw = sd.query_devices()
        # sounddevice.query_devices() returns a list of dicts when called without args
        devices: list[dict[str, Any]] = []
        if isinstance(devices_raw, list):
            devices = [d for d in devices_raw if isinstance(d, dict)]
        elif isinstance(devices_raw, dict):
            devices = [devices_raw]
    except Exception:
        return

    forced_idx: int | None = None
    forced_raw = os.environ.get("JARVIS_AUDIO_DEVICE")
    if forced_raw is not None and forced_raw.strip() != "":
        try:
            forced_idx = int(forced_raw)
        except ValueError:
            forced_idx = None

    candidates: list[int] = []
    for idx, dev in enumerate(devices):
        try:
            max_channels = dev.get("max_input_channels", 0) if isinstance(dev, dict) else 0
            if int(max_channels or 0) <= 0:
                continue
        except Exception:
            continue
        name = str(dev.get("name") or "").lower() if isinstance(dev, dict) else ""
        if any(token in name for token in ("pulse", "pipewire", "default")):
            candidates.append(idx)

    if forced_idx is not None:
        candidates.insert(0, forced_idx)

    if not candidates:
        # Fallback: take the first input device.
        for idx, dev in enumerate(devices):
            try:
                max_channels = dev.get("max_input_channels", 0) if isinstance(dev, dict) else 0
                if int(max_channels or 0) > 0:
                    candidates.append(idx)
                    break
            except Exception:
                continue

    # Deduplicate while preserving order.
    seen: set[int] = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    best_idx: int | None = None
    best_score: float | None = None
    forced_score: float | None = None

    for idx in candidates[:5]:
        try:
            info_raw = sd.query_devices(idx, "input")
            # sounddevice.query_devices(idx, "input") returns a dict
            info: dict[str, Any] = info_raw if isinstance(info_raw, dict) else {}
        except Exception:
            continue
        try:
            sr = int(info.get("default_samplerate") or 44100)
        except Exception:
            sr = 44100
        sr = max(8000, min(192000, sr))

        secs = 0.25
        try:
            audio = sd.rec(
                int(sr * secs),
                samplerate=sr,
                channels=1,
                dtype="float32",
                device=idx,
            )
            sd.wait()
        except Exception:
            continue

        try:
            rms = float(np.sqrt(np.mean(audio**2)))
            peak = float(np.max(np.abs(audio)))
        except Exception:
            continue

        # Scoring:
        # - Prefer low RMS (silence noise floor)
        # - Penalize clipping hard
        # - Penalize "dead" input (too low)
        if rms < 1e-4:
            score = 10.0
        else:
            score = rms
        if peak >= 0.98:
            score += 1.0
        elif peak >= 0.90:
            score += 0.2

        if forced_idx is not None and idx == forced_idx:
            forced_score = score

        if best_score is None or score < best_score:
            best_score = score
            best_idx = idx

    if best_idx is None:
        return

    # If user already set a device, only override when it looks clearly wrong.
    # Typical symptom: peak close to 1.0 even in silence (clipping) -> VAD never ends.
    if forced_idx is not None and forced_score is not None:
        forced_looks_bad = forced_score >= 0.25 or forced_score >= (best_score or 0.0) + 0.15
        if not forced_looks_bad:
            return
        if best_idx != forced_idx:
            os.environ["JARVIS_AUDIO_DEVICE_PREV"] = str(forced_idx)

    os.environ["JARVIS_AUDIO_DEVICE"] = str(best_idx)
    os.environ["JARVIS_AUDIO_DEVICE_AUTO_SELECTED"] = "1"


def _auto_calibrate_audio_device() -> None:
    try:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
    except Exception:
        return
    device_raw = os.environ.get("JARVIS_AUDIO_DEVICE")
    device = int(device_raw) if device_raw and device_raw.isdigit() else None
    seconds = float(os.environ.get("JARVIS_AUDIO_CALIB_SECONDS", "0.3"))
    try:
        info_raw = sd.query_devices(device, "input")
        # sounddevice.query_devices(device, "input") returns a dict
        info: dict[str, Any] = info_raw if isinstance(info_raw, dict) else {}
        sr = int(info.get("default_samplerate") or 44100)
    except Exception:
        sr = 44100
    sr = max(8000, min(192000, sr))
    try:
        audio = sd.rec(
            int(sr * seconds),
            samplerate=sr,
            channels=1,
            dtype="float32",
            device=device,
        )
        sd.wait()
    except Exception:
        return
    try:
        rms = float(np.sqrt(np.mean(audio**2)))
        peak = float(np.max(np.abs(audio)))
    except Exception:
        return
    # Se pico >= 0.98 ou RMS muito alto, reduzir ganho automático
    if peak >= 0.98 or rms >= 0.2:
        os.environ["JARVIS_AUDIO_INPUT_GAIN_DB"] = "-6"
        os.environ["JARVIS_AUDIO_INPUT_CLIPPED"] = "1"
    os.environ["JARVIS_AUDIO_INPUT_RMS"] = f"{rms:.6f}"
    os.environ["JARVIS_AUDIO_INPUT_PEAK"] = f"{peak:.6f}"


def _detect_piper_ready(config: Any) -> bool:
    try:
        from jarvis.interface.saida.tts import check_tts_deps

        deps = check_tts_deps()
        if not deps.get("piper"):
            return False
    except Exception:
        return False

    models_dir = os.environ.get("JARVIS_PIPER_MODELS_DIR", "").strip()
    if models_dir:
        base = Path(models_dir)
    else:
        base = Path(__file__).resolve().parents[3] / "storage/models/piper"

    voice = (os.environ.get("JARVIS_PIPER_VOICE", "pt_BR-faber-medium") or "").strip()
    if not voice:
        voice = "pt_BR-faber-medium"

    quality_order = (
        os.environ.get("JARVIS_PIPER_VOICE_QUALITY_ORDER", "low,medium,high")
        or "low,medium,high"
    )
    qualities = [q.strip() for q in quality_order.split(",") if q.strip()]
    has_quality_suffix = any(voice.endswith(suffix) for suffix in ("-low", "-medium", "-high"))
    if voice and not has_quality_suffix:
        candidates = [f"{voice}-{q}" for q in qualities] + [voice]
    else:
        candidates = [voice]

    for candidate in candidates:
        onnx = base / f"{candidate}.onnx"
        js = base / f"{candidate}.onnx.json"
        if onnx.exists() and js.exists():
            return True

    return False


def auto_configure_voice_profile(config: Any) -> tuple[bool, str | None]:
    """
    Apply a "production-ish" voice profile automatically for non-technical users.

    Goals:
    - Prefer a human voice (Piper) and NEVER fall back to robotic espeak-ng.
    - Keep CPU usage predictable (thread caps).
    - Reduce perceived latency (phase 1 ack + warmup).

    This only sets env vars that are currently missing, so power users can override.
    """
    if not _env_bool("JARVIS_AUTO_CONFIGURE", True):
        return True, None

    # Apply voice profile if JARVIS_VOICE_PROFILE is set
    if _env_is_set("JARVIS_VOICE_PROFILE"):
        try:
            from jarvis.interface.infra.profiles import load_profile, apply_profile
            profile = load_profile()
            apply_profile(profile)
        except Exception:
            pass

    # Pick a reasonable mic input automatically if user didn't choose one.
    _auto_select_audio_input_device()

    # Prefer captura direta em 16 kHz para evitar resample no caminho quente.
    _set_default_env("JARVIS_AUDIO_PREFER_16K", "1")

    # If user explicitly forced espeak, respect it (but warn upstream if needed).
    # (User story says robotic is unacceptable, but we won't override explicit choice.)
    engine_pref = (os.environ.get("JARVIS_TTS_ENGINE", "") or "").strip().lower()
    if engine_pref in {"espeak", "espeak-ng"}:
        return True, None

    # Defaults that help discovery without forcing user to edit .env
    _set_default_env("JARVIS_DEBUG", "0")

    # Hard requirement: do not fall back to robotic voice.
    _set_default_env("JARVIS_TTS_ENGINE", "piper")
    _set_default_env("JARVIS_TTS_ENGINE_STRICT", "1")
    # AEC leve por padrao para mitigar eco do TTS capturado pelo mic.
    _set_default_env("JARVIS_AEC_BACKEND", "simple")
    # Auto-calibração básica: reduzir ganho quando RMS/peak altos (preflight).
    _set_default_env("JARVIS_AUDIO_AUTO_CALIBRATE", "1")

    # In voice-loop, never block the terminal waiting for "guidance".
    # Without an LLM, the system can't do arbitrary automation anyway.
    #
    # NOTE: some repos ship a `.env` with chat auto-open enabled, which is
    # disruptive in voice mode (it opens editors/browsers on background noise).
    # For voice UX, we force-disable those here; advanced users can turn off
    # auto-config entirely via `JARVIS_AUTO_CONFIGURE=0`.
    _set_env("JARVIS_MAX_GUIDANCE_ATTEMPTS", "0")
    _set_env("JARVIS_AUTO_LEARN_PROCEDURES", "0")
    _set_env("JARVIS_CHAT_AUTO_OPEN", "0")

    # Auto-calibração: se habilitada, medir ruído/clipping antes de iniciar STT.
    if _env_bool("JARVIS_AUDIO_AUTO_CALIBRATE", True):
        _auto_calibrate_audio_device()

    # Prefer repo-local models.
    _set_default_env("JARVIS_PIPER_MODELS_DIR", "storage/models/piper")
    _set_default_env("JARVIS_PIPER_VOICE", "pt_BR-faber-medium")

    # Best path for latency: in-proc Python backend keeps model loaded.
    _set_default_env("JARVIS_PIPER_BACKEND", "python")

    # CPU-safe by default (leave room for STT/LLM/etc.).
    _set_default_env("JARVIS_PIPER_INTRA_OP_THREADS", "1")
    _set_default_env("JARVIS_PIPER_INTER_OP_THREADS", "1")

    # Latency perceived improvements
    _set_default_env("JARVIS_TTS_STREAMING", "1")
    _set_default_env("JARVIS_TTS_CACHE", "1")
    # Warmup helps after startup; keep it async by default (blocking warmup is opt-in).
    _set_default_env("JARVIS_TTS_WARMUP", "1")
    _set_default_env("JARVIS_VOICE_PHASE1", "1")
    _set_default_env("JARVIS_TTS_ACK_PHRASE", "Entendi. Já vou responder.")
    # Make phase 1 feel "perfect" on first interaction: ensure the phrase audio is ready.
    _set_default_env("JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING", "1")
    # Warmup do STT para evitar cold start na primeira transcrição.
    _set_default_env("JARVIS_STT_WARMUP", "1")

    # Keep overlap off unless explicitly enabled (avoid CPU contention).
    _set_default_env("JARVIS_VOICE_OVERLAP_PLAN", "0")

    # Reduce false triggers (keyboard/noise): require wake word ("jarvis") in text.
    _set_default_env("JARVIS_REQUIRE_WAKE_WORD", "1")
    _set_default_env("JARVIS_WAKE_WORD", "jarvis")
    _set_default_env("JARVIS_STT_LANGUAGE", "pt")
    _set_default_env("JARVIS_STT_COMMAND_BIAS", "jarvis, oi jarvis")

    # Make "Jarvis" more likely to be transcribed correctly (helps wake-word gating).
    _set_default_env("JARVIS_STT_INITIAL_PROMPT", "Jarvis")

    # Low-latency STT/VAD preset (shorter endpointing, fast decode params).
    _set_default_env("JARVIS_STT_PROFILE", "fast")
    # Cap STT threads to avoid starving the rest of the system.
    _set_default_env("JARVIS_STT_CPU_THREADS", "2")
    _set_default_env("JARVIS_STT_WORKERS", "1")

    # Allow short commands like "Jarvis, ok" (default was a bit long for quick tests).
    _set_default_env("JARVIS_MIN_AUDIO_SECONDS", "0.6")

    # Make VAD mais responsivo: agressivo 3 e endpoint mais curto (aproxima do preset fast).
    _set_default_env("JARVIS_VAD_AGGRESSIVENESS", "3")
    _set_default_env("JARVIS_VAD_SILENCE_MS", "250")
    _set_default_env("JARVIS_VAD_PRE_ROLL_MS", "120")
    _set_default_env("JARVIS_VAD_POST_ROLL_MS", "120")

    # Avoid follow-up window disabling the wake word (prevents random background audio from triggering commands).
    _set_default_env("JARVIS_FOLLOWUP_SECONDS", "0")
    _set_default_env("JARVIS_FOLLOWUP_MAX_COMMANDS", "0")

    # Emotion detection can auto-download large models and consume CPU.
    # Keep it off by default for the "interface" performance work.
    _set_default_env("JARVIS_EMOTION_ENABLED", "0")

    # Avoid "30s of silence" when VAD does not detect end-of-speech (default is 30s).
    # Power users can raise this if they regularly speak longer commands.
    _set_default_env("JARVIS_VOICE_MAX_SECONDS", "8")

    # Some microphones clip (peak=1.0) and constant noise can confuse VAD.
    # Avoid auto-amplifying audio by default in voice mode.
    _set_env("JARVIS_STT_NORMALIZE_AUDIO", "0")

    if not _detect_piper_ready(config):
        return (
            False,
            "Voz humanizada (Piper) é obrigatória, mas o Piper/modelo não foi encontrado.\n"
            "Coloque um modelo em `storage/models/piper/` (ex.: `pt_BR-faber-medium.onnx` + `.onnx.json`).\n"
            "Não vou cair para voz robótica (espeak-ng).",
        )

    return True, None
