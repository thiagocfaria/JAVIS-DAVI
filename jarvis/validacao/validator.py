"""
Validator module for verifying action results.

Uses OCR and screenshots to validate that actions completed successfully.
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..cerebro.actions import Action
from ..seguranca.privacy import PrivacyMasker, SensitiveRegion

try:
    from PIL import Image, ImageGrab  # type: ignore
except ImportError:
    Image = None
    ImageGrab = None

try:
    import pytesseract  # type: ignore
except ImportError:
    pytesseract = None

try:
    from jarvis_vision import Validator as RustValidator  # type: ignore
except ImportError:
    RustValidator = None

try:
    import subprocess
except ImportError:
    subprocess = None


def _image_to_png_bytes(image: Image.Image) -> bytes | None:
    if image is None:
        return None
    try:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None


def _coerce_png_bytes(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, list):
        try:
            return bytes(value)
        except Exception:
            return None
    return None


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    if image is None:
        return image
    max_dim = int(os.environ.get("JARVIS_OCR_FAST_MAX_DIM", "0") or 0)
    if max_dim <= 0:
        return image
    width, height = image.size
    if max(width, height) <= max_dim:
        return image
    scale = max_dim / float(max(width, height))
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.BILINEAR)


@dataclass
class ValidationResult:
    """Result of action validation."""
    status: str  # "ok", "failed", "unknown", "requires_human"
    confidence: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)
    screenshot_path: str | None = None
    ocr_text: str | None = None
    error: str | None = None


@dataclass
class ValidationCheckpoint:
    """A saved state checkpoint for validation."""
    name: str
    screenshot: Image.Image | None
    ocr_text: str
    timestamp: float
    expected_elements: list[str] = field(default_factory=list)


class Validator:
    """
    Validates action results using OCR and screenshots.
    
    Features:
    - Screenshot capture before/after actions
    - OCR-based text validation
    - Visual checkpoint comparison
    - CAPTCHA/2FA detection
    - Privacy masking before external analysis
    """

    def __init__(
        self,
        screenshot_dir: Path | None = None,
        enable_ocr: bool = True,
        save_screenshots: bool = False,
        mask_screenshots: bool = True,
    ) -> None:
        self.screenshot_dir = screenshot_dir or Path(tempfile.gettempdir()) / "jarvis_screenshots"
        self._rust_validator = None
        self._force_rust = os.environ.get("JARVIS_FORCE_RUST_VISION", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        disable_rust = os.environ.get("JARVIS_DISABLE_RUST_VISION", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if RustValidator is not None and not disable_rust:
            try:
                self._rust_validator = RustValidator(
                    screenshot_dir=str(self.screenshot_dir),
                    enable_ocr=enable_ocr,
                    save_screenshots=save_screenshots,
                )
            except Exception:
                self._rust_validator = None
        if self._force_rust and self._rust_validator is None:
            raise RuntimeError("Rust vision requerido, mas jarvis_vision nao esta disponivel.")
        self.enable_ocr = enable_ocr and (pytesseract is not None or self._rust_validator is not None)
        self.save_screenshots = save_screenshots
        self.mask_screenshots = mask_screenshots
        self.privacy_masker = PrivacyMasker()
        self._checkpoints: dict[str, ValidationCheckpoint] = {}
        self._ocr_cache_enabled = os.environ.get("JARVIS_OCR_DISABLE_CACHE", "").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._ocr_cache_size = max(0, int(os.environ.get("JARVIS_OCR_CACHE_SIZE", "4") or 0))
        self._ocr_cache: dict[str, str] = {}
        self._ocr_cache_order: list[str] = []

        if self.save_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def _mask_for_export(self, image: Image.Image) -> Image.Image:
        if not self.mask_screenshots:
            return image
        try:
            masked = self.privacy_masker.process_screenshot(image)
            return masked or image
        except Exception:
            return image

    def take_screenshot(self) -> Image.Image | None:
        """Take a screenshot of the current screen."""
        if self._rust_validator is not None:
            png_bytes = _coerce_png_bytes(self._rust_validator.take_screenshot_png())
            if png_bytes and Image is not None:
                try:
                    with Image.open(io.BytesIO(png_bytes)) as img:
                        img.load()
                        return img.copy()
                except Exception:
                    return None
            if self._force_rust:
                return None

        if Image is None:
            return None

        try:
            # Try PIL ImageGrab first (works on many platforms)
            if ImageGrab is not None:
                return ImageGrab.grab()
        except Exception:
            pass

        # Fallback: use gnome-screenshot or scrot on Linux
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            session = os.environ.get("XDG_SESSION_TYPE", "").lower()
            prefer_scrot = session == "x11"
            commands: list[list[str]] = []
            if prefer_scrot:
                commands.append(["scrot", tmp_path])
            else:
                if shutil.which("grim"):
                    commands.append(["grim", tmp_path])
                commands.append(["gnome-screenshot", "-f", tmp_path])
                commands.append(["scrot", tmp_path])

            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                if result.returncode == 0 and os.path.exists(tmp_path):
                    img = Image.open(tmp_path)
                    img.load()  # Load into memory
                    os.unlink(tmp_path)
                    return img

        except Exception:
            pass

        return None

    def extract_text_ocr(self, image: Image.Image) -> str:
        """Extract text from image using OCR."""
        if image is None or not self.enable_ocr:
            return ""

        cache_key = None
        if self._ocr_cache_enabled and self._ocr_cache_size > 0:
            png_bytes = _image_to_png_bytes(image)
            if png_bytes:
                cache_key = hashlib.md5(png_bytes).hexdigest()
                cached = self._ocr_cache.get(cache_key)
                if cached is not None:
                    return cached

        if self._rust_validator is not None:
            png_bytes = _image_to_png_bytes(image)
            if png_bytes:
                text = self._rust_validator.ocr_text(png_bytes)
                if text:
                    result = text.strip()
                    self._store_ocr_cache(cache_key, result)
                    return result
            if self._force_rust:
                return ""

        if pytesseract is None:
            return ""

        try:
            # Use Portuguese + English
            image_for_ocr = _resize_for_ocr(image)
            text = pytesseract.image_to_string(
                image_for_ocr,
                lang="por+eng",
                config="--oem 1 --psm 6",
            )
            result = text.strip()
            self._store_ocr_cache(cache_key, result)
            return result
        except Exception:
            return ""

    def _store_ocr_cache(self, cache_key: str | None, text: str) -> None:
        if not cache_key or not self._ocr_cache_enabled or self._ocr_cache_size <= 0:
            return
        self._ocr_cache[cache_key] = text
        self._ocr_cache_order.append(cache_key)
        if len(self._ocr_cache_order) > self._ocr_cache_size:
            oldest = self._ocr_cache_order.pop(0)
            self._ocr_cache.pop(oldest, None)

    def save_checkpoint(
        self,
        name: str,
        expected_elements: list[str] | None = None,
    ) -> bool:
        """
        Save a visual checkpoint for later comparison.
        
        Args:
            name: Checkpoint identifier
            expected_elements: Text elements expected to be present
            
        Returns:
            True if checkpoint saved successfully
        """
        if self._rust_validator is not None:
            return bool(self._rust_validator.save_checkpoint(name, expected_elements or []))

        screenshot = self.take_screenshot()
        if screenshot is None:
            return False

        ocr_text = self.extract_text_ocr(screenshot) if self.enable_ocr else ""

        self._checkpoints[name] = ValidationCheckpoint(
            name=name,
            screenshot=screenshot,
            ocr_text=ocr_text,
            timestamp=time.time(),
            expected_elements=expected_elements or [],
        )

        if self.save_screenshots:
            path = self.screenshot_dir / f"checkpoint_{name}_{int(time.time())}.png"
            self._mask_for_export(screenshot).save(str(path))

        return True

    def compare_with_checkpoint(
        self,
        checkpoint_name: str,
        similarity_threshold: float = 0.8,
    ) -> ValidationResult:
        """
        Compare current screen with a saved checkpoint.
        
        Args:
            checkpoint_name: Name of saved checkpoint
            similarity_threshold: Minimum similarity (0-1) to consider match
            
        Returns:
            ValidationResult with comparison details
        """
        if self._rust_validator is not None:
            result = self._rust_validator.compare_with_checkpoint(
                checkpoint_name,
                similarity_threshold,
            )
            return ValidationResult(
                status=result.get("status", "unknown"),
                confidence=float(result.get("confidence", 1.0)),
                details=result.get("details", {}) or {},
                ocr_text=result.get("ocr_text"),
                error=result.get("error") or None,
            )

        if checkpoint_name not in self._checkpoints:
            return ValidationResult(
                status="unknown",
                error=f"Checkpoint '{checkpoint_name}' not found",
            )

        checkpoint = self._checkpoints[checkpoint_name]
        current_screenshot = self.take_screenshot()

        if current_screenshot is None:
            return ValidationResult(
                status="unknown",
                error="Could not take screenshot",
            )

        current_text = self.extract_text_ocr(current_screenshot) if self.enable_ocr else ""

        # Check expected elements
        missing_elements = []
        for element in checkpoint.expected_elements:
            if element.lower() not in current_text.lower():
                missing_elements.append(element)

        if missing_elements:
            return ValidationResult(
                status="failed",
                confidence=1.0 - (len(missing_elements) / len(checkpoint.expected_elements)),
                details={
                    "missing_elements": missing_elements,
                    "expected": checkpoint.expected_elements,
                },
                ocr_text=current_text,
            )

        return ValidationResult(
            status="ok",
            confidence=1.0,
            details={"matched_elements": checkpoint.expected_elements},
            ocr_text=current_text,
        )

    def detect_captcha_or_2fa(self, image: Image.Image | None = None) -> bool:
        """
        Detect if current screen shows CAPTCHA or 2FA prompt.
        
        Returns:
            True if CAPTCHA/2FA detected (requires human intervention)
        """
        if self._rust_validator is not None:
            png_bytes = _image_to_png_bytes(image) if image is not None else None
            return bool(self._rust_validator.detect_captcha_or_2fa(png_bytes))

        if image is None:
            image = self.take_screenshot()

        if image is None or not self.enable_ocr:
            return False

        text = self.extract_text_ocr(image).lower()

        # CAPTCHA indicators
        captcha_patterns = [
            r"captcha",
            r"recaptcha",
            r"hcaptcha",
            r"prove.*human",
            r"robot",
            r"não.*robô",
            r"selecione.*imagens",
            r"select.*images",
            r"verify.*human",
        ]

        # 2FA indicators
        twofa_patterns = [
            r"two.?factor",
            r"2fa",
            r"dois.*fatores",
            r"verification.*code",
            r"código.*verificação",
            r"enter.*code",
            r"digite.*código",
            r"sms.*code",
            r"authenticator",
            r"autenticador",
        ]

        all_patterns = captcha_patterns + twofa_patterns

        for pattern in all_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def detect_error_modal(self, image: Image.Image | None = None) -> str | None:
        """
        Detect error modals or unexpected dialogs.
        
        Returns:
            Error message if detected, None otherwise
        """
        if self._rust_validator is not None:
            png_bytes = _image_to_png_bytes(image) if image is not None else None
            return self._rust_validator.detect_error_modal(png_bytes) or None

        if image is None:
            image = self.take_screenshot()

        if image is None or not self.enable_ocr:
            return None

        text = self.extract_text_ocr(image).lower()

        error_patterns = [
            (r"erro|error", "Error detected"),
            (r"falha|failed|failure", "Failure detected"),
            (r"não.*encontrado|not.*found", "Not found"),
            (r"acesso.*negado|access.*denied", "Access denied"),
            (r"conexão.*perdida|connection.*lost", "Connection lost"),
            (r"tempo.*esgotado|timeout|timed.*out", "Timeout"),
            (r"inválido|invalid", "Invalid input"),
        ]

        for pattern, message in error_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return message

        return None

    def validate(self, action: Action) -> dict[str, str]:
        """
        Validate that an action completed successfully.
        
        This is the main validation entry point.
        
        Args:
            action: The action that was executed
            
        Returns:
            Dictionary with validation status and details
        """
        if self._rust_validator is not None:
            result = self._rust_validator.validate_action(action.action_type, action.params or {})
            return {
                "status": result.get("status", "unknown"),
                "confidence": str(result.get("confidence", 1.0)),
                "error": result.get("error") or "",
            }

        result = self._validate_action(action)
        return {
            "status": result.status,
            "confidence": str(result.confidence),
            "error": result.error or "",
        }

    def _validate_action(self, action: Action) -> ValidationResult:
        """Internal validation logic."""
        action_type = action.action_type
        params = action.params or {}

        # Take screenshot for validation
        screenshot = self.take_screenshot()

        # Check for CAPTCHA/2FA (requires human)
        if screenshot and self.detect_captcha_or_2fa(screenshot):
            return ValidationResult(
                status="requires_human",
                details={"reason": "CAPTCHA or 2FA detected"},
            )

        # Check for error modals
        if screenshot:
            error = self.detect_error_modal(screenshot)
            if error:
                return ValidationResult(
                    status="failed",
                    error=error,
                    details={"detected_error": error},
                )

        # Action-specific validation
        if action_type == "open_app":
            return self._validate_open_app(params.get("app", ""), screenshot)

        if action_type == "open_url":
            return self._validate_open_url(params.get("url", ""), screenshot)

        if action_type == "type_text":
            return self._validate_type_text(params.get("text", ""), screenshot)

        # Default: assume success if no errors detected
        return ValidationResult(status="ok", confidence=0.8)

    def _validate_open_app(
        self,
        app_name: str,
        screenshot: Image.Image | None,
    ) -> ValidationResult:
        """Validate that an app was opened."""
        if not screenshot or not self.enable_ocr:
            return ValidationResult(status="ok", confidence=0.5)

        # Check if app name appears in window title (via OCR)
        text = self.extract_text_ocr(screenshot)
        app_lower = app_name.lower()

        # Common app name variations
        if app_lower in text.lower():
            return ValidationResult(
                status="ok",
                confidence=0.9,
                details={"app_found_in_screen": True},
            )

        # App might have opened but name not visible
        return ValidationResult(status="ok", confidence=0.6)

    def _validate_open_url(
        self,
        url: str,
        screenshot: Image.Image | None,
    ) -> ValidationResult:
        """Validate that a URL was opened."""
        if not screenshot or not self.enable_ocr:
            return ValidationResult(status="ok", confidence=0.5)

        text = self.extract_text_ocr(screenshot)

        # Extract domain from URL
        domain = url.replace("https://", "").replace("http://", "").split("/")[0]

        if domain.lower() in text.lower():
            return ValidationResult(
                status="ok",
                confidence=0.9,
                details={"url_found_in_screen": True},
            )

        return ValidationResult(status="ok", confidence=0.6)

    def _validate_type_text(
        self,
        expected_text: str,
        screenshot: Image.Image | None,
    ) -> ValidationResult:
        """Validate that text was typed correctly."""
        if not screenshot or not self.enable_ocr or not expected_text:
            return ValidationResult(status="ok", confidence=0.5)

        text = self.extract_text_ocr(screenshot)

        # Check if typed text appears on screen
        if expected_text.lower() in text.lower():
            return ValidationResult(
                status="ok",
                confidence=0.95,
                details={"text_found_in_screen": True},
            )

        # Partial match
        words = expected_text.lower().split()
        found_words = sum(1 for word in words if word in text.lower())
        ratio = found_words / len(words) if words else 0

        if ratio >= 0.5:
            return ValidationResult(
                status="ok",
                confidence=0.7,
                details={"partial_match": ratio},
            )

        return ValidationResult(
            status="ok",
            confidence=0.5,
            details={"text_not_verified": True},
        )

    def get_masked_screenshot_for_ai(
        self,
        app_name: str | None = None,
        url: str | None = None,
    ) -> Image.Image | None:
        """
        Get a privacy-masked screenshot safe for sending to external AI.
        
        Returns None if the current app/URL should not be captured.
        """
        if self._rust_validator is not None:
            png_bytes = _coerce_png_bytes(
                self._rust_validator.get_masked_screenshot_for_ai(app_name, url)
            )
            if png_bytes and Image is not None:
                try:
                    with Image.open(io.BytesIO(png_bytes)) as img:
                        img.load()
                        return img.copy()
                except Exception:
                    return None
            if self._force_rust:
                return None

        # Check if screenshot is allowed
        from ..seguranca.policy import get_policy_kernel
        policy = get_policy_kernel()
        decision = policy.check_screenshot_allowed(app_name or "", url or "")

        if not decision.allowed:
            return None

        screenshot = self.take_screenshot()
        if screenshot is None:
            return None

        # Apply privacy masking
        return self.privacy_masker.process_screenshot(
            screenshot,
            app_name=app_name,
            url=url,
            auto_detect=True,
            use_blur=True,
        )


def check_validator_deps() -> dict:
    """Check which validator dependencies are available."""
    return {
        "pillow": Image is not None,
        "pytesseract": pytesseract is not None,
        "imagegrab": ImageGrab is not None,
        "rust_vision": RustValidator is not None,
    }
