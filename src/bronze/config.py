"""Bronze ingestion configuration loaded from environment variables and CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

from pathlib import Path

from pyspark.sql.types import StructType

from bronze.schemas import (
    CUSTOMERS_BRONZE_SCHEMA,
    ORDERS_BRONZE_SCHEMA,
    PRODUCTS_BRONZE_SCHEMA,
)

ENV_CATALOG = "MEDALLION_CATALOG"
ENV_BRONZE_SCHEMA = "MEDALLION_BRONZE_SCHEMA"
ENV_SOURCE_BASE_PATH = "MEDALLION_SOURCE_BASE_PATH"
ENV_WRITE_MODE = "MEDALLION_BRONZE_WRITE_MODE"

DEFAULT_BRONZE_SCHEMA = "bronze"
DEFAULT_SOURCE_BASE_PATH = "data"
DEFAULT_WRITE_MODE = "overwrite"


@dataclass(frozen=True)
class EntityIngestSpec:
    """Specification for ingesting one Bronze entity."""

    entity_name: str
    source_filename: str
    table_name: str
    schema: StructType
    partition_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class BronzeConfig:
    """Runtime configuration for Bronze ingestion."""

    source_base_path: str
    catalog: str | None = None
    bronze_schema: str = DEFAULT_BRONZE_SCHEMA
    write_mode: str = DEFAULT_WRITE_MODE

    def qualified_table_name(self, table_name: str) -> str:
        """Return catalog.schema.table or schema.table."""
        if self.catalog:
            return f"{self.catalog}.{self.bronze_schema}.{table_name}"
        return f"{self.bronze_schema}.{table_name}"

    def source_path(self, filename: str) -> str:
        """Build full source path for a CSV filename."""
        return build_source_path(self.source_base_path, filename)


def build_source_path(source_base_path: str, filename: str) -> str:
    """Build a source CSV path for local, file://, or DBFS locations."""
    base = source_base_path.rstrip("/")
    if base.startswith("dbfs:") or base.startswith("/dbfs"):
        return f"{base}/{filename}"
    if base.startswith("file://"):
        return f"{base.rstrip('/')}/{filename}"
    return str((Path(base) / filename).resolve()).replace("\\", "/")


def load_bronze_config(
    *,
    source_base_path: str | None = None,
    catalog: str | None = None,
    bronze_schema: str | None = None,
    write_mode: str | None = None,
) -> BronzeConfig:
    """Load Bronze configuration from explicit args with environment fallbacks."""
    resolved_catalog = catalog if catalog is not None else os.getenv(ENV_CATALOG) or None
    if resolved_catalog == "":
        resolved_catalog = None

    return BronzeConfig(
        source_base_path=source_base_path
        or os.getenv(ENV_SOURCE_BASE_PATH, DEFAULT_SOURCE_BASE_PATH),
        catalog=resolved_catalog,
        bronze_schema=bronze_schema
        or os.getenv(ENV_BRONZE_SCHEMA, DEFAULT_BRONZE_SCHEMA),
        write_mode=write_mode or os.getenv(ENV_WRITE_MODE, DEFAULT_WRITE_MODE),
    )


def add_bronze_config_args(parser) -> None:
    """Register Bronze configuration arguments on an argparse parser."""
    parser.add_argument(
        "--source-base-path",
        default=None,
        help=(
            "Directory containing source CSV files (local path, file://, or dbfs:/). "
            f"Env: {ENV_SOURCE_BASE_PATH}"
        ),
    )
    parser.add_argument(
        "--catalog",
        default=None,
        help=f"Unity Catalog name (optional). Env: {ENV_CATALOG}",
    )
    parser.add_argument(
        "--bronze-schema",
        default=None,
        help=f"Bronze schema name. Env: {ENV_BRONZE_SCHEMA} (default: {DEFAULT_BRONZE_SCHEMA})",
    )
    parser.add_argument(
        "--write-mode",
        default=None,
        choices=("overwrite", "append"),
        help=f"Delta write mode. Env: {ENV_WRITE_MODE} (default: {DEFAULT_WRITE_MODE})",
    )


def config_from_args(args) -> BronzeConfig:
    """Build BronzeConfig from parsed argparse namespace."""
    return load_bronze_config(
        source_base_path=args.source_base_path,
        catalog=args.catalog,
        bronze_schema=args.bronze_schema,
        write_mode=args.write_mode,
    )


CUSTOMERS_SPEC = EntityIngestSpec(
    entity_name="customers",
    source_filename="customers.csv",
    table_name="customers",
    schema=CUSTOMERS_BRONZE_SCHEMA,
)

ORDERS_SPEC = EntityIngestSpec(
    entity_name="orders",
    source_filename="orders.csv",
    table_name="orders",
    schema=ORDERS_BRONZE_SCHEMA,
    partition_columns=("order_date",),
)

PRODUCTS_SPEC = EntityIngestSpec(
    entity_name="products",
    source_filename="products.csv",
    table_name="products",
    schema=PRODUCTS_BRONZE_SCHEMA,
)

ALL_ENTITY_SPECS: tuple[EntityIngestSpec, ...] = (
    CUSTOMERS_SPEC,
    PRODUCTS_SPEC,
    ORDERS_SPEC,
)
