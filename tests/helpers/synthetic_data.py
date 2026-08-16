"""Deterministic synthetic rows for Silver dimension tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal


def valid_customer_row(
    customer_id: int = 1,
    email: str = "valid@example.com",
    segment: str = "Standard",
) -> tuple:
    return (
        customer_id,
        f"Customer {customer_id}",
        email,
        "US",
        date(2024, 1, 1),
        segment,
        Decimal("100.00"),
    )


def valid_product_row(product_id: int = 1) -> tuple:
    return (
        product_id,
        f"Product {product_id}",
        "Electronics",
        Decimal("99.99"),
        Decimal("50.00"),
        100,
        10,
    )


def valid_order_row(
    order_id: int = 1,
    customer_id: int = 1,
    product_id: int = 1,
    quantity: int = 2,
    unit_price: Decimal = Decimal("50.00"),
    order_status: str = "Completed",
    payment_date: date | None = date(2024, 1, 2),
) -> tuple:
    total_amount = Decimal(str(quantity)) * unit_price
    return (
        order_id,
        customer_id,
        date(2024, 1, 1),
        product_id,
        quantity,
        unit_price,
        total_amount,
        order_status,
        payment_date,
    )
