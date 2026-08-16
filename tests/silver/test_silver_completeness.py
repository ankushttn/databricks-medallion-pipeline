"""Completeness dimension tests — positive and negative cases."""

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


def _customer_ctx() -> QualityContext:
    return QualityContext("run-1", datetime(2026, 1, 1), "customers", "customer_id")


def _order_ctx() -> QualityContext:
    return QualityContext("run-1", datetime(2026, 1, 1), "orders", "order_id")


def test_valid_customer_email_passes_completeness(spark) -> None:
    df = spark.createDataFrame([Row(*valid_customer_row())], CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, _customer_ctx(), "01_quality_completeness")
    assert silver_df.filter(F.col("_is_valid")).count() == 1
    assert issue_count(silver_df, "completeness:email_null") == 0


def test_null_email_fails_completeness(spark) -> None:
    df = spark.createDataFrame([Row(*valid_customer_row(email=""))], CUSTOMERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, _customer_ctx(), "01_quality_completeness")
    assert silver_df.filter(~F.col("_is_valid")).count() == 1
    assert issue_count(silver_df, "completeness:email_null") == 1


def test_null_customer_id_fails_completeness(spark) -> None:
    row = list(valid_order_row())
    row[1] = None
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, _order_ctx(), "01_quality_completeness")
    assert issue_count(silver_df, "completeness:customer_id_null") == 1


def test_null_product_id_fails_completeness(spark) -> None:
    row = list(valid_order_row())
    row[3] = None
    df = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)
    silver_df, _ = apply_single_dimension(df, _order_ctx(), "01_quality_completeness")
    assert issue_count(silver_df, "completeness:product_id_null") == 1


def test_sample_data_completeness_defect_counts(silver_tables) -> None:
    assert issue_count(silver_tables["customers"], "completeness:email_null") == 50
    assert issue_count(silver_tables["orders"], "completeness:customer_id_null") == 100
    assert issue_count(silver_tables["orders"], "completeness:product_id_null") == 200
