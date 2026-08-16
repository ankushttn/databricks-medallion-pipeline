"""End-to-end medallion pipeline integration tests."""

from __future__ import annotations

import pytest
from pyspark.sql import functions as F

from silver.constants import EXPECTED_DEFECT_COUNTS
from helpers.dimension_test_utils import issue_count

pytestmark = [pytest.mark.integration, pytest.mark.spark]


def test_bronze_to_silver_row_parity(bronze_tables, silver_tables) -> None:
    for entity in ("customers", "products", "orders"):
        assert bronze_tables["counts"][entity] == silver_tables[entity].count()


def test_silver_invalid_orders_match_gold_exclusion(silver_tables, gold_tables) -> None:
    invalid_orders = silver_tables["orders"].filter(~F.col("_is_valid")).count()
    assert invalid_orders == 420

    spark = gold_tables["spark"]
    config = gold_tables["config"]
    trend_orders = (
        spark.table(config.gold_table("daily_weekly_trends"))
        .filter(F.col("trend_grain") == "DAILY")
        .agg(F.sum("total_orders"))
        .collect()[0][0]
    )
    valid_orders = silver_tables["orders"].filter(F.col("_is_valid")).count()
    assert trend_orders == valid_orders


def test_mandatory_defects_detected_end_to_end(silver_tables) -> None:
    customers = silver_tables["customers"]
    orders = silver_tables["orders"]
    for issue_code, expected in EXPECTED_DEFECT_COUNTS.items():
        if issue_code.startswith("uniqueness:"):
            assert issue_count(
                customers if "customer" in issue_code else orders, issue_code
            ) >= expected
        elif issue_code.startswith("completeness:email"):
            assert issue_count(customers, issue_code) == expected
        elif issue_code.startswith("completeness:"):
            assert issue_count(orders, issue_code) == expected
        elif issue_code.startswith("referential:"):
            assert issue_count(orders, issue_code) == expected


def test_gold_product_count_matches_valid_products_with_orders(gold_tables, silver_tables) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    sales_count = spark.table(config.gold_table("sales_by_product")).count()
    valid_products = silver_tables["products"].filter(F.col("_is_valid")).count()
    assert 0 < sales_count <= valid_products


def test_gold_customer_count_matches_valid_customers(gold_tables, silver_tables) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    revenue_count = spark.table(config.gold_table("revenue_by_customer")).count()
    valid_customers = silver_tables["customers"].filter(F.col("_is_valid")).count()
    assert revenue_count == valid_customers
