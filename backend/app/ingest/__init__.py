"""Ingest: PSI snapshot in data/raw/ -> typed, checked tables in data/processed/.

    python -m app.ingest           rebuild data/processed/
    python -m app.ingest --check   fail if the committed files are out of date
"""

from .build import Outputs, build, check, write

__all__ = ["Outputs", "build", "check", "write"]
