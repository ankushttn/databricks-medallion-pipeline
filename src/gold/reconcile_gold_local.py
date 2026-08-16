"""Run independent Gold reconciliation and write a report."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pyspark.sql import SparkSession

from bronze.schemas import (
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)
from gold.config import GoldConfig
from gold.gold_engine import run_gold_pipeline, setup_logging
from gold.reconciliation import ReconciliationReport, run_full_reconciliation
from gold.validate_gold_local import build_silver_tables, read_bronze_csv, register_silver_views

logger = logging.getLogger(__name__)


def render_report(report: ReconciliationReport, run_id: str) -> str:
    lines = [
        "# Gold Reconciliation Report",
        "",
        f"**Run ID:** `{run_id}`  ",
        f"**Status:** {'PASS' if report.all_passed else 'FAIL'}",
        "",
        "Independent reconciliation recomputes Gold metrics using alternate aggregation paths",
        "(deduplicated order facts, semi-joins, Python segment classification) and compares",
        "row-level results to Gold SQL output.",
        "",
        "## Reconciliation Checks",
        "",
        "| check_name | table | result | gold | expected | detail |",
        "|------------|-------|--------|------|----------|--------|",
    ]
    for result in report.results:
        status = "PASS" if result.passed else "**FAIL**"
        lines.append(
            f"| {result.check_name} | {result.table_name} | {status} | "
            f"{result.gold_value} | {result.expected_value} | {result.detail} |"
        )

    lines.extend(["", "## Product Traces (Bronze → Silver → Gold)", ""])
    lines.append(
        "| product_id | bronze_rows | silver_valid | silver_invalid | "
        "gold_orders | expected_orders | gold_revenue | expected_revenue | result | notes |"
    )
    lines.append(
        "|------------|-------------|--------------|----------------|"
        "-------------|-----------------|--------------|------------------|--------|-------|"
    )
    for trace in report.product_traces:
        status = "PASS" if trace.passed else "**FAIL**"
        lines.append(
            f"| {trace.entity_id} | {trace.bronze_order_rows} | {trace.silver_valid_order_rows} | "
            f"{trace.silver_invalid_order_rows} | {trace.gold_total_orders} | "
            f"{trace.expected_total_orders} | {trace.gold_total_revenue} | "
            f"{trace.expected_total_revenue:.2f} | {status} | {trace.notes} |"
        )

    lines.extend(["", "## Customer Traces (Bronze → Silver → Gold)", ""])
    lines.append(
        "| customer_id | bronze_rows | silver_valid | silver_invalid | "
        "gold_orders | expected_orders | gold_revenue | expected_revenue | result | notes |"
    )
    lines.append(
        "|------------|-------------|--------------|----------------|"
        "-------------|-----------------|--------------|------------------|--------|-------|"
    )
    for trace in report.customer_traces:
        status = "PASS" if trace.passed else "**FAIL**"
        lines.append(
            f"| {trace.entity_id} | {trace.bronze_order_rows} | {trace.silver_valid_order_rows} | "
            f"{trace.silver_invalid_order_rows} | {trace.gold_total_orders} | "
            f"{trace.expected_total_orders} | {trace.gold_total_revenue} | "
            f"{trace.expected_total_revenue:.2f} | {status} | {trace.notes} |"
        )

    return "\n".join(lines) + "\n"


def run_reconciliation(data_dir: Path, run_id: str | None = None) -> ReconciliationReport:
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("gold-reconciliation")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    validated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    bronze_orders = read_bronze_csv(spark, data_dir, "orders")
    silver_customers, silver_products, silver_orders = build_silver_tables(
        spark, data_dir, run_id, validated_at
    )
    register_silver_views(spark, silver_customers, silver_products, silver_orders)

    config = GoldConfig(local_mode=True)
    run_gold_pipeline(config, spark=spark)

    return run_full_reconciliation(
        spark,
        config,
        bronze_orders,
        silver_orders,
        silver_customers,
        silver_products,
    )


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Independent Gold reconciliation.")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[2]
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    run_id = args.run_id or "gold-reconciliation-001"
    report = run_reconciliation(data_dir, run_id=run_id)

    md_path = output_dir / "GOLD_RECONCILIATION_REPORT.md"
    json_path = output_dir / "GOLD_RECONCILIATION_REPORT.json"
    md_path.write_text(render_report(report, run_id), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "all_passed": report.all_passed,
                "results": [asdict(r) for r in report.results],
                "product_traces": [asdict(t) for t in report.product_traces],
                "customer_traces": [asdict(t) for t in report.customer_traces],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    logger.info("Reconciliation report: %s (passed=%s)", md_path, report.all_passed)
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
