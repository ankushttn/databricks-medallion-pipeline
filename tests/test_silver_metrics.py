"""Unit tests for Silver metrics helpers (no Spark)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from silver.metrics import _spark_timestamp  # noqa: E402


def test_spark_timestamp_strips_timezone() -> None:
    aware = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    naive = _spark_timestamp(aware)
    assert naive.tzinfo is None
    assert naive.year == 2026
