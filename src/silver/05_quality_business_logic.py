"""Silver layer: business logic quality checks."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from silver.check_helpers import business_rule_check
from silver.constants import ALLOWED_ORDER_STATUSES, AMOUNT_TOLERANCE
from silver.quality_framework import QualityCheck, QualityContext, is_null_or_blank

DIMENSION = "business_logic"


def prepare(df: DataFrame, ctx: QualityContext) -> DataFrame:
    """Business rules operate on existing entity columns."""
    return df


def get_checks(ctx: QualityContext) -> list[QualityCheck]:
    """Return entity-specific business rule checks."""
    if ctx.entity == "customers":
        return [
            business_rule_check(
                "BUS-CUST-001",
                "lifetime value non-negative",
                "business:negative_lifetime_value",
                F.col("lifetime_value").isNotNull() & (F.col("lifetime_value") < 0),
                failure_reason="lifetime_value must be greater than or equal to zero",
            ),
        ]
    if ctx.entity == "products":
        return [
            business_rule_check(
                "BUS-PROD-001",
                "price positive",
                "business:non_positive_price",
                F.col("price").isNotNull() & (F.col("price") <= 0),
                failure_reason="price must be greater than zero",
            ),
            business_rule_check(
                "BUS-PROD-002",
                "cost non-negative",
                "business:negative_cost",
                F.col("cost").isNotNull() & (F.col("cost") < 0),
                failure_reason="cost must be greater than or equal to zero",
            ),
            business_rule_check(
                "BUS-PROD-003",
                "stock quantity non-negative",
                "business:negative_stock_quantity",
                F.col("stock_quantity").isNotNull() & (F.col("stock_quantity") < 0),
                failure_reason="stock_quantity must be greater than or equal to zero",
            ),
            business_rule_check(
                "BUS-PROD-004",
                "reorder level non-negative",
                "business:negative_reorder_level",
                F.col("reorder_level").isNotNull() & (F.col("reorder_level") < 0),
                failure_reason="reorder_level must be greater than or equal to zero",
            ),
            business_rule_check(
                "BUS-PROD-005",
                "price not below cost",
                "business:price_below_cost",
                F.col("price").isNotNull()
                & F.col("cost").isNotNull()
                & (F.col("price") < F.col("cost")),
                failure_reason="price must be greater than or equal to cost",
            ),
        ]
    if ctx.entity == "orders":
        expected_total = (
            F.col("quantity").cast("decimal(12,2)") * F.col("unit_price").cast("decimal(12,2)")
        )
        amount_diff = F.abs(
            F.col("total_amount").cast("decimal(12,2)") - expected_total
        )
        typed_inputs_present = (
            F.col("quantity").isNotNull()
            & F.col("unit_price").isNotNull()
            & F.col("total_amount").isNotNull()
        )
        return [
            business_rule_check(
                "BUS-ORD-001",
                "quantity positive",
                "business:non_positive_quantity",
                F.col("quantity").isNotNull() & (F.col("quantity") <= 0),
                failure_reason="quantity must be greater than zero",
            ),
            business_rule_check(
                "BUS-ORD-002",
                "unit price non-negative",
                "business:negative_unit_price",
                F.col("unit_price").isNotNull() & (F.col("unit_price") < 0),
                failure_reason="unit_price must be greater than or equal to zero",
            ),
            business_rule_check(
                "BUS-ORD-003",
                "total amount consistency",
                "business:total_amount_mismatch",
                typed_inputs_present & (amount_diff > F.lit(AMOUNT_TOLERANCE)),
                failure_reason="total_amount must equal quantity * unit_price within tolerance",
            ),
            business_rule_check(
                "BUS-ORD-004",
                "order status allowed values",
                "business:invalid_order_status",
                (~is_null_or_blank(F.col("order_status")))
                & (~F.col("order_status").isin(*sorted(ALLOWED_ORDER_STATUSES))),
                failure_reason="order_status is not a recognized lifecycle state",
            ),
            business_rule_check(
                "BUS-ORD-005",
                "payment date not before order date",
                "business:payment_before_order",
                F.col("payment_date").isNotNull()
                & F.col("order_date").isNotNull()
                & (F.col("payment_date") < F.col("order_date")),
                failure_reason="payment_date cannot be earlier than order_date",
            ),
            business_rule_check(
                "BUS-ORD-006",
                "completed orders require payment date",
                "business:missing_payment_date",
                (F.col("order_status") == F.lit("Completed"))
                & F.col("payment_date").isNull(),
                failure_reason="Completed orders must have a payment_date",
            ),
        ]
    return []
