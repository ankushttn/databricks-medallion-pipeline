"""Tests for dashboard SQL queries against local Gold temp views."""

from __future__ import annotations

import pytest

from dashboard.query_loader import load_dashboard_queries, localize_sql
from dashboard.validate_dashboard_local import (
    REQUIRED_QUERIES,
    collect_kpi_snapshot,
    validate_query,
)

pytestmark = [pytest.mark.dashboard, pytest.mark.spark]


@pytest.fixture(scope="module")
def dashboard_queries(gold_tables):
    return {q.name: localize_sql(q.sql) for q in load_dashboard_queries()}


def test_required_queries_present(dashboard_queries):
    assert REQUIRED_QUERIES.issubset(set(dashboard_queries))


@pytest.mark.parametrize("query_name", sorted(REQUIRED_QUERIES))
def test_required_query_executes(spark, dashboard_queries, query_name):
    result = validate_query(spark, query_name, dashboard_queries[query_name])
    assert result.passed, result.detail


def test_all_queries_execute(spark, dashboard_queries):
    failures = []
    for name, sql in dashboard_queries.items():
        result = validate_query(spark, name, sql)
        if not result.passed:
            failures.append(f"{name}: {result.detail}")
    assert not failures, "; ".join(failures)


def test_kpi_totals_match_gold_trends(spark, dashboard_queries):
    snapshot = collect_kpi_snapshot(spark, dashboard_queries)
    trends = spark.table("gold_daily_weekly_trends").filter("trend_grain = 'DAILY'")
    expected_revenue = float(trends.agg({"total_revenue": "sum"}).collect()[0][0])
    expected_orders = int(trends.agg({"total_orders": "sum"}).collect()[0][0])

    assert abs(float(snapshot["total_revenue"]) - expected_revenue) < 0.01
    assert int(snapshot["total_orders"]) == expected_orders


def test_top_products_query_returns_at_most_ten_rows(spark, dashboard_queries):
    count = spark.sql(dashboard_queries["chart_top_10_products_by_revenue"]).count()
    assert 0 < count <= 10


def test_segmentation_customer_counts_sum_to_valid_customers(spark, dashboard_queries):
    segment_total = (
        spark.sql(dashboard_queries["chart_customer_segmentation"])
        .agg({"customer_count": "sum"})
        .collect()[0][0]
    )
    customer_total = spark.sql(dashboard_queries["kpi_total_customers"]).collect()[0][0]
    assert int(segment_total) == int(customer_total)
