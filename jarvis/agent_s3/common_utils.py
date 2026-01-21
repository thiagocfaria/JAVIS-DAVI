import re
import time
from io import BytesIO
from typing import TYPE_CHECKING, Dict, Tuple

if TYPE_CHECKING:
    from PIL import Image as PILImage

try:
    from PIL import Image as _Image
    Image = _Image
except Exception:  # pragma: no cover
    Image = None

from .procedural_memory import PROCEDURAL_MEMORY

import logging

logger = logging.getLogger("jarvis.agent_s3")


def create_action_from_code(agent, code: str, obs: Dict):
    """Evaluate grounded code into a Jarvis action using the agent instance."""
    agent.assign_screenshot(obs)
    return eval(code)


def call_llm_safe(
    agent, temperature: float = 0.0, use_thinking: bool = False, **kwargs
) -> str:
    max_retries = 3
    attempt = 0
    response = ""
    while attempt < max_retries:
        try:
            response = agent.get_response(
                temperature=temperature, use_thinking=use_thinking, **kwargs
            )
            if response is None:
                raise ValueError("empty_response")
            break
        except Exception as exc:
            attempt += 1
            logger.warning("LLM attempt %s failed: %s", attempt, exc)
            if attempt == max_retries:
                logger.error("Max retries reached for LLM call.")
        time.sleep(1.0)
    return response or ""


def call_llm_formatted(generator, format_checkers, **kwargs):
    max_retries = 3
    attempt = 0
    response = ""
    messages = generator.messages.copy()
    while attempt < max_retries:
        response = call_llm_safe(generator, messages=messages, **kwargs)
        feedback_msgs = []
        for format_checker in format_checkers:
            success, feedback = format_checker(response)
            if not success:
                feedback_msgs.append(feedback)
        if not feedback_msgs:
            break
        logger.error("Response formatting error on attempt %s: %s", attempt, response)
        messages.append(
            {"role": "assistant", "content": [{"type": "text", "text": response}]}
        )
        delimiter = "\n- "
        formatting_feedback = f"- {delimiter.join(feedback_msgs)}"
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROCEDURAL_MEMORY.FORMATTING_FEEDBACK_PROMPT.replace(
                            "FORMATTING_FEEDBACK", formatting_feedback
                        ),
                    }
                ],
            }
        )
        attempt += 1
        if attempt == max_retries:
            logger.error("Max retries reached when formatting response.")
        time.sleep(1.0)
    return response


def split_thinking_response(full_response: str) -> Tuple[str, str]:
    try:
        thoughts = full_response.split("<thoughts>")[-1].split("</thoughts>")[0].strip()
        answer = full_response.split("<answer>")[-1].split("</answer>")[0].strip()
        return answer, thoughts
    except Exception:
        return full_response, ""


def parse_code_from_string(input_string: str) -> str:
    input_string = input_string.strip()
    pattern = r"```(?:\w+\s+)?(.*?)```"
    matches = re.findall(pattern, input_string, re.DOTALL)
    if not matches:
        return ""
    return matches[-1]


def extract_agent_functions(code: str):
    pattern = r"(agent\.\w+\(\s*.*\))"
    return re.findall(pattern, code)


def compress_image(image_bytes: bytes | None = None, image: "PILImage.Image | None" = None) -> bytes:
    if Image is None:
        raise RuntimeError("pillow_not_available")
    if not image:
        if image_bytes is None:
            raise ValueError("Either image_bytes or image must be provided")
        image = Image.open(BytesIO(image_bytes))
    if image is None:
        raise ValueError("Image is None")
    output = BytesIO()
    image.save(output, format="WEBP")
    return output.getvalue()
