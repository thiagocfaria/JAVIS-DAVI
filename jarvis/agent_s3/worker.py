from functools import partial
import logging
import textwrap
from typing import Dict, List, Tuple

from .grounding import ACI
from .module import BaseModule
from .procedural_memory import PROCEDURAL_MEMORY
from .common_utils import (
    call_llm_safe,
    call_llm_formatted,
    parse_code_from_string,
    split_thinking_response,
    create_action_from_code,
)
from .formatters import (
    SINGLE_ACTION_FORMATTER,
    CODE_VALID_FORMATTER,
)

logger = logging.getLogger("jarvis.agent_s3")


class Worker(BaseModule):
    def __init__(
        self,
        worker_engine_params: Dict,
        grounding_agent: ACI,
        platform: str = "linux",
        max_trajectory_length: int = 8,
        enable_reflection: bool = True,
        skipped_actions: List[str] | None = None,
    ):
        super().__init__(worker_engine_params, platform)

        self.temperature = worker_engine_params.get("temperature", 0.0)
        self.use_thinking = worker_engine_params.get("use_thinking", False)
        self.grounding_agent = grounding_agent
        self.max_trajectory_length = max_trajectory_length
        self.enable_reflection = enable_reflection
        self.skipped_actions = skipped_actions or []

        self.reset()

    def reset(self):
        sys_prompt = PROCEDURAL_MEMORY.construct_simple_worker_procedural_memory(
            type(self.grounding_agent), skipped_actions=self.skipped_actions
        ).replace("CURRENT_OS", self.platform)

        self.generator_agent = self._create_agent(sys_prompt)
        self.reflection_agent = self._create_agent(
            PROCEDURAL_MEMORY.REFLECTION_ON_TRAJECTORY
        )

        self.turn_count = 0
        self.worker_history = []
        self.reflections = []
        self.screenshot_inputs = []

    def flush_messages(self):
        engine_type = self.engine_params.get("engine_type", "")

        if engine_type in ["openai_compat", "openai", "vllm"]:
            max_images = self.max_trajectory_length
            for agent in [self.generator_agent, self.reflection_agent]:
                if agent is None:
                    continue
                img_count = 0
                for i in range(len(agent.messages) - 1, -1, -1):
                    for j in range(len(agent.messages[i]["content"])):
                        if "image" in agent.messages[i]["content"][j].get("type", ""):
                            img_count += 1
                            if img_count > max_images:
                                del agent.messages[i]["content"][j]
        else:
            if len(self.generator_agent.messages) > 2 * self.max_trajectory_length + 1:
                self.generator_agent.messages.pop(1)
                self.generator_agent.messages.pop(1)
            if len(self.reflection_agent.messages) > self.max_trajectory_length + 1:
                self.reflection_agent.messages.pop(1)

    def _generate_reflection(self, instruction: str, obs: Dict) -> Tuple[str, str]:
        reflection = None
        reflection_thoughts = None
        if self.enable_reflection:
            if self.turn_count == 0:
                text_content = textwrap.dedent(
                    f"""
                    Task Description: {instruction}
                    Current Trajectory below:
                    """
                )
                updated_sys_prompt = (
                    self.reflection_agent.system_prompt + "\n" + text_content
                )
                self.reflection_agent.add_system_prompt(updated_sys_prompt)
                self.reflection_agent.add_message(
                    text_content="The initial screen is provided. No action has been taken yet.",
                    image_content=obs["screenshot"],
                    role="user",
                )
            else:
                self.reflection_agent.add_message(
                    text_content=self.worker_history[-1],
                    image_content=obs["screenshot"],
                    role="user",
                )
                full_reflection = call_llm_safe(
                    self.reflection_agent,
                    temperature=self.temperature,
                    use_thinking=self.use_thinking,
                )
                reflection, reflection_thoughts = split_thinking_response(
                    full_reflection
                )
                self.reflections.append(reflection)
                logger.info("REFLECTION: %s", reflection)
        return reflection, reflection_thoughts

    def generate_next_action(self, instruction: str, obs: Dict) -> Tuple[Dict, List]:
        self.grounding_agent.assign_screenshot(obs)
        self.grounding_agent.set_task_instruction(instruction)

        generator_message = (
            "" if self.turn_count > 0 else "The initial screen is provided. No action has been taken yet."
        )

        if self.turn_count == 0:
            prompt_with_instructions = self.generator_agent.system_prompt.replace(
                "TASK_DESCRIPTION", instruction
            )
            self.generator_agent.add_system_prompt(prompt_with_instructions)

        reflection, reflection_thoughts = self._generate_reflection(instruction, obs)
        if reflection:
            generator_message += (
                "REFLECTION: You may use this reflection on the previous action and overall trajectory:\n"
                f"{reflection}\n"
            )

        generator_message += (
            f"\nCurrent Text Buffer = [{','.join(self.grounding_agent.notes)}]\n"
        )

        if (
            hasattr(self.grounding_agent, "last_code_agent_result")
            and self.grounding_agent.last_code_agent_result is not None
        ):
            code_result = self.grounding_agent.last_code_agent_result
            generator_message += "\nCODE AGENT RESULT:\n"
            generator_message += (
                f"Task/Subtask Instruction: {code_result.get('task_instruction','')}\n"
            )
            generator_message += f"Steps Completed: {code_result.get('steps_executed',0)}\n"
            generator_message += f"Max Steps: {code_result.get('budget',0)}\n"
            generator_message += (
                f"Completion Reason: {code_result.get('completion_reason','')}\n"
            )
            generator_message += f"Summary: {code_result.get('summary','')}\n"
            self.grounding_agent.last_code_agent_result = None

        self.generator_agent.add_message(
            generator_message, image_content=obs["screenshot"], role="user"
        )

        format_checkers = [
            SINGLE_ACTION_FORMATTER,
            partial(CODE_VALID_FORMATTER, self.grounding_agent, obs),
        ]
        plan = call_llm_formatted(
            self.generator_agent,
            format_checkers,
            temperature=self.temperature,
            use_thinking=self.use_thinking,
        )
        self.worker_history.append(plan)
        self.generator_agent.add_message(plan, role="assistant")

        plan_code = parse_code_from_string(plan)
        try:
            if not plan_code:
                raise ValueError("empty_plan_code")
            exec_action = create_action_from_code(self.grounding_agent, plan_code, obs)
        except Exception as exc:
            logger.error("Failed to evaluate plan code: %s", exc)
            exec_action = self.grounding_agent.wait(1.333)

        executor_info = {
            "plan": plan,
            "plan_code": plan_code,
            "exec_action": exec_action,
            "reflection": reflection,
            "reflection_thoughts": reflection_thoughts,
        }
        self.turn_count += 1
        self.screenshot_inputs.append(obs["screenshot"])
        self.flush_messages()
        return executor_info, [exec_action]
