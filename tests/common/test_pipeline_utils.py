"""Tests for shared pipeline utilities and configuration validation."""

from __future__ import annotations

import pytest

from bronze.config import validate_bronze_config, BronzeConfig
from common.pipeline_utils import (
    ConfigurationError,
    validate_local_source_directory,
    validate_schema_name,
    validate_write_mode,
)
from gold.config import GoldConfig, validate_gold_config
from silver.config import SilverConfig, validate_silver_config

pytestmark = pytest.mark.unit


def test_validate_write_mode_accepts_overwrite() -> None:
    assert validate_write_mode("overwrite", layer="Test") == "overwrite"


def test_validate_write_mode_rejects_invalid() -> None:
    with pytest.raises(ConfigurationError, match="write_mode"):
        validate_write_mode("invalid", layer="Test")


def test_validate_schema_name_rejects_empty() -> None:
    with pytest.raises(ConfigurationError, match="bronze_schema"):
        validate_schema_name("  ", field="bronze_schema")


def test_validate_local_source_directory_missing(tmp_path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(ConfigurationError, match="Source directory not found"):
        validate_local_source_directory(str(missing))


def test_validate_local_source_directory_skips_dbfs() -> None:
    validate_local_source_directory("dbfs:/FileStore/medallion/data")


def test_validate_bronze_config_rejects_bad_write_mode(data_dir) -> None:
    config = BronzeConfig(
        source_base_path=str(data_dir),
        write_mode="merge",
    )
    with pytest.raises(ConfigurationError):
        validate_bronze_config(config)


def test_validate_silver_config_rejects_empty_schema() -> None:
    config = SilverConfig(silver_schema="")
    with pytest.raises(ConfigurationError):
        validate_silver_config(config)


def test_validate_gold_config_accepts_defaults() -> None:
    validate_gold_config(GoldConfig())
