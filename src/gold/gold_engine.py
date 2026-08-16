"""Gold layer engine — SQL rendering, execution, and validation."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.utils import AnalysisException

from gold.config import GoldConfig
from gold.constants import GOLD_TABLE_SCRIPTS, SEGMENT_TYPES
from gold.validations import VALIDATIONS, ValidationResult
from common.pipeline_utils import log_table_created, log_validation_result

logger = logging.getLogger(__name__)


class GoldBuildError(Exception):
    """Raised when Gold table creation fails."""


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


def gold_sql_dir() -> Path:
    return Path(__file__).resolve().parent


def load_sql_template(script_name: str) -> str:
    path = gold_sql_dir() / script_name
    if not path.exists():
        raise GoldBuildError(f"Gold SQL script not found: {path}")
    return path.read_text(encoding="utf-8")


def render_sql(template: str, config: GoldConfig) -> str:
    """Substitute table placeholders in a Gold SQL template."""
    return template.format(**config.sql_placeholders())


def ensure_gold_schema_exists(spark: SparkSession, config: GoldConfig) -> None:
    qualified = (
        f"{config.catalog}.{config.gold_schema}" if config.catalog else config.gold_schema
    )
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {qualified}")


def execute_gold_script(spark: SparkSession, config: GoldConfig, script_name: str) -> str:
    """Render and execute one Gold SQL script."""
    template = load_sql_template(script_name)
    sql = render_sql(template, config)
    if config.local_mode:
        sql = sql.replace("USING DELTA", "").replace(
            "CREATE OR REPLACE TABLE", "CREATE OR REPLACE TEMP VIEW"
        )
    logger.info("Executing Gold script %s -> %s", script_name, script_name.replace(".sql", ""))
    try:
        spark.sql(sql)
    except AnalysisException as exc:
        logger.error("Gold SQL failed script=%s", script_name, exc_info=True)
        raise GoldBuildError(f"Failed executing {script_name}: {exc}") from exc
    return sql


def run_gold_pipeline(config: GoldConfig, spark: SparkSession | None = None) -> SparkSession:
    """Build all Gold tables from Silver inputs."""
    active_spark = spark or get_spark_session("gold_create_tables")
    pipeline_start = time.perf_counter()
    logger.info("Gold pipeline START local_mode=%s", config.local_mode)
    if not config.local_mode:
        ensure_gold_schema_exists(active_spark, config)

    for script_name, table_name in GOLD_TABLE_SCRIPTS:
        execute_gold_script(active_spark, config, script_name)
        row_count = active_spark.table(config.gold_table(table_name)).count()
        log_table_created(config.gold_table(table_name), row_count)

    logger.info(
        "Gold pipeline build complete tables=%d elapsed_s=%.2f",
        len(GOLD_TABLE_SCRIPTS),
        time.perf_counter() - pipeline_start,
    )
    return active_spark


def run_gold_validations(spark: SparkSession, config: GoldConfig) -> list[ValidationResult]:
    """Execute validation queries against Gold tables."""
    results: list[ValidationResult] = []
    placeholders = config.sql_placeholders()

    for validation in VALIDATIONS:
        sql = validation.sql.format(**placeholders)
        try:
            row = spark.sql(sql).collect()[0]
            passed = bool(row["passed"])
            detail = row["detail"]
        except AnalysisException as exc:
            passed = False
            detail = str(exc)
            logger.error(
                "Gold validation query failed table=%s check=%s",
                validation.table_name,
                validation.name,
                exc_info=True,
            )

        result = ValidationResult(
            table_name=validation.table_name,
            validation_name=validation.name,
            description=validation.description,
            passed=passed,
            detail=detail,
        )
        results.append(result)
        log_validation_result(
            layer="gold",
            check_name=f"{validation.table_name}.{validation.name}",
            passed=passed,
            detail=detail,
        )

    return results


def all_validations_passed(results: list[ValidationResult]) -> bool:
    return all(result.passed for result in results)
