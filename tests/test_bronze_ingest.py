"""Tests for Bronze ingestion layer."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(SRC_DIR))

from bronze.config import (  # noqa: E402
    CUSTOMERS_SPEC,
    ORDERS_SPEC,
    build_source_path,
    load_bronze_config,
)
from bronze.ingest_utils import (  # noqa: E402
    BronzeSourceFileError,
    count_csv_data_rows,
    validate_csv_header,
    verify_source_file_exists,
)
from bronze.schemas import (  # noqa: E402
    CUSTOMERS_CSV_COLUMNS,
    EXPECTED_ROW_COUNTS,
    ORDERS_CSV_COLUMNS,
    PRODUCTS_CSV_COLUMNS,
)


@pytest.fixture
def project_data_config():
    """Bronze config pointing at project data directory."""
    return load_bronze_config(source_base_path=str(DATA_DIR))


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


def test_build_source_path_local() -> None:
    path = build_source_path(str(DATA_DIR), "customers.csv")
    assert path.endswith("customers.csv")
    assert Path(path).parent == DATA_DIR.resolve()


def test_build_source_path_dbfs() -> None:
    path = build_source_path("dbfs:/FileStore/medallion/data", "orders.csv")
    assert path == "dbfs:/FileStore/medallion/data/orders.csv"


def test_qualified_table_name_without_catalog() -> None:
    config = load_bronze_config(source_base_path="data", catalog=None)
    assert config.qualified_table_name("orders") == "bronze.orders"


def test_csv_headers_match_schema(project_data_config) -> None:
    for filename, columns in (
        ("customers.csv", CUSTOMERS_CSV_COLUMNS),
        ("products.csv", PRODUCTS_CSV_COLUMNS),
        ("orders.csv", ORDERS_CSV_COLUMNS),
    ):
        path = project_data_config.source_path(filename)
        validate_csv_header(path, columns)


def test_csv_row_counts_match_expected(project_data_config) -> None:
    for entity, filename in (
        ("customers", "customers.csv"),
        ("products", "products.csv"),
        ("orders", "orders.csv"),
    ):
        path = project_data_config.source_path(filename)
        assert count_csv_data_rows(path) == EXPECTED_ROW_COUNTS[entity]


def test_missing_file_raises() -> None:
    config = load_bronze_config(source_base_path=str(DATA_DIR))
    missing = config.source_path("does_not_exist.csv")
    with pytest.raises(BronzeSourceFileError, match="not found"):
        verify_source_file_exists(missing)


def test_customers_spec_has_no_partitions() -> None:
    assert CUSTOMERS_SPEC.partition_columns == ()


def test_orders_spec_partitioned_by_order_date() -> None:
    assert ORDERS_SPEC.partition_columns == ("order_date",)


def test_bronze_schema_field_count() -> None:
    assert len(CUSTOMERS_SPEC.schema.fields) == 7
    assert len(CUSTOMERS_CSV_COLUMNS) == 7
