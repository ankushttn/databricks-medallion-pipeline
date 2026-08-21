"""Gold layer: create and populate Gold Delta tables from Silver SQL scripts.

Executes, in order:

1. ``01_sales_by_product.sql`` → ``gold.sales_by_product``
2. ``02_revenue_by_customer.sql`` → ``gold.revenue_by_customer``
3. ``03_daily_weekly_trends.sql`` → ``gold.daily_weekly_trends``
4. ``04_customer_segmentation.sql`` → ``gold.customer_segmentation``

All scripts filter Silver inputs to ``_is_valid = TRUE``.
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
import sys
from datetime import datetime, timezone

from gold.config import add_gold_config_args, config_from_args
from common.pipeline_utils import ConfigurationError, PipelineRunContext, pipeline_timer
from gold.gold_engine import (
    GoldBuildError,
    all_validations_passed,
    configure_src_path,
    run_gold_pipeline,
    run_gold_validations,
    setup_logging,
)

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gold analytics tables from Silver.")
    add_gold_config_args(parser)
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip post-build Gold validation queries.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_src_path()
    setup_logging()
    args = parse_args(argv)
    config = config_from_args(args)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_ctx = PipelineRunContext(layer="gold", run_id=run_id)

    try:
        with pipeline_timer(run_ctx, catalog=config.catalog, gold_schema=config.gold_schema):
            spark = run_gold_pipeline(config)
            if not args.skip_validation:
                results = run_gold_validations(spark, config)
                if not all_validations_passed(results):
                    failing = sum(1 for r in results if not r.passed)
                    raise GoldBuildError(f"Gold validation failed: {failing} failing checks")
        return 0
    except ConfigurationError as exc:
        logger.error("Gold configuration invalid: %s", exc)
        return 1
    except GoldBuildError as exc:
        logger.error("Gold build failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    code = main([
        "--catalog", "databricks_assignment",
    ])
    if code != 0:
        raise RuntimeError(f"Gold pipeline failed with exit code {code}")
    print("Gold layer creation completed successfully")
