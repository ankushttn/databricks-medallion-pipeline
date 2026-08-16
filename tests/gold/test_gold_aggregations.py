"""Tests for Gold layer aggregations."""

from __future__ import annotations

import pytest
from pyspark.sql import functions as F

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD, SEGMENT_TYPES
from gold.gold_engine import all_validations_passed, run_gold_validations

pytestmark = [pytest.mark.gold, pytest.mark.spark]


def test_invalid_orders_excluded_from_gold(gold_tables: dict) -> None:
    silver_orders = gold_tables["silver_orders"]
    config = gold_tables["config"]
    spark = gold_tables["spark"]

    valid_order_count = silver_orders.filter(F.col("_is_valid")).count()
    invalid_order_count = silver_orders.filter(~F.col("_is_valid")).count()
    assert invalid_order_count == 420

    trends = spark.table(config.gold_table("daily_weekly_trends")).filter(
        F.col("trend_grain") == "DAILY"
    )
    trend_orders = trends.agg(F.sum("total_orders").alias("orders")).collect()[0].orders
    assert trend_orders == valid_order_count


def test_sales_by_product_grain(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    sales = spark.table(config.gold_table("sales_by_product"))
    assert sales.count() == sales.select("product_id").distinct().count()
    assert sales.filter(F.col("total_orders") <= 0).count() == 0


def test_revenue_by_customer_lifetime_value(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    revenue = spark.table(config.gold_table("revenue_by_customer"))
    mismatch = revenue.filter(
        F.abs(F.col("lifetime_value_actual") - F.col("total_revenue")) > 0.01
    )
    assert mismatch.count() == 0


def test_customer_segmentation_mutually_exclusive(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    segments = spark.table(config.gold_table("customer_segmentation"))
    segment_types = {row.segment_type for row in segments.collect()}
    assert segment_types.issubset(set(SEGMENT_TYPES))
    total_customers = segments.agg(F.sum("customer_count")).collect()[0][0]
    silver_customers = spark.table("silver_customers").filter(F.col("_is_valid")).count()
    assert total_customers == silver_customers


def test_high_value_threshold_constant() -> None:
    assert HIGH_VALUE_REVENUE_THRESHOLD == 2500.00


def test_gold_validations_pass(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    results = run_gold_validations(spark, config)
    assert all_validations_passed(results)
