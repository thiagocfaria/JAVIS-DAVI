"""
Configuration module for Jarvis.

All configuration is loaded from environment variables.
Self-hosted architecture (local/VPS brain, no external API).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(key: str, default: str | None = None) -> str | None:
    """Get environment variable or default."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    """Get boolean environment variable."""
    from .utils import normalize_text

    value = os.environ.get(key)
    if value is None:
        return default
    return normalize_text(value) in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    """Get integer environment variable."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Get float environment variable."""
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _load_dotenv(dotenv_path: Path | None = None) -> None:
    """Load .env values into os.environ if present (no override)."""
    disable = os.environ.get("JARVIS_DISABLE_DOTENV", "").strip().lower()
    if disable in {"1", "true", "yes", "on"}:
        return

    candidates: list[Path] = []
    if dotenv_path is not None:
        candidates.append(dotenv_path)
    else:
        candidates.append(Path.cwd() / ".env")
        candidates.append(Path(__file__).resolve().parents[2] / ".env")

    for candidate in candidates:
        if not candidate.exists():
            continue
        _apply_dotenv(candidate)
        break


def _apply_dotenv(dotenv_path: Path) -> None:
    try:
        content = dotenv_path.read_text(encoding="utf-8")
    except Exception:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


@dataclass(frozen=True)
class Config:
    """Immutable configuration object."""

    # Data directories
    data_dir: Path
    cache_dir: Path
    log_path: Path
    memory_db: Path
    procedures_path: Path
    policy_user_path: Path
    stop_file_path: Path
    chat_log_path: Path
    chat_inbox_path: Path
    chat_open_cooldown_s: int
    procedures_max_total: int
    procedures_max_per_tag: int
    procedures_ttl_days: int

    # LLM settings (self-hosted)
    local_llm_base_url: str | None
    local_llm_api_key: str | None
    local_llm_model: str
    local_llm_timeout_s: int
    local_llm_cooldown_s: int
    llm_confidence_min: float
    max_failures_per_command: int
    max_guidance_attempts: int
    browser_ai_enabled: bool
    browser_ai_url: str
    auto_learn_procedures: bool
    block_external_sensitive: bool
    external_ask_on_sensitive: bool
    chat_auto_open: bool
    chat_open_command: str | None

    # STT settings
    stt_mode: str  # local, auto, none
    stt_audio_trim_backend: str

    # TTS settings
    tts_mode: str  # piper, espeak, none

    # Security & Approval
    require_approval: bool
    approval_passphrase: str | None
    approval_voice_passphrase: str | None
    approval_key_passphrase: str | None
    approval_mode: str  # voice_and_key, voice_or_key, key_only

    # System
    session_type: str
    dry_run: bool
    allow_open_app: bool

    # Privacy
    mask_screenshots: bool

    # Budget
    budget_path: Path
    budget_max_calls: int
    budget_max_chars: int

    # Agent S3 (GUI agent)
    s3_worker_engine_type: str
    s3_worker_base_url: str | None
    s3_worker_api_key: str | None
    s3_worker_model: str
    s3_grounding_engine_type: str
    s3_grounding_base_url: str | None
    s3_grounding_api_key: str | None
    s3_grounding_model: str
    s3_grounding_width: int
    s3_grounding_height: int
    s3_max_steps: int
    s3_max_trajectory: int
    s3_enable_reflection: bool
    s3_enable_code_agent: bool
    s3_code_agent_budget: int
    s3_code_workdir: str | None
    s3_max_image_dim: int


def load_config() -> Config:
    """Load configuration from environment variables."""
    _load_dotenv()
    data_dir = Path(
        _env("JARVIS_DATA_DIR", str(Path.home() / ".jarvis")) or str(Path.home() / ".jarvis")
    )
    cache_dir = data_dir / "cache"
    log_path = data_dir / "events.jsonl"
    memory_db = data_dir / "memory.sqlite3"
    procedures_path = Path(
        _env("JARVIS_PROCEDURES_PATH", str(data_dir / "procedures.db")) or str(data_dir / "procedures.db")
    )
    policy_user_path = Path(
        _env("JARVIS_POLICY_USER_PATH", str(data_dir / "policy_user.json")) or str(data_dir / "policy_user.json")
    )
    stop_file_path = Path(_env("JARVIS_STOP_FILE_PATH", str(data_dir / "STOP")) or str(data_dir / "STOP"))
    chat_log_path = Path(_env("JARVIS_CHAT_LOG_PATH", str(data_dir / "chat.log")) or str(data_dir / "chat.log"))
    chat_inbox_path = Path(
        _env("JARVIS_CHAT_INBOX_PATH", str(data_dir / "chat_inbox.txt")) or str(data_dir / "chat_inbox.txt")
    )
    budget_path = Path(_env("JARVIS_BUDGET_PATH", str(data_dir / "orcamento.json")) or str(data_dir / "orcamento.json"))

    # Legacy passphrase support
    legacy_passphrase = _env("JARVIS_APPROVAL_PASSPHRASE")
    voice_passphrase = _env("JARVIS_APPROVAL_VOICE_PASSPHRASE", legacy_passphrase)
    key_passphrase = _env("JARVIS_APPROVAL_KEY_PASSPHRASE", legacy_passphrase)

    # STT mode defaults to local (no cloud)
    stt_mode = _env("JARVIS_STT_MODE", "local") or "local"

    return Config(
        # Data directories
        data_dir=data_dir,
        cache_dir=cache_dir,
        log_path=log_path,
        memory_db=memory_db,
        procedures_path=procedures_path,
        policy_user_path=policy_user_path,
        stop_file_path=stop_file_path,
        chat_log_path=chat_log_path,
        chat_inbox_path=chat_inbox_path,
        chat_open_cooldown_s=_env_int("JARVIS_CHAT_OPEN_COOLDOWN_S", 60),
        procedures_max_total=_env_int("JARVIS_PROCEDURES_MAX_TOTAL", 300),
        procedures_max_per_tag=_env_int("JARVIS_PROCEDURES_MAX_PER_TAG", 20),
        procedures_ttl_days=_env_int("JARVIS_PROCEDURES_TTL_DAYS", 90),
        # LLM (self-hosted)
        local_llm_base_url=_env("JARVIS_LOCAL_LLM_BASE_URL"),
        local_llm_api_key=_env("JARVIS_LOCAL_LLM_API_KEY"),
        local_llm_model=_env("JARVIS_LOCAL_LLM_MODEL", "qwen2.5-7b-instruct") or "qwen2.5-7b-instruct",
        local_llm_timeout_s=_env_int("JARVIS_LOCAL_LLM_TIMEOUT_S", 30),
        local_llm_cooldown_s=_env_int("JARVIS_LOCAL_LLM_COOLDOWN_S", 300),
        llm_confidence_min=_env_float("JARVIS_LLM_CONFIDENCE_MIN", 0.55),
        max_failures_per_command=_env_int("JARVIS_MAX_FAILURES_PER_COMMAND", 2),
        max_guidance_attempts=_env_int("JARVIS_MAX_GUIDANCE_ATTEMPTS", 2),
        browser_ai_enabled=_env_bool("JARVIS_BROWSER_AI_ENABLED", True),
        browser_ai_url=_env("JARVIS_BROWSER_AI_URL", "https://chatgpt.com") or "https://chatgpt.com",
        auto_learn_procedures=_env_bool("JARVIS_AUTO_LEARN_PROCEDURES", True),
        block_external_sensitive=_env_bool("JARVIS_BLOCK_EXTERNAL_SENSITIVE", True),
        external_ask_on_sensitive=_env_bool("JARVIS_EXTERNAL_ASK_ON_SENSITIVE", True),
        chat_auto_open=_env_bool("JARVIS_CHAT_AUTO_OPEN", False),
        chat_open_command=_env("JARVIS_CHAT_OPEN_COMMAND"),
        # STT
        stt_mode=stt_mode or "local",
        stt_audio_trim_backend=_env("JARVIS_AUDIO_TRIM_BACKEND", "none") or "none",
        # TTS
        tts_mode=_env("JARVIS_TTS_MODE", "local") or "local",
        # Security
        require_approval=_env_bool("JARVIS_REQUIRE_APPROVAL", True),
        approval_passphrase=legacy_passphrase,
        approval_voice_passphrase=voice_passphrase,
        approval_key_passphrase=key_passphrase,
        approval_mode=_env("JARVIS_APPROVAL_MODE", "voice_and_key") or "voice_and_key",
        # System
        session_type=_env("XDG_SESSION_TYPE", "unknown") or "unknown",
        dry_run=_env_bool("JARVIS_DRY_RUN", False),
        allow_open_app=_env_bool("JARVIS_ALLOW_OPEN_APP", True),
        # Privacy
        mask_screenshots=_env_bool("JARVIS_MASK_SCREENSHOTS", True),
        # Budget
        budget_path=budget_path,
        budget_max_calls=_env_int("JARVIS_BUDGET_MAX_CALLS", 0),
        budget_max_chars=_env_int("JARVIS_BUDGET_MAX_CHARS", 0),
        # Agent S3
        s3_worker_engine_type=_env("JARVIS_S3_WORKER_ENGINE_TYPE", "openai_compat") or "openai_compat",
        s3_worker_base_url=_env(
            "JARVIS_S3_WORKER_BASE_URL", _env("JARVIS_LOCAL_LLM_BASE_URL")
        ),
        s3_worker_api_key=_env(
            "JARVIS_S3_WORKER_API_KEY", _env("JARVIS_LOCAL_LLM_API_KEY")
        ),
        s3_worker_model=_env(
            "JARVIS_S3_WORKER_MODEL",
            _env("JARVIS_LOCAL_LLM_MODEL", "qwen2.5-7b-instruct") or "qwen2.5-7b-instruct",
        ) or (_env("JARVIS_LOCAL_LLM_MODEL", "qwen2.5-7b-instruct") or "qwen2.5-7b-instruct"),
        s3_grounding_engine_type=_env(
            "JARVIS_S3_GROUNDING_ENGINE_TYPE", "openai_compat"
        ) or "openai_compat",
        s3_grounding_base_url=_env(
            "JARVIS_S3_GROUNDING_BASE_URL", _env("JARVIS_LOCAL_LLM_BASE_URL")
        ),
        s3_grounding_api_key=_env(
            "JARVIS_S3_GROUNDING_API_KEY", _env("JARVIS_LOCAL_LLM_API_KEY")
        ),
        s3_grounding_model=_env("JARVIS_S3_GROUNDING_MODEL", "ui-tars-1.5-7b") or "ui-tars-1.5-7b",
        s3_grounding_width=_env_int("JARVIS_S3_GROUNDING_WIDTH", 1920),
        s3_grounding_height=_env_int("JARVIS_S3_GROUNDING_HEIGHT", 1080),
        s3_max_steps=_env_int("JARVIS_S3_MAX_STEPS", 15),
        s3_max_trajectory=_env_int("JARVIS_S3_MAX_TRAJECTORY", 8),
        s3_enable_reflection=_env_bool("JARVIS_S3_ENABLE_REFLECTION", True),
        s3_enable_code_agent=_env_bool("JARVIS_S3_ENABLE_CODE_AGENT", False),
        s3_code_agent_budget=_env_int("JARVIS_S3_CODE_AGENT_BUDGET", 20),
        s3_code_workdir=_env("JARVIS_S3_CODE_WORKDIR"),
        s3_max_image_dim=_env_int("JARVIS_S3_MAX_IMAGE_DIM", 1920),
    )


def ensure_dirs(config: Config) -> None:
    """Ensure required directories exist."""
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)


def get_env_template() -> str:
    """Get template for .env file with all configuration options."""
    return """# Jarvis Configuration
# Copy this to .env and fill in your values

# ============================================================================
# SELF-HOSTED BRAIN (local/VPS)
# ============================================================================
JARVIS_LOCAL_LLM_BASE_URL=
JARVIS_LOCAL_LLM_API_KEY=
JARVIS_LOCAL_LLM_MODEL=qwen2.5-7b-instruct
JARVIS_LOCAL_LLM_TIMEOUT_S=30
JARVIS_LOCAL_LLM_COOLDOWN_S=300

# Confidence gate (0-1)
JARVIS_LLM_CONFIDENCE_MIN=0.55

# Max failures before asking for guidance
JARVIS_MAX_FAILURES_PER_COMMAND=2
JARVIS_MAX_GUIDANCE_ATTEMPTS=2

# Browser AI (manual assist)
JARVIS_BROWSER_AI_ENABLED=true
JARVIS_BROWSER_AI_URL=https://chatgpt.com

# Auto-learn procedures after guidance success
JARVIS_AUTO_LEARN_PROCEDURES=true

# External/manual safety prompts
JARVIS_BLOCK_EXTERNAL_SENSITIVE=true
JARVIS_EXTERNAL_ASK_ON_SENSITIVE=true
JARVIS_SENSITIVE_KEYWORDS_STRICT=false

# User policy file (extra blocks)
JARVIS_POLICY_USER_PATH=~/.jarvis/policy_user.json

# Procedures book (SQLite)
JARVIS_PROCEDURES_PATH=~/.jarvis/procedures.db
JARVIS_PROCEDURES_MAX_TOTAL=300
JARVIS_PROCEDURES_MAX_PER_TAG=20
JARVIS_PROCEDURES_TTL_DAYS=90

# ============================================================================
# STT SETTINGS (Speech-to-Text)
# ============================================================================

# STT mode: local (faster-whisper), auto, none
JARVIS_STT_MODE=local

# ============================================================================
# TTS SETTINGS (Text-to-Speech)
# ============================================================================

# TTS mode: local (tries piper then espeak), none
JARVIS_TTS_MODE=local

# ============================================================================
# AGENT S3 SETTINGS (GUI agent)
# ============================================================================
JARVIS_S3_WORKER_ENGINE_TYPE=openai_compat
JARVIS_S3_WORKER_BASE_URL=
JARVIS_S3_WORKER_API_KEY=
JARVIS_S3_WORKER_MODEL=qwen2.5-7b-instruct
JARVIS_S3_GROUNDING_ENGINE_TYPE=openai_compat
JARVIS_S3_GROUNDING_BASE_URL=
JARVIS_S3_GROUNDING_API_KEY=
JARVIS_S3_GROUNDING_MODEL=ui-tars-1.5-7b
JARVIS_S3_GROUNDING_WIDTH=1920
JARVIS_S3_GROUNDING_HEIGHT=1080
JARVIS_S3_MAX_STEPS=15
JARVIS_S3_MAX_TRAJECTORY=8
JARVIS_S3_ENABLE_REFLECTION=true
JARVIS_S3_ENABLE_CODE_AGENT=false
JARVIS_S3_CODE_AGENT_BUDGET=20
JARVIS_S3_CODE_WORKDIR=
JARVIS_S3_MAX_IMAGE_DIM=1920

# ============================================================================
# SECURITY (Approval required for actions)
# ============================================================================

# Require approval for actions
JARVIS_REQUIRE_APPROVAL=true

# Approval mode: voice_and_key, voice_or_key, key_only
JARVIS_APPROVAL_MODE=voice_and_key

# Passphrases for approval
JARVIS_APPROVAL_VOICE_PASSPHRASE=jarvis
JARVIS_APPROVAL_KEY_PASSPHRASE=confirmar

# Whitelist of allowed contacts (comma-separated)
JARVIS_CONTACT_WHITELIST=

# Additional blocked domains (comma-separated)
JARVIS_BLOCKED_DOMAINS=

# ============================================================================
# PRIVACY
# ============================================================================

# Mask screenshots before sending to AI
JARVIS_MASK_SCREENSHOTS=true

# Apps to never capture screenshots (comma-separated)
JARVIS_BLACKLISTED_APPS=1password,bitwarden,keepass

# ============================================================================
# DATA STORAGE
# ============================================================================

# Local data directory
JARVIS_DATA_DIR=~/.jarvis

# ============================================================================
# DAILY BUDGET (LLM calls)
# ============================================================================
JARVIS_BUDGET_PATH=~/.jarvis/orcamento.json
JARVIS_BUDGET_MAX_CALLS=0
JARVIS_BUDGET_MAX_CHARS=0

# ============================================================================
# DEBUGGING
# ============================================================================

# Dry run mode (plan but don't execute)
JARVIS_DRY_RUN=false

# Allow opening apps
JARVIS_ALLOW_OPEN_APP=true
"""
