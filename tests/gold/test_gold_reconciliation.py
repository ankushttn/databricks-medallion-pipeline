"""Senior-level Gold reconciliation tests."""

from __future__ import annotations

import pytest
from pyspark.sql import functions as F

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD
from gold.reconciliation import (
    classify_segment,
    expected_customer_segmentation,
    reconcile_duplicate_and_null_handling,
    reconcile_revenue_by_customer,
    reconcile_sales_by_product,
    reconcile_segmentation,
    reconcile_trends,
    run_full_reconciliation,
    select_representative_customer_ids,
    select_representative_product_ids,
    trace_customer,
    trace_product,
    valid_orders,
)

pytestmark = [pytest.mark.gold, pytest.mark.spark, pytest.mark.integration]


def test_full_reconciliation_passes(reconciliation_context: dict) -> None:
    report = run_full_reconciliation(
        reconciliation_context["spark"],
        reconciliation_context["config"],
        reconciliation_context["bronze_orders"],
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
        reconciliation_context["silver_products"],
    )
    failures = [r for r in report.results if not r.passed]
    trace_failures = [t for t in report.product_traces + report.customer_traces if not t.passed]
    assert not failures, f"Reconciliation failures: {failures}"
    assert not trace_failures, f"Trace failures: {trace_failures}"
    assert len(report.product_traces) >= 5
    assert len(report.customer_traces) >= 5


def test_sales_by_product_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    results = reconcile_sales_by_product(
        gold_sales,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_products"],
    )
    assert all(r.passed for r in results)


def test_revenue_by_customer_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_revenue = spark.table(config.gold_table("revenue_by_customer"))
    results = reconcile_revenue_by_customer(
        gold_revenue,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert all(r.passed for r in results)


def test_trends_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_trends = spark.table(config.gold_table("daily_weekly_trends"))
    results = reconcile_trends(gold_trends, reconciliation_context["silver_orders"])
    assert all(r.passed for r in results)


def test_segmentation_independent_match(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_segments = spark.table(config.gold_table("customer_segmentation"))
    results = reconcile_segmentation(
        gold_segments,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert all(r.passed for r in results)


def test_duplicate_and_null_exclusion(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    results = reconcile_duplicate_and_null_handling(
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
        reconciliation_context["silver_products"],
        gold_sales,
    )
    assert all(r.passed for r in results)


def test_five_product_traces(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_sales = spark.table(config.gold_table("sales_by_product"))
    product_ids = select_representative_product_ids(gold_sales)
    assert len(product_ids) == 5
    for product_id in product_ids:
        trace = trace_product(
            product_id,
            reconciliation_context["bronze_orders"],
            reconciliation_context["silver_orders"],
            reconciliation_context["silver_products"],
            gold_sales,
        )
        assert trace.passed, f"Product {product_id} trace failed: {trace}"


def test_five_customer_traces(reconciliation_context: dict) -> None:
    spark = reconciliation_context["spark"]
    config = reconciliation_context["config"]
    gold_revenue = spark.table(config.gold_table("revenue_by_customer"))
    customer_ids = select_representative_customer_ids(
        gold_revenue,
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    assert len(customer_ids) == 5
    for customer_id in customer_ids:
        trace = trace_customer(
            customer_id,
            reconciliation_context["bronze_orders"],
            reconciliation_context["silver_orders"],
            reconciliation_context["silver_customers"],
            gold_revenue,
        )
        assert trace.passed, f"Customer {customer_id} trace failed: {trace}"


@pytest.mark.unit
def test_classify_segment_boundary() -> None:
    assert classify_segment(0, 0) == "Inactive"
    assert classify_segment(1, HIGH_VALUE_REVENUE_THRESHOLD) == "High-Value"
    assert classify_segment(1, HIGH_VALUE_REVENUE_THRESHOLD - 0.01) == "One-Time"
    assert classify_segment(2, 100) == "Repeat"


def test_expected_segmentation_sums_to_valid_customers(reconciliation_context: dict) -> None:
    expected = expected_customer_segmentation(
        reconciliation_context["silver_orders"],
        reconciliation_context["silver_customers"],
    )
    total = expected.agg(F.sum("customer_count")).collect()[0][0]
    valid_customers = reconciliation_context["silver_customers"].filter(F.col("_is_valid")).count()
    assert total == valid_customers


def test_valid_order_dedup_count(reconciliation_context: dict) -> None:
    silver_orders = reconciliation_context["silver_orders"]
    raw_valid = silver_orders.filter(F.col("_is_valid")).count()
    dedup_valid = valid_orders(silver_orders).select("order_id").dropDuplicates(["order_id"]).count()
    assert dedup_valid == raw_valid, "No duplicate valid order_id rows should exist"
