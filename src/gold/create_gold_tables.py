"""Gold layer: create and populate Gold Delta tables from Silver SQL scripts.

Executes, in order:

1. ``01_sales_by_product.sql`` → ``gold.sales_by_product``
2. ``02_revenue_by_customer.sql`` → ``gold.revenue_by_customer``
3. ``03_daily_weekly_trends.sql`` → ``gold.daily_weekly_trends``
4. ``04_customer_segmentation.sql`` → ``gold.customer_segmentation``

All scripts filter Silver inputs to ``_is_valid = TRUE``.
"""

from __future__ import annotations

import argparse
import logging
import sys

from gold.config import add_gold_config_args, config_from_args
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

    try:
        spark = run_gold_pipeline(config)
    except GoldBuildError as exc:
        logger.error("Gold build failed: %s", exc)
        return 1

    if args.skip_validation:
        return 0

    results = run_gold_validations(spark, config)
    if not all_validations_passed(results):
        logger.error("Gold validation failed (%d failing checks)", sum(1 for r in results if not r.passed))
        return 1

    logger.info("Gold pipeline completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
