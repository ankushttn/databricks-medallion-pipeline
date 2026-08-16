"""Tests for Gold layer aggregations."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SRC_DIR))

from bronze.schemas import (  # noqa: E402
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)
from gold.config import GoldConfig  # noqa: E402
from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD, SEGMENT_TYPES  # noqa: E402
from gold.gold_engine import all_validations_passed, run_gold_pipeline, run_gold_validations  # noqa: E402
from silver.quality_engine import apply_all_dimensions  # noqa: E402
from silver.quality_framework import QualityContext  # noqa: E402


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[1]")
        .appName("gold-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session


def _read_csv(spark: SparkSession, filename: str, schema):
    return (
        spark.read.schema(schema)
        .option("header", True)
        .option("nullValue", "")
        .csv(str(DATA_DIR / filename))
    )


@pytest.fixture(scope="module")
def gold_tables(spark: SparkSession):
    customers = _read_csv(spark, "customers.csv", CUSTOMERS_BRONZE_SCHEMA)
    products = _read_csv(spark, "products.csv", PRODUCTS_BRONZE_SCHEMA)
    orders = _read_csv(spark, "orders.csv", ORDERS_BRONZE_SCHEMA)
    validated_at = datetime(2026, 8, 16, 8, 0, 0)
    run_id = "gold-test-run"

    silver_customers, _, _ = apply_all_dimensions(
        customers,
        QualityContext(run_id, validated_at, "customers", "customer_id"),
    )
    silver_products, _, _ = apply_all_dimensions(
        products,
        QualityContext(run_id, validated_at, "products", "product_id"),
    )
    silver_orders, _, _ = apply_all_dimensions(
        orders,
        QualityContext(
            run_id,
            validated_at,
            "orders",
            "order_id",
            valid_customer_ids=silver_customers,
            valid_product_ids=silver_products,
        ),
    )

    silver_customers.createOrReplaceTempView("silver_customers")
    silver_products.createOrReplaceTempView("silver_products")
    silver_orders.createOrReplaceTempView("silver_orders")

    config = GoldConfig(local_mode=True)
    run_gold_pipeline(config, spark=spark)
    return {
        "config": config,
        "silver_orders": silver_orders,
        "spark": spark,
    }


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
    valid_customers = gold_tables["silver_orders"].sparkSession.table("silver_customers").filter(
        F.col("_is_valid")
    ).count()
    # segmentation counts valid customers from customers table, not orders
    silver_customers = spark.table("silver_customers").filter(F.col("_is_valid")).count()
    assert total_customers == silver_customers


def test_high_value_threshold_constant() -> None:
    assert HIGH_VALUE_REVENUE_THRESHOLD > 0


def test_gold_validations_pass(gold_tables: dict) -> None:
    spark = gold_tables["spark"]
    config = gold_tables["config"]
    results = run_gold_validations(spark, config)
    assert all_validations_passed(results)
