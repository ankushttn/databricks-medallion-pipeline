"""Validate dashboard queries locally against Gold temp views built from sample CSV data."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pyspark.sql import SparkSession
from pyspark.sql.utils import AnalysisException
from py4j.protocol import Py4JJavaError

from dashboard.query_loader import load_dashboard_queries, localize_sql
from gold.config import GoldConfig
from gold.gold_engine import run_gold_pipeline, setup_logging
from gold.validate_gold_local import build_silver_tables, read_bronze_csv, register_silver_views

logger = logging.getLogger(__name__)

REQUIRED_QUERIES = {
    "kpi_total_revenue",
    "kpi_total_orders",
    "kpi_average_order_value",
    "kpi_total_customers",
    "chart_top_10_products_by_revenue",
    "chart_customer_revenue_distribution",
    "chart_customer_segmentation",
}


@dataclass
class QueryValidationResult:
    query_name: str
    passed: bool
    row_count: int
    detail: str


@dataclass
class DashboardValidationReport:
    run_id: str
    validated_at: str
    results: list[QueryValidationResult]
    kpi_snapshot: dict[str, float | int]
    all_passed: bool


def get_spark_session() -> SparkSession:
    return (
        SparkSession.builder.master("local[1]")
        .appName("dashboard-local-validation")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )


def _to_number(value) -> float | int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def validate_query(spark: SparkSession, query_name: str, sql: str) -> QueryValidationResult:
    try:
        df = spark.sql(sql)
        row_count = df.count()
        detail = f"executed_ok rows={row_count}"
        passed = row_count >= 0

        if query_name == "chart_top_10_products_by_revenue" and row_count > 10:
            passed = False
            detail = f"expected_at_most_10_rows got={row_count}"
        elif query_name == "chart_customer_revenue_distribution" and row_count == 0:
            passed = False
            detail = "histogram returned zero buckets"
        elif query_name == "chart_customer_segmentation" and row_count == 0:
            passed = False
            detail = "segmentation returned zero rows"
        elif query_name.startswith("kpi_") and row_count != 1:
            passed = False
            detail = f"kpi_expected_single_row got={row_count}"

        return QueryValidationResult(query_name, passed, row_count, detail)
    except (AnalysisException, Py4JJavaError) as exc:
        logger.error(
            "Dashboard query failed name=%s sql_error=%s",
            query_name,
            exc,
            exc_info=True,
        )
        return QueryValidationResult(query_name, False, 0, f"sql_error={exc}")


def collect_kpi_snapshot(spark: SparkSession, queries: dict[str, str]) -> dict[str, float | int]:
    snapshot: dict[str, float | int] = {}
    kpi_map = {
        "kpi_total_revenue": "total_revenue",
        "kpi_total_orders": "total_orders",
        "kpi_average_order_value": "avg_order_value",
        "kpi_total_customers": "total_customers",
    }
    for query_name, column in kpi_map.items():
        row = spark.sql(queries[query_name]).collect()[0]
        snapshot[column] = _to_number(row[column])
    return snapshot


def run_dashboard_validation(
    data_dir: Path,
    run_id: str = "dashboard-validation-001",
) -> DashboardValidationReport:
    spark = get_spark_session()
    validated_at = datetime.now(timezone.utc)

    silver_customers, silver_products, silver_orders = build_silver_tables(
        spark, data_dir, run_id, validated_at
    )
    register_silver_views(spark, silver_customers, silver_products, silver_orders)
    config = GoldConfig(local_mode=True)
    run_gold_pipeline(config, spark)

    queries = {
        q.name: localize_sql(q.sql)
        for q in load_dashboard_queries()
    }
    missing = REQUIRED_QUERIES - set(queries)
    if missing:
        raise ValueError(f"Missing required dashboard queries: {sorted(missing)}")

    results = [
        validate_query(spark, name, sql)
        for name, sql in sorted(queries.items())
    ]
    kpi_snapshot = collect_kpi_snapshot(spark, queries)

    # Cross-check KPI totals against Gold trends (duplicate-join safe: same single table).
    trends = spark.table("gold_daily_weekly_trends").filter("trend_grain = 'DAILY'")
    expected_revenue = float(trends.agg({"total_revenue": "sum"}).collect()[0][0])
    expected_orders = int(trends.agg({"total_orders": "sum"}).collect()[0][0])
    revenue_ok = abs(float(kpi_snapshot["total_revenue"]) - expected_revenue) < 0.01
    orders_ok = int(kpi_snapshot["total_orders"]) == expected_orders
    if not revenue_ok or not orders_ok:
        results.append(
            QueryValidationResult(
                "kpi_cross_check_trends",
                False,
                0,
                f"revenue_ok={revenue_ok} orders_ok={orders_ok}",
            )
        )
    else:
        results.append(
            QueryValidationResult(
                "kpi_cross_check_trends",
                True,
                1,
                "KPI totals match gold.daily_weekly_trends DAILY grain",
            )
        )

    all_passed = all(r.passed for r in results)
    return DashboardValidationReport(
        run_id=run_id,
        validated_at=validated_at.isoformat(),
        results=results,
        kpi_snapshot=kpi_snapshot,
        all_passed=all_passed,
    )


def render_report(report: DashboardValidationReport) -> str:
    lines = [
        "# Dashboard Query Validation Report",
        "",
        f"**Run ID:** `{report.run_id}`  ",
        f"**Validated at:** {report.validated_at}  ",
        f"**Status:** {'PASS' if report.all_passed else 'FAIL'}",
        "",
        "Local validation executes each query in `dashboard_queries.sql` against",
        "Gold temp views built from sample CSV data. This does **not** verify",
        "Databricks SQL Dashboard UI configuration.",
        "",
        "## KPI Snapshot",
        "",
        "| metric | value |",
        "|--------|-------|",
    ]
    for key, value in report.kpi_snapshot.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(
        [
            "",
            "## Query Results",
            "",
            "| query_name | result | row_count | detail |",
            "|------------|--------|-----------|--------|",
        ]
    )
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"| {result.query_name} | {status} | {result.row_count} | {result.detail} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Validate dashboard queries locally.")
    parser.add_argument("--data-dir", default="data", help="Directory containing Bronze CSV files")
    parser.add_argument("--output-dir", default="data", help="Directory for validation report")
    parser.add_argument("--run-id", default=None, help="Validation run identifier")
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[2]
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    run_id = args.run_id or "dashboard-validation-001"
    report = run_dashboard_validation(data_dir, run_id=run_id)

    md_path = output_dir / "DASHBOARD_VALIDATION_REPORT.md"
    json_path = output_dir / "DASHBOARD_VALIDATION_REPORT.json"
    md_path.write_text(render_report(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(asdict(report), indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Dashboard validation report: %s (passed=%s)", md_path, report.all_passed)
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
