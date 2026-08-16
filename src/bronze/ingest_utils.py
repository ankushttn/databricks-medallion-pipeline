"""Shared utilities for Bronze CSV ingestion into Delta tables."""

from __future__ import annotations

import csv
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit
from pyspark.sql.utils import AnalysisException

from bronze.config import BronzeConfig, EntityIngestSpec

logger = logging.getLogger(__name__)


class BronzeIngestionError(Exception):
    """Raised when Bronze ingestion fails."""


class BronzeSourceFileError(BronzeIngestionError):
    """Raised when a source CSV file is missing or unreadable."""


@dataclass(frozen=True)
class IngestResult:
    """Outcome of a single Bronze entity ingestion."""

    entity_name: str
    source_path: str
    target_table: str
    rows_read: int
    rows_written: int
    status: str
    ingested_at: datetime
    message: str = ""


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for Bronze scripts."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def configure_src_path() -> None:
    """Ensure `src/` is on sys.path for package imports in script execution."""
    src_dir = Path(__file__).resolve().parents[1]
    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


def get_spark_session(app_name: str) -> SparkSession:
    """Return the active Spark session or create one with Delta support."""
    active = SparkSession.getActiveSession()
    if active is not None:
        return active

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )
    return builder.getOrCreate()


def _local_path_for_check(source_path: str) -> Path | None:
    """Return a local Path for existence checks when possible."""
    if source_path.startswith("dbfs:"):
        return Path(source_path.replace("dbfs:", "/dbfs", 1))
    if source_path.startswith("file://"):
        return Path(source_path.replace("file://", "", 1))
    if source_path.startswith("/dbfs"):
        return Path(source_path)
    return Path(source_path)


def verify_source_file_exists(source_path: str) -> None:
    """Raise BronzeSourceFileError if the source file cannot be found locally."""
    local_path = _local_path_for_check(source_path)
    if local_path is None:
        return
    if not local_path.is_file():
        raise BronzeSourceFileError(f"Source CSV not found: {source_path}")


def count_csv_data_rows(source_path: str) -> int:
    """Count CSV data rows (excluding header) for logging and validation."""
    local_path = _local_path_for_check(source_path)
    if local_path is None or not local_path.is_file():
        return -1

    with local_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)  # header
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def validate_csv_header(source_path: str, expected_columns: Sequence[str]) -> None:
    """Validate CSV header columns match the expected Bronze business schema."""
    local_path = _local_path_for_check(source_path)
    if local_path is None or not local_path.is_file():
        return

    with local_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise BronzeSourceFileError(
                f"Source CSV is empty (no header): {source_path}"
            ) from exc

    if header != list(expected_columns):
        raise BronzeIngestionError(
            f"CSV header mismatch for {source_path}. "
            f"Expected {list(expected_columns)}, got {header}"
        )


def read_bronze_csv(spark: SparkSession, source_path: str, spec: EntityIngestSpec) -> DataFrame:
    """Read a CSV file using an explicit schema without business transformations."""
    try:
        return (
            spark.read.format("csv")
            .option("header", "true")
            .option("nullValue", "")
            .option("mode", "FAILFAST")
            .option("dateFormat", "yyyy-MM-dd")
            .schema(spec.schema)
            .load(source_path)
        )
    except AnalysisException as exc:
        logger.error("Failed to read CSV: %s", source_path, exc_info=True)
        raise BronzeIngestionError(
            f"Malformed input or read failure for {source_path}: {exc}"
        ) from exc


def add_ingestion_metadata(df: DataFrame, source_path: str) -> DataFrame:
    """Append Bronze ingestion metadata columns without modifying business fields."""
    return (
        df.withColumn("_ingested_at", current_timestamp())
        .withColumn("_source_file", lit(source_path))
    )


def write_bronze_delta(
    df: DataFrame,
    target_table: str,
    write_mode: str,
    partition_columns: Sequence[str],
) -> None:
    """Write a DataFrame to a Bronze Delta table."""
    writer = df.write.format("delta").mode(write_mode).option("overwriteSchema", "true")
    if partition_columns:
        writer = writer.partitionBy(*partition_columns)
    try:
        writer.saveAsTable(target_table)
    except AnalysisException as exc:
        logger.error("Failed to write Delta table: %s", target_table, exc_info=True)
        raise BronzeIngestionError(
            f"Failed to write Bronze table {target_table}: {exc}"
        ) from exc


def ensure_bronze_schema_exists(spark: SparkSession, config: BronzeConfig) -> None:
    """Create the Bronze schema if it does not exist."""
    qualified_schema = (
        f"{config.catalog}.{config.bronze_schema}"
        if config.catalog
        else config.bronze_schema
    )
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {qualified_schema}")


def ingest_entity(
    spark: SparkSession,
    config: BronzeConfig,
    spec: EntityIngestSpec,
) -> IngestResult:
    """Ingest one CSV source into a Bronze Delta table."""
    source_path = config.source_path(spec.source_filename)
    target_table = config.qualified_table_name(spec.table_name)
    started_at = datetime.now(timezone.utc)

    logger.info(
        "Starting Bronze ingestion entity=%s source=%s target=%s",
        spec.entity_name,
        source_path,
        target_table,
    )

    try:
        verify_source_file_exists(source_path)
        validate_csv_header(source_path, [field.name for field in spec.schema.fields])
        expected_csv_rows = count_csv_data_rows(source_path)

        df = read_bronze_csv(spark, source_path, spec)
        rows_read = df.count()

        if expected_csv_rows >= 0 and rows_read != expected_csv_rows:
            raise BronzeIngestionError(
                f"Row count mismatch for {spec.entity_name}: "
                f"CSV has {expected_csv_rows} rows, Spark read {rows_read}"
            )

        df = add_ingestion_metadata(df, source_path)
        ensure_bronze_schema_exists(spark, config)
        write_bronze_delta(
            df,
            target_table=target_table,
            write_mode=config.write_mode,
            partition_columns=spec.partition_columns,
        )

        rows_written = rows_read
        result = IngestResult(
            entity_name=spec.entity_name,
            source_path=source_path,
            target_table=target_table,
            rows_read=rows_read,
            rows_written=rows_written,
            status="SUCCESS",
            ingested_at=started_at,
        )
        logger.info(
            "Bronze ingestion SUCCESS entity=%s source=%s target=%s rows_read=%d rows_written=%d",
            spec.entity_name,
            source_path,
            target_table,
            rows_read,
            rows_written,
        )
        return result

    except (BronzeSourceFileError, BronzeIngestionError) as exc:
        logger.error(
            "Bronze ingestion FAILED entity=%s source=%s target=%s error=%s",
            spec.entity_name,
            source_path,
            target_table,
            exc,
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.error(
            "Bronze ingestion FAILED entity=%s source=%s target=%s error=%s",
            spec.entity_name,
            source_path,
            target_table,
            exc,
            exc_info=True,
        )
        raise BronzeIngestionError(
            f"Unexpected failure ingesting {spec.entity_name}: {exc}"
        ) from exc


def run_ingestion(
    spec: EntityIngestSpec,
    argv: Sequence[str] | None = None,
    *,
    app_name: str | None = None,
) -> int:
    """CLI entry point for a single-entity Bronze ingestion script."""
    import argparse

    from bronze.config import add_bronze_config_args, config_from_args

    configure_src_path()
    setup_logging()

    parser = argparse.ArgumentParser(
        description=f"Bronze ingestion: {spec.entity_name}",
    )
    add_bronze_config_args(parser)
    args = parser.parse_args(argv)
    config = config_from_args(args)

    try:
        spark = get_spark_session(app_name or f"bronze_ingest_{spec.entity_name}")
        ingest_entity(spark, config, spec)
        return 0
    except BronzeIngestionError:
        return 1


def run_ingest_all(argv: Sequence[str] | None = None) -> int:
    """CLI entry point to ingest all Bronze entities."""
    import argparse

    from bronze.config import ALL_ENTITY_SPECS, add_bronze_config_args, config_from_args

    configure_src_path()
    setup_logging()

    parser = argparse.ArgumentParser(description="Bronze ingestion: all entities")
    add_bronze_config_args(parser)
    args = parser.parse_args(argv)
    config = config_from_args(args)

    spark = get_spark_session("bronze_ingest_all")
    failures: list[str] = []

    for spec in ALL_ENTITY_SPECS:
        try:
            ingest_entity(spark, config, spec)
        except BronzeIngestionError as exc:
            failures.append(f"{spec.entity_name}: {exc}")

    if failures:
        for message in failures:
            logger.error("Bronze ingest_all failure: %s", message)
        return 1

    logger.info("Bronze ingest_all completed successfully for all entities")
    return 0
