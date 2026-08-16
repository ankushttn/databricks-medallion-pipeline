"""Shared helpers for building declarative quality checks."""

from __future__ import annotations

from pyspark.sql import Column
from pyspark.sql import functions as F

from silver.quality_framework import QualityCheck, is_null_or_blank


def completeness_check(
    check_id: str,
    column: str,
    *,
    display_name: str | None = None,
) -> QualityCheck:
    """Build a null-or-blank completeness check for a column."""
    label = display_name or column
    return QualityCheck(
        check_id=check_id,
        check_name=f"{label} completeness",
        dimension="completeness",
        issue_code=f"completeness:{column}_null",
        failure_reason=f"{label} is null or blank",
        fail_condition=is_null_or_blank(F.col(column)),
    )


def typed_null_check(
    check_id: str,
    column: str,
    data_type: str,
) -> QualityCheck:
    """Flag null values on typed columns (unparseable or missing typed value)."""
    return QualityCheck(
        check_id=check_id,
        check_name=f"{column} {data_type} validation",
        dimension="type_validation",
        issue_code=f"type:{column}_invalid",
        failure_reason=f"{column} is not a valid {data_type}",
        fail_condition=F.col(column).isNull(),
    )


def allowed_values_check(
    check_id: str,
    column: str,
    allowed_values: frozenset[str],
    *,
    dimension: str = "type_validation",
    issue_prefix: str = "type",
) -> QualityCheck:
    """Flag values outside an allowed set when the column is present."""
    return QualityCheck(
        check_id=check_id,
        check_name=f"{column} allowed values",
        dimension=dimension,
        issue_code=f"{issue_prefix}:{column}_invalid",
        failure_reason=f"{column} is not in the allowed value set",
        fail_condition=(~is_null_or_blank(F.col(column)))
        & (~F.col(column).isin(*sorted(allowed_values))),
    )


def email_format_check(check_id: str = "TYP-CUST-004") -> QualityCheck:
    """Validate basic email format when email is present."""
    email = F.col("email")
    invalid = (~is_null_or_blank(email)) & (
        ~email.rlike(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    )
    return QualityCheck(
        check_id=check_id,
        check_name="email format validation",
        dimension="type_validation",
        issue_code="type:email_format_invalid",
        failure_reason="email is present but malformed",
        fail_condition=invalid,
    )


def uniqueness_check(
    check_id: str,
    pk_column: str,
    entity_label: str,
) -> QualityCheck:
    """Flag all rows participating in a duplicated primary key."""
    return QualityCheck(
        check_id=check_id,
        check_name=f"{entity_label} primary key uniqueness",
        dimension="uniqueness",
        issue_code=f"uniqueness:duplicate_{pk_column}",
        failure_reason=f"duplicate {pk_column} detected",
        fail_condition=(F.col("_pk_dup_count") > 1) & F.col(pk_column).isNotNull(),
    )


def referential_check(
    check_id: str,
    fk_column: str,
    ref_exists_column: str,
    parent_entity: str,
) -> QualityCheck:
    """Flag non-null foreign keys that do not resolve to a parent row."""
    return QualityCheck(
        check_id=check_id,
        check_name=f"{fk_column} referential integrity",
        dimension="referential_integrity",
        issue_code=f"referential:invalid_{fk_column}",
        failure_reason=f"{fk_column} does not exist in {parent_entity}",
        fail_condition=F.col(fk_column).isNotNull() & (~F.col(ref_exists_column)),
    )


def business_rule_check(
    check_id: str,
    check_name: str,
    issue_code: str,
    fail_condition: Column,
    *,
    applies_when: Column | None = None,
    failure_reason: str,
) -> QualityCheck:
    """Build a business-logic quality check."""
    return QualityCheck(
        check_id=check_id,
        check_name=check_name,
        dimension="business_logic",
        issue_code=issue_code,
        failure_reason=failure_reason,
        fail_condition=fail_condition,
        applies_when=applies_when,
    )
