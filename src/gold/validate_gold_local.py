"""Run Gold layer locally from CSV-derived Silver temp views and produce a validation report."""

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
from gold.config import GoldConfig
from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD
from gold.gold_engine import (
    all_validations_passed,
    run_gold_pipeline,
    run_gold_validations,
    setup_logging,
)
from gold.validations import ValidationResult
from silver.quality_engine import apply_all_dimensions
from silver.quality_framework import QualityContext

logger = logging.getLogger(__name__)


@dataclass
class GoldValidationOutcome:
    run_id: str
    validated_at: str
    gold_table_counts: dict[str, int]
    silver_valid_counts: dict[str, int]
    validation_results: list[ValidationResult]
    invalid_orders_excluded: int
    summary_rows: list[dict]
    all_passed: bool


def get_spark_session() -> SparkSession:
    return (
        SparkSession.builder.master("local[1]")
        .appName("gold-local-validation")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.driver.host", "127.0.0.1")
        .getOrCreate()
    )


def read_bronze_csv(spark: SparkSession, data_dir: Path, entity: str) -> DataFrame:
    schemas = {
        "customers": CUSTOMERS_BRONZE_SCHEMA,
        "products": PRODUCTS_BRONZE_SCHEMA,
        "orders": ORDERS_BRONZE_SCHEMA,
    }
    path = str(data_dir / f"{entity}.csv")
    return (
        spark.read.schema(schemas[entity])
        .option("header", True)
        .option("nullValue", "")
        .csv(path)
    )


def build_silver_tables(
    spark: SparkSession,
    data_dir: Path,
    run_id: str,
    validated_at: datetime,
) -> tuple[DataFrame, DataFrame, DataFrame]:
    customers = read_bronze_csv(spark, data_dir, "customers")
    products = read_bronze_csv(spark, data_dir, "products")
    orders = read_bronze_csv(spark, data_dir, "orders")

    customer_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="customers",
        row_id_column="customer_id",
    )
    silver_customers, _, _ = apply_all_dimensions(customers, customer_ctx)

    product_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="products",
        row_id_column="product_id",
    )
    silver_products, _, _ = apply_all_dimensions(products, product_ctx)

    order_ctx = QualityContext(
        run_id=run_id,
        validated_at=validated_at,
        entity="orders",
        row_id_column="order_id",
        valid_customer_ids=silver_customers,
        valid_product_ids=silver_products,
    )
    silver_orders, _, _ = apply_all_dimensions(orders, order_ctx)

    return silver_customers, silver_products, silver_orders


def register_silver_views(
    spark: SparkSession,
    customers: DataFrame,
    products: DataFrame,
    orders: DataFrame,
) -> None:
    customers.createOrReplaceTempView("silver_customers")
    products.createOrReplaceTempView("silver_products")
    orders.createOrReplaceTempView("silver_orders")


def _gold_summary_rows(spark: SparkSession, config: GoldConfig) -> list[dict]:
    """Collect summary metrics from each Gold table for the report."""
    rows: list[dict] = []

    sales = spark.table(config.gold_table("sales_by_product"))
    sales_agg = sales.agg(
        F.count("*").alias("total_rows"),
        F.sum("total_orders").alias("total_orders"),
        F.sum("total_revenue").alias("total_revenue"),
    ).collect()[0]
    rows.append(
        {
            "check_name": "sales_by_product_summary",
            "table_name": "gold.sales_by_product",
            "total_rows": sales_agg.total_rows,
            "passed_rows": sales_agg.total_rows,
            "failed_rows": 0,
            "pass_percentage": 100.0,
            "failure_percentage": 0.0,
            "detail": f"orders={sales_agg.total_orders}, revenue={sales_agg.total_revenue}",
        }
    )

    customers = spark.table(config.gold_table("revenue_by_customer"))
    cust_agg = customers.agg(
        F.count("*").alias("total_rows"),
        F.sum("total_orders").alias("total_orders"),
        F.sum("total_revenue").alias("total_revenue"),
        F.sum(F.when(F.col("total_orders") > 0, 1).otherwise(0)).alias("customers_with_orders"),
    ).collect()[0]
    rows.append(
        {
            "check_name": "revenue_by_customer_summary",
            "table_name": "gold.revenue_by_customer",
            "total_rows": cust_agg.total_rows,
            "passed_rows": cust_agg.customers_with_orders,
            "failed_rows": cust_agg.total_rows - cust_agg.customers_with_orders,
            "pass_percentage": round(
                (cust_agg.customers_with_orders / cust_agg.total_rows * 100) if cust_agg.total_rows else 100, 2
            ),
            "failure_percentage": round(
                ((cust_agg.total_rows - cust_agg.customers_with_orders) / cust_agg.total_rows * 100)
                if cust_agg.total_rows
                else 0,
                2,
            ),
            "detail": f"orders={cust_agg.total_orders}, revenue={cust_agg.total_revenue}",
        }
    )

    trends = spark.table(config.gold_table("daily_weekly_trends"))
    for grain in ("DAILY", "WEEKLY"):
        grain_df = trends.filter(F.col("trend_grain") == grain)
        agg = grain_df.agg(
            F.count("*").alias("total_rows"),
            F.sum("total_orders").alias("total_orders"),
            F.sum("total_revenue").alias("total_revenue"),
        ).collect()[0]
        rows.append(
            {
                "check_name": f"daily_weekly_trends_{grain.lower()}_summary",
                "table_name": "gold.daily_weekly_trends",
                "total_rows": agg.total_rows,
                "passed_rows": agg.total_rows,
                "failed_rows": 0,
                "pass_percentage": 100.0,
                "failure_percentage": 0.0,
                "detail": f"grain={grain}, orders={agg.total_orders}, revenue={agg.total_revenue}",
            }
        )

    segments = spark.table(config.gold_table("customer_segmentation"))
    for seg in segments.collect():
        rows.append(
            {
                "check_name": f"segment_{seg.segment_type.lower().replace('-', '_')}",
                "table_name": "gold.customer_segmentation",
                "total_rows": seg.customer_count,
                "passed_rows": seg.customer_count,
                "failed_rows": 0,
                "pass_percentage": 100.0,
                "failure_percentage": 0.0,
                "detail": f"avg_revenue={seg.avg_revenue}, total_revenue={seg.total_revenue}",
            }
        )

    return rows


def render_report(outcome: GoldValidationOutcome, summary_rows: list[dict]) -> str:
    lines = [
        "# Gold Layer Validation Report",
        "",
        f"**Run ID:** `{outcome.run_id}`  ",
        f"**Validated at:** {outcome.validated_at}  ",
        f"**Overall status:** {'PASS' if outcome.all_passed else 'FAIL'}",
        "",
        "## Assumptions",
        "",
        "- Only Silver rows with `_is_valid = TRUE` are used in Gold aggregations.",
        "- Invalid rows (NULL FKs, duplicate PKs, referential failures, etc.) are excluded.",
        "- `COUNT(DISTINCT order_id)` prevents duplicate-key double counting if any invalid rows slipped through.",
        f"- High-Value segment threshold: `${HIGH_VALUE_REVENUE_THRESHOLD:,.2f}` lifetime actual revenue.",
        "- Segmentation is mutually exclusive with priority: Inactive → High-Value → Repeat → One-Time.",
        "- **Note:** `Inactive` may have zero customers when every valid customer has at least one valid order.",
        "",
        "## Silver Input Summary",
        "",
        "| entity | valid_rows | invalid_rows_excluded |",
        "|--------|------------|------------------------|",
    ]
    for entity, valid in outcome.silver_valid_counts.items():
        lines.append(f"| silver.{entity} | {valid:,} | excluded from Gold |")
    lines.append("")
    lines.append(f"**Invalid orders excluded from Gold:** {outcome.invalid_orders_excluded:,}")
    lines.append("")
    lines.append("## Gold Table Row Counts")
    lines.append("")
    lines.append("| table_name | row_count |")
    lines.append("|------------|-----------|")
    for table, count in outcome.gold_table_counts.items():
        lines.append(f"| {table} | {count:,} |")

    lines.extend(["", "## Gold Metrics Summary", ""])
    lines.append(
        "| check_name | table_name | total_rows | passed_rows | failed_rows | "
        "pass_percentage | failure_percentage | detail |"
    )
    lines.append(
        "|------------|------------|------------|-------------|-------------|"
        "-----------------|---------------------|--------|"
    )
    for row in summary_rows:
        lines.append(
            f"| {row['check_name']} | {row['table_name']} | {row['total_rows']:,} | "
            f"{row['passed_rows']:,} | {row['failed_rows']:,} | {row['pass_percentage']:.2f}% | "
            f"{row['failure_percentage']:.2f}% | {row['detail']} |"
        )

    lines.extend(["", "## Validation Queries", ""])
    lines.append("| table | validation | result | detail |")
    lines.append("|-------|------------|--------|--------|")
    for result in outcome.validation_results:
        status = "PASS" if result.passed else "**FAIL**"
        lines.append(
            f"| {result.table_name} | {result.validation_name} | {status} | {result.detail} |"
        )
    return "\n".join(lines) + "\n"


def run_local_gold_validation(data_dir: Path, run_id: str | None = None) -> GoldValidationOutcome:
    spark = get_spark_session()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    validated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    silver_customers, silver_products, silver_orders = build_silver_tables(
        spark, data_dir, run_id, validated_at
    )
    register_silver_views(spark, silver_customers, silver_products, silver_orders)

    config = GoldConfig(local_mode=True)
    run_gold_pipeline(config, spark=spark)

    validation_results = run_gold_validations(spark, config)
    summary_rows = _gold_summary_rows(spark, config)

    gold_counts = {
        config.gold_table(name): spark.table(config.gold_table(name)).count()
        for _, name in [
            ("01", "sales_by_product"),
            ("02", "revenue_by_customer"),
            ("03", "daily_weekly_trends"),
            ("04", "customer_segmentation"),
        ]
    }

    silver_valid = {
        "customers": silver_customers.filter(F.col("_is_valid")).count(),
        "products": silver_products.filter(F.col("_is_valid")).count(),
        "orders": silver_orders.filter(F.col("_is_valid")).count(),
    }
    invalid_orders = silver_orders.filter(~F.col("_is_valid")).count()

    return GoldValidationOutcome(
        run_id=run_id,
        validated_at=validated_at.isoformat(),
        gold_table_counts=gold_counts,
        silver_valid_counts=silver_valid,
        validation_results=validation_results,
        invalid_orders_excluded=invalid_orders,
        summary_rows=summary_rows,
        all_passed=all_validations_passed(validation_results),
    )


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Validate Gold layer locally from CSV data.")
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

    outcome = run_local_gold_validation(data_dir, run_id=args.run_id)
    md_path = output_dir / "GOLD_VALIDATION_REPORT.md"
    json_path = output_dir / "GOLD_VALIDATION_REPORT.json"
    md_path.write_text(render_report(outcome, outcome.summary_rows), encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "run_id": outcome.run_id,
                "validated_at": outcome.validated_at,
                "all_passed": outcome.all_passed,
                "gold_table_counts": outcome.gold_table_counts,
                "silver_valid_counts": outcome.silver_valid_counts,
                "invalid_orders_excluded": outcome.invalid_orders_excluded,
                "summary_rows": outcome.summary_rows,
                "validation_results": [asdict(r) for r in outcome.validation_results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Gold validation report: %s", md_path)
    return 0 if outcome.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
