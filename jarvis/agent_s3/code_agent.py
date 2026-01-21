import logging
from typing import Dict, List, Tuple, Optional

from .procedural_memory import PROCEDURAL_MEMORY
from .common_utils import call_llm_safe, split_thinking_response
from .mllm import LMMAgent

logger = logging.getLogger("jarvis.agent_s3")


def extract_code_block(action: str) -> Tuple[Optional[str], Optional[str]]:
    if "```python" in action:
        code_type = "python"
        code = action.split("```python")[1].split("```")[0].strip()
    elif "```bash" in action:
        code_type = "bash"
        code = action.split("```bash")[1].split("```")[0].strip()
    elif "```" in action:
        code_type = None
        code = action.split("```")[1].split("```")[0].strip()
    else:
        code_type = None
        code = None

    logger.debug(
        "Extracted code block: type=%s length=%s", code_type, len(code) if code else 0
    )
    return code_type, code


def execute_code(code_type: str, code: str, env_controller) -> Dict:
    logger.info("CODING_AGENT_CODE_EXECUTION - Type: %s", code_type)

    try:
        if code_type == "bash":
            result = env_controller.run_bash_script(code, timeout=30)
        elif code_type == "python":
            result = env_controller.run_python_script(code)
        else:
            result = {"status": "error", "error": f"Unknown code type: {code_type}"}
        return result
    except Exception as exc:
        logger.error("Error executing %s code: %s", code_type, exc)
        return {"status": "error", "error": str(exc)}


def format_result(result: Dict, step_count: int) -> str:
    if not result:
        logger.warning("Step %s: No result returned from execution", step_count + 1)
        return f"""
Step {step_count + 1} Error:
Error: No result returned from execution
"""

    status = result.get("status", "unknown")
    return_code = result.get("returncode", result.get("return_code", -1))

    if "returncode" in result:
        output = result.get("output", "")
        error = result.get("error", "")
    else:
        output = result.get("output", "")
        error = result.get("error", "")

    result_text = f"Step {step_count + 1} Result:\n"
    result_text += f"Status: {status}\n"
    result_text += f"Return Code: {return_code}\n"

    if output:
        result_text += f"Output:\n{output}\n"

    if error:
        result_text += f"Error:\n{error}\n"

    return result_text


class CodeAgent:
    """A dedicated agent for executing code with a budget of steps."""

    def __init__(self, engine_params: Dict, budget: int = 20):
        if not engine_params:
            raise ValueError("engine_params cannot be None or empty")

        self.engine_params = engine_params
        self.budget = budget
        self.agent = None

        logger.info("CodeAgent initialized with budget=%s", budget)
        self.reset()

    def reset(self) -> None:
        self.agent = LMMAgent(
            engine_params=self.engine_params,
            system_prompt=PROCEDURAL_MEMORY.CODE_AGENT_PROMPT,
        )

    def execute(self, task_instruction: str, screenshot: str, env_controller) -> Dict:
        logger.info("Starting code execution for task: %s", task_instruction)
        logger.info("Budget: %s steps", self.budget)

        self.reset()

        if self.agent is None:
            raise RuntimeError("Agent not initialized")
        context = (
            f"Task: {task_instruction}\n\nCurrent screenshot is provided for context."
        )
        # Convert screenshot string to bytes if needed
        screenshot_bytes: bytes | None = None
        if isinstance(screenshot, str):
            screenshot_bytes = screenshot.encode("utf-8")
        elif isinstance(screenshot, bytes):
            screenshot_bytes = screenshot
        self.agent.add_message(context, image_content=screenshot_bytes, role="user")

        step_count = 0
        execution_history = []
        completion_reason = None

        while step_count < self.budget:
            response = call_llm_safe(self.agent, temperature=1)

            if not response or response.strip() == "":
                raise RuntimeError("LLM returned empty response")

            action, thoughts = split_thinking_response(response)
            execution_history.append(
                {"step": step_count + 1, "action": action, "thoughts": thoughts}
            )

            action_upper = action.upper().strip()
            if action_upper == "DONE":
                completion_reason = "DONE"
                break
            if action_upper == "FAIL":
                completion_reason = "FAIL"
                break

            code_type, code = extract_code_block(action)

            if code and code_type:
                result = execute_code(code_type, code, env_controller)
            else:
                result = {"status": "skipped", "message": "No code block found"}

            if self.agent is None:
                raise RuntimeError("Agent not initialized")
            self.agent.add_message(response, role="assistant")
            result_context = format_result(result, step_count)
            self.agent.add_message(result_context, role="user")

            step_count += 1

        if completion_reason is None:
            completion_reason = f"BUDGET_EXHAUSTED_AFTER_{step_count}_STEPS"

        summary = self._generate_summary(execution_history, task_instruction)

        return {
            "task_instruction": task_instruction,
            "completion_reason": completion_reason,
            "summary": summary,
            "execution_history": execution_history,
            "steps_executed": step_count,
            "budget": self.budget,
        }

    def _generate_summary(
        self, execution_history: List[Dict], task_instruction: str
    ) -> str:
        if not execution_history:
            return "No actions were executed."

        if self.agent is None:
            raise RuntimeError("Agent not initialized")
        prompt = (
            "Summarize the completed steps in 3-5 bullet points, focusing on outputs.\n"
            f"Task: {task_instruction}\n"
            f"Steps: {execution_history}\n"
        )
        self.agent.add_message(prompt, role="user")
        response = call_llm_safe(self.agent, temperature=0.2)
        action, _thoughts = split_thinking_response(response)
        return action or response
