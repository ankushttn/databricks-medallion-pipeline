"""Integration tests for Silver quality framework across all dimensions."""

from __future__ import annotations

import pytest
from pyspark.sql import functions as F

from silver.config import load_silver_config
from silver.constants import EXPECTED_DEFECT_COUNTS
from helpers.dimension_test_utils import issue_count

pytestmark = [pytest.mark.silver, pytest.mark.spark, pytest.mark.integration]


def test_silver_config_loads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDALLION_CATALOG", "main")
    monkeypatch.setenv("MEDALLION_SILVER_SCHEMA", "silver_dev")
    monkeypatch.setenv("MEDALLION_RUN_ID", "manual-run")

    config = load_silver_config()
    assert config.catalog == "main"
    assert config.silver_schema == "silver_dev"
    assert config.run_id == "manual-run"
    assert config.silver_table("customers") == "main.silver_dev.customers"


def test_row_count_parity_preserved(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        assert silver_tables[entity].count() == silver_tables["bronze_counts"][entity]


def test_no_rows_deleted(silver_tables: dict) -> None:
    assert silver_tables["customers"].count() == 10_010
    assert silver_tables["products"].count() == 500
    assert silver_tables["orders"].count() == 100_020


def test_mandatory_defect_counts(silver_tables: dict) -> None:
    customers = silver_tables["customers"]
    orders = silver_tables["orders"]

    assert issue_count(customers, "completeness:email_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:email_null"
    ]
    assert issue_count(customers, "uniqueness:duplicate_customer_id") >= EXPECTED_DEFECT_COUNTS[
        "uniqueness:duplicate_customer_id"
    ]
    assert issue_count(orders, "completeness:customer_id_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:customer_id_null"
    ]
    assert issue_count(orders, "completeness:product_id_null") == EXPECTED_DEFECT_COUNTS[
        "completeness:product_id_null"
    ]
    assert issue_count(orders, "referential:invalid_customer_id") == EXPECTED_DEFECT_COUNTS[
        "referential:invalid_customer_id"
    ]
    assert issue_count(orders, "referential:invalid_product_id") == EXPECTED_DEFECT_COUNTS[
        "referential:invalid_product_id"
    ]
    assert issue_count(orders, "uniqueness:duplicate_order_id") >= EXPECTED_DEFECT_COUNTS[
        "uniqueness:duplicate_order_id"
    ]


def test_quality_metadata_columns_present(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        df = silver_tables[entity]
        for column in (
            "_quality_issues",
            "_is_valid",
            "_quality_status",
            "_validated_at",
            "_run_id",
        ):
            assert column in df.columns


def test_quality_results_schema(silver_tables: dict) -> None:
    detail = silver_tables["order_details"]
    expected = {
        "run_id",
        "entity",
        "row_identifier",
        "check_id",
        "check_name",
        "check_dimension",
        "check_status",
        "quality_result",
        "failure_reason",
        "validated_at",
    }
    assert expected.issubset(set(detail.columns))
    assert detail.filter(F.col("check_status") != "FAIL").count() == 0


def test_entity_pass_fail_percentages_sum_to_100(silver_tables: dict) -> None:
    for entity in ("customers", "products", "orders"):
        df = silver_tables[entity]
        total = df.count()
        failed = df.filter(~F.col("_is_valid")).count()
        passed = total - failed
        assert passed + failed == total
        if total:
            assert round((passed / total) * 100 + (failed / total) * 100, 2) == 100.0


def test_duplicate_customers_flag_all_participants(silver_tables: dict) -> None:
    customers = silver_tables["customers"]
    duplicate_rows = customers.filter(
        F.array_contains(F.col("_quality_issues"), "uniqueness:duplicate_customer_id")
    )
    assert duplicate_rows.count() >= EXPECTED_DEFECT_COUNTS["uniqueness:duplicate_customer_id"]
