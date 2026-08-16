"""Constants for Gold layer aggregations."""

from __future__ import annotations

# Customers with actual revenue (sum of valid orders) at or above this threshold
# are classified as High-Value. See GOLD_ARCHITECTURE.md for full segmentation rules.
HIGH_VALUE_REVENUE_THRESHOLD = 2500.00

GOLD_TABLE_SCRIPTS: tuple[tuple[str, str], ...] = (
    ("01_sales_by_product.sql", "sales_by_product"),
    ("02_revenue_by_customer.sql", "revenue_by_customer"),
    ("03_daily_weekly_trends.sql", "daily_weekly_trends"),
    ("04_customer_segmentation.sql", "customer_segmentation"),
)

SEGMENT_TYPES = ("High-Value", "Repeat", "One-Time", "Inactive")
