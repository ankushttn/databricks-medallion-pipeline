"""Silver quality engine — orchestrates dimension checks and writes outputs."""

from __future__ import annotations

import importlib
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.utils import AnalysisException

from silver.config import SilverConfig
from silver.constants import ENTITY_PARTITION_COLUMNS, ENTITY_PRIMARY_KEYS
from silver.metrics import (
    build_check_summary,
    build_entity_metrics,
    build_failures_by_table,
    log_failures_by_check,
    log_metrics_summary,
)
from silver.quality_framework import (
    QualityCheck,
    QualityContext,
    apply_checks_to_dataframe,
    finalize_silver_entity,
)

logger = logging.getLogger(__name__)

DIMENSION_MODULE_NAMES = (
    "01_quality_completeness",
    "02_quality_uniqueness",
    "03_quality_type_validation",
    "04_quality_referential_integrity",
    "05_quality_business_logic",
)

PREPARE_COLUMNS = ("_pk_dup_count", "_customer_ref_exists", "_product_ref_exists")


class SilverValidationError(Exception):
    """Raised when Silver validation fails."""


def configure_src_path() -> None:
    """Ensure `src/` is on sys.path for package imports."""
    src_dir = Path(__file__).resolve().parents[1]
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_spark_session(app_name: str) -> SparkSession:
    from bronze.ingest_utils import get_spark_session as bronze_get_spark

    return bronze_get_spark(app_name)


def generate_run_id(config: SilverConfig) -> str:
    """Return configured or time-based run identifier."""
    if config.run_id:
        return config.run_id
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_dimension_modules() -> list:
    """Import all Silver quality dimension modules in execution order."""
    return [importlib.import_module(f"silver.{name}") for name in DIMENSION_MODULE_NAMES]


def read_bronze_table(spark: SparkSession, table_name: str) -> DataFrame:
    """Read a Bronze Delta table."""
    try:
        return spark.table(table_name)
    except AnalysisException as exc:
        logger.error("Failed to read Bronze table %s", table_name, exc_info=True)
        raise SilverValidationError(f"Bronze table not found or unreadable: {table_name}") from exc


def ensure_silver_schema_exists(spark: SparkSession, config: SilverConfig) -> None:
    """Create Silver schema if missing."""
    qualified = (
        f"{config.catalog}.{config.silver_schema}"
        if config.catalog
        else config.silver_schema
    )
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {qualified}")


def write_silver_table(
    df: DataFrame,
    table_name: str,
    write_mode: str,
    partition_columns: tuple[str, ...],
) -> None:
    """Write entity DataFrame to Silver Delta table."""
    writer = df.write.format("delta").mode(write_mode).option("overwriteSchema", "true")
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    try:
        writer.saveAsTable(table_name)
    except AnalysisException as exc:
        logger.error("Failed to write Silver table %s", table_name, exc_info=True)
        raise SilverValidationError(f"Failed to write Silver table {table_name}: {exc}") from exc


def validate_row_count_parity(bronze_df: DataFrame, silver_df: DataFrame, entity: str) -> None:
    """Ensure Silver retains every Bronze row."""
    bronze_count = bronze_df.count()
    silver_count = silver_df.count()
    if bronze_count != silver_count:
        raise SilverValidationError(
            f"Row count mismatch for {entity}: bronze={bronze_count} silver={silver_count}"
        )
    logger.info(
        "Row count parity OK entity=%s bronze=%d silver=%d",
        entity,
        bronze_count,
        silver_count,
    )


def drop_prepare_columns(df: DataFrame) -> DataFrame:
    """Remove temporary columns added by dimension prepare hooks."""
    existing = [column for column in PREPARE_COLUMNS if column in df.columns]
    return df.drop(*existing) if existing else df


def apply_all_dimensions(
    df: DataFrame,
    ctx: QualityContext,
) -> tuple[DataFrame, DataFrame, list[QualityCheck]]:
    """Run prepare hooks, apply all checks once, finalize Silver metadata."""
    modules = load_dimension_modules()
    working = df
    for module in modules:
        working = module.prepare(working, ctx)

    checks: list[QualityCheck] = []
    for module in modules:
        checks.extend(module.get_checks(ctx))

    working, detail_df = apply_checks_to_dataframe(working, checks, ctx)
    working = drop_prepare_columns(working)
    working = finalize_silver_entity(working, ctx)
    return working, detail_df, checks


def process_entity(
    spark: SparkSession,
    config: SilverConfig,
    entity: str,
    ctx: QualityContext,
) -> tuple[DataFrame, DataFrame, DataFrame, DataFrame, list[QualityCheck]]:
    """Read Bronze, validate, and return Silver entity + metrics inputs."""
    bronze_table = config.bronze_table(entity)
    silver_table = config.silver_table(entity)

    logger.info("Processing Silver entity=%s bronze=%s silver=%s", entity, bronze_table, silver_table)
    bronze_df = read_bronze_table(spark, bronze_table)

    silver_df, detail_df, checks = apply_all_dimensions(bronze_df, ctx)
    validate_row_count_parity(bronze_df, silver_df, entity)

    write_silver_table(
        silver_df,
        silver_table,
        config.write_mode,
        ENTITY_PARTITION_COLUMNS[entity],
    )

    metrics_df = build_entity_metrics(silver_df, entity, ctx.run_id, ctx.validated_at)
    summary_df = build_check_summary(silver_df, entity, checks, ctx.run_id, ctx.validated_at)
    return silver_df, detail_df, metrics_df, summary_df, checks


def run_silver_pipeline(config: SilverConfig) -> int:
    """Execute full Silver validation pipeline."""
    spark = get_spark_session("silver_create_tables")
    ensure_silver_schema_exists(spark, config)

    run_id = generate_run_id(config)
    validated_at = datetime.now(timezone.utc)
    logger.info("Starting Silver pipeline run_id=%s", run_id)

    all_details: list[DataFrame] = []
    all_metrics: list[DataFrame] = []
    all_summaries: list[DataFrame] = []

    silver_customers: DataFrame | None = None
    silver_products: DataFrame | None = None

    for entity in ("customers", "products", "orders"):
        pk = ENTITY_PRIMARY_KEYS[entity]
        ctx = QualityContext(
            run_id=run_id,
            validated_at=validated_at,
            entity=entity,
            row_id_column=pk,
            valid_customer_ids=silver_customers,
            valid_product_ids=silver_products,
        )
        silver_df, detail_df, metrics_df, summary_df, checks = process_entity(
            spark, config, entity, ctx
        )

        if entity == "customers":
            silver_customers = silver_df
        elif entity == "products":
            silver_products = silver_df

        if detail_df.head(1):
            all_details.append(detail_df)
        all_metrics.append(metrics_df)
        all_summaries.append(summary_df)

    metrics_combined = build_failures_by_table(all_metrics)
    log_metrics_summary(metrics_combined)

    summary_combined = all_summaries[0]
    for frame in all_summaries[1:]:
        summary_combined = summary_combined.unionByName(frame)
    log_failures_by_check(summary_combined)

    write_silver_table(
        metrics_combined,
        config.silver_table("data_quality_metrics"),
        config.write_mode,
        (),
    )
    write_silver_table(
        summary_combined,
        config.silver_table("data_quality_summary"),
        config.write_mode,
        (),
    )

    if all_details:
        detail_combined = all_details[0]
        for frame in all_details[1:]:
            detail_combined = detail_combined.unionByName(frame)
        write_silver_table(
            detail_combined,
            config.silver_table("data_quality_results"),
            config.write_mode,
            (),
        )

    logger.info("Silver pipeline completed successfully run_id=%s", run_id)
    return 0
