"""Constants and allowed values for Silver quality checks."""

from __future__ import annotations

ALLOWED_CUSTOMER_SEGMENTS = frozenset({"Premium", "Standard", "Basic"})
ALLOWED_ORDER_STATUSES = frozenset(
    {"Completed", "Pending", "Shipped", "Cancelled", "Returned"}
)
ALLOWED_PRODUCT_CATEGORIES = frozenset(
    {"Electronics", "Clothing", "Home", "Sports", "Books", "Beauty", "Toys", "Garden"}
)

# Total amount tolerance for quantity * unit_price comparison.
AMOUNT_TOLERANCE = 0.01

# Assignment-mandated defect counts (for metrics logging / tests).
EXPECTED_DEFECT_COUNTS = {
    "completeness:email_null": 50,
    "completeness:customer_id_null": 100,
    "completeness:product_id_null": 200,
    "referential:invalid_customer_id": 50,
    "referential:invalid_product_id": 30,
    "uniqueness:duplicate_customer_id": 10,  # duplicate keys (>=10 rows flagged)
    "uniqueness:duplicate_order_id": 20,
}

ENTITY_PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
}

ENTITY_PARTITION_COLUMNS = {
    "customers": (),
    "products": (),
    "orders": ("order_date",),
}
