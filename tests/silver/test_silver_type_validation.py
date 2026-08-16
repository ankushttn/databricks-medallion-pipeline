"""Type validation dimension tests — positive and negative cases."""

from __future__ import annotations

from datetime import datetime

import pytest
from pyspark.sql import Row
from pyspark.sql import functions as F

from bronze.schemas import CUSTOMERS_BRONZE_SCHEMA, ORDERS_BRONZE_SCHEMA
from silver.quality_framework import QualityContext
from helpers.dimension_test_utils import apply_single_dimension, issue_count
from helpers.synthetic_data import valid_customer_row, valid_order_row

pytestmark = [pytest.mark.silver, pytest.mark.spark]


def test_valid_customer_passes_type_checks(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    df = spark.createDataFrame([Row(*valid_customer_row())], CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "03_quality_type_validation")
    assert silver_df.filter(F.col("_is_valid")).count() == 1


def test_invalid_email_format_fails_type_check(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    df = spark.createDataFrame(
        [Row(*valid_customer_row(email="not-an-email"))],
        CUSTOMERS_BRONZE_SCHEMA,
    )
    silver_df, _ = apply_single_dimension(df, ctx, "03_quality_type_validation")
    assert issue_count(silver_df, "type:email_format_invalid") == 1


def test_invalid_customer_segment_fails_type_check(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    df = spark.createDataFrame(
        [Row(*valid_customer_row(segment="Enterprise"))],
        CUSTOMERS_BRONZE_SCHEMA,
    )
    silver_df, _ = apply_single_dimension(df, ctx, "03_quality_type_validation")
    assert issue_count(silver_df, "type:customer_segment_invalid") == 1


def test_invalid_order_status_fails_business_not_type(spark) -> None:
    """Order status allowed-values is enforced in business_logic, not type_validation."""
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")
    row = list(valid_order_row())
    row[7] = "Unknown"
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "03_quality_type_validation")
    assert issue_count(silver_df, "business:invalid_order_status") == 0


def test_sample_data_products_have_zero_type_failures(silver_tables) -> None:
    """Products were generated without intentional defects — all type checks pass."""
    products = silver_tables["products"]
    invalid = products.filter(~F.col("_is_valid")).count()
    assert invalid == 0


def test_sample_data_clean_customers_pass_type_checks(silver_tables) -> None:
    customers = silver_tables["customers"]
    clean = customers.filter(
        ~F.array_contains(F.col("_quality_issues"), "completeness:email_null")
        & ~F.array_contains(F.col("_quality_issues"), "uniqueness:duplicate_customer_id")
    )
    assert clean.filter(~F.col("_is_valid")).count() == 0
