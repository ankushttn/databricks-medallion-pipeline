"""Focused tests for Gold customer segmentation business rules."""

from __future__ import annotations

import pytest
from pyspark.sql import functions as F

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD
from gold.reconciliation import classify_segment, expected_customer_segmentation

pytestmark = [pytest.mark.gold, pytest.mark.spark]

# Deterministic counts from seed-42 sample data (verified via reconciliation).
EXPECTED_SEGMENT_COUNTS = {
    "High-Value": 9652,
    "Repeat": 284,
    "One-Time": 4,
}


def test_segmentation_counts_match_sample_data(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    segments = spark.table(config.gold_table("customer_segmentation"))
    actual = {row.segment_type: row.customer_count for row in segments.collect()}
    for segment, expected_count in EXPECTED_SEGMENT_COUNTS.items():
        assert actual.get(segment) == expected_count, f"{segment} count mismatch"


def test_inactive_segment_absent_when_all_customers_have_orders(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    segments = spark.table(config.gold_table("customer_segmentation"))
    segment_types = {row.segment_type for row in segments.collect()}
    assert "Inactive" not in segment_types


def test_high_value_threshold_applied(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    revenue = spark.table(config.gold_table("revenue_by_customer"))
    high_value_customers = revenue.filter(
        F.col("lifetime_value_actual") >= HIGH_VALUE_REVENUE_THRESHOLD
    ).count()
    segments = spark.table(config.gold_table("customer_segmentation"))
    high_value_segment = segments.filter(F.col("segment_type") == "High-Value").collect()[0]
    assert high_value_customers == high_value_segment.customer_count


def test_independent_segmentation_matches_gold(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    expected = expected_customer_segmentation(
        gold_tables["silver_orders"],
        gold_tables["silver_customers"],
    )
    gold_segments = spark.table(config.gold_table("customer_segmentation"))
    for row in gold_segments.collect():
        expected_row = expected.filter(F.col("segment_type") == row.segment_type).collect()[0]
        assert row.customer_count == expected_row.customer_count


@pytest.mark.unit
@pytest.mark.parametrize(
    ("orders", "revenue", "expected"),
    [
        (0, 0, "Inactive"),
        (1, 100, "One-Time"),
        (2, 100, "Repeat"),
        (1, HIGH_VALUE_REVENUE_THRESHOLD, "High-Value"),
        (5, HIGH_VALUE_REVENUE_THRESHOLD + 1000, "High-Value"),
    ],
)
def test_classify_segment_priority(orders, revenue, expected) -> None:
    assert classify_segment(orders, revenue) == expected
