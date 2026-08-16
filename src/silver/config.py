"""Silver layer configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_CATALOG = "MEDALLION_CATALOG"
ENV_BRONZE_SCHEMA = "MEDALLION_BRONZE_SCHEMA"
ENV_SILVER_SCHEMA = "MEDALLION_SILVER_SCHEMA"
ENV_WRITE_MODE = "MEDALLION_SILVER_WRITE_MODE"
ENV_RUN_ID = "MEDALLION_RUN_ID"

DEFAULT_BRONZE_SCHEMA = "bronze"
DEFAULT_SILVER_SCHEMA = "silver"
DEFAULT_WRITE_MODE = "overwrite"


@dataclass(frozen=True)
class SilverConfig:
    """Runtime configuration for Silver validation."""

    catalog: str | None = None
    bronze_schema: str = DEFAULT_BRONZE_SCHEMA
    silver_schema: str = DEFAULT_SILVER_SCHEMA
    write_mode: str = DEFAULT_WRITE_MODE
    run_id: str | None = None

    def bronze_table(self, table: str) -> str:
        return self._qualified(self.bronze_schema, table)

    def silver_table(self, table: str) -> str:
        return self._qualified(self.silver_schema, table)

    def _qualified(self, schema: str, table: str) -> str:
        if self.catalog:
            return f"{self.catalog}.{schema}.{table}"
        return f"{schema}.{table}"


def load_silver_config(
    *,
    catalog: str | None = None,
    bronze_schema: str | None = None,
    silver_schema: str | None = None,
    write_mode: str | None = None,
    run_id: str | None = None,
) -> SilverConfig:
    """Load Silver configuration from explicit args with environment fallbacks."""
    resolved_catalog = catalog if catalog is not None else os.getenv(ENV_CATALOG) or None
    if resolved_catalog == "":
        resolved_catalog = None

    return SilverConfig(
        catalog=resolved_catalog,
        bronze_schema=bronze_schema or os.getenv(ENV_BRONZE_SCHEMA, DEFAULT_BRONZE_SCHEMA),
        silver_schema=silver_schema or os.getenv(ENV_SILVER_SCHEMA, DEFAULT_SILVER_SCHEMA),
        write_mode=write_mode or os.getenv(ENV_WRITE_MODE, DEFAULT_WRITE_MODE),
        run_id=run_id or os.getenv(ENV_RUN_ID),
    )


def add_silver_config_args(parser) -> None:
    """Register Silver configuration arguments on an argparse parser."""
    parser.add_argument("--catalog", default=None, help=f"Unity Catalog. Env: {ENV_CATALOG}")
    parser.add_argument(
        "--bronze-schema",
        default=None,
        help=f"Bronze schema. Env: {ENV_BRONZE_SCHEMA}",
    )
    parser.add_argument(
        "--silver-schema",
        default=None,
        help=f"Silver schema. Env: {ENV_SILVER_SCHEMA}",
    )
    parser.add_argument(
        "--write-mode",
        default=None,
        choices=("overwrite", "append"),
        help=f"Delta write mode. Env: {ENV_WRITE_MODE}",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help=f"Validation run identifier. Env: {ENV_RUN_ID}",
    )


def config_from_args(args) -> SilverConfig:
    """Build SilverConfig from parsed argparse namespace."""
    return load_silver_config(
        catalog=args.catalog,
        bronze_schema=args.bronze_schema,
        silver_schema=args.silver_schema,
        write_mode=args.write_mode,
        run_id=args.run_id,
    )
