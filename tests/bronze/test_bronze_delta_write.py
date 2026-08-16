"""Tests that Bronze ingestion targets Delta Lake format."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bronze.ingest_utils import write_bronze_delta

pytestmark = [pytest.mark.bronze, pytest.mark.unit]


def test_write_bronze_delta_uses_delta_format_and_save_as_table() -> None:
    """Bronze writes must use Delta format (BR-07) even when not run on Databricks."""
    mock_df = MagicMock()
    mock_writer = MagicMock()
    mock_df.write.format.return_value = mock_writer
    mock_writer.mode.return_value = mock_writer
    mock_writer.option.return_value = mock_writer

    write_bronze_delta(
        mock_df,
        target_table="bronze.customers",
        write_mode="overwrite",
        partition_columns=(),
    )

    mock_df.write.format.assert_called_once_with("delta")
    mock_writer.mode.assert_called_once_with("overwrite")
    mock_writer.option.assert_called_once_with("overwriteSchema", "true")
    mock_writer.saveAsTable.assert_called_once_with("bronze.customers")


def test_write_bronze_delta_partitions_orders_by_order_date() -> None:
    mock_df = MagicMock()
    mock_writer = MagicMock()
    mock_df.write.format.return_value = mock_writer
    mock_writer.mode.return_value = mock_writer
    mock_writer.option.return_value = mock_writer
    mock_writer.partitionBy.return_value = mock_writer

    write_bronze_delta(
        mock_df,
        target_table="bronze.orders",
        write_mode="overwrite",
        partition_columns=("order_date",),
    )

    mock_writer.partitionBy.assert_called_once_with("order_date")
    mock_writer.saveAsTable.assert_called_once_with("bronze.orders")
