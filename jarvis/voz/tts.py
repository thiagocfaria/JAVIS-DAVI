"""
Text-to-Speech module with Piper support.

Piper is a fast, local neural TTS engine with natural-sounding voices.
Falls back to espeak-ng if Piper is not available.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import audioop
from pathlib import Path
from typing import Optional

from ..cerebro.config import Config


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float_optional(key: str) -> float | None:
    value = os.environ.get(key)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


class TextToSpeech:
    """
    Text-to-Speech engine with Piper support.
    
    Priority order:
    1. Piper (neural TTS, natural voice)
    2. espeak-ng (robotic but always available)
    3. No TTS (silent mode)
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._piper_available: bool | None = None
        self._espeak_available: bool | None = None
        self._piper_model: str | None = None
        self._debug_enabled = _env_bool("JARVIS_DEBUG", False)
        self._speak_lock = threading.Lock()
        self._volume_override = _env_float_optional("JARVIS_TTS_VOLUME")
        if self._volume_override is None:
            self._volume = 1.0
            self._volume_is_default = True
        else:
            self._volume = self._clamp_volume(self._volume_override)
            self._volume_is_default = False

        # Piper model paths (can be overridden via environment)
        self._piper_models_dir = Path(
            os.environ.get("JARVIS_PIPER_MODELS_DIR", str(Path.home() / ".local/share/piper-models"))
        )

        # Default Portuguese Brazilian voice
        self._default_voice = os.environ.get("JARVIS_PIPER_VOICE", "pt_BR-faber-medium")

    def _debug(self, message: str) -> None:
        if self._debug_enabled:
            print(f"[tts] {message}")

    @staticmethod
    def _clamp_volume(volume: float) -> float:
        if volume < 0.0:
            return 0.0
        if volume > 2.0:
            return 2.0
        return volume

    def _scale_audio(self, audio_bytes: bytes) -> bytes:
        if not audio_bytes or self._volume == 1.0:
            return audio_bytes
        try:
            return audioop.mul(audio_bytes, 2, float(self._volume))
        except Exception:
            return audio_bytes

    def _espeak_amplitude(self) -> int | None:
        if self._volume_is_default:
            return None
        amplitude = int(self._volume * 100)
        if amplitude < 0:
            amplitude = 0
        if amplitude > 200:
            amplitude = 200
        return amplitude

    def speak(self, text: str) -> None:
        """
        Speak the given text.
        
        Tries Piper first, falls back to espeak-ng.
        """
        if self.config.tts_mode == "none":
            return

        if not text or not text.strip():
            return

        with self._speak_lock:
            # Try Piper first
            if self._try_piper(text):
                return

            # Fallback to espeak
            self._debug("piper indisponivel; usando espeak-ng")
            self._speak_espeak(text)

    def _try_piper(self, text: str) -> bool:
        """
        Try to speak using Piper TTS.
        
        Returns True if successful, False to fallback.
        """
        if self._piper_available is False:
            return False

        # Check if piper is installed
        if self._piper_available is None:
            self._piper_available = shutil.which("piper") is not None
            if not self._piper_available:
                return False

        # Find model file
        model_path = self._find_piper_model()
        if model_path is None:
            self._piper_available = False
            return False

        aec_module = None
        aec_enabled = False
        try:
            from . import vad as vad_module

            aec_enabled = vad_module.is_aec_enabled()
            aec_module = vad_module
        except Exception:
            aec_enabled = False

        try:
            # Piper reads text from stdin and outputs WAV to stdout
            piper_cmd = [
                "piper",
                "--model", str(model_path),
                "--output-raw",
            ]

            aplay_cmd = ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"]

            if not aec_enabled and (self._volume_is_default or self._volume == 1.0):
                # Run piper | aplay pipeline
                piper_proc = subprocess.Popen(
                    piper_cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )

                aplay_proc = subprocess.Popen(
                    aplay_cmd,
                    stdin=piper_proc.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                # Send text to piper
                piper_proc.stdin.write(text.encode("utf-8"))
                piper_proc.stdin.close()

                # Wait for completion (with timeout)
                piper_rc = piper_proc.wait(timeout=30)
                aplay_rc = aplay_proc.wait(timeout=30)
                if piper_rc != 0 or aplay_rc != 0:
                    self._debug(f"piper/aplay retornaram codigo {piper_rc}/{aplay_rc}")
                return True

            piper_proc = subprocess.Popen(
                piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            piper_proc.stdin.write(text.encode("utf-8"))
            piper_proc.stdin.close()

            raw_audio = b""
            if piper_proc.stdout is not None:
                raw_audio = piper_proc.stdout.read()
            piper_rc = piper_proc.wait(timeout=30)
            if piper_rc != 0:
                self._debug(f"piper retornou codigo {piper_rc}")

            if self._volume <= 0.0:
                return True

            scaled_audio = self._scale_audio(raw_audio)
            if aec_enabled and aec_module is not None and scaled_audio:
                try:
                    aec_module.push_playback_reference(scaled_audio, 22050)
                except Exception:
                    pass
            aplay_proc = subprocess.Popen(
                aplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if aplay_proc.stdin is not None and scaled_audio:
                aplay_proc.stdin.write(scaled_audio)
                aplay_proc.stdin.close()
            aplay_rc = aplay_proc.wait(timeout=30)
            if aplay_rc != 0:
                self._debug(f"aplay retornou codigo {aplay_rc}")
            return True

        except Exception as exc:
            self._debug(f"piper falhou: {exc}")
            return False

    def _find_piper_model(self) -> Path | None:
        """Find Piper model file."""
        if self._piper_model:
            return Path(self._piper_model) if Path(self._piper_model).exists() else None

        # Check common locations
        search_paths = [
            self._piper_models_dir,
            Path.home() / ".local/share/piper",
            Path("/usr/share/piper-voices"),
            Path("/usr/local/share/piper-voices"),
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            # Look for model file matching default voice
            for model_file in base_path.rglob("*.onnx"):
                if self._default_voice in model_file.stem:
                    self._piper_model = str(model_file)
                    return model_file

            # Any Portuguese model
            for model_file in base_path.rglob("*pt_BR*.onnx"):
                self._piper_model = str(model_file)
                return model_file

            # Any model at all
            for model_file in base_path.rglob("*.onnx"):
                self._piper_model = str(model_file)
                return model_file

        return None

    def _speak_espeak(self, text: str) -> None:
        """Speak using espeak-ng (fallback)."""
        if self._espeak_available is False:
            return

        if self._espeak_available is None:
            self._espeak_available = shutil.which("espeak-ng") is not None
            if not self._espeak_available:
                return

        cmd = ["espeak-ng", "-v", "pt-br"]
        amplitude = self._espeak_amplitude()
        if amplitude is not None:
            cmd.extend(["-a", str(amplitude)])
        cmd.append(text)
        try:
            subprocess.Popen(
                cmd,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            self._debug(f"espeak falhou: {exc}")

    def speak_async(self, text: str) -> None:
        """
        Speak text asynchronously (non-blocking).
        
        Uses a background thread to avoid blocking the main loop.
        """
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()

    def get_available_engines(self) -> list[str]:
        """Get list of available TTS engines."""
        engines = []

        if shutil.which("piper") and self._find_piper_model():
            engines.append("piper")

        if shutil.which("espeak-ng"):
            engines.append("espeak-ng")

        return engines


def check_tts_deps() -> dict:
    """Check TTS dependencies."""
    return {
        "piper": shutil.which("piper") is not None,
        "espeak-ng": shutil.which("espeak-ng") is not None,
        "aplay": shutil.which("aplay") is not None,
    }


def install_piper_instructions() -> str:
    """Get instructions for installing Piper."""
    return """
Para instalar Piper TTS:

1. Baixe o binário:
   wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
   tar -xzf piper_linux_x86_64.tar.gz
   sudo mv piper /usr/local/bin/

2. Baixe uma voz em português:
   mkdir -p ~/.local/share/piper-models
   cd ~/.local/share/piper-models
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx
   wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json

3. Teste:
   echo "Olá, eu sou o Jarvis" | piper --model ~/.local/share/piper-models/pt_BR-faber-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -t raw -
"""
