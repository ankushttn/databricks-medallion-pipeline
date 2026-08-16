"""Run Silver validation locally against generated CSV data and produce a quality report.

Reads CSV files as Bronze-equivalent inputs (no Delta required), applies the full
Silver quality framework, verifies mandatory defect counts, and writes a report.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from bronze.schemas import (
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)
from silver.constants import EXPECTED_DEFECT_COUNTS
from silver.metrics import build_check_summary, build_entity_metrics
from silver.quality_engine import apply_all_dimensions, setup_logging
from silver.quality_framework import QualityCheck, QualityContext

logger = logging.getLogger(__name__)

MANDATORY_CHECKS = {
    "customers": {
        "completeness:email_null": {"expected": 50, "label": "NULL emails"},
        "uniqueness:duplicate_customer_id": {"expected": 10, "label": "duplicate customer_id rows", "min_rows": True},
    },
    "orders": {
        "completeness:customer_id_null": {"expected": 100, "label": "NULL customer_id"},
        "completeness:product_id_null": {"expected": 200, "label": "NULL product_id"},
        "referential:invalid_customer_id": {"expected": 50, "label": "invalid customer_id"},
        "referential:invalid_product_id": {"expected": 30, "label": "invalid product_id"},
        "uniqueness:duplicate_order_id": {"expected": 20, "label": "duplicate order_id rows", "min_rows": True},
    },
}


@dataclass(frozen=True)
class CheckReportRow:
    """Single row in the Silver quality report."""

    check_name: str
    table_name: str
    total_rows: int
    passed_rows: int
    failed_rows: int
    pass_percentage: float
    failure_percentage: float
    check_id: str = ""
    issue_code: str = ""
    check_dimension: str = ""
    expected_failures: int | None = None
    status: str = "OK"


@dataclass
class ValidationOutcome:
    """Outcome of a local Silver validation run."""

    run_id: str
    validated_at: str
    entity_metrics: list[CheckReportRow]
    check_metrics: list[CheckReportRow]
    mandatory_results: list[dict]
    unexpected_failures: list[dict]
    all_mandatory_passed: bool


def get_spark_session() -> SparkSession:
    return (
        SparkSession.builder.master("local[1]")
        .appName("silver-local-validation")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )


def read_bronze_csv(spark: SparkSession, data_dir: Path, entity: str) -> DataFrame:
    """Read a CSV file with Bronze schema and synthetic ingest metadata."""
    schemas = {
        "customers": CUSTOMERS_BRONZE_SCHEMA,
        "products": PRODUCTS_BRONZE_SCHEMA,
        "orders": ORDERS_BRONZE_SCHEMA,
    }
    path = str(data_dir / f"{entity}.csv")
    df = (
        spark.read.schema(schemas[entity])
        .option("header", True)
        .option("nullValue", "")
        .csv(path)
    )
    ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return df.withColumn("_ingested_at", F.lit(ingested_at)).withColumn(
        "_source_file", F.lit(path)
    )


def issue_count(df: DataFrame, issue_code: str) -> int:
    return df.filter(F.array_contains(F.col("_quality_issues"), issue_code)).count()


def build_check_report_rows(
    entity: str,
    entity_df: DataFrame,
    checks: list[QualityCheck],
) -> list[CheckReportRow]:
    """Build per-check report rows with pass/fail counts."""
    total = entity_df.count()
    rows: list[CheckReportRow] = []
    for check in checks:
        failed = issue_count(entity_df, check.issue_code)
        passed = total - failed
        fail_pct = round((failed / total * 100.0) if total else 0.0, 2)
        pass_pct = round(100.0 - fail_pct, 2)
        rows.append(
            CheckReportRow(
                check_name=check.check_name,
                table_name=f"silver.{entity}",
                total_rows=total,
                passed_rows=passed,
                failed_rows=failed,
                pass_percentage=pass_pct,
                failure_percentage=fail_pct,
                check_id=check.check_id,
                issue_code=check.issue_code,
                check_dimension=check.dimension,
            )
        )
    return rows


def build_entity_report_row(entity: str, entity_df: DataFrame) -> CheckReportRow:
    """Build entity-level summary row."""
    total = entity_df.count()
    failed = entity_df.filter(~F.col("_is_valid")).count()
    passed = total - failed
    fail_pct = round((failed / total * 100.0) if total else 0.0, 2)
    pass_pct = round(100.0 - fail_pct, 2)
    return CheckReportRow(
        check_name="ENTITY_SUMMARY",
        table_name=f"silver.{entity}",
        total_rows=total,
        passed_rows=passed,
        failed_rows=failed,
        pass_percentage=pass_pct,
        failure_percentage=fail_pct,
        check_dimension="summary",
        status="INFO",
    )


def verify_mandatory_checks(
    entity: str,
    entity_df: DataFrame,
) -> tuple[list[dict], bool]:
    """Verify assignment-mandated defect counts."""
    specs = MANDATORY_CHECKS.get(entity, {})
    results: list[dict] = []
    all_passed = True

    for issue_code, spec in specs.items():
        actual = issue_count(entity_df, issue_code)
        expected = spec["expected"]
        min_rows = spec.get("min_rows", False)
        if min_rows:
            passed = actual >= expected
            comparison = f">= {expected}"
        else:
            passed = actual == expected
            comparison = f"== {expected}"

        if not passed:
            all_passed = False

        results.append(
            {
                "entity": entity,
                "issue_code": issue_code,
                "label": spec["label"],
                "expected": expected,
                "actual": actual,
                "comparison": comparison,
                "passed": passed,
            }
        )

    return results, all_passed


def find_unexpected_failures(
    check_rows: list[CheckReportRow],
    mandatory_issue_codes: set[str],
) -> list[dict]:
    """Return checks with failures that are not part of mandatory assignment defects."""
    unexpected: list[dict] = []
    for row in check_rows:
        if row.failed_rows == 0:
            continue
        if row.issue_code in mandatory_issue_codes:
            continue
        if row.check_name == "ENTITY_SUMMARY":
            continue
        unexpected.append(
            {
                "check_name": row.check_name,
                "table_name": row.table_name,
                "issue_code": row.issue_code,
                "failed_rows": row.failed_rows,
                "failure_percentage": row.failure_percentage,
            }
        )
    return unexpected


def run_local_validation(data_dir: Path, run_id: str | None = None) -> ValidationOutcome:
    """Execute Silver validation on CSV data and return structured results."""
    spark = get_spark_session()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    validated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    customers_bronze = read_bronze_csv(spark, data_dir, "customers")
    products_bronze = read_bronze_csv(spark, data_dir, "products")
    orders_bronze = read_bronze_csv(spark, data_dir, "orders")

    customer_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="customers",
        row_id_column="customer_id",
    )
    silver_customers, _, customer_checks = apply_all_dimensions(customers_bronze, customer_ctx)

    product_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="products",
        row_id_column="product_id",
    )
    silver_products, _, product_checks = apply_all_dimensions(products_bronze, product_ctx)

    order_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="orders",
        row_id_column="order_id",
        valid_customer_ids=silver_customers,
        valid_product_ids=silver_products,
    )
    silver_orders, _, order_checks = apply_all_dimensions(orders_bronze, order_ctx)

    # Row-count parity
    for entity, bronze_df, silver_df in (
        ("customers", customers_bronze, silver_customers),
        ("products", products_bronze, silver_products),
        ("orders", orders_bronze, silver_orders),
    ):
        bronze_count = bronze_df.count()
        silver_count = silver_df.count()
        if bronze_count != silver_count:
            raise RuntimeError(
                f"Row count mismatch for {entity}: bronze={bronze_count} silver={silver_count}"
            )
        logger.info("Row parity OK %s bronze=%d silver=%d", entity, bronze_count, silver_count)

    entity_metrics = [
        build_entity_report_row("customers", silver_customers),
        build_entity_report_row("products", silver_products),
        build_entity_report_row("orders", silver_orders),
    ]

    check_metrics: list[CheckReportRow] = []
    check_metrics.extend(build_check_report_rows("customers", silver_customers, customer_checks))
    check_metrics.extend(build_check_report_rows("products", silver_products, product_checks))
    check_metrics.extend(build_check_report_rows("orders", silver_orders, order_checks))

    mandatory_results: list[dict] = []
    mandatory_passed = True
    for entity, silver_df in (
        ("customers", silver_customers),
        ("orders", silver_orders),
    ):
        results, passed = verify_mandatory_checks(entity, silver_df)
        mandatory_results.extend(results)
        mandatory_passed = mandatory_passed and passed

    mandatory_codes = set(EXPECTED_DEFECT_COUNTS.keys())
    unexpected = find_unexpected_failures(check_metrics, mandatory_codes)

    return ValidationOutcome(
        run_id=run_id,
        validated_at=validated_at.isoformat(),
        entity_metrics=entity_metrics,
        check_metrics=check_metrics,
        mandatory_results=mandatory_results,
        unexpected_failures=unexpected,
        all_mandatory_passed=mandatory_passed,
    )


def render_markdown_report(outcome: ValidationOutcome) -> str:
    """Render validation outcome as a markdown report."""
    lines = [
        "# Silver Quality Validation Report",
        "",
        f"**Run ID:** `{outcome.run_id}`  ",
        f"**Validated at:** {outcome.validated_at}  ",
        f"**Mandatory checks:** {'PASS' if outcome.all_mandatory_passed else 'FAIL'}",
        "",
        "## Entity Summary",
        "",
        "| table_name | total_rows | passed_rows | failed_rows | pass_percentage | failure_percentage |",
        "|------------|------------|-------------|-------------|-----------------|---------------------|",
    ]

    for row in outcome.entity_metrics:
        lines.append(
            f"| {row.table_name} | {row.total_rows:,} | {row.passed_rows:,} | "
            f"{row.failed_rows:,} | {row.pass_percentage:.2f}% | {row.failure_percentage:.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Per-Check Results",
            "",
            "| check_name | table_name | total_rows | passed_rows | failed_rows | "
            "pass_percentage | failure_percentage | issue_code |",
            "|------------|------------|------------|-------------|-------------|"
            "-----------------|---------------------|------------|",
        ]
    )

    for row in sorted(outcome.check_metrics, key=lambda r: (r.table_name, r.check_dimension, r.check_name)):
        lines.append(
            f"| {row.check_name} | {row.table_name} | {row.total_rows:,} | {row.passed_rows:,} | "
            f"{row.failed_rows:,} | {row.pass_percentage:.2f}% | {row.failure_percentage:.2f}% | "
            f"`{row.issue_code}` |"
        )

    lines.extend(["", "## Mandatory Defect Verification", ""])
    lines.append("| entity | check | expected | actual | result |")
    lines.append("|--------|-------|----------|--------|--------|")
    for item in outcome.mandatory_results:
        status = "PASS" if item["passed"] else "**FAIL**"
        lines.append(
            f"| {item['entity']} | {item['label']} (`{item['issue_code']}`) | "
            f"{item['comparison']} | {item['actual']:,} | {status} |"
        )

    lines.extend(["", "## Unexpected Failures (non-assignment)", ""])
    if outcome.unexpected_failures:
        lines.append("| check_name | table_name | issue_code | failed_rows | failure_percentage |")
        lines.append("|------------|------------|------------|-------------|---------------------|")
        for item in outcome.unexpected_failures:
            lines.append(
                f"| {item['check_name']} | {item['table_name']} | `{item['issue_code']}` | "
                f"{item['failed_rows']:,} | {item['failure_percentage']:.2f}% |"
            )
    else:
        lines.append("_No unexpected check failures detected._")

    failing_checks = [r for r in outcome.check_metrics if r.failed_rows > 0]
    lines.extend(["", "## All Failing Checks (full transparency)", ""])
    if failing_checks:
        lines.append("| check_name | table_name | failed_rows | failure_percentage | issue_code |")
        lines.append("|------------|------------|-------------|---------------------|------------|")
        for row in sorted(failing_checks, key=lambda r: -r.failed_rows):
            lines.append(
                f"| {row.check_name} | {row.table_name} | {row.failed_rows:,} | "
                f"{row.failure_percentage:.2f}% | `{row.issue_code}` |"
            )
    else:
        lines.append("_No failing checks._")

    return "\n".join(lines) + "\n"


def write_report(outcome: ValidationOutcome, output_dir: Path) -> tuple[Path, Path]:
    """Write markdown and JSON reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "SILVER_QUALITY_REPORT.md"
    json_path = output_dir / "SILVER_QUALITY_REPORT.json"

    md_path.write_text(render_markdown_report(outcome), encoding="utf-8")
    payload = {
        "run_id": outcome.run_id,
        "validated_at": outcome.validated_at,
        "all_mandatory_passed": outcome.all_mandatory_passed,
        "entity_metrics": [asdict(r) for r in outcome.entity_metrics],
        "check_metrics": [asdict(r) for r in outcome.check_metrics],
        "mandatory_results": outcome.mandatory_results,
        "unexpected_failures": outcome.unexpected_failures,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path, json_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Silver quality validation.")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing customers.csv, products.csv, orders.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Directory for SILVER_QUALITY_REPORT.md/json",
    )
    parser.add_argument("--run-id", default=None, help="Optional deterministic run id")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(argv)

    project_root = Path(__file__).resolve().parents[2]
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    logger.info("Running Silver validation data_dir=%s", data_dir)
    outcome = run_local_validation(data_dir, run_id=args.run_id)
    md_path, json_path = write_report(outcome, output_dir)

    logger.info("Report written: %s", md_path)
    logger.info("JSON written: %s", json_path)

    for item in outcome.mandatory_results:
        status = "PASS" if item["passed"] else "FAIL"
        logger.info(
            "Mandatory %s %s actual=%s expected %s -> %s",
            item["entity"],
            item["issue_code"],
            item["actual"],
            item["comparison"],
            status,
        )

    if outcome.unexpected_failures:
        logger.warning("Unexpected failures detected: %d checks", len(outcome.unexpected_failures))
        for item in outcome.unexpected_failures:
            logger.warning(
                "Unexpected failure %s %s failed_rows=%d",
                item["table_name"],
                item["issue_code"],
                item["failed_rows"],
            )

    return 0 if outcome.all_mandatory_passed else 1


if __name__ == "__main__":
    sys.exit(main())
