"""Bronze layer: ingest products CSV into Delta."""

from __future__ import annotations

import sys

from bronze.config import PRODUCTS_SPEC
from bronze.ingest_utils import configure_src_path, run_ingestion

configure_src_path()


def main() -> int:
    """Ingest products.csv into bronze.products."""
    return run_ingestion(PRODUCTS_SPEC, app_name="bronze_ingest_products")


if __name__ == "__main__":
    sys.exit(main())
