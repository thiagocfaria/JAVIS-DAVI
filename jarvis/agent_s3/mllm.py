"""Minimal multimodal agent wrapper for Agent-S S3 (OpenAI-compatible)."""
from __future__ import annotations

import base64
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    np = None

from .engine import LMMEngineOpenAICompat, LMMEnginevLLM


class LMMAgent:
    def __init__(self, engine_params: dict | None = None, system_prompt: str | None = None, engine=None):
        if engine is None:
            if engine_params is None:
                raise ValueError("engine_params must be provided")
            engine_type = engine_params.get("engine_type")
            if engine_type in {"openai_compat", "openai", "vllm"}:
                self.engine = LMMEngineOpenAICompat(**engine_params)
            else:
                raise ValueError(f"engine_type '{engine_type}' is not supported")
        else:
            self.engine = engine

        self.messages: list[dict[str, Any]] = []
        if system_prompt:
            self.add_system_prompt(system_prompt)
        else:
            self.add_system_prompt("You are a helpful assistant.")

    def encode_image(self, image_content: bytes | str) -> str:
        if isinstance(image_content, str):
            with open(image_content, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        return base64.b64encode(image_content).decode("utf-8")

    def reset(self) -> None:
        self.messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}],
            }
        ]

    def add_system_prompt(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
        if self.messages:
            self.messages[0] = {
                "role": "system",
                "content": [{"type": "text", "text": self.system_prompt}],
            }
        else:
            self.messages.append(
                {
                    "role": "system",
                    "content": [{"type": "text", "text": self.system_prompt}],
                }
            )

    def remove_message_at(self, index: int) -> None:
        if index < len(self.messages):
            self.messages.pop(index)

    def replace_message_at(
        self,
        index: int,
        text_content: str,
        image_content: bytes | None = None,
        image_detail: str = "high",
    ) -> None:
        if index < len(self.messages):
            self.messages[index] = {
                "role": self.messages[index]["role"],
                "content": [{"type": "text", "text": text_content}],
            }
            if image_content:
                base64_image = self.encode_image(image_content)
                self.messages[index]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": image_detail,
                        },
                    }
                )

    def add_message(
        self,
        text_content: str,
        image_content: bytes | list[bytes] | None = None,
        role: str | None = None,
        image_detail: str = "high",
        put_text_last: bool = False,
    ) -> None:
        if role != "user":
            if self.messages[-1]["role"] == "system":
                role = "user"
            elif self.messages[-1]["role"] == "user":
                role = "assistant"
            elif self.messages[-1]["role"] == "assistant":
                role = "user"

        message: dict[str, Any] = {
            "role": role,
            "content": [{"type": "text", "text": text_content}],
        }

        if image_content:
            if isinstance(image_content, list):
                for image in image_content:
                    base64_image = self.encode_image(image)
                    message["content"].append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": image_detail,
                            },
                        }
                    )
            else:
                base64_image = self.encode_image(image_content)
                message["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": image_detail,
                        },
                    }
                )

        if put_text_last:
            text_item = message["content"].pop(0)
            message["content"].append(text_item)

        self.messages.append(message)

    def get_response(
        self,
        user_message: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_new_tokens: int | None = None,
        use_thinking: bool = False,
        **kwargs: Any,
    ) -> str:
        if messages is None:
            messages = self.messages
        if user_message:
            messages.append(
                {"role": "user", "content": [{"type": "text", "text": user_message}]}
            )

        if use_thinking and hasattr(self.engine, "generate_with_thinking"):
            return self.engine.generate_with_thinking(
                messages, temperature=temperature, max_new_tokens=max_new_tokens, **kwargs
            )

        return self.engine.generate(
            messages, temperature=temperature, max_new_tokens=max_new_tokens, **kwargs
        )
