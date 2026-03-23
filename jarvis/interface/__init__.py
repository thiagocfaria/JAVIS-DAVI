"""API publica estavel da interface Jarvis."""

from .audio import BYTES_PER_SAMPLE, SAMPLE_RATE, coerce_pcm_bytes
from .entrada import FollowUpSession, SpeechToText
from .infra import ChatInbox, ChatLog, append_line
from .saida import TextToSpeech

__all__ = [
    "SAMPLE_RATE",
    "BYTES_PER_SAMPLE",
    "coerce_pcm_bytes",
    "SpeechToText",
    "FollowUpSession",
    "TextToSpeech",
    "ChatInbox",
    "ChatLog",
    "append_line",
]
