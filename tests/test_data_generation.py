"""Tests for sample data generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "data_generation"))

from generate_sample_data import (  # noqa: E402
    DEFECT_COUNTS,
    DataGenerationValidationError,
    GenerationConfig,
    _duplicate_extra_row_count,
    _is_null,
    generate_all,
    validate_defect_counts,
)


def _count_null_emails(customers: list[dict]) -> int:
    return sum(1 for row in customers if _is_null(row["email"]))


def test_generate_all_produces_expected_row_counts() -> None:
    """Integration test: full generation succeeds with expected volumes."""
    config = GenerationConfig(seed=42, output_dir=Path("data"))
    customers, products, orders = generate_all(config)

    assert len(customers) == config.customer_count + DEFECT_COUNTS.duplicate_customer_ids
    assert len(products) == config.product_count
    assert len(orders) == config.order_count + DEFECT_COUNTS.duplicate_order_ids


def test_intentional_defect_counts() -> None:
    """Verify all assignment-mandated defect counts on generated data."""
    config = GenerationConfig(seed=99, output_dir=Path("data"))
    customers, _, orders = generate_all(config)

    assert _count_null_emails(customers) == DEFECT_COUNTS.null_emails
    assert _duplicate_extra_row_count(customers, "customer_id") == DEFECT_COUNTS.duplicate_customer_ids
    assert sum(1 for row in orders if _is_null(row["customer_id"])) == DEFECT_COUNTS.null_customer_id
    assert sum(1 for row in orders if _is_null(row["product_id"])) == DEFECT_COUNTS.null_product_id
    assert _duplicate_extra_row_count(orders, "order_id") == DEFECT_COUNTS.duplicate_order_ids

    valid_customers = set(range(1, config.customer_count + 1))
    invalid_customer_count = sum(
        1
        for row in orders
        if not _is_null(row["customer_id"]) and int(row["customer_id"]) not in valid_customers
    )
    assert invalid_customer_count == DEFECT_COUNTS.invalid_customer_id

    valid_products = set(range(1, config.product_count + 1))
    invalid_product_count = sum(
        1
        for row in orders
        if not _is_null(row["product_id"]) and int(row["product_id"]) not in valid_products
    )
    assert invalid_product_count == DEFECT_COUNTS.invalid_product_id


def test_deterministic_output() -> None:
    """Same seed must produce identical in-memory datasets."""
    config = GenerationConfig(seed=7, output_dir=Path("data"))
    customers_a, products_a, orders_a = generate_all(config)
    customers_b, products_b, orders_b = generate_all(config)

    assert customers_a == customers_b
    assert products_a == products_b
    assert orders_a == orders_b


def test_validate_defect_counts_raises_on_mismatch() -> None:
    """Validation must fail loudly when defect counts are wrong."""
    customers = [
        {
            "customer_id": 1,
            "customer_name": "Test User",
            "email": "",
            "country": "US",
            "signup_date": "2024-01-01",
            "customer_segment": "Standard",
            "lifetime_value": "100.00",
        }
    ]
    orders: list[dict] = []

    with pytest.raises(DataGenerationValidationError, match="NULL emails"):
        validate_defect_counts(customers, orders, DEFECT_COUNTS, 1, 1)
