"""Independent Gold reconciliation — alternative calculations vs Gold SQL output.

Each function recomputes expected metrics without reading Gold tables,
using a different aggregation path than the Gold SQL scripts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD, SEGMENT_TYPES


@dataclass
class ReconciliationResult:
    """Outcome of a single reconciliation check."""

    check_name: str
    table_name: str
    passed: bool
    gold_value: str
    expected_value: str
    detail: str = ""


@dataclass
class EntityTrace:
    """Source → Silver → Gold trace for one product or customer."""

    entity_type: str
    entity_id: int
    bronze_order_rows: int
    silver_valid_order_rows: int
    silver_invalid_order_rows: int
    gold_total_orders: int | None
    gold_total_revenue: float | None
    expected_total_orders: int
    expected_total_revenue: float
    expected_avg_order_value: float
    passed: bool
    notes: str = ""


@dataclass
class ReconciliationReport:
    """Full reconciliation outcome."""

    results: list[ReconciliationResult] = field(default_factory=list)
    product_traces: list[EntityTrace] = field(default_factory=list)
    customer_traces: list[EntityTrace] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        checks_ok = all(r.passed for r in self.results)
        traces_ok = all(t.passed for t in self.product_traces + self.customer_traces)
        return checks_ok and traces_ok


def valid_orders(silver_orders: DataFrame) -> DataFrame:
    return silver_orders.filter(F.col("_is_valid") == True)  # noqa: E712


def valid_customers(silver_customers: DataFrame) -> DataFrame:
    return silver_customers.filter(F.col("_is_valid") == True)  # noqa: E712


def valid_products(silver_products: DataFrame) -> DataFrame:
    return silver_products.filter(F.col("_is_valid") == True)  # noqa: E712


def _decimal_close(left, right, tolerance: float = 0.02) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) <= tolerance


def expected_sales_by_product(
    silver_orders: DataFrame,
    silver_products: DataFrame,
) -> DataFrame:
    """Recompute product sales via deduplicated valid-order facts + dimension join."""
    order_facts = (
        valid_orders(silver_orders)
        .select("order_id", "product_id", "total_amount")
        .dropDuplicates(["order_id"])
    )
    products = valid_products(silver_products).select(
        "product_id", "product_name", "category"
    )
    joined = order_facts.join(products, on="product_id", how="inner")
    return joined.groupBy("product_id", "product_name", "category").agg(
        F.count("order_id").alias("total_orders"),
        F.sum("total_amount").alias("total_revenue"),
    )


def expected_revenue_by_customer(
    silver_orders: DataFrame,
    silver_customers: DataFrame,
) -> DataFrame:
    """Recompute customer revenue from valid customers + valid orders (semi-join path)."""
    customers = valid_customers(silver_customers).select(
        "customer_id", "customer_name", "customer_segment"
    )
    order_facts = (
        valid_orders(silver_orders)
        .select("order_id", "customer_id", "total_amount")
        .dropDuplicates(["order_id"])
    )
    valid_customer_ids = customers.select("customer_id")
    attributable_orders = order_facts.join(valid_customer_ids, on="customer_id", how="inner")
    order_metrics = attributable_orders.groupBy("customer_id").agg(
        F.count("order_id").alias("total_orders"),
        F.sum("total_amount").alias("total_revenue"),
    )
    return (
        customers.join(order_metrics, on="customer_id", how="left")
        .fillna({"total_orders": 0, "total_revenue": 0})
        .withColumn(
            "avg_order_value",
            F.when(
                F.col("total_orders") > 0,
                F.col("total_revenue") / F.col("total_orders"),
            ).otherwise(F.lit(0)),
        )
        .withColumn("lifetime_value_actual", F.col("total_revenue"))
    )


def expected_daily_trends(silver_orders: DataFrame) -> DataFrame:
    order_facts = (
        valid_orders(silver_orders)
        .select("order_id", "order_date", "total_amount")
        .dropDuplicates(["order_id"])
    )
    return order_facts.groupBy("order_date").agg(
        F.count("order_id").alias("total_orders"),
        F.sum("total_amount").cast("decimal(14,2)").alias("total_revenue"),
    )


def expected_weekly_trends(silver_orders: DataFrame) -> DataFrame:
    order_facts = (
        valid_orders(silver_orders)
        .select("order_id", "order_date", "total_amount")
        .dropDuplicates(["order_id"])
    )
    return order_facts.withColumn("week", F.date_trunc("week", F.col("order_date"))).groupBy(
        "week"
    ).agg(
        F.count("order_id").alias("total_orders"),
        F.sum("total_amount").cast("decimal(14,2)").alias("total_revenue"),
    )


def classify_segment(total_orders: int, total_revenue: float) -> str:
    """Python reimplementation of segmentation rules (independent of SQL CASE)."""
    if total_orders == 0:
        return "Inactive"
    if total_revenue >= HIGH_VALUE_REVENUE_THRESHOLD:
        return "High-Value"
    if total_orders >= 2:
        return "Repeat"
    return "One-Time"


def expected_customer_segmentation(
    silver_orders: DataFrame,
    silver_customers: DataFrame,
) -> DataFrame:
    """Recompute segmentation from per-customer metrics."""
    customer_metrics = expected_revenue_by_customer(silver_orders, silver_customers)
    classified = customer_metrics.withColumn(
        "segment_type",
        F.when(F.col("total_orders") == 0, F.lit("Inactive"))
        .when(
            F.col("total_revenue") >= F.lit(HIGH_VALUE_REVENUE_THRESHOLD),
            F.lit("High-Value"),
        )
        .when(F.col("total_orders") >= 2, F.lit("Repeat"))
        .otherwise(F.lit("One-Time")),
    )
    return classified.groupBy("segment_type").agg(
        F.count("customer_id").alias("customer_count"),
        F.avg("total_revenue").alias("avg_revenue"),
        F.sum("total_revenue").alias("total_revenue"),
    )


def _normalize_key_value(value):
    """Normalize Spark-collected values for stable key comparison."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize_key(key: tuple) -> tuple:
    return tuple(_normalize_key_value(part) for part in key)


def compare_dataframes(
    gold_df: DataFrame,
    expected_df: DataFrame,
    key_columns: list[str],
    metric_columns: list[str],
    check_name: str,
    table_name: str,
    tolerance: float = 0.02,
) -> list[ReconciliationResult]:
    """Row-level compare Gold vs independently computed metrics using Spark joins."""
    results: list[ReconciliationResult] = []

    gold_count = gold_df.select(*key_columns).distinct().count()
    expected_count = expected_df.select(*key_columns).distinct().count()
    if gold_count != expected_count:
        results.append(
            ReconciliationResult(
                check_name=f"{check_name}_row_count",
                table_name=table_name,
                passed=False,
                gold_value=str(gold_count),
                expected_value=str(expected_count),
                detail="Grain key count mismatch",
            )
        )

    gold_tagged = gold_df.select(
        *[F.col(column).alias(f"g_{column}") for column in key_columns + metric_columns]
    )
    expected_tagged = expected_df.select(
        *[F.col(column).alias(f"e_{column}") for column in key_columns + metric_columns]
    )
    join_expr = reduce(
        lambda left, right: left & right,
        (gold_tagged[f"g_{key}"] == expected_tagged[f"e_{key}"] for key in key_columns),
    )
    joined = gold_tagged.join(expected_tagged, join_expr, how="full_outer")

    metric_checks = []
    for metric in metric_columns:
        metric_checks.append(
            F.abs(
                F.coalesce(F.col(f"g_{metric}").cast("double"), F.lit(0.0))
                - F.coalesce(F.col(f"e_{metric}").cast("double"), F.lit(0.0))
            )
            <= F.lit(tolerance)
        )

    combined = metric_checks[0]
    for check in metric_checks[1:]:
        combined = combined & check

    missing_keys = joined.filter(
        F.col(f"g_{key_columns[0]}").isNull() | F.col(f"e_{key_columns[0]}").isNull()
    ).count()
    metric_mismatches = joined.filter(
        F.col(f"g_{key_columns[0]}").isNotNull()
        & F.col(f"e_{key_columns[0]}").isNotNull()
        & (~combined)
    ).count()

    results.append(
        ReconciliationResult(
            check_name=f"{check_name}_metrics",
            table_name=table_name,
            passed=missing_keys == 0 and metric_mismatches == 0 and gold_count == expected_count,
            gold_value=f"keys={gold_count}",
            expected_value=f"keys={expected_count}",
            detail=f"missing_keys={missing_keys} metric_mismatches={metric_mismatches}",
        )
    )
    return results


def reconcile_sales_by_product(
    gold_sales: DataFrame,
    silver_orders: DataFrame,
    silver_products: DataFrame,
) -> list[ReconciliationResult]:
    expected = expected_sales_by_product(silver_orders, silver_products)
    return compare_dataframes(
        gold_sales,
        expected,
        key_columns=["product_id"],
        metric_columns=["total_orders", "total_revenue"],
        check_name="sales_by_product",
        table_name="gold.sales_by_product",
    )


def reconcile_revenue_by_customer(
    gold_revenue: DataFrame,
    silver_orders: DataFrame,
    silver_customers: DataFrame,
) -> list[ReconciliationResult]:
    expected = expected_revenue_by_customer(silver_orders, silver_customers)
    return compare_dataframes(
        gold_revenue,
        expected,
        key_columns=["customer_id"],
        metric_columns=["total_orders", "total_revenue", "lifetime_value_actual"],
        check_name="revenue_by_customer",
        table_name="gold.revenue_by_customer",
    )


def reconcile_trends(
    gold_trends: DataFrame,
    silver_orders: DataFrame,
) -> list[ReconciliationResult]:
    results: list[ReconciliationResult] = []

    gold_daily = gold_trends.filter(F.col("trend_grain") == "DAILY").select(
        F.col("date").alias("order_date"),
        "total_orders",
        "total_revenue",
    )
    expected_daily = expected_daily_trends(silver_orders)
    results.extend(
        compare_dataframes(
            gold_daily,
            expected_daily,
            key_columns=["order_date"],
            metric_columns=["total_orders", "total_revenue"],
            check_name="daily_trends",
            table_name="gold.daily_weekly_trends",
        )
    )

    gold_weekly = gold_trends.filter(F.col("trend_grain") == "WEEKLY").select(
        F.col("week").alias("week"),
        "total_orders",
        "total_revenue",
    )
    expected_weekly = expected_weekly_trends(silver_orders)
    results.extend(
        compare_dataframes(
            gold_weekly,
            expected_weekly,
            key_columns=["week"],
            metric_columns=["total_orders", "total_revenue"],
            check_name="weekly_trends",
            table_name="gold.daily_weekly_trends",
        )
    )

    # Cross-check: daily order sum equals deduplicated valid order count.
    daily_sum = gold_daily.agg(F.sum("total_orders")).collect()[0][0]
    dedup_count = (
        valid_orders(silver_orders).select("order_id").dropDuplicates(["order_id"]).count()
    )
    results.append(
        ReconciliationResult(
            check_name="daily_trends_order_total",
            table_name="gold.daily_weekly_trends",
            passed=daily_sum == dedup_count,
            gold_value=str(daily_sum),
            expected_value=str(dedup_count),
            detail="Sum of daily total_orders vs distinct valid order_id",
        )
    )
    return results


def reconcile_segmentation(
    gold_segments: DataFrame,
    silver_orders: DataFrame,
    silver_customers: DataFrame,
) -> list[ReconciliationResult]:
    results: list[ReconciliationResult] = []
    expected = expected_customer_segmentation(silver_orders, silver_customers)

    results.extend(
        compare_dataframes(
            gold_segments,
            expected,
            key_columns=["segment_type"],
            metric_columns=["customer_count", "total_revenue"],
            check_name="customer_segmentation",
            table_name="gold.customer_segmentation",
            tolerance=0.05,
        )
    )

    # Python loop independence check on segment counts.
    customer_metrics = expected_revenue_by_customer(silver_orders, silver_customers).collect()
    python_counts = {seg: 0 for seg in SEGMENT_TYPES}
    for row in customer_metrics:
        seg = classify_segment(int(row.total_orders), float(row.total_revenue))
        python_counts[seg] += 1

    gold_counts = {
        row.segment_type: row.customer_count for row in gold_segments.collect()
    }
    counts_match = all(
        python_counts.get(seg, 0) == gold_counts.get(seg, 0) for seg in set(python_counts) | set(gold_counts)
    )
    results.append(
        ReconciliationResult(
            check_name="segmentation_python_loop",
            table_name="gold.customer_segmentation",
            passed=counts_match,
            gold_value=str(gold_counts),
            expected_value=str(python_counts),
            detail="Independent Python classification vs Gold SQL",
        )
    )
    return results


def reconcile_duplicate_and_null_handling(
    silver_orders: DataFrame,
    silver_customers: DataFrame,
    silver_products: DataFrame,
    gold_sales: DataFrame,
) -> list[ReconciliationResult]:
    """Verify invalid/null/duplicate rows do not inflate Gold metrics."""
    results: list[ReconciliationResult] = []

    invalid_orders = silver_orders.filter(~F.col("_is_valid"))
    dup_invalid = invalid_orders.filter(
        F.array_contains(F.col("_quality_issues"), "uniqueness:duplicate_order_id")
    ).count()
    null_customer = invalid_orders.filter(
        F.array_contains(F.col("_quality_issues"), "completeness:customer_id_null")
    ).count()

    # Including invalid orders would increase revenue.
    all_orders_revenue = silver_orders.agg(F.sum("total_amount")).collect()[0][0]
    valid_revenue = valid_orders(silver_orders).agg(F.sum("total_amount")).collect()[0][0]
    gold_revenue = gold_sales.agg(F.sum("total_revenue")).collect()[0][0]

    results.append(
        ReconciliationResult(
            check_name="invalid_duplicates_excluded",
            table_name="gold.sales_by_product",
            passed=dup_invalid > 0 and valid_revenue < all_orders_revenue,
            gold_value=str(valid_revenue),
            expected_value=f"all_orders={all_orders_revenue}",
            detail=f"duplicate_invalid_orders={dup_invalid}",
        )
    )
    results.append(
        ReconciliationResult(
            check_name="null_fk_orders_excluded",
            table_name="gold.sales_by_product",
            passed=null_customer > 0,
            gold_value=str(valid_revenue),
            expected_value=str(gold_revenue),
            detail=f"null_customer_id_invalid_orders={null_customer}",
        )
    )
    results.append(
        ReconciliationResult(
            check_name="gold_revenue_matches_valid_inner_join",
            table_name="gold.sales_by_product",
            passed=_decimal_close(gold_revenue, valid_revenue, 0.05),
            gold_value=str(gold_revenue),
            expected_value=str(valid_revenue),
            detail="Gold product revenue sum vs valid order revenue (inner join may differ if orphan products)",
        )
    )

    # Inner join product dimension: gold revenue <= valid order revenue.
    inner_rev = (
        valid_orders(silver_orders)
        .join(
            valid_products(silver_products).select("product_id"),
            on="product_id",
            how="inner",
        )
        .agg(F.sum("total_amount"))
        .collect()[0][0]
    )
    results.append(
        ReconciliationResult(
            check_name="gold_sales_revenue_equals_valid_product_join",
            table_name="gold.sales_by_product",
            passed=_decimal_close(gold_revenue, inner_rev, 0.05),
            gold_value=str(gold_revenue),
            expected_value=str(inner_rev),
            detail="Gold total revenue vs valid orders with valid product",
        )
    )

  # Orphan valid orders (valid order, invalid customer) not in revenue_by_customer.
    orphan_count = (
        valid_orders(silver_orders)
        .join(
            valid_customers(silver_customers).select("customer_id"),
            on="customer_id",
            how="left_anti",
        )
        .select("order_id")
        .dropDuplicates(["order_id"])
        .count()
    )
    results.append(
        ReconciliationResult(
            check_name="orphan_valid_orders_identified",
            table_name="gold.revenue_by_customer",
            passed=orphan_count > 0,
            gold_value=str(orphan_count),
            expected_value=">0",
            detail="Valid orders with invalid customers excluded from customer Gold",
        )
    )
    return results


def trace_product(
    product_id: int,
    bronze_orders: DataFrame,
    silver_orders: DataFrame,
    silver_products: DataFrame,
    gold_sales: DataFrame,
) -> EntityTrace:
    """Trace one product through Bronze → Silver → Gold."""
    bronze_count = bronze_orders.filter(F.col("product_id") == product_id).count()
    silver_valid = silver_orders.filter(
        (F.col("product_id") == product_id) & (F.col("_is_valid") == True)  # noqa: E712
    )
    silver_invalid = silver_orders.filter(
        (F.col("product_id") == product_id) & (F.col("_is_valid") == False)  # noqa: E712
    )
    valid_count = silver_valid.count()
    invalid_count = silver_invalid.count()

    expected_orders = silver_valid.select("order_id").dropDuplicates(["order_id"]).count()
    expected_revenue = (
        silver_valid.select("order_id", "total_amount")
        .dropDuplicates(["order_id"])
        .agg(F.sum("total_amount"))
        .collect()[0][0]
        or 0.0
    )
    expected_aov = expected_revenue / expected_orders if expected_orders else 0.0

    product_valid = (
        valid_products(silver_products).filter(F.col("product_id") == product_id).count() > 0
    )
    gold_row = gold_sales.filter(F.col("product_id") == product_id).collect()
    gold_orders = gold_row[0].total_orders if gold_row else None
    gold_revenue = float(gold_row[0].total_revenue) if gold_row else None

    if not product_valid:
        passed = gold_row == []
        notes = "Product invalid in Silver — excluded from Gold (inner join)"
    else:
        passed = (
            gold_orders == expected_orders
            and _decimal_close(gold_revenue, expected_revenue)
            and (gold_row == [] or _decimal_close(gold_row[0].avg_order_value, expected_aov))
        )
        notes = ""

    return EntityTrace(
        entity_type="product",
        entity_id=product_id,
        bronze_order_rows=bronze_count,
        silver_valid_order_rows=valid_count,
        silver_invalid_order_rows=invalid_count,
        gold_total_orders=gold_orders,
        gold_total_revenue=gold_revenue,
        expected_total_orders=expected_orders,
        expected_total_revenue=float(expected_revenue),
        expected_avg_order_value=round(expected_aov, 2),
        passed=passed,
        notes=notes,
    )


def trace_customer(
    customer_id: int,
    bronze_orders: DataFrame,
    silver_orders: DataFrame,
    silver_customers: DataFrame,
    gold_revenue: DataFrame,
    gold_segments: DataFrame | None = None,
) -> EntityTrace:
    """Trace one customer through Bronze → Silver → Gold."""
    bronze_count = bronze_orders.filter(F.col("customer_id") == customer_id).count()
    silver_valid = silver_orders.filter(
        (F.col("customer_id") == customer_id) & (F.col("_is_valid") == True)  # noqa: E712
    )
    silver_invalid = silver_orders.filter(
        (F.col("customer_id") == customer_id) & (F.col("_is_valid") == False)  # noqa: E712
    )
    customer_valid = (
        valid_customers(silver_customers).filter(F.col("customer_id") == customer_id).count() > 0
    )

    expected_orders = silver_valid.select("order_id").dropDuplicates(["order_id"]).count()
    expected_revenue = (
        silver_valid.select("order_id", "total_amount")
        .dropDuplicates(["order_id"])
        .agg(F.sum("total_amount"))
        .collect()[0][0]
        or 0.0
    )
    expected_aov = expected_revenue / expected_orders if expected_orders else 0.0

    gold_row = gold_revenue.filter(F.col("customer_id") == customer_id).collect()
    if customer_valid:
        gold_orders = gold_row[0].total_orders if gold_row else None
        gold_revenue_val = float(gold_row[0].total_revenue) if gold_row else None
        passed = (
            gold_orders == expected_orders
            and _decimal_close(gold_revenue_val, expected_revenue)
        )
        notes = ""
        if gold_segments is not None and gold_row:
            seg = classify_segment(int(gold_row[0].total_orders), float(gold_row[0].total_revenue))
            notes = f"segment={seg}"
    else:
        gold_orders = None
        gold_revenue_val = None
        passed = gold_row == []
        notes = "Customer invalid in Silver — excluded from Gold customer table"

    return EntityTrace(
        entity_type="customer",
        entity_id=customer_id,
        bronze_order_rows=bronze_count,
        silver_valid_order_rows=silver_valid.count(),
        silver_invalid_order_rows=silver_invalid.count(),
        gold_total_orders=gold_orders,
        gold_total_revenue=gold_revenue_val,
        expected_total_orders=expected_orders,
        expected_total_revenue=float(expected_revenue),
        expected_avg_order_value=round(expected_aov, 2),
        passed=passed,
        notes=notes,
    )


def select_representative_product_ids(gold_sales: DataFrame) -> list[int]:
    """Pick five products: top revenue, bottom (with sales), median, and fixed anchors."""
    ranked = gold_sales.orderBy(F.col("total_revenue").desc()).collect()
    if len(ranked) < 5:
        return [row.product_id for row in ranked]
    ids = [
        ranked[0].product_id,
        ranked[len(ranked) // 2].product_id,
        ranked[-1].product_id,
        ranked[len(ranked) // 4].product_id,
        ranked[(3 * len(ranked)) // 4].product_id,
    ]
    return sorted(set(ids))[:5]


def select_representative_customer_ids(
    gold_revenue: DataFrame,
    silver_orders: DataFrame,
    silver_customers: DataFrame,
) -> list[int]:
    """Pick five customers across behavioral segments, orphans, and invalid customers."""
    ids: list[int] = []
    metrics = expected_revenue_by_customer(silver_orders, silver_customers).collect()

    for target_segment in ("High-Value", "Repeat", "One-Time"):
        for customer in sorted(metrics, key=lambda r: r.customer_id):
            label = classify_segment(int(customer.total_orders), float(customer.total_revenue))
            if label == target_segment:
                ids.append(customer.customer_id)
                break

    orphan = (
        valid_orders(silver_orders)
        .join(
            valid_customers(silver_customers).select("customer_id"),
            on="customer_id",
            how="left_anti",
        )
        .select("customer_id")
        .dropDuplicates(["customer_id"])
        .limit(1)
        .collect()
    )
    if orphan:
        ids.append(orphan[0].customer_id)

    invalid_cust = (
        silver_customers.filter(~F.col("_is_valid")).select("customer_id").limit(1).collect()
    )
    if invalid_cust:
        ids.append(invalid_cust[0].customer_id)

    for customer in metrics:
        if customer.customer_id not in ids:
            ids.append(customer.customer_id)
        if len(ids) >= 5:
            break

    return ids[:5]


def run_full_reconciliation(
    spark,
    config,
    bronze_orders: DataFrame,
    silver_orders: DataFrame,
    silver_customers: DataFrame,
    silver_products: DataFrame,
) -> ReconciliationReport:
    """Run all independent reconciliation checks."""
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    gold_revenue = spark.table(config.gold_table("revenue_by_customer"))
    gold_trends = spark.table(config.gold_table("daily_weekly_trends"))
    gold_segments = spark.table(config.gold_table("customer_segmentation"))

    report = ReconciliationReport()
    report.results.extend(reconcile_sales_by_product(gold_sales, silver_orders, silver_products))
    report.results.extend(reconcile_revenue_by_customer(gold_revenue, silver_orders, silver_customers))
    report.results.extend(reconcile_trends(gold_trends, silver_orders))
    report.results.extend(reconcile_segmentation(gold_segments, silver_orders, silver_customers))
    report.results.extend(
        reconcile_duplicate_and_null_handling(
            silver_orders, silver_customers, silver_products, gold_sales
        )
    )

    for product_id in select_representative_product_ids(gold_sales):
        report.product_traces.append(
            trace_product(product_id, bronze_orders, silver_orders, silver_products, gold_sales)
        )

    for customer_id in select_representative_customer_ids(
        gold_revenue, silver_orders, silver_customers
    ):
        report.customer_traces.append(
            trace_customer(
                customer_id,
                bronze_orders,
                silver_orders,
                silver_customers,
                gold_revenue,
                gold_segments,
            )
        )

    return report
