"""Explicit Spark schemas for Bronze CSV ingestion."""

from __future__ import annotations

from pyspark.sql.types import (
    DateType,
    DecimalType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

CUSTOMERS_BRONZE_SCHEMA = StructType(
    [
        StructField("customer_id", IntegerType(), nullable=True),
        StructField("customer_name", StringType(), nullable=True),
        StructField("email", StringType(), nullable=True),
        StructField("country", StringType(), nullable=True),
        StructField("signup_date", DateType(), nullable=True),
        StructField("customer_segment", StringType(), nullable=True),
        StructField("lifetime_value", DecimalType(12, 2), nullable=True),
    ]
)

PRODUCTS_BRONZE_SCHEMA = StructType(
    [
        StructField("product_id", IntegerType(), nullable=True),
        StructField("product_name", StringType(), nullable=True),
        StructField("category", StringType(), nullable=True),
        StructField("price", DecimalType(10, 2), nullable=True),
        StructField("cost", DecimalType(10, 2), nullable=True),
        StructField("stock_quantity", IntegerType(), nullable=True),
        StructField("reorder_level", IntegerType(), nullable=True),
    ]
)

ORDERS_BRONZE_SCHEMA = StructType(
    [
        StructField("order_id", IntegerType(), nullable=True),
        StructField("customer_id", IntegerType(), nullable=True),
        StructField("order_date", DateType(), nullable=True),
        StructField("product_id", IntegerType(), nullable=True),
        StructField("quantity", IntegerType(), nullable=True),
        StructField("unit_price", DecimalType(10, 2), nullable=True),
        StructField("total_amount", DecimalType(12, 2), nullable=True),
        StructField("order_status", StringType(), nullable=True),
        StructField("payment_date", DateType(), nullable=True),
    ]
)

BRONZE_METADATA_SCHEMA = StructType(
    [
        StructField("_ingested_at", TimestampType(), nullable=False),
        StructField("_source_file", StringType(), nullable=False),
    ]
)

# Expected CSV headers (business columns only) — used for static validation.
CUSTOMERS_CSV_COLUMNS = [field.name for field in CUSTOMERS_BRONZE_SCHEMA.fields]
PRODUCTS_CSV_COLUMNS = [field.name for field in PRODUCTS_BRONZE_SCHEMA.fields]
ORDERS_CSV_COLUMNS = [field.name for field in ORDERS_BRONZE_SCHEMA.fields]

EXPECTED_ROW_COUNTS = {
    "customers": 10_010,
    "products": 500,
    "orders": 100_020,
}
