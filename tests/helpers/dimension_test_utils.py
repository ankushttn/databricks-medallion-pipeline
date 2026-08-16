"""Utilities for applying individual Silver quality dimensions in tests."""

from __future__ import annotations

import importlib

from pyspark.sql import DataFrame

from silver.quality_engine import drop_prepare_columns
from silver.quality_framework import QualityContext, apply_checks_to_dataframe, finalize_silver_entity


def apply_single_dimension(
    df: DataFrame,
    ctx: QualityContext,
    module_name: str,
) -> tuple[DataFrame, DataFrame]:
    """Run one Silver dimension module (prepare + checks + finalize)."""
    module = importlib.import_module(f"silver.{module_name}")
    working = module.prepare(df, ctx)
    checks = module.get_checks(ctx)
    working, detail_df = apply_checks_to_dataframe(working, checks, ctx)
    working = drop_prepare_columns(working)
    working = finalize_silver_entity(working, ctx)
    return working, detail_df


def issue_count(df: DataFrame, issue_code: str) -> int:
    from pyspark.sql import functions as F

    return df.filter(F.array_contains(F.col("_quality_issues"), issue_code)).count()
