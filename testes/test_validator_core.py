"""Tests for jarvis.validacao.validator — mocked where PIL/OCR required."""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from jarvis.validacao.validator import (
    ValidationResult,
    _coerce_png_bytes,
    check_validator_deps,
)


# ---------------------------------------------------------------------------
# Pure helpers (no external deps)
# ---------------------------------------------------------------------------

class TestCoercePngBytes(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(_coerce_png_bytes(None))

    def test_bytes_passthrough(self) -> None:
        b = b"\x89PNG\r\n"
        self.assertEqual(_coerce_png_bytes(b), b)

    def test_bytearray_converts(self) -> None:
        ba = bytearray(b"hello")
        result = _coerce_png_bytes(ba)
        self.assertEqual(result, b"hello")

    def test_list_of_ints_converts(self) -> None:
        result = _coerce_png_bytes([72, 101, 108])
        self.assertEqual(result, b"Hel")

    def test_invalid_list_returns_none(self) -> None:
        result = _coerce_png_bytes([999, "bad"])
        self.assertIsNone(result)

    def test_string_returns_none(self) -> None:
        result = _coerce_png_bytes("not bytes")
        self.assertIsNone(result)


class TestValidationResultDataclass(unittest.TestCase):
    def test_defaults(self) -> None:
        r = ValidationResult(status="ok")
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.confidence, 1.0)
        self.assertEqual(r.details, {})
        self.assertIsNone(r.screenshot_path)
        self.assertIsNone(r.ocr_text)
        self.assertIsNone(r.error)

    def test_failed_with_error(self) -> None:
        r = ValidationResult(status="failed", error="Timeout", confidence=0.0)
        self.assertEqual(r.status, "failed")
        self.assertEqual(r.error, "Timeout")
        self.assertEqual(r.confidence, 0.0)

    def test_requires_human(self) -> None:
        r = ValidationResult(status="requires_human", details={"reason": "2FA"})
        self.assertEqual(r.status, "requires_human")
        self.assertEqual(r.details["reason"], "2FA")


class TestCheckValidatorDeps(unittest.TestCase):
    def test_returns_dict_with_keys(self) -> None:
        deps = check_validator_deps()
        self.assertIn("pillow", deps)
        self.assertIn("pytesseract", deps)
        self.assertIn("imagegrab", deps)
        self.assertIn("rust_vision", deps)

    def test_values_are_bool(self) -> None:
        deps = check_validator_deps()
        for key, val in deps.items():
            self.assertIsInstance(val, bool, f"{key} should be bool")


# ---------------------------------------------------------------------------
# Validator — init and logic with mocks
# ---------------------------------------------------------------------------

class TestValidatorInit(unittest.TestCase):
    def test_init_no_pil_no_ocr(self) -> None:
        """When PIL is absent, OCR must be disabled."""
        with patch("jarvis.validacao.validator.Image", None), \
             patch("jarvis.validacao.validator.pytesseract", None), \
             patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator()
            self.assertFalse(v.enable_ocr)

    def test_init_save_screenshots_creates_dir(self) -> None:
        import tempfile
        from pathlib import Path
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            tmp = Path(tempfile.mkdtemp())
            v = Validator(screenshot_dir=tmp, save_screenshots=True)
            self.assertTrue(tmp.exists())

    def test_ocr_cache_size_env(self) -> None:
        with patch.dict(os.environ, {"JARVIS_OCR_CACHE_SIZE": "8"}), \
             patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator()
            self.assertEqual(v._ocr_cache_size, 8)

    def test_ocr_cache_disabled_env(self) -> None:
        with patch.dict(os.environ, {"JARVIS_OCR_DISABLE_CACHE": "1"}), \
             patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator()
            self.assertFalse(v._ocr_cache_enabled)


class TestValidatorDetectCaptcha(unittest.TestCase):
    def _make_validator(self) -> object:
        with patch("jarvis.validacao.validator.RustValidator", None), \
             patch("jarvis.validacao.validator.pytesseract") as mock_tess, \
             patch("jarvis.validacao.validator.Image") as mock_img:
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            v._pytesseract = mock_tess
            return v

    def test_detect_captcha_from_text(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="please solve the captcha"):
                self.assertTrue(v.detect_captcha_or_2fa(mock_img))

    def test_detect_2fa_from_text(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="enter your 2fa code"):
                self.assertTrue(v.detect_captcha_or_2fa(mock_img))

    def test_no_captcha_clean_text(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="welcome to the app"):
                self.assertFalse(v.detect_captcha_or_2fa(mock_img))

    def test_no_ocr_returns_false(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None), \
             patch("jarvis.validacao.validator.pytesseract", None), \
             patch("jarvis.validacao.validator.Image", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            self.assertFalse(v.detect_captcha_or_2fa(MagicMock()))


class TestValidatorDetectError(unittest.TestCase):
    def test_detect_error_modal_error_keyword(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="erro ao processar"):
                result = v.detect_error_modal(mock_img)
                self.assertIsNotNone(result)

    def test_detect_error_access_denied(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="acesso negado"):
                result = v.detect_error_modal(mock_img)
                self.assertEqual(result, "Access denied")

    def test_no_error_returns_none(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            with patch.object(v, "extract_text_ocr", return_value="bem vindo ao painel"):
                result = v.detect_error_modal(mock_img)
                self.assertIsNone(result)


class TestValidatorOCRCache(unittest.TestCase):
    def test_cache_stores_and_returns(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None), \
             patch("jarvis.validacao.validator.pytesseract") as mock_tess, \
             patch("jarvis.validacao.validator.Image") as mock_pil:
            import io
            mock_pil.open.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_tess.image_to_string.return_value = "texto extraido"

            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)

            # populate cache manually
            v._store_ocr_cache("abc123", "cached text")
            cached = v._ocr_cache.get("abc123")
            self.assertEqual(cached, "cached text")

    def test_cache_eviction(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator()
            v._ocr_cache_size = 2
            v._ocr_cache_enabled = True
            v._store_ocr_cache("k1", "v1")
            v._store_ocr_cache("k2", "v2")
            v._store_ocr_cache("k3", "v3")  # should evict k1
            self.assertNotIn("k1", v._ocr_cache)
            self.assertIn("k3", v._ocr_cache)

    def test_cache_skip_when_disabled(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator()
            v._ocr_cache_enabled = False
            v._store_ocr_cache("key", "value")
            self.assertNotIn("key", v._ocr_cache)


class TestValidatorValidate(unittest.TestCase):
    """Test the main validate() method with a fully mocked validator."""

    def _make_validator_no_screenshot(self) -> object:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            v.take_screenshot = MagicMock(return_value=None)
            return v

    def test_validate_returns_dict(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_validator_no_screenshot()
        action = Action(action_type="wait", params={})
        result = v.validate(action)
        self.assertIn("status", result)
        self.assertIn("confidence", result)

    def test_validate_safe_action_ok(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_validator_no_screenshot()
        action = Action(action_type="open_app", params={"app": "firefox"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_validate_detects_captcha(self) -> None:
        from jarvis.cerebro.actions import Action
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_screenshot = MagicMock()
            v.take_screenshot = MagicMock(return_value=mock_screenshot)
            v.detect_captcha_or_2fa = MagicMock(return_value=True)
            action = Action(action_type="click", params={})
            result = v.validate(action)
            self.assertEqual(result["status"], "requires_human")

    def test_validate_detects_error_modal(self) -> None:
        from jarvis.cerebro.actions import Action
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_screenshot = MagicMock()
            v.take_screenshot = MagicMock(return_value=mock_screenshot)
            v.detect_captcha_or_2fa = MagicMock(return_value=False)
            v.detect_error_modal = MagicMock(return_value="Timeout")
            action = Action(action_type="click", params={})
            result = v.validate(action)
            self.assertEqual(result["status"], "failed")


class TestValidatorCheckpoint(unittest.TestCase):
    def test_save_checkpoint_no_screenshot(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            v.take_screenshot = MagicMock(return_value=None)
            result = v.save_checkpoint("test_cp")
            self.assertFalse(result)

    def test_compare_missing_checkpoint(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            result = v.compare_with_checkpoint("nonexistent")
            self.assertEqual(result.status, "unknown")
            self.assertIn("nonexistent", result.error)

    def test_compare_no_current_screenshot(self) -> None:
        from jarvis.validacao.validator import ValidationCheckpoint
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            import time
            v = Validator(enable_ocr=False)
            v._checkpoints["cp"] = ValidationCheckpoint(
                name="cp", screenshot=None, ocr_text="",
                timestamp=time.time(), expected_elements=["button"]
            )
            v.take_screenshot = MagicMock(return_value=None)
            result = v.compare_with_checkpoint("cp")
            self.assertEqual(result.status, "unknown")

    def test_compare_missing_elements(self) -> None:
        from jarvis.validacao.validator import ValidationCheckpoint
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            import time
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            v._checkpoints["cp"] = ValidationCheckpoint(
                name="cp", screenshot=mock_img, ocr_text="",
                timestamp=time.time(), expected_elements=["Save button", "Title bar"]
            )
            v.take_screenshot = MagicMock(return_value=mock_img)
            v.extract_text_ocr = MagicMock(return_value="nothing here")
            result = v.compare_with_checkpoint("cp")
            self.assertEqual(result.status, "failed")
            self.assertIn("missing_elements", result.details)

    def test_compare_all_elements_found(self) -> None:
        from jarvis.validacao.validator import ValidationCheckpoint
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            import time
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            v._checkpoints["cp"] = ValidationCheckpoint(
                name="cp", screenshot=mock_img, ocr_text="",
                timestamp=time.time(), expected_elements=["save button"]
            )
            v.take_screenshot = MagicMock(return_value=mock_img)
            v.extract_text_ocr = MagicMock(return_value="click save button here")
            result = v.compare_with_checkpoint("cp")
            self.assertEqual(result.status, "ok")


class TestResizeForOCR(unittest.TestCase):
    def test_no_resize_when_max_dim_zero(self) -> None:
        from jarvis.validacao.validator import _resize_for_ocr
        mock_img = MagicMock()
        mock_img.size = (1920, 1080)
        with patch.dict(os.environ, {"JARVIS_OCR_FAST_MAX_DIM": "0"}):
            result = _resize_for_ocr(mock_img)
            self.assertIs(result, mock_img)
            mock_img.resize.assert_not_called()

    def test_resize_when_exceeds_max(self) -> None:
        from jarvis.validacao.validator import _resize_for_ocr
        mock_img = MagicMock()
        mock_img.size = (1920, 1080)
        mock_img.resize.return_value = mock_img
        with patch.dict(os.environ, {"JARVIS_OCR_FAST_MAX_DIM": "800"}):
            result = _resize_for_ocr(mock_img)
            mock_img.resize.assert_called_once()

    def test_no_resize_when_smaller_than_max(self) -> None:
        from jarvis.validacao.validator import _resize_for_ocr
        mock_img = MagicMock()
        mock_img.size = (400, 300)
        with patch.dict(os.environ, {"JARVIS_OCR_FAST_MAX_DIM": "800"}):
            result = _resize_for_ocr(mock_img)
            self.assertIs(result, mock_img)

    def test_none_image_returns_none(self) -> None:
        from jarvis.validacao.validator import _resize_for_ocr
        result = _resize_for_ocr(None)
        self.assertIsNone(result)


class TestValidatorExtractTextOCR(unittest.TestCase):
    def test_extract_empty_when_no_ocr(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            result = v.extract_text_ocr(MagicMock())
            self.assertEqual(result, "")

    def test_extract_with_pytesseract(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None), \
             patch("jarvis.validacao.validator.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "  hello world  "
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            result = v.extract_text_ocr(mock_img)
            self.assertEqual(result, "hello world")

    def test_extract_caches_result(self) -> None:
        with patch("jarvis.validacao.validator.RustValidator", None), \
             patch("jarvis.validacao.validator.pytesseract") as mock_tess:
            mock_tess.image_to_string.return_value = "cached text"
            from jarvis.validacao.validator import Validator
            import io as _io
            v = Validator(enable_ocr=True)
            # Pre-seed cache
            v._store_ocr_cache("deadbeef" * 4, "already cached")
            # Verify cache works on _store_ocr_cache path
            cached = v._ocr_cache.get("deadbeef" * 4)
            self.assertEqual(cached, "already cached")


class TestValidateActionRouting(unittest.TestCase):
    """Test _validate_action routes to the right sub-validator."""

    def _make_v(self) -> object:
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=True)
            v.take_screenshot = MagicMock(return_value=MagicMock())
            v.detect_captcha_or_2fa = MagicMock(return_value=False)
            v.detect_error_modal = MagicMock(return_value=None)
            return v

    def test_open_url_found_in_screen(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        v.extract_text_ocr = MagicMock(return_value="google.com search")
        action = Action(action_type="open_url", params={"url": "https://google.com"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_open_app_found_in_screen(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        v.extract_text_ocr = MagicMock(return_value="Firefox browser window")
        action = Action(action_type="open_app", params={"app": "Firefox"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_type_text_found_in_screen(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        v.extract_text_ocr = MagicMock(return_value="hello world typing done")
        action = Action(action_type="type_text", params={"text": "hello world"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_type_text_partial_match(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        # Only half the words found → partial match confidence
        v.extract_text_ocr = MagicMock(return_value="hello nothing else")
        action = Action(action_type="type_text", params={"text": "hello world complete"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_type_text_not_found(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        v.extract_text_ocr = MagicMock(return_value="completely different content")
        action = Action(action_type="type_text", params={"text": "xyzzy frobnicator"})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_default_action_ok(self) -> None:
        from jarvis.cerebro.actions import Action
        v = self._make_v()
        action = Action(action_type="scroll", params={})
        result = v.validate(action)
        self.assertEqual(result["status"], "ok")

    def test_validate_no_screenshot(self) -> None:
        from jarvis.cerebro.actions import Action
        with patch("jarvis.validacao.validator.RustValidator", None):
            from jarvis.validacao.validator import Validator
            v = Validator(enable_ocr=False)
            v.take_screenshot = MagicMock(return_value=None)
            action = Action(action_type="open_url", params={"url": "https://example.com"})
            result = v.validate(action)
            # No screenshot → low confidence ok
            self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
