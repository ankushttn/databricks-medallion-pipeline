"""Senior-level Gold reconciliation tests — independent expected-value calculations."""

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
from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD  # noqa: E402
from gold.gold_engine import run_gold_pipeline  # noqa: E402
from gold.reconciliation import (  # noqa: E402
    classify_segment,
    expected_customer_segmentation,
    expected_revenue_by_customer,
    expected_sales_by_product,
    reconcile_duplicate_and_null_handling,
    reconcile_revenue_by_customer,
    reconcile_sales_by_product,
    reconcile_segmentation,
    reconcile_trends,
    run_full_reconciliation,
    select_representative_customer_ids,
    select_representative_product_ids,
    trace_customer,
    trace_product,
    valid_orders,
)
from silver.quality_engine import apply_all_dimensions  # noqa: E402
from silver.quality_framework import QualityContext  # noqa: E402


@pytest.fixture(scope="module")
def reconciliation_context(spark: SparkSession):
    customers = (
        spark.read.schema(CUSTOMERS_BRONZE_SCHEMA)
        .option("header", True)
        .option("nullValue", "")
        .csv(str(DATA_DIR / "customers.csv"))
    )
    products = (
        spark.read.schema(PRODUCTS_BRONZE_SCHEMA)
        .option("header", True)
        .option("nullValue", "")
        .csv(str(DATA_DIR / "products.csv"))
    )
    orders = (
        spark.read.schema(ORDERS_BRONZE_SCHEMA)
        .option("header", True)
        .option("nullValue", "")
        .csv(str(DATA_DIR / "orders.csv"))
    )
    bronze_orders = orders
    validated_at = datetime(2026, 8, 16, 8, 30, 0)
    run_id = "gold-reconciliation-test"

    silver_customers, _, _ = apply_all_dimensions(
        customers, QualityContext(run_id, validated_at, "customers", "customer_id")
    )
    silver_products, _, _ = apply_all_dimensions(
        products, QualityContext(run_id, validated_at, "products", "product_id")
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
        "spark": spark,
        "config": config,
        "bronze_orders": bronze_orders,
        "silver_orders": silver_orders,
        "silver_customers": silver_customers,
        "silver_products": silver_products,
    }


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[1]")
        .appName("gold-reconciliation-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session


def test_full_reconciliation_passes(reconciliation_context: dict) -> None:
    report = run_full_reconciliation(
        reconciliation_context["spark"],
        reconciliation_context["config"],
        reconciliation_context["bronze_orders"],
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
        reconciliation_context["silver_products"],
    )
    failures = [r for r in report.results if not r.passed]
    trace_failures = [t for t in report.product_traces + report.customer_traces if not t.passed]
    assert not failures, f"Reconciliation failures: {failures}"
    assert not trace_failures, f"Trace failures: {trace_failures}"
    assert len(report.product_traces) >= 5
    assert len(report.customer_traces) >= 5


def test_sales_by_product_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    results = reconcile_sales_by_product(
        gold_sales,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_products"],
    )
    assert all(r.passed for r in results)


def test_revenue_by_customer_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_revenue = spark.table(config.gold_table("revenue_by_customer"))
    results = reconcile_revenue_by_customer(
        gold_revenue,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert all(r.passed for r in results)


def test_trends_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_trends = spark.table(config.gold_table("daily_weekly_trends"))
    results = reconcile_trends(gold_trends, reconciliation_context["silver_orders"])
    assert all(r.passed for r in results)


def test_segmentation_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_segments = spark.table(config.gold_table("customer_segmentation"))
    results = reconcile_segmentation(
        gold_segments,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert all(r.passed for r in results)


def test_duplicate_and_null_exclusion(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    results = reconcile_duplicate_and_null_handling(
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
        reconciliation_context["silver_products"],
        gold_sales,
    )
    assert all(r.passed for r in results)


def test_five_product_traces(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    product_ids = select_representative_product_ids(gold_sales)
    assert len(product_ids) == 5
    for product_id in product_ids:
        trace = trace_product(
            product_id,
            reconciliation_context["bronze_orders"],
            reconciliation_context["silver_orders"],
            reconciliation_context["silver_products"],
            gold_sales,
        )
        assert trace.passed, f"Product {product_id} trace failed: {trace}"


def test_five_customer_traces(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_revenue = spark.table(config.gold_table("revenue_by_customer"))
    customer_ids = select_representative_customer_ids(
        gold_revenue,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert len(customer_ids) == 5
    for customer_id in customer_ids:
        trace = trace_customer(
            customer_id,
            reconciliation_context["bronze_orders"],
            reconciliation_context["silver_orders"],
            reconciliation_context["silver_customers"],
            gold_revenue,
        )
        assert trace.passed, f"Customer {customer_id} trace failed: {trace}"


def test_classify_segment_boundary() -> None:
    assert classify_segment(0, 0) == "Inactive"
    assert classify_segment(1, HIGH_VALUE_REVENUE_THRESHOLD) == "High-Value"
    assert classify_segment(1, HIGH_VALUE_REVENUE_THRESHOLD - 0.01) == "One-Time"
    assert classify_segment(2, 100) == "Repeat"


def test_expected_segmentation_sums_to_valid_customers(reconciliation_context: dict) -> None:
    expected = expected_customer_segmentation(
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    total = expected.agg(F.sum("customer_count")).collect()[0][0]
    valid_customers = reconciliation_context["silver_customers"].filter(F.col("_is_valid")).count()
    assert total == valid_customers


def test_valid_order_dedup_count(reconciliation_context: dict) -> None:
    silver_orders = reconciliation_context["silver_orders"]
    raw_valid = silver_orders.filter(F.col("_is_valid")).count()
    dedup_valid = valid_orders(silver_orders).select("order_id").dropDuplicates(["order_id"]).count()
    assert dedup_valid == raw_valid, "No duplicate valid order_id rows should exist"
