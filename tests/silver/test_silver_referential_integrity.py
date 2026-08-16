"""Referential integrity dimension tests — positive and negative cases."""

from __future__ import annotations

from datetime import datetime

import pytest
from pyspark.sql import Row
from pyspark.sql import functions as F

from bronze.schemas import CUSTOMERS_BRONZE_SCHEMA, ORDERS_BRONZE_SCHEMA, PRODUCTS_BRONZE_SCHEMA
from silver.quality_framework import QualityContext
from helpers.dimension_test_utils import apply_single_dimension, issue_count
from helpers.synthetic_data import valid_customer_row, valid_order_row, valid_product_row

pytestmark = [pytest.mark.silver, pytest.mark.spark]


def test_valid_foreign_keys_pass_referential_check(spark) -> None:
    customers = spark.createDataFrame([Row(*valid_customer_row(1))], CUSTOMERS_BRONZE_SCHEMA)
    products = spark.createDataFrame([Row(*valid_product_row(1))], PRODUCTS_BRONZE_SCHEMA)
    orders = spark.createDataFrame([Row(*valid_order_row(1, 1, 1))], ORDERS_BRONZE_SCHEMA)

    ctx = QualityContext(
        "run-1",
        datetime(2026, 1, 1),
        "orders",
        "order_id",
        valid_customer_ids=customers,
        valid_product_ids=products,
    )
    silver_df, _ = apply_single_dimension(orders, ctx, "04_quality_referential_integrity")
    assert silver_df.filter(F.col("_is_valid")).count() == 1
    assert issue_count(silver_df, "referential:invalid_customer_id") == 0
    assert issue_count(silver_df, "referential:invalid_product_id") == 0


def test_invalid_customer_id_fails_referential_check(spark) -> None:
    customers = spark.createDataFrame([Row(*valid_customer_row(1))], CUSTOMERS_BRONZE_SCHEMA)
    products = spark.createDataFrame([Row(*valid_product_row(1))], PRODUCTS_BRONZE_SCHEMA)
    orders = spark.createDataFrame([Row(*valid_order_row(1, 999, 1))], ORDERS_BRONZE_SCHEMA)

    ctx = QualityContext(
        "run-1",
        datetime(2026, 1, 1),
        "orders",
        "order_id",
        valid_customer_ids=customers,
        valid_product_ids=products,
    )
    silver_df, _ = apply_single_dimension(orders, ctx, "04_quality_referential_integrity")
    assert issue_count(silver_df, "referential:invalid_customer_id") == 1


def test_null_foreign_keys_skip_referential_check(spark) -> None:
    customers = spark.createDataFrame([Row(*valid_customer_row(1))], CUSTOMERS_BRONZE_SCHEMA)
    products = spark.createDataFrame([Row(*valid_product_row(1))], PRODUCTS_BRONZE_SCHEMA)
    row = list(valid_order_row())
    row[1] = None
    orders = spark.createDataFrame([Row(*row)], ORDERS_BRONZE_SCHEMA)

    ctx = QualityContext(
        "run-1",
        datetime(2026, 1, 1),
        "orders",
        "order_id",
        valid_customer_ids=customers,
        valid_product_ids=products,
    )
    silver_df, _ = apply_single_dimension(orders, ctx, "04_quality_referential_integrity")
    assert issue_count(silver_df, "referential:invalid_customer_id") == 0


def test_sample_data_orphan_foreign_key_counts(silver_tables) -> None:
    orders = silver_tables["orders"]
    assert issue_count(orders, "referential:invalid_customer_id") == 50
    assert issue_count(orders, "referential:invalid_product_id") == 30
