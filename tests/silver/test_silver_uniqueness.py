"""Uniqueness dimension tests — positive and negative cases."""

from __future__ import annotations

from datetime import datetime

import pytest
from pyspark.sql import Row
from pyspark.sql import functions as F

from bronze.schemas import CUSTOMERS_BRONZE_SCHEMA, PRODUCTS_BRONZE_SCHEMA
from silver.quality_framework import QualityContext
from helpers.dimension_test_utils import apply_single_dimension, issue_count
from helpers.synthetic_data import valid_customer_row, valid_product_row

pytestmark = [pytest.mark.silver, pytest.mark.spark]


def test_unique_customer_passes_uniqueness(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    df = spark.createDataFrame([Row(*valid_customer_row(1))], CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "02_quality_uniqueness")
    assert silver_df.filter(F.col("_is_valid")).count() == 1


def test_duplicate_customer_id_flags_both_rows(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")
    rows = [Row(*valid_customer_row(1)), Row(*valid_customer_row(1, email="dup@example.com"))]
    df = spark.createDataFrame(rows, CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "02_quality_uniqueness")
    assert issue_count(silver_df, "uniqueness:duplicate_customer_id") == 2


def test_unique_product_passes_uniqueness(spark) -> None:
    ctx = QualityContext("run-1", datetime(2026, 1, 1), "products", "product_id")
    df = spark.createDataFrame([Row(*valid_product_row(1))], PRODUCTS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, ctx, "02_quality_uniqueness")
    assert silver_df.filter(F.col("_is_valid")).count() == 1


def test_sample_data_duplicate_customer_rows_flagged(silver_tables) -> None:
    flagged = issue_count(silver_tables["customers"], "uniqueness:duplicate_customer_id")
    assert flagged == 20


def test_sample_data_duplicate_order_rows_flagged(silver_tables) -> None:
    flagged = issue_count(silver_tables["orders"], "uniqueness:duplicate_order_id")
    assert flagged == 40


def test_products_have_no_duplicate_pk_issues(silver_tables) -> None:
    assert issue_count(silver_tables["products"], "uniqueness:duplicate_product_id") == 0
