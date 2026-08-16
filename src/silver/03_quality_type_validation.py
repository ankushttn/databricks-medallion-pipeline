"""Silver layer: type and format validation quality checks."""

from __future__ import annotations

from pyspark.sql import DataFrame

from silver.check_helpers import (
    allowed_values_check,
    email_format_check,
    typed_null_check,
)
from silver.constants import ALLOWED_CUSTOMER_SEGMENTS, ALLOWED_PRODUCT_CATEGORIES
from silver.quality_framework import QualityCheck, QualityContext

DIMENSION = "type_validation"


def prepare(df: DataFrame, ctx: QualityContext) -> DataFrame:
    """Type validation operates on existing typed Bronze columns."""
    return df


def get_checks(ctx: QualityContext) -> list[QualityCheck]:
    """Return entity-specific type, format, and allowed-value checks."""
    if ctx.entity == "customers":
        return [
            typed_null_check("TYP-CUST-001", "customer_id", "integer"),
            typed_null_check("TYP-CUST-002", "signup_date", "date"),
            typed_null_check("TYP-CUST-003", "lifetime_value", "decimal"),
            email_format_check(),
            allowed_values_check(
                "TYP-CUST-005",
                "customer_segment",
                ALLOWED_CUSTOMER_SEGMENTS,
            ),
        ]
    if ctx.entity == "products":
        return [
            typed_null_check("TYP-PROD-001", "product_id", "integer"),
            typed_null_check("TYP-PROD-002", "price", "decimal"),
            typed_null_check("TYP-PROD-003", "cost", "decimal"),
            typed_null_check("TYP-PROD-004", "stock_quantity", "integer"),
            typed_null_check("TYP-PROD-005", "reorder_level", "integer"),
            allowed_values_check(
                "TYP-PROD-006",
                "category",
                ALLOWED_PRODUCT_CATEGORIES,
            ),
        ]
    if ctx.entity == "orders":
        return [
            typed_null_check("TYP-ORD-001", "order_id", "integer"),
            typed_null_check("TYP-ORD-004", "order_date", "date"),
            typed_null_check("TYP-ORD-005", "quantity", "integer"),
            typed_null_check("TYP-ORD-006", "unit_price", "decimal"),
            typed_null_check("TYP-ORD-007", "total_amount", "decimal"),
            typed_null_check("TYP-ORD-008", "order_status", "string"),
        ]
    return []
