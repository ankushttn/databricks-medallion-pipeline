"""Tests that intentional quality defects exist in committed sample CSV data."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "data_generation"))

from validate_sample_data import EXPECTED_DEFECTS, run_validation  # noqa: E402

pytestmark = [pytest.mark.data_generation, pytest.mark.integration]


@pytest.mark.unit
def test_independent_validator_passes_on_project_data(data_dir: Path) -> None:
    report = run_validation(data_dir)
    failures = [r for r in report.results if not r.passed]
    assert report.passed, f"Sample data validation failures: {failures[:5]}"


@pytest.mark.unit
def test_validator_runs_all_checks(data_dir: Path) -> None:
    report = run_validation(data_dir)
    assert len(report.results) >= 30


@pytest.mark.unit
def test_intentional_defect_categories_present(data_dir: Path) -> None:
    report = run_validation(data_dir)
    categories = {r.category for r in report.results}
    for expected in ("row_counts", "null_counts", "duplicate_pks", "orphan_fks", "intentional_issues"):
        assert expected in categories


@pytest.mark.unit
def test_expected_defect_spec_matches_assignment() -> None:
    assert EXPECTED_DEFECTS["null_email"] == 50
    assert EXPECTED_DEFECTS["duplicate_customer_id_extra_rows"] == 10
    assert EXPECTED_DEFECTS["null_customer_id"] == 100
    assert EXPECTED_DEFECTS["null_product_id"] == 200
    assert EXPECTED_DEFECTS["orphan_customer_id"] == 50
    assert EXPECTED_DEFECTS["orphan_product_id"] == 30
    assert EXPECTED_DEFECTS["duplicate_order_id_extra_rows"] == 20
