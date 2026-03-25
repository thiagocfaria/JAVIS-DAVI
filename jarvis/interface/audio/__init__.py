"""API publica estavel de audio da interface."""

from .audio_utils import BYTES_PER_SAMPLE, SAMPLE_RATE, coerce_pcm_bytes

__all__ = ["SAMPLE_RATE", "BYTES_PER_SAMPLE", "coerce_pcm_bytes"]
