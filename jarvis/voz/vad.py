"""
Voice Activity Detection (VAD) module using webrtcvad.

This module provides lightweight voice activity detection without PyTorch.
webrtcvad is a C library wrapped in Python, very efficient and low memory.
"""
from __future__ import annotations

import collections
import struct
from collections.abc import Generator
from typing import Optional, Tuple

try:
    import webrtcvad  # type: ignore
except ImportError:
    webrtcvad = None

try:
    import numpy as np  # type: ignore
    import sounddevice as sd  # type: ignore
except (ImportError, OSError):
    np = None
    sd = None


class VADError(Exception):
    """Voice Activity Detection error."""
    pass


class VoiceActivityDetector:
    """
    Lightweight VAD using webrtcvad (C library, no PyTorch).
    
    Aggressiveness levels:
        0 - Least aggressive (more false positives, catches more speech)
        1 - Low aggressiveness
        2 - Medium aggressiveness  
        3 - Most aggressive (fewer false positives, may miss quiet speech)
    """

    # Supported sample rates by webrtcvad
    SUPPORTED_RATES = (8000, 16000, 32000, 48000)
    # Frame duration must be 10, 20, or 30 ms
    SUPPORTED_FRAME_DURATIONS_MS = (10, 20, 30)

    def __init__(
        self,
        aggressiveness: int = 2,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
    ) -> None:
        if webrtcvad is None:
            raise VADError("webrtcvad not installed. Run: pip install webrtcvad")

        if sample_rate not in self.SUPPORTED_RATES:
            raise VADError(f"Sample rate must be one of {self.SUPPORTED_RATES}")

        if frame_duration_ms not in self.SUPPORTED_FRAME_DURATIONS_MS:
            raise VADError(f"Frame duration must be one of {self.SUPPORTED_FRAME_DURATIONS_MS} ms")

        if not 0 <= aggressiveness <= 3:
            raise VADError("Aggressiveness must be 0-3")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.bytes_per_frame = self.frame_size * 2  # 16-bit audio = 2 bytes per sample

        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, audio_frame: bytes) -> bool:
        """
        Check if an audio frame contains speech.
        
        Args:
            audio_frame: Raw 16-bit PCM audio bytes (mono)
            
        Returns:
            True if speech detected, False otherwise
        """
        if len(audio_frame) != self.bytes_per_frame:
            raise VADError(
                f"Frame must be {self.bytes_per_frame} bytes, got {len(audio_frame)}"
            )
        return self._vad.is_speech(audio_frame, self.sample_rate)

    def is_speech_numpy(self, audio_array: np.ndarray) -> bool:
        """
        Check if a numpy audio array contains speech.
        
        Args:
            audio_array: Numpy array of float32 audio samples (-1.0 to 1.0)
            
        Returns:
            True if speech detected, False otherwise
        """
        if np is None:
            raise VADError("numpy not installed")

        # Convert float32 to int16 bytes
        int16_data = (audio_array * 32767).astype(np.int16)
        audio_bytes = int16_data.tobytes()

        return self.is_speech(audio_bytes)

    def frames_from_audio(self, audio_bytes: bytes) -> Generator[bytes, None, None]:
        """
        Split audio bytes into frames suitable for VAD processing.
        
        Args:
            audio_bytes: Raw 16-bit PCM audio bytes
            
        Yields:
            Audio frames of correct size for VAD
        """
        offset = 0
        while offset + self.bytes_per_frame <= len(audio_bytes):
            yield audio_bytes[offset:offset + self.bytes_per_frame]
            offset += self.bytes_per_frame

    def detect_speech_segments(
        self,
        audio_bytes: bytes,
        padding_frames: int = 10,
        threshold_ratio: float = 0.9,
    ) -> list[tuple[int, int]]:
        """
        Detect speech segments in audio.
        
        Uses a ring buffer to smooth out detection and avoid choppy segments.
        
        Args:
            audio_bytes: Raw 16-bit PCM audio bytes
            padding_frames: Number of frames to buffer for smoothing
            threshold_ratio: Ratio of voiced frames needed to trigger speech
            
        Returns:
            List of (start_byte, end_byte) tuples for speech segments
        """
        segments = []
        ring_buffer = collections.deque(maxlen=padding_frames)
        triggered = False
        voiced_frames = []
        segment_start = 0

        frame_idx = 0
        for frame in self.frames_from_audio(audio_bytes):
            is_speech = self.is_speech(frame)
            ring_buffer.append((frame_idx, frame, is_speech))

            if not triggered:
                num_voiced = sum(1 for _, _, speech in ring_buffer if speech)
                if num_voiced > threshold_ratio * ring_buffer.maxlen:
                    triggered = True
                    segment_start = ring_buffer[0][0] * self.bytes_per_frame
                    voiced_frames = [f for _, f, _ in ring_buffer]
            else:
                voiced_frames.append(frame)
                num_unvoiced = sum(1 for _, _, speech in ring_buffer if not speech)
                if num_unvoiced > threshold_ratio * ring_buffer.maxlen:
                    triggered = False
                    segment_end = (frame_idx + 1) * self.bytes_per_frame
                    segments.append((segment_start, segment_end))
                    voiced_frames = []

            frame_idx += 1

        # Handle remaining speech at end
        if triggered and voiced_frames:
            segment_end = frame_idx * self.bytes_per_frame
            segments.append((segment_start, segment_end))

        return segments


class StreamingVAD:
    """
    Streaming VAD for real-time audio capture.
    
    Records audio until speech ends, using VAD to detect when to stop.
    """

    def __init__(
        self,
        aggressiveness: int = 2,
        sample_rate: int = 16000,
        silence_duration_ms: int = 800,
        max_duration_s: int = 30,
    ) -> None:
        if sd is None or np is None:
            raise VADError("sounddevice and numpy required for streaming VAD")

        self.vad = VoiceActivityDetector(
            aggressiveness=aggressiveness,
            sample_rate=sample_rate,
            frame_duration_ms=30,
        )
        self.sample_rate = sample_rate
        self.silence_frames = int(silence_duration_ms / 30)  # frames of silence to stop
        self.max_frames = int(max_duration_s * 1000 / 30)  # max frames to record

    def record_until_silence(self) -> bytes:
        """
        Record audio until silence is detected after speech.
        
        Returns:
            Raw 16-bit PCM audio bytes containing the speech
        """
        frame_size = self.vad.frame_size
        audio_buffer = []
        silence_count = 0
        speech_detected = False
        frame_count = 0

        def callback(indata, frames, time_info, status):
            nonlocal silence_count, speech_detected, frame_count

            if status:
                pass  # Ignore status errors for now

            # Convert to mono if needed and to int16
            mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            int16_data = (mono * 32767).astype(np.int16)
            audio_buffer.append(int16_data.tobytes())

            # Check VAD on each frame
            for i in range(0, len(int16_data), frame_size):
                chunk = int16_data[i:i + frame_size]
                if len(chunk) == frame_size:
                    frame_bytes = chunk.tobytes()
                    is_speech = self.vad.is_speech(frame_bytes)

                    if is_speech:
                        speech_detected = True
                        silence_count = 0
                    elif speech_detected:
                        silence_count += 1

                    frame_count += 1

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=frame_size,
            callback=callback,
        ):
            # Wait until speech ends or max duration
            import time
            while True:
                time.sleep(0.05)
                if speech_detected and silence_count >= self.silence_frames:
                    break
                if frame_count >= self.max_frames:
                    break

        return b"".join(audio_buffer)

    def record_fixed_duration(self, seconds: int = 5) -> tuple[bytes, bool]:
        """
        Record audio for a fixed duration.
        
        Args:
            seconds: Duration to record
            
        Returns:
            Tuple of (audio_bytes, speech_detected)
        """
        frame_size = self.vad.frame_size
        total_samples = int(seconds * self.sample_rate)

        audio = sd.rec(total_samples, samplerate=self.sample_rate, channels=1, dtype='float32')
        sd.wait()

        # Convert to int16 bytes
        int16_data = (audio.flatten() * 32767).astype(np.int16)
        audio_bytes = int16_data.tobytes()

        # Check if speech was detected
        speech_frames = 0
        total_frames = 0
        for frame in self.vad.frames_from_audio(audio_bytes):
            if self.vad.is_speech(frame):
                speech_frames += 1
            total_frames += 1

        speech_detected = speech_frames > (total_frames * 0.1)  # 10% threshold

        return audio_bytes, speech_detected


def check_vad_available() -> bool:
    """Check if VAD dependencies are available."""
    return webrtcvad is not None and np is not None and sd is not None
