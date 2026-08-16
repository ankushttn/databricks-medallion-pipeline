"""Silver layer: referential integrity quality checks."""

from __future__ import annotations

import logging

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from silver.check_helpers import referential_check
from silver.quality_framework import QualityCheck, QualityContext

logger = logging.getLogger(__name__)

DIMENSION = "referential_integrity"


def prepare(df: DataFrame, ctx: QualityContext) -> DataFrame:
    """Annotate orders with parent-key existence flags."""
    if ctx.entity != "orders":
        return df

    if ctx.valid_customer_ids is None or ctx.valid_product_ids is None:
        logger.warning(
            "Referential prepare skipped for orders: parent Silver tables unavailable"
        )
        return (
            df.withColumn("_customer_ref_exists", F.lit(False))
            .withColumn("_product_ref_exists", F.lit(False))
        )

    valid_customers = ctx.valid_customer_ids.select(
        F.col("customer_id").alias("_ref_customer_id")
    ).distinct()
    valid_products = ctx.valid_product_ids.select(
        F.col("product_id").alias("_ref_product_id")
    ).distinct()

    enriched = df.join(
        valid_customers,
        df.customer_id == valid_customers._ref_customer_id,
        "left",
    )
    enriched = enriched.withColumn(
        "_customer_ref_exists",
        F.col("_ref_customer_id").isNotNull(),
    ).drop("_ref_customer_id")

    enriched = enriched.join(
        valid_products,
        enriched.product_id == valid_products._ref_product_id,
        "left",
    )
    enriched = enriched.withColumn(
        "_product_ref_exists",
        F.col("_ref_product_id").isNotNull(),
    ).drop("_ref_product_id")

    return enriched


def get_checks(ctx: QualityContext) -> list[QualityCheck]:
    """Return foreign-key referential checks for orders."""
    if ctx.entity != "orders":
        return []
    return [
        referential_check(
            "REF-ORD-001",
            "customer_id",
            "_customer_ref_exists",
            "silver.customers",
        ),
        referential_check(
            "REF-ORD-002",
            "product_id",
            "_product_ref_exists",
            "silver.products",
        ),
    ]
