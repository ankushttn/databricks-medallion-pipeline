"""Generate deterministic sample e-commerce CSV data with intentional quality defects.

Produces customers.csv, products.csv, and orders.csv for the medallion pipeline.
See DATA_GENERATION_NOTES.md for specifications.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from random import Random
from typing import Any, Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_SEED = 42
DEFAULT_OUTPUT_DIR = "data"

CUSTOMER_COUNT = 10_000
PRODUCT_COUNT = 500
ORDER_COUNT = 100_000

CUSTOMER_COLUMNS = [
    "customer_id",
    "customer_name",
    "email",
    "country",
    "signup_date",
    "customer_segment",
    "lifetime_value",
]

PRODUCT_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "price",
    "cost",
    "stock_quantity",
    "reorder_level",
]

ORDER_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "product_id",
    "quantity",
    "unit_price",
    "total_amount",
    "order_status",
    "payment_date",
]

COUNTRIES = ("US", "UK", "DE", "FR", "CA", "AU", "IN", "JP", "BR", "MX")
SEGMENTS = ("Premium", "Standard", "Basic")
CATEGORIES = (
    "Electronics",
    "Clothing",
    "Home",
    "Sports",
    "Books",
    "Beauty",
    "Toys",
    "Garden",
)
ORDER_STATUSES = ("Completed", "Pending", "Shipped", "Cancelled", "Returned")
FIRST_NAMES = (
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Emma", "Oliver", "Ava", "Noah", "Sophia",
)
LAST_NAMES = (
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
)
PRODUCT_ADJECTIVES = ("Pro", "Ultra", "Essential", "Classic", "Deluxe", "Smart", "Eco")
EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

# Invalid FK values — outside valid generated ID ranges (customers 1..10000, products 1..500).
INVALID_CUSTOMER_ID_START = 800_001
INVALID_PRODUCT_ID_START = 700_001


@dataclass(frozen=True)
class DefectCounts:
    """Mandatory intentional quality defect counts (assignment specification)."""

    null_emails: int = 50
    duplicate_customer_ids: int = 10
    null_customer_id: int = 100
    null_product_id: int = 200
    invalid_customer_id: int = 50
    invalid_product_id: int = 30
    duplicate_order_ids: int = 20


DEFECT_COUNTS = DefectCounts()


@dataclass(frozen=True)
class SupplementaryDefectCounts:
    """Additional defects to reach the assignment ~700 Silver invalid-row target (A-07)."""

    price_below_cost: int = 210


SUPPLEMENTARY_DEFECT_COUNTS = SupplementaryDefectCounts()
TARGET_SILVER_INVALID_ROWS = 700


@dataclass(frozen=True)
class GenerationConfig:
    """Runtime configuration for data generation."""

    seed: int
    output_dir: Path
    customer_count: int = CUSTOMER_COUNT
    product_count: int = PRODUCT_COUNT
    order_count: int = ORDER_COUNT
    defects: DefectCounts = DEFECT_COUNTS
    supplementary: SupplementaryDefectCounts = SUPPLEMENTARY_DEFECT_COUNTS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger for CLI execution."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args(argv: Sequence[str] | None = None) -> GenerationConfig:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate deterministic e-commerce sample CSV data.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help=f"Directory for output CSV files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default: {DEFAULT_SEED})",
    )
    args = parser.parse_args(argv)
    return GenerationConfig(seed=args.seed, output_dir=args.output_dir)


def _random_date(rng: Random, start: date, end: date) -> date:
    """Return a random date in the inclusive range [start, end]."""
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))


def _format_decimal(value: float) -> str:
    """Format a monetary value to two decimal places."""
    return f"{value:.2f}"


def _is_null(value: Any) -> bool:
    """Return True when a CSV value represents NULL."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _duplicate_extra_row_count(rows: list[dict[str, Any]], key: str) -> int:
    """Count extra rows caused by duplicated key values (sum of count-1 per dup key)."""
    counts = Counter(row[key] for row in rows)
    return sum(count - 1 for count in counts.values() if count > 1)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def generate_customers(rng: Random, count: int) -> list[dict[str, Any]]:
    """Generate clean customer records with unique customer_id values."""
    logger.info("Generating %d base customer records", count)
    customers: list[dict[str, Any]] = []
    signup_start = date(2018, 1, 1)
    signup_end = date(2025, 6, 30)

    for customer_id in range(1, count + 1):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        domain = rng.choice(("example.com", "mail.com", "shop.io", "customer.net"))
        customers.append(
            {
                "customer_id": customer_id,
                "customer_name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}{customer_id}@{domain}",
                "country": rng.choice(COUNTRIES),
                "signup_date": _random_date(rng, signup_start, signup_end).isoformat(),
                "customer_segment": rng.choice(SEGMENTS),
                "lifetime_value": _format_decimal(rng.uniform(100.0, 49_999.99)),
            }
        )
    return customers


def inject_customer_defects(
    customers: list[dict[str, Any]],
    rng: Random,
    defects: DefectCounts,
) -> list[dict[str, Any]]:
    """Inject NULL emails and duplicate customer_id rows into customer data."""
    logger.info(
        "Injecting customer defects: %d NULL emails, %d duplicate customer_id rows",
        defects.null_emails,
        defects.duplicate_customer_ids,
    )
    result = [dict(row) for row in customers]

    # NULL emails — select from rows that will not be used for duplication.
    eligible_for_null = list(range(len(result)))
    null_email_indices = set(rng.sample(eligible_for_null, defects.null_emails))
    for idx in null_email_indices:
        result[idx]["email"] = ""

    # Duplicate customer_id — copy rows with valid email to avoid extra null emails.
    eligible_for_dup = [
        i for i in range(len(result)) if i not in null_email_indices
    ]
    dup_source_indices = rng.sample(eligible_for_dup, defects.duplicate_customer_ids)
    for idx in dup_source_indices:
        duplicate_row = dict(result[idx])
        result.append(duplicate_row)

    return result


def inject_product_supplementary_defects(
    products: list[dict[str, Any]],
    rng: Random,
    count: int,
) -> set[int]:
    """Inject business-logic defects (price below cost) on clean product rows."""
    if count <= 0:
        return set()
    if count > len(products):
        raise DataGenerationValidationError(
            f"Cannot inject {count} product supplementary defects into {len(products)} rows"
        )
    logger.info(
        "Injecting supplementary product defects: %d rows with cost > price",
        count,
    )
    indices = rng.sample(range(len(products)), count)
    affected_ids: set[int] = set()
    for idx in indices:
        price = float(products[idx]["price"])
        products[idx]["cost"] = _format_decimal(price + 10.0)
        affected_ids.add(int(products[idx]["product_id"]))
    return affected_ids


def generate_products(rng: Random, count: int) -> list[dict[str, Any]]:
    """Generate clean product records with no intentional defects."""
    logger.info("Generating %d product records (no intentional defects)", count)
    products: list[dict[str, Any]] = []

    for product_id in range(1, count + 1):
        category = rng.choice(CATEGORIES)
        adjective = rng.choice(PRODUCT_ADJECTIVES)
        price = round(rng.uniform(5.0, 499.99), 2)
        cost = round(price * rng.uniform(0.35, 0.75), 2)
        stock = rng.randint(10, 2_000)
        products.append(
            {
                "product_id": product_id,
                "product_name": f"{adjective} {category} Item {product_id}",
                "category": category,
                "price": _format_decimal(price),
                "cost": _format_decimal(cost),
                "stock_quantity": stock,
                "reorder_level": max(5, stock // 10),
            }
        )
    return products


def generate_orders(
    rng: Random,
    count: int,
    customer_ids: range,
    products: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate clean order records with valid FKs and consistent amounts."""
    logger.info("Generating %d base order records", count)
    product_by_id = {int(p["product_id"]): p for p in products}
    order_start = date(2023, 1, 1)
    order_end = date(2025, 6, 30)
    orders: list[dict[str, Any]] = []

    for order_id in range(1, count + 1):
        customer_id = rng.choice(list(customer_ids))
        product_id = rng.choice(list(product_by_id))
        product = product_by_id[product_id]
        quantity = rng.randint(1, 5)
        unit_price = float(product["price"])
        total_amount = round(quantity * unit_price, 2)
        order_date = _random_date(rng, order_start, order_end)
        status = rng.choices(
            ORDER_STATUSES,
            weights=(55, 15, 15, 10, 5),
            k=1,
        )[0]
        payment_date = _payment_date_for_status(rng, order_date, status)

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": order_date.isoformat(),
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": _format_decimal(unit_price),
                "total_amount": _format_decimal(total_amount),
                "order_status": status,
                "payment_date": payment_date,
            }
        )
    return orders


def _payment_date_for_status(rng: Random, order_date: date, status: str) -> str:
    """Return payment_date string or empty for NULL based on order status."""
    if status in ("Pending", "Cancelled"):
        return ""
    lag_days = rng.randint(0, 7)
    return (order_date + timedelta(days=lag_days)).isoformat()


def inject_order_defects(
    orders: list[dict[str, Any]],
    rng: Random,
    defects: DefectCounts,
    valid_customer_ids: range,
    valid_product_ids: range,
) -> list[dict[str, Any]]:
    """Inject NULL FKs, invalid FKs, and duplicate order_id rows."""
    total_defect_slots = (
        defects.null_customer_id
        + defects.null_product_id
        + defects.invalid_customer_id
        + defects.invalid_product_id
    )
    logger.info(
        "Injecting order defects: %d NULL customer_id, %d NULL product_id, "
        "%d invalid customer_id, %d invalid product_id, %d duplicate order_id rows",
        defects.null_customer_id,
        defects.null_product_id,
        defects.invalid_customer_id,
        defects.invalid_product_id,
        defects.duplicate_order_ids,
    )

    result = [dict(row) for row in orders]
    base_count = len(result)
    all_indices = list(range(base_count))
    chosen = rng.sample(all_indices, total_defect_slots)

    offset = 0
    null_customer_indices = set(chosen[offset : offset + defects.null_customer_id])
    offset += defects.null_customer_id
    null_product_indices = set(chosen[offset : offset + defects.null_product_id])
    offset += defects.null_product_id
    invalid_customer_indices = set(chosen[offset : offset + defects.invalid_customer_id])
    offset += defects.invalid_customer_id
    invalid_product_indices = set(chosen[offset : offset + defects.invalid_product_id])

    for idx in null_customer_indices:
        result[idx]["customer_id"] = ""

    for idx in null_product_indices:
        result[idx]["product_id"] = ""

    invalid_customer_values = list(
        range(
            INVALID_CUSTOMER_ID_START,
            INVALID_CUSTOMER_ID_START + defects.invalid_customer_id,
        )
    )
    for i, idx in enumerate(sorted(invalid_customer_indices)):
        result[idx]["customer_id"] = invalid_customer_values[i]

    invalid_product_values = list(
        range(
            INVALID_PRODUCT_ID_START,
            INVALID_PRODUCT_ID_START + defects.invalid_product_id,
        )
    )
    for i, idx in enumerate(sorted(invalid_product_indices)):
        result[idx]["product_id"] = invalid_product_values[i]

    # Duplicate order_id rows — source from clean orders only.
    defect_indices = (
        null_customer_indices
        | null_product_indices
        | invalid_customer_indices
        | invalid_product_indices
    )
    clean_indices = [i for i in range(base_count) if i not in defect_indices]
    dup_source_indices = rng.sample(clean_indices, defects.duplicate_order_ids)
    for idx in dup_source_indices:
        result.append(dict(result[idx]))

    return result


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write rows to a CSV file with header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class DataGenerationValidationError(Exception):
    """Raised when generated data fails validation."""


def validate_defect_counts(
    customers: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    defects: DefectCounts,
    customer_count: int,
    product_count: int,
) -> None:
    """Verify exact intentional defect counts; raise on mismatch."""
    logger.info("Validating intentional defect counts")
    errors: list[str] = []

    null_email_count = sum(1 for row in customers if _is_null(row["email"]))
    if null_email_count != defects.null_emails:
        errors.append(
            f"NULL emails: expected {defects.null_emails}, got {null_email_count}"
        )

    dup_customer_extra = _duplicate_extra_row_count(customers, "customer_id")
    if dup_customer_extra != defects.duplicate_customer_ids:
        errors.append(
            f"Duplicate customer_id rows: expected {defects.duplicate_customer_ids} "
            f"extra rows, got {dup_customer_extra}"
        )

    null_customer_count = sum(1 for row in orders if _is_null(row["customer_id"]))
    if null_customer_count != defects.null_customer_id:
        errors.append(
            f"NULL customer_id: expected {defects.null_customer_id}, "
            f"got {null_customer_count}"
        )

    null_product_count = sum(1 for row in orders if _is_null(row["product_id"]))
    if null_product_count != defects.null_product_id:
        errors.append(
            f"NULL product_id: expected {defects.null_product_id}, "
            f"got {null_product_count}"
        )

    valid_customer_set = set(range(1, customer_count + 1))
    invalid_customer_count = sum(
        1
        for row in orders
        if not _is_null(row["customer_id"])
        and int(row["customer_id"]) not in valid_customer_set
    )
    if invalid_customer_count != defects.invalid_customer_id:
        errors.append(
            f"Invalid customer_id: expected {defects.invalid_customer_id}, "
            f"got {invalid_customer_count}"
        )

    valid_product_set = set(range(1, product_count + 1))
    invalid_product_count = sum(
        1
        for row in orders
        if not _is_null(row["product_id"])
        and int(row["product_id"]) not in valid_product_set
    )
    if invalid_product_count != defects.invalid_product_id:
        errors.append(
            f"Invalid product_id: expected {defects.invalid_product_id}, "
            f"got {invalid_product_count}"
        )

    dup_order_extra = _duplicate_extra_row_count(orders, "order_id")
    if dup_order_extra != defects.duplicate_order_ids:
        errors.append(
            f"Duplicate order_id rows: expected {defects.duplicate_order_ids} "
            f"extra rows, got {dup_order_extra}"
        )

    if errors:
        for message in errors:
            logger.error("Validation failed: %s", message)
        raise DataGenerationValidationError(
            "Generated data does not satisfy expected defect counts:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    logger.info("All intentional defect counts verified successfully")


def validate_supplementary_defect_counts(
    products: list[dict[str, Any]],
    supplementary_product_ids: set[int],
    supplementary: SupplementaryDefectCounts,
) -> None:
    """Verify supplementary product business-logic defects were applied as designed."""
    if supplementary.price_below_cost <= 0:
        return
    below_cost = [
        int(row["product_id"])
        for row in products
        if float(row["cost"]) > float(row["price"])
    ]
    if len(below_cost) != supplementary.price_below_cost:
        raise DataGenerationValidationError(
            f"price_below_cost products: expected {supplementary.price_below_cost}, "
            f"got {len(below_cost)}"
        )
    if set(below_cost) != supplementary_product_ids:
        raise DataGenerationValidationError(
            "Supplementary price_below_cost product IDs do not match injected set"
        )
    logger.info(
        "Supplementary product defects verified: %d price_below_cost rows",
        supplementary.price_below_cost,
    )


def validate_no_uncontrolled_issues(
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    defects: DefectCounts,
    customer_count: int,
    product_count: int,
    supplementary_product_ids: set[int] | None = None,
) -> None:
    """Ensure clean rows do not contain unexpected quality problems."""
    logger.info("Validating absence of uncontrolled quality issues")
    errors: list[str] = []
    supplementary_product_ids = supplementary_product_ids or set()

    customer_id_counts = Counter(row["customer_id"] for row in customers)
    twice_customer_ids = [k for k, v in customer_id_counts.items() if v == 2]
    if len(twice_customer_ids) != defects.duplicate_customer_ids:
        errors.append(
            f"expected {defects.duplicate_customer_ids} customer_id values with "
            f"exactly 2 rows, got {len(twice_customer_ids)}"
        )
    if any(v > 2 for v in customer_id_counts.values()):
        errors.append("customer_id appears more than twice (uncontrolled)")

    for i, row in enumerate(customers):
        row_errors: list[str] = []
        if _is_null(row["customer_name"]):
            row_errors.append("null customer_name")
        if _is_null(row["country"]):
            row_errors.append("null country")
        if _is_null(row["signup_date"]):
            row_errors.append("null signup_date")
        if _is_null(row["customer_segment"]):
            row_errors.append("null customer_segment")
        if float(row["lifetime_value"]) < 0:
            row_errors.append("negative lifetime_value")
        if not _is_null(row["email"]) and not EMAIL_PATTERN.match(str(row["email"])):
            row_errors.append("malformed email")
        cid = int(row["customer_id"])
        if cid < 1 or cid > customer_count:
            row_errors.append(f"customer_id out of range: {cid}")
        if row_errors:
            errors.append(f"customer row {i} (id={row['customer_id']}): {row_errors}")

    product_id_counts = Counter(row["product_id"] for row in products)
    if any(v > 1 for v in product_id_counts.values()):
        errors.append("duplicate product_id in products (uncontrolled)")
    for i, row in enumerate(products):
        row_errors: list[str] = []
        product_id = int(row["product_id"])
        is_supplementary = product_id in supplementary_product_ids
        if float(row["price"]) <= 0:
            row_errors.append("non-positive price")
        if float(row["cost"]) < 0:
            row_errors.append("negative cost")
        if int(row["stock_quantity"]) < 0:
            row_errors.append("negative stock_quantity")
        if int(row["reorder_level"]) < 0:
            row_errors.append("negative reorder_level")
        if is_supplementary:
            if float(row["cost"]) <= float(row["price"]):
                row_errors.append("supplementary defect missing: cost must exceed price")
        elif float(row["cost"]) > float(row["price"]):
            row_errors.append("uncontrolled price_below_cost")
        if row_errors:
            errors.append(f"product row {i} (id={row['product_id']}): {row_errors}")

    order_id_counts = Counter(row["order_id"] for row in orders)
    twice_order_ids = [k for k, v in order_id_counts.items() if v == 2]
    if len(twice_order_ids) != defects.duplicate_order_ids:
        errors.append(
            f"expected {defects.duplicate_order_ids} order_id values with "
            f"exactly 2 rows, got {len(twice_order_ids)}"
        )
    if any(v > 2 for v in order_id_counts.values()):
        errors.append("order_id appears more than twice (uncontrolled)")

    for i, row in enumerate(orders):
        row_errors: list[str] = []
        qty = int(row["quantity"])
        unit_price = float(row["unit_price"])
        total = float(row["total_amount"])
        if qty <= 0:
            row_errors.append("non-positive quantity")
        if unit_price <= 0:
            row_errors.append("non-positive unit_price")
        if abs(total - round(qty * unit_price, 2)) > 0.01:
            row_errors.append("total_amount mismatch")
        if row["order_status"] not in ORDER_STATUSES:
            row_errors.append("invalid order_status")
        if _is_null(row["order_date"]):
            row_errors.append("null order_date")

        if row_errors:
            errors.append(f"order row {i} (id={row['order_id']}): {row_errors}")

    if errors:
        for message in errors[:20]:
            logger.error("Uncontrolled issue: %s", message)
        if len(errors) > 20:
            logger.error("... and %d more uncontrolled issues", len(errors) - 20)
        raise DataGenerationValidationError(
            "Uncontrolled quality issues detected in generated data"
        )

    logger.info("No uncontrolled quality issues detected")


def validate_row_counts(
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    config: GenerationConfig,
) -> None:
    """Validate approximate row counts and schema columns."""
    logger.info("Validating row counts and schemas")
    errors: list[str] = []

    expected_customers = config.customer_count + config.defects.duplicate_customer_ids
    if len(customers) != expected_customers:
        errors.append(
            f"customers: expected {expected_customers} rows, got {len(customers)}"
        )
    if len(products) != config.product_count:
        errors.append(
            f"products: expected {config.product_count} rows, got {len(products)}"
        )
    expected_orders = config.order_count + config.defects.duplicate_order_ids
    if len(orders) != expected_orders:
        errors.append(f"orders: expected {expected_orders} rows, got {len(orders)}")

    for name, rows, columns in (
        ("customers", customers, CUSTOMER_COLUMNS),
        ("products", products, PRODUCT_COLUMNS),
        ("orders", orders, ORDER_COLUMNS),
    ):
        if rows and set(rows[0].keys()) != set(columns):
            errors.append(f"{name}: column mismatch, expected {columns}")

    if errors:
        raise DataGenerationValidationError(
            "Row count / schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    logger.info(
        "Row counts: customers=%d, products=%d, orders=%d",
        len(customers),
        len(products),
        len(orders),
    )


def validate_generated_data(
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    orders: list[dict[str, Any]],
    config: GenerationConfig,
    supplementary_product_ids: set[int] | None = None,
) -> None:
    """Run all validation checks; raise DataGenerationValidationError on failure."""
    supplementary_product_ids = supplementary_product_ids or set()
    validate_row_counts(customers, products, orders, config)
    validate_defect_counts(
        customers,
        orders,
        config.defects,
        config.customer_count,
        config.product_count,
    )
    validate_supplementary_defect_counts(
        products,
        supplementary_product_ids,
        config.supplementary,
    )
    validate_no_uncontrolled_issues(
        customers,
        products,
        orders,
        config.defects,
        config.customer_count,
        config.product_count,
        supplementary_product_ids,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_all(config: GenerationConfig) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    """Generate customers, products, and orders with intentional defects."""
    rng = Random(config.seed)
    logger.info("Starting data generation with seed=%d", config.seed)

    customers = generate_customers(rng, config.customer_count)
    customers = inject_customer_defects(customers, rng, config.defects)

    products = generate_products(rng, config.product_count)

    customer_id_range = range(1, config.customer_count + 1)
    orders = generate_orders(rng, config.order_count, customer_id_range, products)
    orders = inject_order_defects(
        orders,
        rng,
        config.defects,
        customer_id_range,
        range(1, config.product_count + 1),
    )

    supplementary_product_ids = inject_product_supplementary_defects(
        products,
        rng,
        config.supplementary.price_below_cost,
    )

    validate_generated_data(
        customers,
        products,
        orders,
        config,
        supplementary_product_ids,
    )
    return customers, products, orders


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    setup_logging()
    config = parse_args(argv)

    try:
        customers, products, orders = generate_all(config)

        write_csv(config.output_dir / "customers.csv", customers, CUSTOMER_COLUMNS)
        write_csv(config.output_dir / "products.csv", products, PRODUCT_COLUMNS)
        write_csv(config.output_dir / "orders.csv", orders, ORDER_COLUMNS)

        logger.info("Data generation completed successfully")
        return 0
    except DataGenerationValidationError:
        logger.error("Data generation failed validation", exc_info=True)
        return 1
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        logger.error("Data generation failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    # Pass empty argv to use defaults when running in Databricks
    # Don't use sys.exit() in Databricks - just call main() directly
    main(argv=[])
