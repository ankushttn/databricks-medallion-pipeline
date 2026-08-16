"""Static validation for Bronze ingestion readiness (no Spark/Delta required)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from bronze.config import ALL_ENTITY_SPECS, BronzeConfig, add_bronze_config_args, config_from_args
from bronze.ingest_utils import (
    BronzeIngestionError,
    BronzeSourceFileError,
    count_csv_data_rows,
    setup_logging,
    validate_csv_header,
    verify_source_file_exists,
)
from bronze.schemas import EXPECTED_ROW_COUNTS

logger = logging.getLogger(__name__)


def static_validate_bronze_sources(config: BronzeConfig) -> list[str]:
    """Validate source CSV files exist, headers match, and row counts are expected."""
    errors: list[str] = []

    for spec in ALL_ENTITY_SPECS:
        source_path = config.source_path(spec.source_filename)
        entity = spec.entity_name

        try:
            verify_source_file_exists(source_path)
            validate_csv_header(source_path, [f.name for f in spec.schema.fields])
            row_count = count_csv_data_rows(source_path)
            expected = EXPECTED_ROW_COUNTS.get(entity)

            if expected is not None and row_count != expected:
                errors.append(
                    f"{entity}: row count {row_count} != expected {expected}"
                )
            else:
                logger.info(
                    "Static validation PASS entity=%s path=%s rows=%d",
                    entity,
                    source_path,
                    row_count,
                )
        except (BronzeSourceFileError, BronzeIngestionError) as exc:
            errors.append(f"{entity}: {exc}")

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI for static Bronze source validation."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Static validation of Bronze source CSV files (no Spark required).",
    )
    add_bronze_config_args(parser)
    args = parser.parse_args(argv)
    config = config_from_args(args)

    errors = static_validate_bronze_sources(config)
    if errors:
        for err in errors:
            logger.error("Static validation FAILED: %s", err)
        return 1

    logger.info("Static Bronze source validation PASSED for all entities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
