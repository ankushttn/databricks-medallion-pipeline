"""Shared pipeline utilities for logging, timing, and configuration validation."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

ALLOWED_WRITE_MODES = frozenset({"overwrite", "append"})


class ConfigurationError(ValueError):
    """Raised when pipeline configuration is invalid."""


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging for pipeline scripts."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


def validate_write_mode(write_mode: str, *, layer: str) -> str:
    """Validate Delta write mode."""
    normalized = write_mode.strip().lower()
    if normalized not in ALLOWED_WRITE_MODES:
        raise ConfigurationError(
            f"{layer} write_mode must be one of {sorted(ALLOWED_WRITE_MODES)}, got {write_mode!r}"
        )
    return normalized


def validate_schema_name(schema: str, *, field: str) -> str:
    """Validate a non-empty schema name."""
    name = schema.strip()
    if not name:
        raise ConfigurationError(f"{field} must be a non-empty string")
    return name


def validate_local_source_directory(source_base_path: str) -> None:
    """Validate a local source directory exists (skipped for remote DBFS paths)."""
    base = source_base_path.strip()
    if base.startswith(("dbfs:", "/dbfs", "file://")):
        return
    path = Path(base)
    if not path.is_dir():
        raise ConfigurationError(f"Source directory not found: {source_base_path}")


@dataclass(frozen=True)
class PipelineRunContext:
    """Metadata for a single pipeline execution."""

    layer: str
    run_id: str


def log_pipeline_start(ctx: PipelineRunContext, **details: object) -> None:
    """Log pipeline start with run context."""
    detail_str = " ".join(f"{key}={value}" for key, value in sorted(details.items()))
    logger.info(
        "Pipeline START layer=%s run_id=%s %s",
        ctx.layer,
        ctx.run_id,
        detail_str.strip(),
    )


def log_pipeline_end(
    ctx: PipelineRunContext,
    *,
    status: str,
    elapsed_seconds: float,
    **details: object,
) -> None:
    """Log pipeline completion with duration."""
    detail_str = " ".join(f"{key}={value}" for key, value in sorted(details.items()))
    log_fn = logger.info if status == "SUCCESS" else logger.error
    log_fn(
        "Pipeline END layer=%s run_id=%s status=%s elapsed_s=%.2f %s",
        ctx.layer,
        ctx.run_id,
        status,
        elapsed_seconds,
        detail_str.strip(),
    )


@contextmanager
def pipeline_timer(ctx: PipelineRunContext, **start_details: object) -> Iterator[None]:
    """Context manager that logs pipeline start/end with elapsed time."""
    log_pipeline_start(ctx, **start_details)
    started = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - started
        log_pipeline_end(ctx, status="FAILED", elapsed_seconds=elapsed)
        raise
    else:
        elapsed = time.perf_counter() - started
        log_pipeline_end(ctx, status="SUCCESS", elapsed_seconds=elapsed)


def log_table_created(table_name: str, row_count: int) -> None:
    """Log table creation outcome."""
    if row_count == 0:
        logger.warning("Table created with zero rows: table=%s row_count=0", table_name)
    else:
        logger.info("Table created: table=%s row_count=%d", table_name, row_count)


def log_validation_result(
    *,
    layer: str,
    check_name: str,
    passed: bool,
    detail: str,
) -> None:
    """Log a single validation check result."""
    level = logging.INFO if passed else logging.ERROR
    logger.log(
        level,
        "Validation %s layer=%s check=%s result=%s detail=%s",
        "PASS" if passed else "FAIL",
        layer,
        check_name,
        "PASS" if passed else "FAIL",
        detail,
    )
