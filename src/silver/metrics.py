"""Build and persist Silver data quality metrics."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

from silver.quality_framework import CHECK_STATUS_FAIL, QualityCheck

logger = logging.getLogger(__name__)

SUMMARY_SCHEMA = StructType(
    [
        StructField("run_id", StringType(), nullable=False),
        StructField("entity", StringType(), nullable=False),
        StructField("check_dimension", StringType(), nullable=False),
        StructField("check_id", StringType(), nullable=False),
        StructField("issue_code", StringType(), nullable=False),
        StructField("issue_count", IntegerType(), nullable=False),
        StructField("issue_rate_pct", DoubleType(), nullable=False),
        StructField("check_pass_rate_pct", DoubleType(), nullable=False),
        StructField("total_records", IntegerType(), nullable=False),
        StructField("valid_records", IntegerType(), nullable=False),
        StructField("invalid_records", IntegerType(), nullable=False),
        StructField("pass_rate_pct", DoubleType(), nullable=False),
        StructField("fail_rate_pct", DoubleType(), nullable=False),
        StructField("reported_at", TimestampType(), nullable=False),
    ]
)

METRICS_SCHEMA = StructType(
    [
        StructField("run_id", StringType(), nullable=False),
        StructField("entity", StringType(), nullable=False),
        StructField("total_rows", IntegerType(), nullable=False),
        StructField("passed_rows", IntegerType(), nullable=False),
        StructField("failed_rows", IntegerType(), nullable=False),
        StructField("pass_percentage", DoubleType(), nullable=False),
        StructField("fail_percentage", DoubleType(), nullable=False),
        StructField("reported_at", TimestampType(), nullable=False),
    ]
)


def _spark_timestamp(value: datetime) -> datetime:
    """Return a Spark-safe naive UTC timestamp."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def build_entity_metrics(
    entity_df: DataFrame,
    entity: str,
    run_id: str,
    reported_at: datetime,
) -> DataFrame:
    """Build entity-level pass/fail metrics."""
    total = entity_df.count()
    failed = entity_df.filter(~F.col("_is_valid")).count()
    passed = total - failed
    pass_pct = (passed / total * 100.0) if total else 100.0
    fail_pct = (failed / total * 100.0) if total else 0.0
    reported_at_value = _spark_timestamp(reported_at)

    spark = entity_df.sparkSession
    return spark.createDataFrame(
        [
            (
                run_id,
                entity,
                total,
                passed,
                failed,
                round(pass_pct, 2),
                round(fail_pct, 2),
                reported_at_value,
            )
        ],
        METRICS_SCHEMA,
    )


def build_check_summary(
    entity_df: DataFrame,
    entity: str,
    checks: list[QualityCheck],
    run_id: str,
    reported_at: datetime,
) -> DataFrame:
    """Build per-check failure counts and rates."""
    total = entity_df.count()
    valid = entity_df.filter(F.col("_is_valid")).count()
    invalid = total - valid
    pass_rate = (valid / total * 100.0) if total else 100.0
    fail_rate = (invalid / total * 100.0) if total else 0.0

    reported_at_value = _spark_timestamp(reported_at)

    rows: list[tuple] = []
    for check in checks:
        issue_count = entity_df.filter(
            F.array_contains(F.col("_quality_issues"), check.issue_code)
        ).count()
        issue_rate = (issue_count / total * 100.0) if total else 0.0
        check_pass_rate = 100.0 - issue_rate
        rows.append(
            (
                run_id,
                entity,
                check.dimension,
                check.check_id,
                check.issue_code,
                issue_count,
                round(issue_rate, 2),
                round(check_pass_rate, 2),
                total,
                valid,
                invalid,
                round(pass_rate, 2),
                round(fail_rate, 2),
                reported_at_value,
            )
        )

    return entity_df.sparkSession.createDataFrame(rows, SUMMARY_SCHEMA)


def build_failures_by_table(metrics_dfs: list[DataFrame]) -> DataFrame:
    """Union entity metrics into a failures-by-table view."""
    if not metrics_dfs:
        raise ValueError("At least one entity metrics DataFrame is required")
    combined = metrics_dfs[0]
    for frame in metrics_dfs[1:]:
        combined = combined.unionByName(frame)
    return combined


def log_metrics_summary(metrics_df: DataFrame) -> None:
    """Log entity metrics to the pipeline logger."""
    for row in metrics_df.collect():
        logger.info(
            "DQ metrics entity=%s total=%d passed=%d failed=%d pass_pct=%.2f fail_pct=%.2f",
            row.entity,
            row.total_rows,
            row.passed_rows,
            row.failed_rows,
            row.pass_percentage,
            row.fail_percentage,
        )


def log_failures_by_check(summary_df: DataFrame) -> None:
    """Log per-check failure counts."""
    failures = summary_df.filter(F.col("issue_count") > 0).collect()
    for row in failures:
        logger.info(
            "DQ check failure entity=%s check=%s issue_code=%s count=%d rate=%.2f%%",
            row.entity,
            row.check_id,
            row.issue_code,
            row.issue_count,
            row.issue_rate_pct,
        )
