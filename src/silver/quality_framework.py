"""Reusable quality-check specifications and Spark helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

CHECK_STATUS_PASS = "PASS"
CHECK_STATUS_FAIL = "FAIL"
QUALITY_RESULT_PASS = "PASS"
QUALITY_RESULT_FAIL = "FAIL"


@dataclass(frozen=True)
class QualityCheck:
    """Declarative specification for a single data quality rule."""

    check_id: str
    check_name: str
    dimension: str
    issue_code: str
    failure_reason: str
    fail_condition: Column
    applies_when: Column | None = None


@dataclass
class QualityContext:
    """Shared context passed to dimension-specific check builders."""

    run_id: str
    validated_at: datetime
    entity: str
    row_id_column: str
    valid_customer_ids: DataFrame | None = None
    valid_product_ids: DataFrame | None = None


QualityModule = tuple[
    str,
    Callable[[DataFrame, QualityContext], DataFrame],
    Callable[[QualityContext], list[QualityCheck]],
]


def is_null_or_blank(column: Column) -> Column:
    """True when column is NULL or blank after trim."""
    return column.isNull() | (F.trim(column) == "")


def row_identifier_expr(row_id_column: str) -> Column:
    """Build a string row identifier from the primary key column."""
    return F.coalesce(F.col(row_id_column).cast(StringType()), F.lit("NULL"))


QUALITY_RESULT_SCHEMA = StructType(
    [
        StructField("run_id", StringType(), nullable=False),
        StructField("entity", StringType(), nullable=False),
        StructField("row_identifier", StringType(), nullable=False),
        StructField("check_id", StringType(), nullable=False),
        StructField("check_name", StringType(), nullable=False),
        StructField("check_dimension", StringType(), nullable=False),
        StructField("check_status", StringType(), nullable=False),
        StructField("quality_result", StringType(), nullable=False),
        StructField("failure_reason", StringType(), nullable=True),
        StructField("validated_at", TimestampType(), nullable=False),
    ]
)


def effective_fail_condition(check: QualityCheck) -> Column:
    """Return fail condition optionally gated by applies_when."""
    if check.applies_when is None:
        return check.fail_condition
    return check.applies_when & check.fail_condition


def spark_timestamp_literal(value: datetime):
    """Return a Spark-safe timestamp literal."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return F.lit(value).cast(TimestampType())


def apply_checks_to_dataframe(
    df: DataFrame,
    checks: list[QualityCheck],
    ctx: QualityContext,
) -> tuple[DataFrame, DataFrame]:
    """Apply checks; return entity DataFrame with _quality_issues and failure detail rows."""
    if not checks:
        spark = df.sparkSession
        return (
            df.withColumn("_quality_issues", F.array().cast("array<string>")),
            _empty_quality_results(spark, ctx),
        )

    issue_columns: list[Column] = []
    for index, check in enumerate(checks):
        col_name = f"_issue_{index}"
        issue_columns.append(col_name)
        df = df.withColumn(
            col_name,
            F.when(effective_fail_condition(check), F.lit(check.issue_code)),
        )

    df = df.withColumn(
        "_quality_issues",
        F.array_compact(F.array(*[F.col(name) for name in issue_columns])),
    )

    # Build failure detail records (one row per failed check per source row).
    validated_at_lit = spark_timestamp_literal(ctx.validated_at)
    row_id_expr = row_identifier_expr(ctx.row_id_column)

    failure_frames: list[DataFrame] = []
    for check in checks:
        fail_mask = effective_fail_condition(check)
        failures = (
            df.filter(fail_mask)
            .select(
                F.lit(ctx.run_id).alias("run_id"),
                F.lit(ctx.entity).alias("entity"),
                row_id_expr.alias("row_identifier"),
                F.lit(check.check_id).alias("check_id"),
                F.lit(check.check_name).alias("check_name"),
                F.lit(check.dimension).alias("check_dimension"),
                F.lit(CHECK_STATUS_FAIL).alias("check_status"),
                F.lit(QUALITY_RESULT_FAIL).alias("quality_result"),
                F.lit(check.failure_reason).alias("failure_reason"),
                validated_at_lit.alias("validated_at"),
            )
        )
        failure_frames.append(failures)

    detail_df = failure_frames[0]
    for frame in failure_frames[1:]:
        detail_df = detail_df.unionByName(frame)

    df = df.drop(*issue_columns)
    return df, detail_df


def finalize_silver_entity(
    df: DataFrame,
    ctx: QualityContext,
) -> DataFrame:
    """Add final Silver quality metadata columns."""
    return (
        df.withColumn(
            "_is_valid",
            F.when(F.size(F.col("_quality_issues")) == 0, F.lit(True)).otherwise(F.lit(False)),
        )
        .withColumn(
            "_quality_status",
            F.when(F.col("_is_valid"), F.lit("VALID")).otherwise(F.lit("INVALID")),
        )
        .withColumn("_validated_at", spark_timestamp_literal(ctx.validated_at))
        .withColumn("_run_id", F.lit(ctx.run_id))
    )


def _empty_quality_results(spark: SparkSession, ctx: QualityContext) -> DataFrame:
    return spark.createDataFrame([], QUALITY_RESULT_SCHEMA)
