"""Tests for Bronze configuration and static CSV validation."""

from __future__ import annotations

import pytest

from bronze.config import (
    CUSTOMERS_SPEC,
    ORDERS_SPEC,
    build_source_path,
    load_and_validate_bronze_config,
    load_bronze_config,
)
from bronze.ingest_utils import (
    BronzeIngestionError,
    BronzeSourceFileError,
    count_csv_data_rows,
    validate_csv_header,
    verify_source_file_exists,
)
from bronze.schemas import CUSTOMERS_CSV_COLUMNS, EXPECTED_ROW_COUNTS, ORDERS_CSV_COLUMNS, PRODUCTS_CSV_COLUMNS
from common.pipeline_utils import ConfigurationError

pytestmark = pytest.mark.bronze


@pytest.mark.unit
def test_load_config_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDALLION_SOURCE_BASE_PATH", "/dbfs/FileStore/medallion/data")
    monkeypatch.setenv("MEDALLION_CATALOG", "main")
    monkeypatch.setenv("MEDALLION_BRONZE_SCHEMA", "bronze")
    monkeypatch.setenv("MEDALLION_BRONZE_WRITE_MODE", "overwrite")

    config = load_bronze_config()
    assert config.source_base_path == "/dbfs/FileStore/medallion/data"
    assert config.catalog == "main"
    assert config.bronze_schema == "bronze"
    assert config.write_mode == "overwrite"
    assert config.qualified_table_name("customers") == "main.bronze.customers"


@pytest.mark.unit
def test_build_source_path_local(data_dir) -> None:
    path = build_source_path(str(data_dir), "customers.csv")
    assert path.endswith("customers.csv")


@pytest.mark.unit
def test_build_source_path_dbfs() -> None:
    path = build_source_path("dbfs:/FileStore/medallion/data", "orders.csv")
    assert path == "dbfs:/FileStore/medallion/data/orders.csv"


@pytest.mark.unit
def test_qualified_table_name_without_catalog() -> None:
    config = load_bronze_config(source_base_path="data", catalog=None)
    assert config.qualified_table_name("orders") == "bronze.orders"


@pytest.mark.unit
def test_csv_headers_match_schema(bronze_config) -> None:
    for filename, columns in (
        ("customers.csv", CUSTOMERS_CSV_COLUMNS),
        ("products.csv", PRODUCTS_CSV_COLUMNS),
        ("orders.csv", ORDERS_CSV_COLUMNS),
    ):
        validate_csv_header(bronze_config.source_path(filename), columns)


@pytest.mark.unit
def test_csv_row_counts_match_expected(bronze_config) -> None:
    for entity, filename in (
        ("customers", "customers.csv"),
        ("products", "products.csv"),
        ("orders", "orders.csv"),
    ):
        path = bronze_config.source_path(filename)
        assert count_csv_data_rows(path) == EXPECTED_ROW_COUNTS[entity]


@pytest.mark.unit
def test_missing_file_raises(data_dir) -> None:
    config = load_bronze_config(source_base_path=str(data_dir))
    missing = config.source_path("does_not_exist.csv")
    with pytest.raises(BronzeSourceFileError, match="not found"):
        verify_source_file_exists(missing)


@pytest.mark.unit
def test_customers_spec_has_no_partitions() -> None:
    assert CUSTOMERS_SPEC.partition_columns == ()


@pytest.mark.unit
def test_orders_spec_partitioned_by_order_date() -> None:
    assert ORDERS_SPEC.partition_columns == ("order_date",)


@pytest.mark.unit
def test_bronze_schema_field_count() -> None:
    assert len(CUSTOMERS_SPEC.schema.fields) == 7
    assert len(CUSTOMERS_CSV_COLUMNS) == 7


def test_load_and_validate_rejects_missing_source_dir(tmp_path) -> None:
    missing = tmp_path / "missing_data"
    with pytest.raises(ConfigurationError, match="Source directory not found"):
        load_and_validate_bronze_config(source_base_path=str(missing))


def test_validate_csv_header_raises_on_mismatch(tmp_path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("wrong,col\n1,x\n", encoding="utf-8")
    with pytest.raises(BronzeIngestionError, match="header mismatch"):
        validate_csv_header(str(bad_csv), CUSTOMERS_CSV_COLUMNS)


def test_validate_csv_header_raises_on_empty_file(tmp_path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(BronzeSourceFileError, match="empty"):
        validate_csv_header(str(empty), CUSTOMERS_CSV_COLUMNS)
