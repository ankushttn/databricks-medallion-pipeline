"""Bronze layer: orchestrate ingestion of all source entities."""

from __future__ import annotations

import sys

from bronze.ingest_utils import configure_src_path, run_ingest_all

configure_src_path()


def main() -> int:
    """Ingest customers, products, and orders into Bronze Delta tables."""
    return run_ingest_all()


if __name__ == "__main__":
    sys.exit(main())
