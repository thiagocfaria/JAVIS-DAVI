"""
Privacy module for masking sensitive data before sending to external AI.

This module provides functionality to:
1. Detect sensitive areas in screenshots (CPF, credit cards, emails, passwords)
2. Apply blur/mask to detected areas
3. Redact sensitive text before sending
4. Blacklist certain apps from ever sending screenshots
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage, ImageDraw, ImageFilter

try:
    from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFilter as _ImageFilter  # type: ignore
    Image = _Image
    ImageDraw = _ImageDraw
    ImageFilter = _ImageFilter
except ImportError:
    Image = None
    ImageDraw = None
    ImageFilter = None

try:
    import pytesseract  # type: ignore
except ImportError:
    pytesseract = None


# ============================================================================
# SENSITIVE DATA PATTERNS (regex)
# ============================================================================

PATTERNS = {
    # Brazilian CPF: XXX.XXX.XXX-XX or XXXXXXXXXXX
    "cpf": re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    # Brazilian CNPJ: XX.XXX.XXX/XXXX-XX
    "cnpj": re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),
    # Credit card numbers (13-19 digits, with optional spaces/dashes)
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3,4}\d{1,4}\b"),
    # CVV (3-4 digits, typically labeled)
    "cvv": re.compile(r"\b(?:cvv|cvc|csc)[\s:]*\d{3,4}\b", re.IGNORECASE),
    # Email addresses
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    # Phone numbers (Brazilian format)
    "phone": re.compile(r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}\b"),
    # Passwords (common patterns in forms)
    "password": re.compile(r"(?:senha|password|pwd)[\s:]*\S+", re.IGNORECASE),
    # PIX keys (various formats)
    "pix": re.compile(r"\b(?:pix|chave)[\s:]*\S+", re.IGNORECASE),
    # Bank account numbers
    "bank_account": re.compile(
        r"\b(?:conta|ag[eê]ncia)[\s:]*\d+[-\s]?\d*\b", re.IGNORECASE
    ),
    # Monetary values (R$ XX.XXX,XX)
    "money": re.compile(r"R\$\s*[\d.,]+"),
    # RG (Brazilian ID)
    "rg": re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[0-9Xx]\b"),
}

# Apps that should NEVER have screenshots sent to external AI
BLACKLISTED_APPS: set[str] = {
    # Password managers
    "1password",
    "bitwarden",
    "keepass",
    "keepassxc",
    "lastpass",
    "dashlane",
    # Banking apps
    "nubank",
    "itau",
    "bradesco",
    "santander",
    "caixa",
    "bb",
    "inter",
    "banco do brasil",
    "original",
    "c6bank",
    "picpay",
    "mercadopago",
    # Crypto wallets
    "metamask",
    "exodus",
    "ledger",
    "trezor",
    # Secure terminals
    "gnome-keyring",
    "seahorse",
}

# Additional blocked domains for URLs
BLOCKED_DOMAINS: set[str] = {
    "banco",
    "bank",
    "pix",
    "nubank",
    "itau",
    "bradesco",
    "santander",
    "caixa",
    "bb.com",
    "inter",
    "c6bank",
    "picpay",
    "mercadopago",
    "paypal",
    "stripe",
    "binance",
    "coinbase",
}


@dataclass
class SensitiveRegion:
    """Represents a sensitive region in an image."""

    x: int
    y: int
    width: int
    height: int
    pattern_type: str
    confidence: float = 1.0


@dataclass
class PrivacyConfig:
    """Configuration for privacy masking."""

    blur_radius: int = 15
    mask_color: tuple[int, int, int] = (0, 0, 0)
    expand_region_px: int = 10
    blacklisted_apps: set[str] = field(default_factory=lambda: BLACKLISTED_APPS.copy())
    blocked_domains: set[str] = field(default_factory=lambda: BLOCKED_DOMAINS.copy())
    patterns: dict = field(default_factory=lambda: PATTERNS.copy())


class PrivacyMasker:
    """
    Masks sensitive data in screenshots before sending to external AI.

    Features:
    - OCR-based detection of sensitive text
    - Regex-based pattern matching
    - Blur or solid mask options
    - App blacklisting
    """

    def __init__(self, config: PrivacyConfig | None = None) -> None:
        self.config = config or PrivacyConfig()

        # Load additional blacklisted apps from environment
        env_apps = os.environ.get("JARVIS_BLACKLISTED_APPS", "")
        if env_apps:
            for app in env_apps.split(","):
                self.config.blacklisted_apps.add(app.strip().lower())

    def is_app_blacklisted(self, app_name: str) -> bool:
        """Check if an app is blacklisted from screenshot capture."""
        if not app_name:
            return False
        app_lower = app_name.lower()
        for blacklisted in self.config.blacklisted_apps:
            if blacklisted in app_lower:
                return True
        return False

    def is_url_blocked(self, url: str) -> bool:
        """Check if a URL should be blocked from screenshot capture."""
        if not url:
            return False
        url_lower = url.lower()
        for domain in self.config.blocked_domains:
            if domain in url_lower:
                return True
        return False

    def detect_sensitive_text(self, text: str) -> list[tuple[str, str, int, int]]:
        """
        Detect sensitive patterns in text.

        Returns:
            List of (pattern_type, matched_text, start, end) tuples
        """
        results = []
        for pattern_name, pattern in self.config.patterns.items():
            for match in pattern.finditer(text):
                results.append(
                    (pattern_name, match.group(), match.start(), match.end())
                )
        return results

    def redact_text(self, text: str) -> str:
        """
        Redact sensitive patterns from text.

        Returns:
            Text with sensitive data replaced by [REDACTED]
        """
        result = text
        # Sort matches by position (reverse) to avoid offset issues
        all_matches = []
        for pattern_name, pattern in self.config.patterns.items():
            for match in pattern.finditer(text):
                all_matches.append((match.start(), match.end(), pattern_name))

        # Replace from end to start
        for start, end, pattern_name in sorted(all_matches, reverse=True):
            placeholder = f"[{pattern_name.upper()}]"
            result = result[:start] + placeholder + result[end:]

        return result

    def detect_sensitive_regions_ocr(self, image: "PILImage.Image") -> list[SensitiveRegion]:
        """
        Detect sensitive regions in an image using OCR.

        Requires pytesseract to be installed.
        """
        if pytesseract is None:
            return []

        if Image is None:
            return []

        regions = []

        try:
            # Get OCR data with bounding boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                text = data["text"][i]
                if not text or not text.strip():
                    continue

                # Check against patterns
                for pattern_name, pattern in self.config.patterns.items():
                    if pattern.search(text):
                        x = data["left"][i]
                        y = data["top"][i]
                        w = data["width"][i]
                        h = data["height"][i]
                        conf = (
                            float(data["conf"][i]) / 100.0
                            if data["conf"][i] != -1
                            else 0.5
                        )

                        regions.append(
                            SensitiveRegion(
                                x=x - self.config.expand_region_px,
                                y=y - self.config.expand_region_px,
                                width=w + 2 * self.config.expand_region_px,
                                height=h + 2 * self.config.expand_region_px,
                                pattern_type=pattern_name,
                                confidence=conf,
                            )
                        )
        except Exception:
            pass  # OCR failed, return empty list

        return regions

    def mask_image(
        self,
        image: "PILImage.Image",
        regions: list[SensitiveRegion] | None = None,
        use_blur: bool = True,
    ) -> "PILImage.Image":
        """
        Mask sensitive regions in an image.

        Args:
            image: PIL Image to mask
            regions: List of regions to mask (auto-detects if None)
            use_blur: Use blur (True) or solid color (False)

        Returns:
            Masked image
        """
        if Image is None:
            raise RuntimeError("PIL/Pillow not installed")

        if regions is None:
            regions = self.detect_sensitive_regions_ocr(image)

        if not regions:
            return image

        result = image.copy()

        for region in regions:
            x1 = max(0, region.x)
            y1 = max(0, region.y)
            x2 = min(image.width, region.x + region.width)
            y2 = min(image.height, region.y + region.height)

            if x2 <= x1 or y2 <= y1:
                continue

            if use_blur:
                # Extract region, blur, and paste back
                box = (x1, y1, x2, y2)
                region_img = result.crop(box)
                if ImageFilter is None:
                    raise RuntimeError("PIL not available")
                blurred = region_img.filter(
                    ImageFilter.GaussianBlur(radius=self.config.blur_radius)
                )
                result.paste(blurred, box)
            else:
                # Draw solid rectangle
                if ImageDraw is None:
                    raise RuntimeError("PIL not available")
                draw = ImageDraw.Draw(result)
                draw.rectangle([x1, y1, x2, y2], fill=self.config.mask_color)

        return result

    def crop_relevant_area(
        self,
        image: "PILImage.Image",
        focus_x: int,
        focus_y: int,
        context_px: int = 200,
    ) -> "PILImage.Image":
        """
        Crop image to relevant area around a focus point.

        This reduces the amount of potentially sensitive data sent.

        Args:
            image: Full screenshot
            focus_x, focus_y: Center point of interest
            context_px: Pixels of context around focus

        Returns:
            Cropped image
        """
        if Image is None:
            raise RuntimeError("PIL/Pillow not installed")

        x1 = max(0, focus_x - context_px)
        y1 = max(0, focus_y - context_px)
        x2 = min(image.width, focus_x + context_px)
        y2 = min(image.height, focus_y + context_px)

        return image.crop((x1, y1, x2, y2))

    def process_screenshot(
        self,
        image: "PILImage.Image",
        app_name: str | None = None,
        url: str | None = None,
        auto_detect: bool = True,
        use_blur: bool = True,
    ) -> "PILImage.Image | None":
        """
        Process a screenshot for safe sending to external AI.

        Returns None if the screenshot should not be sent at all.

        Args:
            image: Screenshot to process
            app_name: Name of the app in the screenshot
            url: URL if it's a browser screenshot
            auto_detect: Automatically detect sensitive regions
            use_blur: Use blur instead of solid mask

        Returns:
            Processed image or None if blocked
        """
        # Check blacklists
        if app_name and self.is_app_blacklisted(app_name):
            return None

        if url and self.is_url_blocked(url):
            return None

        # Detect and mask sensitive regions
        regions = self.detect_sensitive_regions_ocr(image) if auto_detect else []

        return self.mask_image(image, regions, use_blur)


def redact_sensitive_text(text: str) -> str:
    """Convenience function to redact sensitive text."""
    masker = PrivacyMasker()
    return masker.redact_text(text)


def is_app_safe_for_screenshot(app_name: str) -> bool:
    """Check if an app is safe for screenshot capture."""
    masker = PrivacyMasker()
    return not masker.is_app_blacklisted(app_name)


def check_privacy_deps() -> dict:
    """Check which privacy dependencies are available."""
    return {
        "pillow": Image is not None,
        "pytesseract": pytesseract is not None,
    }
