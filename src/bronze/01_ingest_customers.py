"""Bronze layer: ingest customers CSV into Delta."""

from __future__ import annotations

import sys

from bronze.config import CUSTOMERS_SPEC
from bronze.ingest_utils import configure_src_path, run_ingestion

configure_src_path()


def main() -> int:
    """Ingest customers.csv into bronze.customers."""
    return run_ingestion(CUSTOMERS_SPEC, app_name="bronze_ingest_customers")


if __name__ == "__main__":
    sys.exit(main())
