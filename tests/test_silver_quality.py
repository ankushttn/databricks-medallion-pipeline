"""Tests for Silver data quality framework."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
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
from silver.config import load_silver_config  # noqa: E402
from silver.constants import EXPECTED_DEFECT_COUNTS  # noqa: E402
from silver.quality_engine import apply_all_dimensions  # noqa: E402
from silver.quality_framework import QualityContext  # noqa: E402


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[1]")
        .appName("silver-quality-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session


def _read_csv(spark: SparkSession, filename: str, schema):
    path = str(DATA_DIR / filename)
    return (
        spark.read.schema(schema)
        .option("header", True)
        .option("nullValue", "")
        .csv(path)
    )


def _issue_count(df, issue_code: str) -> int:
    return df.filter(F.array_contains(F.col("_quality_issues"), issue_code)).count()


@pytest.fixture(scope="module")
def run_context() -> dict:
    return {
        "run_id": "test-run-001",
        "validated_at": datetime(2026, 8, 15, 12, 0, 0),
    }


@pytest.fixture(scope="module")
def silver_tables(spark: SparkSession, run_context: dict):
    customers = _read_csv(spark, "customers.csv", CUSTOMERS_BRONZE_SCHEMA)
    products = _read_csv(spark, "products.csv", PRODUCTS_BRONZE_SCHEMA)
    orders = _read_csv(spark, "orders.csv", ORDERS_BRONZE_SCHEMA)

    customer_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="customers",
        row_id_column="customer_id",
    )
    silver_customers, _, _ = apply_all_dimensions(customers, customer_ctx)

    product_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="products",
        row_id_column="product_id",
    )
    silver_products, _, _ = apply_all_dimensions(products, product_ctx)

    order_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="orders",
        row_id_column="order_id",
        valid_customer_ids=silver_customers,
        valid_product_ids=silver_products,
    )
    silver_orders, order_details, order_checks = apply_all_dimensions(orders, order_ctx)

    return {
        "customers": silver_customers,
        "products": silver_products,
        "orders": silver_orders,
        "order_details": order_details,
        "order_checks": order_checks,
        "bronze_counts": {
            "customers": customers.count(),
            "products": products.count(),
            "orders": orders.count(),
        },
    }


def test_silver_config_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDALLION_CATALOG", "main")
    monkeypatch.setenv("MEDALLION_SILVER_SCHEMA", "silver_dev")
    monkeypatch.setenv("MEDALLION_RUN_ID", "manual-run")

    config = load_silver_config()
    assert config.catalog == "main"
    assert config.silver_schema == "silver_dev"
    assert config.run_id == "manual-run"
    assert config.silver_table("customers") == "main.silver_dev.customers"


def test_row_count_parity_preserved(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        assert silver_tables[entity].count() == silver_tables["bronze_counts"][entity]


def test_no_rows_deleted(silver_tables: dict) -> None:
    assert silver_tables["customers"].count() == 10_010
    assert silver_tables["products"].count() == 500
    assert silver_tables["orders"].count() == 100_020


def test_mandatory_defect_counts(silver_tables: dict) -> None:
    customers = silver_tables["customers"]
    orders = silver_tables["orders"]

    assert _issue_count(customers, "completeness:email_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:email_null"
    ]
    assert _issue_count(customers, "uniqueness:duplicate_customer_id") >= EXPECTED_DEFECT_COUNTS[
        "uniqueness:duplicate_customer_id"
    ]
    assert _issue_count(orders, "completeness:customer_id_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:customer_id_null"
    ]
    assert _issue_count(orders, "completeness:product_id_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:product_id_null"
    ]
    assert _issue_count(orders, "referential:invalid_customer_id") == EXPECTED_DEFECT_COUNTS[
        "referential:invalid_customer_id"
    ]
    assert _issue_count(orders, "referential:invalid_product_id") == EXPECTED_DEFECT_COUNTS[
        "referential:invalid_product_id"
    ]
    assert _issue_count(orders, "uniqueness:duplicate_order_id") >= EXPECTED_DEFECT_COUNTS[
        "uniqueness:duplicate_order_id"
    ]


def test_quality_metadata_columns_present(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        df = silver_tables[entity]
        for column in (
            "_quality_issues",
            "_is_valid",
            "_quality_status",
            "_validated_at",
            "_run_id",
        ):
            assert column in df.columns


def test_quality_results_schema(silver_tables: dict) -> None:
    detail = silver_tables["order_details"]
    expected = {
        "run_id",
        "entity",
        "row_identifier",
        "check_id",
        "check_name",
        "check_dimension",
        "check_status",
        "quality_result",
        "failure_reason",
        "validated_at",
    }
    assert expected.issubset(set(detail.columns))
    assert detail.filter(F.col("check_status") != "FAIL").count() == 0


def test_entity_pass_fail_percentages_sum_to_100(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        df = silver_tables[entity]
        total = df.count()
        failed = df.filter(~F.col("_is_valid")).count()
        passed = total - failed
        assert passed + failed == total
        if total:
            assert round((passed / total) * 100 + (failed / total) * 100, 2) == 100.0


def test_duplicate_customers_flag_all_participants(silver_tables: dict) -> None:
    customers = silver_tables["customers"]
    duplicate_rows = customers.filter(
        F.array_contains(F.col("_quality_issues"), "uniqueness:duplicate_customer_id")
    )
    assert duplicate_rows.count() >= EXPECTED_DEFECT_COUNTS["uniqueness:duplicate_customer_id"]
