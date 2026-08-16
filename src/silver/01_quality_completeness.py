"""Silver layer: completeness quality checks."""

from __future__ import annotations

from pyspark.sql import DataFrame

from silver.check_helpers import completeness_check
from silver.quality_framework import QualityCheck, QualityContext

DIMENSION = "completeness"


def prepare(df: DataFrame, ctx: QualityContext) -> DataFrame:
    """Completeness checks do not require preparatory columns."""
    return df


def get_checks(ctx: QualityContext) -> list[QualityCheck]:
    """Return entity-specific completeness checks."""
    if ctx.entity == "customers":
        return [
            completeness_check("CMP-CUST-004", "email"),
        ]
    if ctx.entity == "orders":
        return [
            completeness_check("CMP-ORD-002", "customer_id"),
            completeness_check("CMP-ORD-003", "product_id"),
        ]
    return []
