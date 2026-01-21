"""Formatting checks for Agent-S S3 prompts."""

from .common_utils import (
    extract_agent_functions,
    parse_code_from_string,
    create_action_from_code,
    split_thinking_response,
)


def single_action_check(response: str) -> bool:
    return len(extract_agent_functions(parse_code_from_string(response))) == 1


single_action_error_msg = (
    "Incorrect code: There must be a single agent action in the code response."
)


def SINGLE_ACTION_FORMATTER(response: str) -> tuple[bool, str]:
    return (
        single_action_check(response),
        single_action_error_msg,
    )


def _attempt_action_creation(agent, code, obs):
    try:
        return create_action_from_code(agent, code, obs)
    except Exception:
        return None


def code_valid_check(agent, obs, response: str) -> bool:
    return (
        _attempt_action_creation(agent, parse_code_from_string(response), obs)
        is not None
    )


code_valid_error_msg = (
    "Incorrect code: The agent action must be valid and use valid parameters."
)


def CODE_VALID_FORMATTER(agent, obs, response: str) -> tuple[bool, str]:
    return (
        code_valid_check(agent, obs, response),
        code_valid_error_msg,
    )


def thoughts_answer_tag_check(response: str) -> bool:
    return split_thinking_response(response)[1] != ""


thoughts_answer_tag_error_msg = "Incorrect response: The response must contain both <thoughts>...</thoughts> and <answer>...</answer> tags."


def THOUGHTS_ANSWER_TAG_FORMATTER(response: str) -> tuple[bool, str]:
    return (
        thoughts_answer_tag_check(response),
        thoughts_answer_tag_error_msg,
    )


def integer_answer_check(response: str) -> bool:
    return split_thinking_response(response)[0].strip().isdigit()


integer_answer_error_msg = (
    "Incorrect response: The <answer>...</answer> tag must contain a single integer."
)


def INTEGER_ANSWER_FORMATTER(response: str) -> tuple[bool, str]:
    return (
        integer_answer_check(response),
        integer_answer_error_msg,
    )
