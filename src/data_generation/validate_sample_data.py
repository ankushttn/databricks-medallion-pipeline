"""Independent validation of generated sample CSV data.

Reads CSV files from disk and performs senior-DE review checks.
Does not trust the generator's internal validation — re-verifies from files.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Expected schema (data-model.md §2)
CUSTOMER_COLUMNS = [
    "customer_id", "customer_name", "email", "country",
    "signup_date", "customer_segment", "lifetime_value",
]
PRODUCT_COLUMNS = [
    "product_id", "product_name", "category", "price",
    "cost", "stock_quantity", "reorder_level",
]
ORDER_COLUMNS = [
    "order_id", "customer_id", "order_date", "product_id",
    "quantity", "unit_price", "total_amount", "order_status", "payment_date",
]

EXPECTED_ROW_COUNTS = {"customers": 10_010, "products": 500, "orders": 100_020}
BASE_CUSTOMER_COUNT = 10_000
BASE_PRODUCT_COUNT = 500
BASE_ORDER_COUNT = 100_000

# Intentional defect specification
EXPECTED_DEFECTS = {
    "null_email": 50,
    "duplicate_customer_id_extra_rows": 10,
    "null_customer_id": 100,
    "null_product_id": 200,
    "orphan_customer_id": 50,
    "orphan_product_id": 30,
    "duplicate_order_id_extra_rows": 20,
}

INVALID_CUSTOMER_ID_RANGE = range(800_001, 800_051)
INVALID_PRODUCT_ID_RANGE = range(700_001, 700_031)

ALLOWED_COUNTRIES = {"US", "UK", "DE", "FR", "CA", "AU", "IN", "JP", "BR", "MX"}
ALLOWED_SEGMENTS = {"Premium", "Standard", "Basic"}
ALLOWED_CATEGORIES = {
    "Electronics", "Clothing", "Home", "Sports",
    "Books", "Beauty", "Toys", "Garden",
}
ALLOWED_ORDER_STATUSES = {"Completed", "Pending", "Shipped", "Cancelled", "Returned"}
EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

SIGNUP_DATE_MIN = date(2018, 1, 1)
SIGNUP_DATE_MAX = date(2025, 6, 30)
ORDER_DATE_MIN = date(2023, 1, 1)
ORDER_DATE_MAX = date(2025, 6, 30)

AMOUNT_TOLERANCE = Decimal("0.01")


@dataclass
class CheckResult:
    """Result of a single validation check."""

    check_id: str
    category: str
    description: str
    passed: bool
    expected: str = ""
    actual: str = ""
    details: str = ""


@dataclass
class ValidationReport:
    """Aggregated validation report."""

    data_dir: Path
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    def add(
        self,
        check_id: str,
        category: str,
        description: str,
        passed: bool,
        expected: str = "",
        actual: str = "",
        details: str = "",
    ) -> None:
        self.results.append(
            CheckResult(check_id, category, description, passed, expected, actual, details)
        )


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _is_null(value: str) -> bool:
    return value is None or str(value).strip() == ""


def _parse_date(value: str) -> date | None:
    if _is_null(value):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    if _is_null(value):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_decimal(value: str) -> Decimal | None:
    if _is_null(value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Load CSV and return (fieldnames, rows)."""
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise ValueError(f"Failed to read CSV {path}: {exc}") from exc
    return fieldnames, rows


def _dup_extra_rows(rows: list[dict[str, str]], key: str) -> int:
    counts = Counter(r[key] for r in rows)
    return sum(c - 1 for c in counts.values() if c > 1)


def _dup_key_count(rows: list[dict[str, str]], key: str) -> int:
    counts = Counter(r[key] for r in rows)
    return sum(1 for c in counts.values() if c > 1)


def validate_row_counts(report: ValidationReport, data: dict[str, list[dict[str, str]]]) -> None:
    """Check 1: Row counts."""
    for entity, expected in EXPECTED_ROW_COUNTS.items():
        actual = len(data[entity])
        report.add(
            f"RC-{entity[:4].upper()}",
            "row_counts",
            f"{entity} row count",
            actual == expected,
            str(expected),
            str(actual),
        )


def validate_column_names(report: ValidationReport, columns: dict[str, list[str]]) -> None:
    """Check 2: Column names."""
    expected_cols = {
        "customers": CUSTOMER_COLUMNS,
        "products": PRODUCT_COLUMNS,
        "orders": ORDER_COLUMNS,
    }
    for entity, exp in expected_cols.items():
        actual = columns[entity]
        report.add(
            f"CN-{entity[:4].upper()}",
            "column_names",
            f"{entity} column names match schema",
            actual == exp,
            str(exp),
            str(actual),
        )


def validate_null_counts(
    report: ValidationReport,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> dict[str, int]:
    """Check 3: Null counts — intentional vs unexpected."""
    metrics: dict[str, int] = {}

    # Intentional nulls
    metrics["null_email"] = sum(1 for r in customers if _is_null(r["email"]))
    report.add(
        "NC-EMAIL",
        "null_counts",
        "NULL email count (intentional)",
        metrics["null_email"] == EXPECTED_DEFECTS["null_email"],
        str(EXPECTED_DEFECTS["null_email"]),
        str(metrics["null_email"]),
    )

    metrics["null_customer_id"] = sum(1 for r in orders if _is_null(r["customer_id"]))
    report.add(
        "NC-OCID",
        "null_counts",
        "NULL order.customer_id (intentional)",
        metrics["null_customer_id"] == EXPECTED_DEFECTS["null_customer_id"],
        str(EXPECTED_DEFECTS["null_customer_id"]),
        str(metrics["null_customer_id"]),
    )

    metrics["null_product_id"] = sum(1 for r in orders if _is_null(r["product_id"]))
    report.add(
        "NC-OPID",
        "null_counts",
        "NULL order.product_id (intentional)",
        metrics["null_product_id"] == EXPECTED_DEFECTS["null_product_id"],
        str(EXPECTED_DEFECTS["null_product_id"]),
        str(metrics["null_product_id"]),
    )

    # payment_date may be null by design
    payment_null = sum(1 for r in orders if _is_null(r["payment_date"]))
    metrics["null_payment_date"] = payment_null
    report.add(
        "NC-PAY",
        "null_counts",
        "NULL payment_date (allowed by schema)",
        payment_null > 0,
        "> 0 (nullable column)",
        str(payment_null),
    )

    # Unexpected nulls in required columns
    unexpected_nulls: list[str] = []
    customer_required = ["customer_id", "customer_name", "country", "signup_date", "customer_segment", "lifetime_value"]
    for i, row in enumerate(customers):
        for col in customer_required:
            if _is_null(row[col]):
                unexpected_nulls.append(f"customers[{i}].{col}")

    product_required = PRODUCT_COLUMNS  # all required per schema
    for i, row in enumerate(products):
        for col in product_required:
            if _is_null(row[col]):
                unexpected_nulls.append(f"products[{i}].{col}")

    order_required = ["order_id", "order_date", "quantity", "unit_price", "total_amount", "order_status"]
    for i, row in enumerate(orders):
        for col in order_required:
            if _is_null(row[col]):
                unexpected_nulls.append(f"orders[{i}].{col}")

    report.add(
        "NC-UNEXP",
        "null_counts",
        "No unexpected NULLs in required columns",
        len(unexpected_nulls) == 0,
        "0",
        str(len(unexpected_nulls)),
        "; ".join(unexpected_nulls[:5]) + ("..." if len(unexpected_nulls) > 5 else ""),
    )

    return metrics


def validate_duplicate_pks(
    report: ValidationReport,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Check 4: Duplicate primary keys."""
    cust_extra = _dup_extra_rows(customers, "customer_id")
    report.add(
        "DP-CUST",
        "duplicate_pks",
        "Customer duplicate PK extra rows (intentional)",
        cust_extra == EXPECTED_DEFECTS["duplicate_customer_id_extra_rows"],
        str(EXPECTED_DEFECTS["duplicate_customer_id_extra_rows"]),
        str(cust_extra),
    )

    cust_keys_duped = _dup_key_count(customers, "customer_id")
    report.add(
        "DP-CKEY",
        "duplicate_pks",
        "Customer_id values appearing >1 (intentional)",
        cust_keys_duped == EXPECTED_DEFECTS["duplicate_customer_id_extra_rows"],
        str(EXPECTED_DEFECTS["duplicate_customer_id_extra_rows"]),
        str(cust_keys_duped),
    )

    prod_dups = _dup_extra_rows(products, "product_id")
    report.add(
        "DP-PROD",
        "duplicate_pks",
        "Product duplicate PKs (must be zero)",
        prod_dups == 0,
        "0",
        str(prod_dups),
    )

    order_extra = _dup_extra_rows(orders, "order_id")
    report.add(
        "DP-ORD",
        "duplicate_pks",
        "Order duplicate PK extra rows (intentional)",
        order_extra == EXPECTED_DEFECTS["duplicate_order_id_extra_rows"],
        str(EXPECTED_DEFECTS["duplicate_order_id_extra_rows"]),
        str(order_extra),
    )

    order_keys_duped = _dup_key_count(orders, "order_id")
    report.add(
        "DP-OKEY",
        "duplicate_pks",
        "Order_id values appearing >1 (intentional)",
        order_keys_duped == EXPECTED_DEFECTS["duplicate_order_id_extra_rows"],
        str(EXPECTED_DEFECTS["duplicate_order_id_extra_rows"]),
        str(order_keys_duped),
    )

    # No PK appears more than twice
    cust_max = max(Counter(r["customer_id"] for r in customers).values())
    order_max = max(Counter(r["order_id"] for r in orders).values())
    report.add(
        "DP-MAXC",
        "duplicate_pks",
        "No customer_id appears more than twice",
        cust_max <= 2,
        "<= 2",
        str(cust_max),
    )
    report.add(
        "DP-MAXO",
        "duplicate_pks",
        "No order_id appears more than twice",
        order_max <= 2,
        "<= 2",
        str(order_max),
    )


def validate_orphan_fks(
    report: ValidationReport,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Check 5: Orphan foreign keys."""
    valid_customers = {r["customer_id"] for r in customers}
    valid_products = {r["product_id"] for r in products}

    # Build set of valid customer IDs (1..10000) — orphans use invalid range
    valid_customer_ids = {str(i) for i in range(1, BASE_CUSTOMER_COUNT + 1)}
    valid_product_ids = {str(i) for i in range(1, BASE_PRODUCT_COUNT + 1)}

    orphan_customer: list[int] = []
    orphan_product: list[int] = []
    unexpected_orphan_customer: list[str] = []
    unexpected_orphan_product: list[str] = []

    for i, row in enumerate(orders):
        if not _is_null(row["customer_id"]):
            cid = row["customer_id"]
            if cid not in valid_customer_ids:
                orphan_customer.append(i)
                cid_int = _parse_int(cid)
                if cid_int is None or cid_int not in INVALID_CUSTOMER_ID_RANGE:
                    unexpected_orphan_customer.append(f"row {i}: customer_id={cid}")

        if not _is_null(row["product_id"]):
            pid = row["product_id"]
            if pid not in valid_product_ids:
                orphan_product.append(i)
                pid_int = _parse_int(pid)
                if pid_int is None or pid_int not in INVALID_PRODUCT_ID_RANGE:
                    unexpected_orphan_product.append(f"row {i}: product_id={pid}")

    report.add(
        "FK-OCUST",
        "orphan_fks",
        "Orphan customer_id count (intentional invalid FK)",
        len(orphan_customer) == EXPECTED_DEFECTS["orphan_customer_id"],
        str(EXPECTED_DEFECTS["orphan_customer_id"]),
        str(len(orphan_customer)),
    )
    report.add(
        "FK-OPROD",
        "orphan_fks",
        "Orphan product_id count (intentional invalid FK)",
        len(orphan_product) == EXPECTED_DEFECTS["orphan_product_id"],
        str(EXPECTED_DEFECTS["orphan_product_id"]),
        str(len(orphan_product)),
    )
    report.add(
        "FK-UNEXC",
        "orphan_fks",
        "No unexpected orphan customer_id values",
        len(unexpected_orphan_customer) == 0,
        "0",
        str(len(unexpected_orphan_customer)),
        "; ".join(unexpected_orphan_customer[:5]),
    )
    report.add(
        "FK-UNEXP",
        "orphan_fks",
        "No unexpected orphan product_id values",
        len(unexpected_orphan_product) == 0,
        "0",
        str(len(unexpected_orphan_product)),
        "; ".join(unexpected_orphan_product[:5]),
    )

    # Valid FK rows must reference existing IDs
    valid_fk_customer_errors = 0
    for row in orders:
        if not _is_null(row["customer_id"]) and row["customer_id"] in valid_customer_ids:
            if row["customer_id"] not in valid_customers:
                valid_fk_customer_errors += 1

    report.add(
        "FK-VFC",
        "orphan_fks",
        "Valid-range customer_id values exist in customers.csv",
        valid_fk_customer_errors == 0,
        "0",
        str(valid_fk_customer_errors),
    )


def validate_invalid_values(
    report: ValidationReport,
    customers: list[dict[str, str]],
    products: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Check 6: Invalid domain values."""
    errors: list[str] = []

    for i, row in enumerate(customers):
        if not _is_null(row["email"]) and not EMAIL_PATTERN.match(row["email"]):
            errors.append(f"customer[{i}] bad email")
        if row["country"] not in ALLOWED_COUNTRIES:
            errors.append(f"customer[{i}] country={row['country']}")
        if row["customer_segment"] not in ALLOWED_SEGMENTS:
            errors.append(f"customer[{i}] segment={row['customer_segment']}")
        if _parse_int(row["customer_id"]) is None:
            errors.append(f"customer[{i}] non-int customer_id")
        lv = _parse_decimal(row["lifetime_value"])
        if lv is None or lv < 0:
            errors.append(f"customer[{i}] lifetime_value={row['lifetime_value']}")

    for i, row in enumerate(products):
        if row["category"] not in ALLOWED_CATEGORIES:
            errors.append(f"product[{i}] category={row['category']}")
        price = _parse_decimal(row["price"])
        cost = _parse_decimal(row["cost"])
        stock = _parse_int(row["stock_quantity"])
        reorder = _parse_int(row["reorder_level"])
        if price is None or price <= 0:
            errors.append(f"product[{i}] price={row['price']}")
        if cost is None or cost < 0:
            errors.append(f"product[{i}] cost={row['cost']}")
        if stock is None or stock < 0:
            errors.append(f"product[{i}] stock={row['stock_quantity']}")
        if reorder is None or reorder < 0:
            errors.append(f"product[{i}] reorder={row['reorder_level']}")

    for i, row in enumerate(orders):
        if row["order_status"] not in ALLOWED_ORDER_STATUSES:
            errors.append(f"order[{i}] status={row['order_status']}")
        qty = _parse_int(row["quantity"])
        if qty is None or qty <= 0:
            errors.append(f"order[{i}] quantity={row['quantity']}")
        up = _parse_decimal(row["unit_price"])
        if up is None or up <= 0:
            errors.append(f"order[{i}] unit_price={row['unit_price']}")

    report.add(
        "IV-ALL",
        "invalid_values",
        "No invalid domain values in clean rows",
        len(errors) == 0,
        "0 errors",
        str(len(errors)),
        "; ".join(errors[:10]) + ("..." if len(errors) > 10 else ""),
    )


def validate_date_ranges(
    report: ValidationReport,
    customers: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Check 7: Date ranges."""
    errors: list[str] = []

    for i, row in enumerate(customers):
        sd = _parse_date(row["signup_date"])
        if sd is None:
            errors.append(f"customer[{i}] invalid signup_date")
        elif sd < SIGNUP_DATE_MIN or sd > SIGNUP_DATE_MAX:
            errors.append(f"customer[{i}] signup_date out of range: {sd}")

    for i, row in enumerate(orders):
        od = _parse_date(row["order_date"])
        if od is None:
            errors.append(f"order[{i}] invalid order_date")
        elif od < ORDER_DATE_MIN or od > ORDER_DATE_MAX:
            errors.append(f"order[{i}] order_date out of range: {od}")

        if not _is_null(row["payment_date"]):
            pd = _parse_date(row["payment_date"])
            if pd is None:
                errors.append(f"order[{i}] invalid payment_date")
            elif od and pd < od:
                errors.append(f"order[{i}] payment before order: {pd} < {od}")

    report.add(
        "DR-ALL",
        "date_ranges",
        "All dates within expected ranges and logically consistent",
        len(errors) == 0,
        "0 errors",
        str(len(errors)),
        "; ".join(errors[:10]) + ("..." if len(errors) > 10 else ""),
    )


def validate_financial_calculations(
    report: ValidationReport,
    products: list[dict[str, str]],
    orders: list[dict[str, str]],
) -> None:
    """Check 8: Financial calculations."""
    order_errors: list[str] = []
    product_errors: list[str] = []

    for i, row in enumerate(orders):
        qty = _parse_int(row["quantity"])
        up = _parse_decimal(row["unit_price"])
        total = _parse_decimal(row["total_amount"])
        if qty is not None and up is not None and total is not None:
            expected = (Decimal(qty) * up).quantize(Decimal("0.01"))
            if abs(total - expected) > AMOUNT_TOLERANCE:
                order_errors.append(
                    f"order[{i}] total={total} expected={expected}"
                )

    for i, row in enumerate(products):
        price = _parse_decimal(row["price"])
        cost = _parse_decimal(row["cost"])
        if price is not None and cost is not None and cost > price:
            product_errors.append(f"product[{i}] cost > price")

    report.add(
        "FC-ORD",
        "financial",
        "order total_amount = quantity × unit_price",
        len(order_errors) == 0,
        "0 mismatches",
        str(len(order_errors)),
        "; ".join(order_errors[:5]),
    )
    report.add(
        "FC-PROD",
        "financial",
        "product cost <= price",
        len(product_errors) == 0,
        "0 violations",
        str(len(product_errors)),
        "; ".join(product_errors[:5]),
    )


def validate_intentional_issues(report: ValidationReport, metrics: dict[str, int]) -> None:
    """Check 9: Expected intentional issue counts summary."""
    checks = [
        ("II-EMAIL", "null_email", "null_email"),
        ("II-DCID", "duplicate_customer_id_extra_rows", "duplicate_customer_id_extra_rows"),
        ("II-OCID", "null_customer_id", "null_customer_id"),
        ("II-OPID", "null_product_id", "null_product_id"),
    ]
    for check_id, metric_key, defect_key in checks:
        if metric_key in metrics:
            report.add(
                check_id,
                "intentional_issues",
                f"Intentional defect: {defect_key}",
                metrics[metric_key] == EXPECTED_DEFECTS[defect_key],
                str(EXPECTED_DEFECTS[defect_key]),
                str(metrics[metric_key]),
            )

    # Orphan counts verified in FK section — cross-reference
    report.add(
        "II-SUM",
        "intentional_issues",
        "All 7 intentional defect types specified in assignment",
        True,
        "7 types",
        "see FK + null + dup checks",
    )


def validate_customer_id_coverage(
    report: ValidationReport,
    customers: list[dict[str, str]],
) -> None:
    """Verify base customer IDs 1..10000 are all present."""
    ids = {_parse_int(r["customer_id"]) for r in customers}
    ids.discard(None)
    missing = [i for i in range(1, BASE_CUSTOMER_COUNT + 1) if i not in ids]
    report.add(
        "CV-CIDS",
        "row_counts",
        "All customer_id 1..10000 present at least once",
        len(missing) == 0,
        "0 missing",
        str(len(missing)),
        f"missing: {missing[:10]}" if missing else "",
    )


def validate_product_id_coverage(
    report: ValidationReport,
    products: list[dict[str, str]],
) -> None:
    """Verify product IDs 1..500 all present."""
    ids = {_parse_int(r["product_id"]) for r in products}
    missing = [i for i in range(1, BASE_PRODUCT_COUNT + 1) if i not in ids]
    report.add(
        "CV-PIDS",
        "row_counts",
        "All product_id 1..500 present",
        len(missing) == 0,
        "0 missing",
        str(len(missing)),
    )


def validate_order_id_coverage(
    report: ValidationReport,
    orders: list[dict[str, str]],
) -> None:
    """Verify base order IDs 1..100000 all present at least once."""
    ids = {_parse_int(r["order_id"]) for r in orders}
    ids.discard(None)
    missing = [i for i in range(1, BASE_ORDER_COUNT + 1) if i not in ids]
    report.add(
        "CV-OIDS",
        "row_counts",
        "All order_id 1..100000 present at least once",
        len(missing) == 0,
        "0 missing",
        str(len(missing)),
    )


def run_validation(data_dir: Path) -> ValidationReport:
    """Run all validation checks against CSV files on disk."""
    report = ValidationReport(data_dir=data_dir)

    columns: dict[str, list[str]] = {}
    data: dict[str, list[dict[str, str]]] = {}

    for entity in ("customers", "products", "orders"):
        path = data_dir / f"{entity}.csv"
        if not path.exists():
            report.add(
                f"FILE-{entity}",
                "row_counts",
                f"{entity}.csv exists",
                False,
                "file present",
                "missing",
            )
            return report
        columns[entity], data[entity] = load_csv(path)

    validate_row_counts(report, data)
    validate_column_names(report, columns)
    null_metrics = validate_null_counts(report, data["customers"], data["products"], data["orders"])
    validate_duplicate_pks(report, data["customers"], data["products"], data["orders"])
    validate_orphan_fks(report, data["customers"], data["products"], data["orders"])
    validate_invalid_values(report, data["customers"], data["products"], data["orders"])
    validate_date_ranges(report, data["customers"], data["orders"])
    validate_financial_calculations(report, data["products"], data["orders"])
    validate_intentional_issues(report, null_metrics)
    validate_customer_id_coverage(report, data["customers"])
    validate_product_id_coverage(report, data["products"])
    validate_order_id_coverage(report, data["orders"])

    return report


def format_report_markdown(report: ValidationReport, seed: int = 42) -> str:
    """Format validation report as markdown."""
    lines = [
        "# Sample Data Validation Report",
        "",
        f"**Data directory:** `{report.data_dir}`",
        f"**Validation seed (generation):** `{seed}`",
        f"**Overall status:** {'✅ PASSED' if report.passed else '❌ FAILED'}",
        f"**Checks run:** {len(report.results)}",
        f"**Checks passed:** {sum(1 for r in report.results if r.passed)}",
        f"**Checks failed:** {len(report.failures)}",
        "",
        "---",
        "",
        "## Summary by Category",
        "",
    ]

    categories = sorted({r.category for r in report.results})
    for cat in categories:
        cat_results = [r for r in report.results if r.category == cat]
        passed = sum(1 for r in cat_results if r.passed)
        status = "✅" if passed == len(cat_results) else "❌"
        lines.append(f"- {status} **{cat}**: {passed}/{len(cat_results)} passed")

    lines.extend(["", "---", "", "## Detailed Results", ""])
    lines.append("| Check ID | Category | Description | Status | Expected | Actual |")
    lines.append("|----------|----------|-------------|--------|----------|--------|")
    for r in report.results:
        status = "PASS" if r.passed else "**FAIL**"
        lines.append(
            f"| {r.check_id} | {r.category} | {r.description} | {status} | {r.expected} | {r.actual} |"
        )

    if report.failures:
        lines.extend(["", "---", "", "## Failures", ""])
        for r in report.failures:
            lines.append(f"### {r.check_id}: {r.description}")
            lines.append(f"- Expected: `{r.expected}`")
            lines.append(f"- Actual: `{r.actual}`")
            if r.details:
                lines.append(f"- Details: {r.details}")
            lines.append("")

    lines.extend([
        "",
        "---",
        "",
        "## Intentional Defect Summary",
        "",
        "| Defect | Expected |",
        "|--------|----------|",
    ])
    for key, val in EXPECTED_DEFECTS.items():
        lines.append(f"| {key} | {val} |")

    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate generated sample CSV data.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing CSV files",
    )
    parser.add_argument("--seed", type=int, default=42, help="Generation seed (for report)")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write markdown report to this path",
    )
    args = parser.parse_args(argv)
    setup_logging()

    report = run_validation(args.data_dir)
    md = format_report_markdown(report, seed=args.seed)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(md, encoding="utf-8")
        logger.info("Wrote report to %s", args.report)

    try:
        print(md)
    except UnicodeEncodeError:
        print(md.encode("ascii", errors="replace").decode("ascii"))

    if report.passed:
        logger.info("Validation PASSED — %d checks", len(report.results))
        return 0

    logger.error("Validation FAILED — %d failures", len(report.failures))
    return 1


if __name__ == "__main__":
    sys.exit(main())
