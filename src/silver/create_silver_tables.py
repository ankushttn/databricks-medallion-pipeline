"""Silver layer: create and populate Silver Delta tables with quality metadata.

Orchestrates completeness, uniqueness, type validation, referential integrity,
and business-logic checks across customers, products, and orders. Writes:

- ``silver.customers``, ``silver.products``, ``silver.orders``
- ``silver.data_quality_metrics`` (entity pass/fail rollups)
- ``silver.data_quality_summary`` (per-check failure counts)
- ``silver.data_quality_results`` (row-level failure detail)
"""
from __future__ import annotations

import sys
import os

REPO = "/Workspace/Repos/ankushkumar645@gmail.com/databricks-medallion-pipeline"
DATA = f"{REPO}/data"
SRC = f"{REPO}/src"
sys.path.insert(0, SRC)

os.environ["MEDALLION_CATALOG"] = "databricks_assignment"
os.environ["MEDALLION_SOURCE_BASE_PATH"] = DATA
os.environ["MEDALLION_BRONZE_WRITE_MODE"] = "overwrite"

import argparse
import logging

from silver.config import add_silver_config_args, config_from_args
from common.pipeline_utils import ConfigurationError
from silver.quality_engine import (
    SilverValidationError,
    configure_src_path,
    run_silver_pipeline,
    setup_logging,
)

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Silver table creation."""
    parser = argparse.ArgumentParser(
        description="Run Silver data quality validation and create Delta tables.",
    )
    add_silver_config_args(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for Silver validation pipeline."""
    configure_src_path()
    setup_logging()
    args = parse_args(argv)
    config = config_from_args(args)

    try:
        return run_silver_pipeline(config)
    except ConfigurationError as exc:
        logger.error("Silver configuration invalid: %s", exc)
        return 1
    except SilverValidationError as exc:
        logger.error("Silver validation failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    code = main([
        "--catalog", "databricks_assignment",
    ])
    if code != 0:
        raise RuntimeError(f"Silver pipeline failed with exit code {code}")
    print("Silver layer creation completed successfully")
