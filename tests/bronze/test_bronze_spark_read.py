"""Spark-based Bronze ingestion read and schema tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pyspark.sql import functions as F

from bronze.config import CUSTOMERS_SPEC, ORDERS_SPEC, PRODUCTS_SPEC
from bronze.ingest_utils import add_ingestion_metadata, read_bronze_csv
from bronze.schemas import EXPECTED_ROW_COUNTS

pytestmark = [pytest.mark.bronze, pytest.mark.spark]


@pytest.mark.parametrize(
    ("spec", "filename", "entity"),
    [
        (CUSTOMERS_SPEC, "customers.csv", "customers"),
        (PRODUCTS_SPEC, "products.csv", "products"),
        (ORDERS_SPEC, "orders.csv", "orders"),
    ],
)
def test_read_bronze_csv_row_count_matches_expected(
    spark, bronze_config, spec, filename, entity
) -> None:
    path = bronze_config.source_path(filename)
    df = read_bronze_csv(spark, path, spec)
    assert df.count() == EXPECTED_ROW_COUNTS[entity]


def test_read_bronze_customers_schema_types(spark, bronze_config) -> None:
    path = bronze_config.source_path("customers.csv")
    df = read_bronze_csv(spark, path, CUSTOMERS_SPEC)
    row = df.filter(F.col("customer_id") == 1).collect()[0]
    assert isinstance(row.customer_id, int)
    assert isinstance(row.signup_date, date)
    assert isinstance(row.lifetime_value, Decimal)


def test_read_bronze_orders_preserves_null_foreign_keys(spark, bronze_config) -> None:
    path = bronze_config.source_path("orders.csv")
    df = read_bronze_csv(spark, path, ORDERS_SPEC)
    null_customer = df.filter(F.col("customer_id").isNull()).count()
    null_product = df.filter(F.col("product_id").isNull()).count()
    assert null_customer == 100
    assert null_product == 200


def test_add_ingestion_metadata_columns(spark, bronze_tables) -> None:
    enriched = add_ingestion_metadata(bronze_tables["customers"], "data/customers.csv")
    assert "_ingested_at" in enriched.columns
    assert "_source_file" in enriched.columns
    assert enriched.filter(F.col("_source_file") == "data/customers.csv").count() == enriched.count()


def test_bronze_read_does_not_modify_business_columns(spark, bronze_config) -> None:
    path = bronze_config.source_path("products.csv")
    df = read_bronze_csv(spark, path, PRODUCTS_SPEC)
    assert set(df.columns) == {field.name for field in PRODUCTS_SPEC.schema.fields}
    assert df.filter(F.col("price") <= 0).count() == 0
