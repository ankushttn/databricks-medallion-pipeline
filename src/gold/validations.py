"""Gold table validation query definitions."""

from __future__ import annotations

from dataclasses import dataclass

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD, SEGMENT_TYPES


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a single Gold validation query."""

    table_name: str
    validation_name: str
    description: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class GoldValidation:
    """Declarative Gold validation query."""

    table_name: str
    name: str
    description: str
    sql: str


VALIDATIONS: tuple[GoldValidation, ...] = (
    GoldValidation(
        table_name="gold.sales_by_product",
        name="no_null_product_keys",
        description="Every row has a non-null product_id.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_sales_by_product}
            WHERE product_id IS NULL
        """,
    ),
    GoldValidation(
        table_name="gold.sales_by_product",
        name="non_negative_metrics",
        description="Revenue and order counts are non-negative.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_sales_by_product}
            WHERE total_orders < 0 OR total_revenue < 0 OR avg_order_value < 0
        """,
    ),
    GoldValidation(
        table_name="gold.sales_by_product",
        name="avg_order_value_consistency",
        description="avg_order_value equals total_revenue / total_orders when orders > 0.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_sales_by_product}
            WHERE total_orders > 0
              AND ABS(avg_order_value - (total_revenue / total_orders)) > 0.01
        """,
    ),
    GoldValidation(
        table_name="gold.sales_by_product",
        name="no_duplicate_products",
        description="Grain is one row per product_id.",
        sql="""
            SELECT
                COUNT(*) = COUNT(DISTINCT product_id) AS passed,
                CONCAT(
                    'rows=', CAST(COUNT(*) AS STRING),
                    ' distinct_products=', CAST(COUNT(DISTINCT product_id) AS STRING)
                ) AS detail
            FROM {gold_sales_by_product}
        """,
    ),
    GoldValidation(
        table_name="gold.revenue_by_customer",
        name="no_null_customer_keys",
        description="Every row has a non-null customer_id.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_revenue_by_customer}
            WHERE customer_id IS NULL
        """,
    ),
    GoldValidation(
        table_name="gold.revenue_by_customer",
        name="lifetime_value_matches_revenue",
        description="lifetime_value_actual equals total_revenue.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_revenue_by_customer}
            WHERE ABS(lifetime_value_actual - total_revenue) > 0.01
        """,
    ),
    GoldValidation(
        table_name="gold.revenue_by_customer",
        name="avg_order_value_consistency",
        description="avg_order_value equals total_revenue / total_orders when orders > 0.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_revenue_by_customer}
            WHERE total_orders > 0
              AND ABS(avg_order_value - (total_revenue / total_orders)) > 0.01
        """,
    ),
    GoldValidation(
        table_name="gold.revenue_by_customer",
        name="no_duplicate_customers",
        description="Grain is one row per customer_id.",
        sql="""
            SELECT
                COUNT(*) = COUNT(DISTINCT customer_id) AS passed,
                CONCAT(
                    'rows=', CAST(COUNT(*) AS STRING),
                    ' distinct_customers=', CAST(COUNT(DISTINCT customer_id) AS STRING)
                ) AS detail
            FROM {gold_revenue_by_customer}
        """,
    ),
    GoldValidation(
        table_name="gold.daily_weekly_trends",
        name="no_null_dates",
        description="Trend rows have non-null date and week.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_daily_weekly_trends}
            WHERE date IS NULL OR week IS NULL
        """,
    ),
    GoldValidation(
        table_name="gold.daily_weekly_trends",
        name="avg_order_value_consistency",
        description="avg_order_value equals total_revenue / total_orders when orders > 0.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_daily_weekly_trends}
            WHERE total_orders > 0
              AND ABS(avg_order_value - (total_revenue / total_orders)) > 0.01
        """,
    ),
    GoldValidation(
        table_name="gold.daily_weekly_trends",
        name="daily_and_weekly_grains_present",
        description="Both DAILY and WEEKLY trend grains exist.",
        sql="""
            SELECT
                COUNT(DISTINCT trend_grain) = 2 AS passed,
                CONCAT(
                    'grains=', CAST(COLLECT_SET(trend_grain) AS STRING)
                ) AS detail
            FROM {gold_daily_weekly_trends}
        """,
    ),
    GoldValidation(
        table_name="gold.customer_segmentation",
        name="segment_count_within_bounds",
        description="At most four behavioral segment types; all values are allowed types.",
        sql="""
            SELECT
                COUNT(DISTINCT segment_type) <= 4
                AND COUNT_IF(
                    segment_type NOT IN ('High-Value', 'Repeat', 'One-Time', 'Inactive')
                ) = 0 AS passed,
                CONCAT(
                    'segments=', CAST(COLLECT_SET(segment_type) AS STRING),
                    ' count=', CAST(COUNT(DISTINCT segment_type) AS STRING)
                ) AS detail
            FROM {gold_customer_segmentation}
        """,
    ),
    GoldValidation(
        table_name="gold.customer_segmentation",
        name="customer_count_positive",
        description="Each segment has at least one customer.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_customer_segmentation}
            WHERE customer_count <= 0
        """,
    ),
    GoldValidation(
        table_name="gold.customer_segmentation",
        name="avg_revenue_consistency",
        description="avg_revenue equals total_revenue / customer_count.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COUNT(*) AS STRING) AS detail
            FROM {gold_customer_segmentation}
            WHERE customer_count > 0
              AND ABS(avg_revenue - (total_revenue / customer_count)) > 0.01
        """,
    ),
    GoldValidation(
        table_name="gold.customer_segmentation",
        name="segment_types_allowed",
        description="Only expected segment_type values are used.",
        sql="""
            SELECT
                COUNT(*) = 0 AS passed,
                CAST(COLLECT_SET(segment_type) AS STRING) AS detail
            FROM {gold_customer_segmentation}
            WHERE segment_type NOT IN ('High-Value', 'Repeat', 'One-Time', 'Inactive')
        """,
    ),
)

# Export for documentation/tests
EXPECTED_SEGMENT_TYPES = SEGMENT_TYPES
HIGH_VALUE_THRESHOLD = HIGH_VALUE_REVENUE_THRESHOLD
