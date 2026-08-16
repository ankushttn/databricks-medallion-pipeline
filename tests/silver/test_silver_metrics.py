"""Unit tests for Silver metrics helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pyspark.sql import functions as F

from silver.metrics import _spark_timestamp, build_check_summary, build_entity_metrics

pytestmark = pytest.mark.silver


@pytest.mark.unit
def test_spark_timestamp_strips_timezone() -> None:
    aware = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    naive = _spark_timestamp(aware)
    assert naive.tzinfo is None
    assert naive.year == 2026


@pytest.mark.spark
def test_build_entity_metrics_counts_valid_invalid(silver_tables, run_context) -> None:
    customers = silver_tables["customers"]
    metrics = build_entity_metrics(
        customers,
        "customers",
        run_context["run_id"],
        run_context["validated_at"],
    )
    row = metrics.first()
    assert row.total_rows == customers.count()
    assert row.passed_rows + row.failed_rows == row.total_rows
    assert row.failed_rows == customers.filter(~F.col("_is_valid")).count()


@pytest.mark.spark
def test_build_check_summary_includes_mandatory_defects(silver_tables, run_context) -> None:
    checks = silver_tables["order_checks"]
    summary = build_check_summary(
        silver_tables["orders"],
        "orders",
        checks,
        run_context["run_id"],
        run_context["validated_at"],
    )
    issue_codes = {row.issue_code for row in summary.select("issue_code").collect()}
    assert "completeness:customer_id_null" in issue_codes
    assert "referential:invalid_product_id" in issue_codes
