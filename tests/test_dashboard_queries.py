"""Tests for dashboard SQL queries against local Gold temp views."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SRC_DIR))

from bronze.schemas import (  # noqa: E402
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)
from dashboard.query_loader import load_dashboard_queries, localize_sql  # noqa: E402
from dashboard.validate_dashboard_local import (  # noqa: E402
    REQUIRED_QUERIES,
    collect_kpi_snapshot,
    validate_query,
)
from gold.config import GoldConfig  # noqa: E402
from gold.gold_engine import run_gold_pipeline  # noqa: E402
from silver.quality_engine import apply_all_dimensions  # noqa: E402
from silver.quality_framework import QualityContext  # noqa: E402


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[1]")
        .appName("dashboard-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session


@pytest.fixture(scope="module")
def dashboard_queries(spark: SparkSession):
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

    validated_at = datetime(2026, 8, 16, 9, 0, 0)
    run_id = "dashboard-test-run"
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
    run_gold_pipeline(GoldConfig(local_mode=True), spark)

    queries = {q.name: localize_sql(q.sql) for q in load_dashboard_queries()}
    return queries


def test_required_queries_present(dashboard_queries):
    assert REQUIRED_QUERIES.issubset(set(dashboard_queries))


@pytest.mark.parametrize("query_name", sorted(REQUIRED_QUERIES))
def test_required_query_executes(spark, dashboard_queries, query_name):
    result = validate_query(spark, query_name, dashboard_queries[query_name])
    assert result.passed, result.detail


def test_all_queries_execute(spark, dashboard_queries):
    failures = []
    for name, sql in dashboard_queries.items():
        result = validate_query(spark, name, sql)
        if not result.passed:
            failures.append(f"{name}: {result.detail}")
    assert not failures, "; ".join(failures)


def test_kpi_totals_match_gold_trends(spark, dashboard_queries):
    snapshot = collect_kpi_snapshot(spark, dashboard_queries)
    trends = spark.table("gold_daily_weekly_trends").filter("trend_grain = 'DAILY'")
    expected_revenue = float(trends.agg({"total_revenue": "sum"}).collect()[0][0])
    expected_orders = int(trends.agg({"total_orders": "sum"}).collect()[0][0])

    assert abs(float(snapshot["total_revenue"]) - expected_revenue) < 0.01
    assert int(snapshot["total_orders"]) == expected_orders


def test_top_products_query_returns_at_most_ten_rows(spark, dashboard_queries):
    count = spark.sql(dashboard_queries["chart_top_10_products_by_revenue"]).count()
    assert 0 < count <= 10


def test_segmentation_customer_counts_sum_to_valid_customers(spark, dashboard_queries):
    segment_total = (
        spark.sql(dashboard_queries["chart_customer_segmentation"])
        .agg({"customer_count": "sum"})
        .collect()[0][0]
    )
    customer_total = spark.sql(dashboard_queries["kpi_total_customers"]).collect()[0][0]
    assert int(segment_total) == int(customer_total)
