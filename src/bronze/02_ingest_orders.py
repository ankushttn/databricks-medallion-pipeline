"""Bronze layer: ingest orders CSV into Delta."""

from __future__ import annotations

import sys

from bronze.config import ORDERS_SPEC
from bronze.ingest_utils import configure_src_path, run_ingestion

configure_src_path()


def main() -> int:
    """Ingest orders.csv into bronze.orders (partitioned by order_date)."""
    return run_ingestion(ORDERS_SPEC, app_name="bronze_ingest_orders")


if __name__ == "__main__":
    sys.exit(main())
