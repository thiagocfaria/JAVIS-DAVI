from __future__ import annotations

from typing import Optional

from .mllm import LMMAgent


class BaseModule:
    def __init__(self, engine_params: dict, platform: str):
        self.engine_params = engine_params
        self.platform = platform

    def _create_agent(self, system_prompt: str | None = None, engine_params: Optional[dict] = None) -> LMMAgent:
        agent = LMMAgent(engine_params or self.engine_params)
        if system_prompt:
            agent.add_system_prompt(system_prompt)
        return agent
