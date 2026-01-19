"""Compat: entrypoint legacy para jarvis.app."""

from __future__ import annotations

from .entrada.app import main

__all__ = ["main"]

if __name__ == "__main__":
    raise SystemExit(main())
