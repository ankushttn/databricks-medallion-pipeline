"""Shared pytest fixtures for the medallion pipeline test suite."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

# Ensure Spark Python workers use the same interpreter as the test runner (Windows fix).
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
TESTS_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from bronze.config import load_bronze_config  # noqa: E402
from bronze.schemas import (  # noqa: E402
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)
from gold.config import GoldConfig  # noqa: E402
from gold.gold_engine import run_gold_pipeline  # noqa: E402
from silver.quality_engine import apply_all_dimensions  # noqa: E402
from silver.quality_framework import QualityContext  # noqa: E402


def read_bronze_csv(spark: SparkSession, filename: str, schema):
    """Read a project CSV using an explicit Bronze schema."""
    return (
        spark.read.schema(schema)
        .option("header", True)
        .option("nullValue", "")
        .csv(str(DATA_DIR / filename))
    )


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def bronze_config(data_dir: Path):
    return load_bronze_config(source_base_path=str(data_dir))


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    session = (
        SparkSession.builder.master("local[1]")
        .appName("medallion-tests")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    yield session


@pytest.fixture(scope="module")
def run_context() -> dict:
    return {
        "run_id": "test-run-001",
        "validated_at": datetime(2026, 8, 16, 9, 0, 0),
    }


@pytest.fixture(scope="module")
def bronze_tables(spark: SparkSession):
    customers = read_bronze_csv(spark, "customers.csv", CUSTOMERS_BRONZE_SCHEMA)
    products = read_bronze_csv(spark, "products.csv", PRODUCTS_BRONZE_SCHEMA)
    orders = read_bronze_csv(spark, "orders.csv", ORDERS_BRONZE_SCHEMA)
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "counts": {
            "customers": customers.count(),
            "products": products.count(),
            "orders": orders.count(),
        },
    }


@pytest.fixture(scope="module")
def silver_tables(spark: SparkSession, bronze_tables: dict, run_context: dict):
    customers = bronze_tables["customers"]
    products = bronze_tables["products"]
    orders = bronze_tables["orders"]

    customer_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="customers",
        row_id_column="customer_id",
    )
    silver_customers, customer_details, customer_checks = apply_all_dimensions(
        customers, customer_ctx
    )

    product_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="products",
        row_id_column="product_id",
    )
    silver_products, product_details, product_checks = apply_all_dimensions(
        products, product_ctx
    )

    order_ctx = QualityContext(
        run_id=run_context["run_id"],
        validated_at=run_context["validated_at"],
        entity="orders",
        row_id_column="order_id",
        valid_customer_ids=silver_customers,
        valid_product_ids=silver_products,
    )
    silver_orders, order_details, order_checks = apply_all_dimensions(orders, order_ctx)

    silver_customers.createOrReplaceTempView("silver_customers")
    silver_products.createOrReplaceTempView("silver_products")
    silver_orders.createOrReplaceTempView("silver_orders")

    return {
        "customers": silver_customers,
        "products": silver_products,
        "orders": silver_orders,
        "order_details": order_details,
        "order_checks": order_checks,
        "bronze_counts": bronze_tables["counts"],
    }


@pytest.fixture(scope="module")
def gold_tables(spark: SparkSession, silver_tables: dict):
    config = GoldConfig(local_mode=True)
    run_gold_pipeline(config, spark=spark)
    return {
        "spark": spark,
        "config": config,
        "silver_orders": silver_tables["orders"],
        "silver_customers": silver_tables["customers"],
        "silver_products": silver_tables["products"],
    }


@pytest.fixture(scope="module")
def reconciliation_context(spark: SparkSession, bronze_tables: dict, gold_tables: dict):
    return {
        **gold_tables,
        "bronze_orders": bronze_tables["orders"],
    }


def pytest_collection_modifyitems(items):
    """Run lighter layers before Gold/Dashboard/Integration to reduce Spark session strain."""
    layer_order = {
        "data_generation": 0,
        "bronze": 1,
        "silver": 2,
        "gold": 3,
        "dashboard": 4,
        "integration": 5,
    }

    def sort_key(item):
        path = str(item.fspath).replace("\\", "/")
        for layer, priority in layer_order.items():
            if f"/tests/{layer}/" in path:
                return (priority, path)
        return (99, path)

    items.sort(key=sort_key)
