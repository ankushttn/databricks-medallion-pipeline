"""Silver layer: uniqueness quality checks."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from silver.check_helpers import uniqueness_check
from silver.quality_framework import QualityCheck, QualityContext

DIMENSION = "uniqueness"

_ENTITY_PK = {
    "customers": ("customer_id", "UNQ-CUST-001"),
    "products": ("product_id", "UNQ-PROD-001"),
    "orders": ("order_id", "UNQ-ORD-001"),
}


def prepare(df: DataFrame, ctx: QualityContext) -> DataFrame:
    """Add duplicate-key counts used by uniqueness checks."""
    mapping = _ENTITY_PK.get(ctx.entity)
    if mapping is None:
        return df
    pk_column, _ = mapping
    window = Window.partitionBy(pk_column)
    return df.withColumn("_pk_dup_count", F.count(F.lit(1)).over(window))


def get_checks(ctx: QualityContext) -> list[QualityCheck]:
    """Return primary-key uniqueness checks for the entity."""
    mapping = _ENTITY_PK.get(ctx.entity)
    if mapping is None:
        return []
    pk_column, check_id = mapping
    return [
        uniqueness_check(check_id, pk_column, ctx.entity),
    ]
