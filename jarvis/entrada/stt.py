"""
Speech-to-Text module (local only).

Uses faster-whisper locally, with optional VAD support.
"""
from __future__ import annotations

import tempfile
import wave

from ..cerebro.config import Config

try:
    import numpy as np  # type: ignore
    import sounddevice as sd  # type: ignore
except (ImportError, OSError):
    np = None
    sd = None

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:
    WhisperModel = None

# Optional: webrtcvad for voice activity detection
try:
    from ..voz.vad import StreamingVAD, VoiceActivityDetector, check_vad_available
except ImportError:
    VoiceActivityDetector = None
    StreamingVAD = None
    check_vad_available = lambda: False


class STTError(Exception):
    """Speech-to-Text error."""
    pass


class SpeechToText:
    """
    Speech-to-Text with local-only architecture.
    
    Modes:
    - "local": Use local faster-whisper
    - "auto": Alias to local (self-hosted only)
    - "none": STT disabled
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self._local_model: WhisperModel | None = None
        self._vad: VoiceActivityDetector | None = None
        self._streaming_vad: StreamingVAD | None = None

        # Initialize VAD if available
        if check_vad_available():
            try:
                from ..voz.vad import StreamingVAD, VoiceActivityDetector
                self._vad = VoiceActivityDetector(aggressiveness=2)
                self._streaming_vad = StreamingVAD(aggressiveness=2)
            except Exception:
                pass

    def transcribe_once(self, seconds: int = 5) -> str:
        """
        Record audio and transcribe to text.
        
        Args:
            seconds: Duration to record (if not using VAD)
            
        Returns:
            Transcribed text
        """
        mode = self.config.stt_mode

        if mode == "none":
            raise STTError("STT disabled. Set JARVIS_STT_MODE=local or auto.")

        # Record audio
        audio_bytes = self._record_audio(seconds)

        if mode == "local":
            return self._transcribe_local(audio_bytes)

        if mode == "auto":
            return self._transcribe_local(audio_bytes)

        raise STTError(f"Unknown STT mode: {mode}")

    def _record_audio(self, seconds: int) -> bytes:
        """
        Record audio from microphone.
        
        Uses VAD if available to stop when speech ends.
        """
        if sd is None or np is None:
            raise STTError("Missing sounddevice/numpy. Run: pip install sounddevice numpy")

        # Use streaming VAD if available
        if self._streaming_vad is not None:
            try:
                audio_bytes, speech_detected = self._streaming_vad.record_fixed_duration(seconds)
                return audio_bytes
            except Exception:
                pass  # Fall through to simple recording

        # Simple fixed-duration recording
        samplerate = 16000
        audio = sd.rec(
            int(seconds * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        # Convert to int16 bytes
        int16_data = (audio.flatten() * 32767).astype(np.int16)
        return int16_data.tobytes()

    def _transcribe_local(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio using local faster-whisper.
        
        Local transcription via faster-whisper.
        """
        if WhisperModel is None:
            raise STTError("Missing faster-whisper. Run: pip install faster-whisper")

        # Save audio to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
            self._write_wav(wav_path, audio_bytes, 16000)

        try:
            # Load model on first use
            if self._local_model is None:
                # Use small model for balance of speed/quality
                model_size = "small"
                self._local_model = WhisperModel(
                    model_size,
                    device="cpu",
                    compute_type="int8",
                )

            segments, _info = self._local_model.transcribe(wav_path, language="pt")
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip()

        finally:
            import os
            if os.path.exists(wav_path):
                os.unlink(wav_path)

    def _write_wav(self, path: str, audio_bytes: bytes, samplerate: int) -> None:
        """Write audio bytes to WAV file."""
        with wave.open(path, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)  # 16-bit
            handle.setframerate(samplerate)
            handle.writeframes(audio_bytes)

    def transcribe_with_vad(self, max_seconds: int = 30) -> str:
        """
        Record audio using VAD (Voice Activity Detection) and transcribe.
        
        Stops recording when speech ends instead of fixed duration.
        
        Args:
            max_seconds: Maximum recording duration
            
        Returns:
            Transcribed text
        """
        if self._streaming_vad is None:
            # Fall back to fixed duration
            return self.transcribe_once(seconds=5)

        try:
            audio_bytes = self._streaming_vad.record_until_silence()

            return self._transcribe_local(audio_bytes)

        except Exception as e:
            raise STTError(f"VAD transcription failed: {e}")

    def check_speech_present(self, audio_bytes: bytes) -> bool:
        """
        Check if audio contains speech.
        
        Uses VAD to detect speech presence.
        """
        if self._vad is None:
            return True  # Assume speech present if no VAD

        speech_frames = 0
        total_frames = 0

        for frame in self._vad.frames_from_audio(audio_bytes):
            if self._vad.is_speech(frame):
                speech_frames += 1
            total_frames += 1

        # Consider speech present if >10% of frames contain speech
        return (speech_frames / total_frames) > 0.1 if total_frames > 0 else False


def check_stt_deps() -> dict:
    """Check STT dependencies."""
    return {
        "sounddevice": sd is not None,
        "numpy": np is not None,
        "faster_whisper": WhisperModel is not None,
        "webrtcvad": check_vad_available() if callable(check_vad_available) else False,
    }


def _write_wav(path: str, audio, samplerate: int) -> None:
    """Legacy function for backwards compatibility."""
    data = (audio * 32767).astype("int16")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(samplerate)
        handle.writeframes(data.tobytes())
