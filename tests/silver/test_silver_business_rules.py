"""Business logic dimension tests — positive and negative cases."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from pyspark.sql import Row
from pyspark.sql import functions as F

from bronze.schemas import CUSTOMERS_BRONZE_SCHEMA, ORDERS_BRONZE_SCHEMA, PRODUCTS_BRONZE_SCHEMA
from silver.quality_framework import QualityContext
from helpers.dimension_test_utils import apply_single_dimension, issue_count
from helpers.synthetic_data import valid_customer_row, valid_order_row, valid_product_row

pytestmark = [pytest.mark.silver, pytest.mark.spark]


def test_valid_order_passes_business_rules(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")
    df = spark.createDataFrame([Row(*valid_order_row())], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert silver_df.filter(F.col("_is_valid")).count() == 1


def test_total_amount_mismatch_fails_business_rule(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")
    row = list(valid_order_row(quantity=2, unit_price=Decimal("50.00")))
    row[6] = Decimal("99.00")
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert issue_count(silver_df, "business:total_amount_mismatch") == 1


def test_payment_before_order_fails_business_rule(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")
    row = list(valid_order_row(payment_date=date(2023, 12, 31)))
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert issue_count(silver_df, "business:payment_before_order") == 1


def test_completed_order_missing_payment_date_fails(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")
    row = list(valid_order_row(order_status="Completed", payment_date=None))
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert issue_count(silver_df, "business:missing_payment_date") == 1


def test_negative_lifetime_value_fails(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    row = list(valid_customer_row())
    row[6] = Decimal("-1.00")
    df = spark.createDataFrame([Row(*row)], CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert issue_count(silver_df, "business:negative_lifetime_value") == 1


def test_price_below_cost_fails(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "products", "product_id")
    row = list(valid_product_row())
    row[3] = Decimal("10.00")
    row[4] = Decimal("20.00")
    df = spark.createDataFrame([Row(*row)], PRODUCTS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "05_quality_business_logic")
    assert issue_count(silver_df, "business:price_below_cost") == 1


def test_sample_data_products_have_supplementary_business_defects(silver_tables) -> None:
    products = silver_tables["products"]
    invalid = products.filter(~F.col("_is_valid")).count()
    assert invalid == 210
    assert issue_count(products, "business:price_below_cost") == 210


def test_sample_data_clean_orders_pass_business_rules(silver_tables) -> None:
    orders = silver_tables["orders"]
    mandatory_issue_codes = [
        "completeness:customer_id_null",
        "completeness:product_id_null",
        "referential:invalid_customer_id",
        "referential:invalid_product_id",
        "uniqueness:duplicate_order_id",
    ]
    clean = orders
    for code in mandatory_issue_codes:
        clean = clean.filter(~F.array_contains(F.col("_quality_issues"), code))
    assert clean.filter(~F.col("_is_valid")).count() == 0
