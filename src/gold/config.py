"""Gold layer configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from gold.constants import HIGH_VALUE_REVENUE_THRESHOLD
from common.pipeline_utils import validate_schema_name, validate_sql_identifier, validate_write_mode

ENV_CATALOG = "MEDALLION_CATALOG"
ENV_SILVER_SCHEMA = "MEDALLION_SILVER_SCHEMA"
ENV_GOLD_SCHEMA = "MEDALLION_GOLD_SCHEMA"
ENV_WRITE_MODE = "MEDALLION_GOLD_WRITE_MODE"

DEFAULT_SILVER_SCHEMA = "silver"
DEFAULT_GOLD_SCHEMA = "gold"
DEFAULT_WRITE_MODE = "overwrite"


@dataclass(frozen=True)
class GoldConfig:
    """Runtime configuration for Gold table builds."""

    catalog: str | None = None
    silver_schema: str = DEFAULT_SILVER_SCHEMA
    gold_schema: str = DEFAULT_GOLD_SCHEMA
    write_mode: str = DEFAULT_WRITE_MODE
    local_mode: bool = False

    def silver_table(self, table: str) -> str:
        if self.local_mode:
            return f"silver_{table}"
        return self._qualified(self.silver_schema, table)

    def gold_table(self, table: str) -> str:
        if self.local_mode:
            return f"gold_{table}"
        return self._qualified(self.gold_schema, table)

    def _qualified(self, schema: str, table: str) -> str:
        if self.catalog:
            return f"{self.catalog}.{schema}.{table}"
        return f"{schema}.{table}"

    def sql_placeholders(self) -> dict[str, str]:
        """Return placeholder map for Gold SQL templates."""
        return {
            "silver_customers": self.silver_table("customers"),
            "silver_products": self.silver_table("products"),
            "silver_orders": self.silver_table("orders"),
            "gold_sales_by_product": self.gold_table("sales_by_product"),
            "gold_revenue_by_customer": self.gold_table("revenue_by_customer"),
            "gold_daily_weekly_trends": self.gold_table("daily_weekly_trends"),
            "gold_customer_segmentation": self.gold_table("customer_segmentation"),
            "high_value_revenue_threshold": str(HIGH_VALUE_REVENUE_THRESHOLD),
        }


def load_gold_config(
    *,
    catalog: str | None = None,
    silver_schema: str | None = None,
    gold_schema: str | None = None,
    write_mode: str | None = None,
) -> GoldConfig:
    """Load Gold configuration from explicit args with environment fallbacks."""
    resolved_catalog = catalog if catalog is not None else os.getenv(ENV_CATALOG) or None
    if resolved_catalog == "":
        resolved_catalog = None

    return GoldConfig(
        catalog=resolved_catalog,
        silver_schema=silver_schema or os.getenv(ENV_SILVER_SCHEMA, DEFAULT_SILVER_SCHEMA),
        gold_schema=gold_schema or os.getenv(ENV_GOLD_SCHEMA, DEFAULT_GOLD_SCHEMA),
        write_mode=write_mode or os.getenv(ENV_WRITE_MODE, DEFAULT_WRITE_MODE),
    )


def validate_gold_config(config: GoldConfig) -> None:
    """Validate Gold configuration before pipeline execution."""
    validate_write_mode(config.write_mode, layer="Gold")
    validate_schema_name(config.silver_schema, field="silver_schema")
    validate_schema_name(config.gold_schema, field="gold_schema")
    if config.catalog:
        validate_sql_identifier(config.catalog, field="catalog")


def load_and_validate_gold_config(
    *,
    catalog: str | None = None,
    silver_schema: str | None = None,
    gold_schema: str | None = None,
    write_mode: str | None = None,
) -> GoldConfig:
    """Load and validate Gold configuration."""
    config = load_gold_config(
        catalog=catalog,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        write_mode=write_mode,
    )
    validate_gold_config(config)
    return config


def add_gold_config_args(parser) -> None:
    """Register Gold configuration arguments on an argparse parser."""
    parser.add_argument("--catalog", default=None, help=f"Unity Catalog. Env: {ENV_CATALOG}")
    parser.add_argument(
        "--silver-schema",
        default=None,
        help=f"Silver schema. Env: {ENV_SILVER_SCHEMA}",
    )
    parser.add_argument(
        "--gold-schema",
        default=None,
        help=f"Gold schema. Env: {ENV_GOLD_SCHEMA}",
    )
    parser.add_argument(
        "--write-mode",
        default=None,
        choices=("overwrite", "append"),
        help=f"Delta write mode. Env: {ENV_WRITE_MODE}",
    )


def config_from_args(args) -> GoldConfig:
    """Build GoldConfig from parsed argparse namespace."""
    return load_and_validate_gold_config(
        catalog=args.catalog,
        silver_schema=args.silver_schema,
        gold_schema=args.gold_schema,
        write_mode=args.write_mode,
    )
