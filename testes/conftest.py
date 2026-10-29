"""Pytest configuration for Jarvis tests.

This file ensures that the project root is in sys.path so that imports
of 'jarvis' and 'scripts' modules work correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


