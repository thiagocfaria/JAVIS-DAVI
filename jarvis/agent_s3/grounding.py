import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

try:
    import pytesseract
    from pytesseract import Output
except Exception:  # pragma: no cover
    pytesseract = None
    Output = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from .procedural_memory import PROCEDURAL_MEMORY
from .mllm import LMMAgent
from .common_utils import call_llm_safe
from .code_agent import CodeAgent
from .local_env import LocalEnvController
from ..cerebro.actions import Action

import logging

logger = logging.getLogger("jarvis.agent_s3")


class ACI:
    def __init__(self):
        self.notes: List[str] = []


# Agent action decorator

def agent_action(func):
    func.is_agent_action = True
    return func


class JarvisACI(ACI):
    def __init__(
        self,
        env_controller: LocalEnvController,
        platform: str,
        engine_params_for_generation: Dict,
        engine_params_for_grounding: Dict,
        width: int,
        height: int,
        enable_code_agent: bool = False,
        code_agent_budget: int = 20,
        approval_callback=None,
        code_agent_engine_params: Dict | None = None,
    ):
        super().__init__()

        self.env_controller = env_controller
        self.platform = platform
        self.width = width
        self.height = height
        self.approval_callback = approval_callback

        self.notes = []
        self.obs = None

        self.grounding_model = LMMAgent(engine_params_for_grounding)
        self.engine_params_for_grounding = engine_params_for_grounding

        self.text_span_agent = LMMAgent(
            engine_params=engine_params_for_generation,
            system_prompt=PROCEDURAL_MEMORY.PHRASE_TO_WORD_COORDS_PROMPT,
        )

        self.enable_code_agent = enable_code_agent
        if enable_code_agent:
            code_agent_engine_params = code_agent_engine_params or engine_params_for_generation
            self.code_agent = CodeAgent(code_agent_engine_params, code_agent_budget)
        else:
            self.code_agent = None

        self.current_task_instruction = None
        self.last_code_agent_result = None

    def assign_screenshot(self, obs: Dict):
        self.obs = obs

    def set_task_instruction(self, task_instruction: str):
        self.current_task_instruction = task_instruction

    def _get_grounding_dims(self) -> Tuple[int, int]:
        gw = self.engine_params_for_grounding.get("grounding_width")
        gh = self.engine_params_for_grounding.get("grounding_height")
        return int(gw or self.width), int(gh or self.height)

    def resize_coordinates(self, coordinates: List[int]) -> List[int]:
        grounding_width, grounding_height = self._get_grounding_dims()
        return [
            round(coordinates[0] * self.width / grounding_width),
            round(coordinates[1] * self.height / grounding_height),
        ]

    def generate_coords(self, ref_expr: str, obs: Dict) -> List[int]:
        self.grounding_model.reset()
        prompt = f"Query:{ref_expr}\nOutput only the coordinate of one point in your response.\n"
        self.grounding_model.add_message(
            text_content=prompt, image_content=obs["screenshot"], put_text_last=True
        )
        response = call_llm_safe(self.grounding_model)
        numericals = re.findall(r"\d+", response)
        if len(numericals) < 2:
            raise ValueError("invalid_grounding_response")
        return [int(numericals[0]), int(numericals[1])]

    def get_ocr_elements(self, b64_image_data: bytes) -> Tuple[str, List]:
        if pytesseract is None or Image is None:
            raise RuntimeError("pytesseract_not_available")
        image = Image.open(BytesIO(b64_image_data))
        image_data = pytesseract.image_to_data(image, output_type=Output.DICT)

        for i, word in enumerate(image_data["text"]):
            image_data["text"][i] = re.sub(
                r"^[^a-zA-Z\s.,!?;:\-\+]+|[^a-zA-Z\s.,!?;:\-\+]+$", "", word
            )

        ocr_elements = []
        ocr_table = "Text Table:\nWord id\tText\n"
        for i in range(len(image_data["text"])):
            text = image_data["text"][i]
            if text.strip() == "":
                continue
            elem = {
                "left": image_data["left"][i],
                "top": image_data["top"][i],
                "width": image_data["width"][i],
                "height": image_data["height"][i],
                "text": text,
            }
            ocr_elements.append(elem)
            ocr_table += f"{len(ocr_elements) - 1}\t{text}\n"

        return ocr_table, ocr_elements

    def generate_text_coords(
        self, phrase: str, obs: Dict, alignment: str = "start"
    ) -> List[int]:
        if alignment not in {"start", "end", "center"}:
            alignment = "start"

        ocr_table, ocr_elements = self.get_ocr_elements(obs["screenshot"])
        alignment_prompt = "The word should align with the start of the phrase.\n"
        if alignment == "end":
            alignment_prompt = "The word should align with the end of the phrase.\n"
        if alignment == "center":
            alignment_prompt = "The word should align with the center of the phrase.\n"

        self.text_span_agent.add_message(
            alignment_prompt + "Phrase: " + phrase + "\n" + ocr_table,
            role="user",
        )
        self.text_span_agent.add_message(
            "Screenshot:\n", image_content=obs["screenshot"], role="user"
        )

        response = call_llm_safe(self.text_span_agent)
        numericals = re.findall(r"\d+", response)
        text_id = int(numericals[-1]) if numericals else 0
        elem = ocr_elements[text_id]

        if alignment == "start":
            coords = [elem["left"], elem["top"] + (elem["height"] // 2)]
        elif alignment == "end":
            coords = [
                elem["left"] + elem["width"],
                elem["top"] + (elem["height"] // 2),
            ]
        else:
            coords = [
                elem["left"] + (elem["width"] // 2),
                elem["top"] + (elem["height"] // 2),
            ]
        return coords

    def _try_coords(self, description: str) -> Tuple[int | None, int | None]:
        try:
            coords = self.generate_coords(description, self.obs)
            x, y = self.resize_coordinates(coords)
            return x, y
        except Exception as exc:
            logger.debug("Grounding failed: %s", exc)
            return None, None

    @agent_action
    def click(self, element_description: str, num_clicks: int = 1, button_type: str = "left", hold_keys: List = []):
        x, y = self._try_coords(element_description)
        params = {
            "x": x,
            "y": y,
            "target": element_description,
            "button": button_type,
            "clicks": num_clicks,
            "hold_keys": hold_keys,
        }
        return Action("click", params)

    @agent_action
    def switch_applications(self, app_code: str):
        return Action("open_app", {"app": app_code})

    @agent_action
    def open(self, app_or_filename: str):
        return Action("open_app", {"app": app_or_filename})

    @agent_action
    def type(
        self,
        element_description: Optional[str] = None,
        text: str = "",
        overwrite: bool = False,
        enter: bool = False,
    ):
        params: Dict[str, Any] = {
            "text": text,
            "overwrite": overwrite,
            "enter": enter,
        }
        if element_description:
            x, y = self._try_coords(element_description)
            params.update({"x": x, "y": y, "target": element_description})
        return Action("type_text", params)

    @agent_action
    def save_to_knowledge(self, text: List[str]):
        self.notes.extend(text)
        return Action("wait", {"seconds": 1})

    @agent_action
    def drag_and_drop(self, starting_description: str, ending_description: str, hold_keys: List = []):
        x1, y1 = self._try_coords(starting_description)
        x2, y2 = self._try_coords(ending_description)
        params = {
            "start_x": x1,
            "start_y": y1,
            "end_x": x2,
            "end_y": y2,
            "hold_keys": hold_keys,
        }
        return Action("drag", params)

    @agent_action
    def highlight_text_span(self, starting_phrase: str, ending_phrase: str, button: str = "left"):
        coords1 = self.generate_text_coords(starting_phrase, self.obs, alignment="start")
        coords2 = self.generate_text_coords(ending_phrase, self.obs, alignment="end")
        params = {
            "start_x": coords1[0],
            "start_y": coords1[1],
            "end_x": coords2[0],
            "end_y": coords2[1],
            "button": button,
        }
        return Action("drag", params)

    @agent_action
    def call_code_agent(self, task: str = None):
        if not self.enable_code_agent or self.code_agent is None:
            self.last_code_agent_result = {
                "completion_reason": "DISABLED",
                "summary": "Code agent disabled",
                "execution_history": [],
                "steps_executed": 0,
                "budget": 0,
                "task_instruction": task or self.current_task_instruction,
            }
            return Action("wait", {"seconds": 1})

        if self.approval_callback and not self.approval_callback():
            self.last_code_agent_result = {
                "completion_reason": "APPROVAL_DENIED",
                "summary": "Code agent approval denied",
                "execution_history": [],
                "steps_executed": 0,
                "budget": self.code_agent.budget,
                "task_instruction": task or self.current_task_instruction,
            }
            return Action("wait", {"seconds": 1})

        task_to_execute = task or self.current_task_instruction
        if task_to_execute:
            screenshot = self.obs.get("screenshot", "") if self.obs else ""
            result = self.code_agent.execute(task_to_execute, screenshot, self.env_controller)
            self.last_code_agent_result = result
        else:
            self.last_code_agent_result = {
                "completion_reason": "NO_TASK",
                "summary": "No task instruction available",
                "execution_history": [],
                "steps_executed": 0,
                "budget": self.code_agent.budget,
                "task_instruction": "",
            }
        return Action("wait", {"seconds": 1})

    @agent_action
    def scroll(self, element_description: str, clicks: int, shift: bool = False):
        return Action("scroll", {"amount": clicks, "target": element_description, "shift": shift})

    @agent_action
    def hotkey(self, keys: List):
        combo = "+".join([str(key) for key in keys])
        return Action("hotkey", {"combo": combo})

    @agent_action
    def hold_and_press(self, hold_keys: List, press_keys: List):
        combo = "+".join([str(k) for k in (hold_keys + press_keys)])
        return Action("hotkey", {"combo": combo})

    @agent_action
    def wait(self, time: float):
        return Action("wait", {"seconds": time})

    @agent_action
    def done(self):
        return "DONE"

    @agent_action
    def fail(self):
        return "FAIL"
