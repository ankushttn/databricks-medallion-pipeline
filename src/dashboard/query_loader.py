"""Load and prepare dashboard SQL queries for local validation or Databricks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

QUERY_HEADER_PATTERN = re.compile(
    r"^--\s*QUERY:\s*(?P<name>[\w_]+)\s*$",
    re.MULTILINE,
)

GOLD_TABLE_REPLACEMENTS = {
    "gold.sales_by_product": "gold_sales_by_product",
    "gold.revenue_by_customer": "gold_revenue_by_customer",
    "gold.daily_weekly_trends": "gold_daily_weekly_trends",
    "gold.customer_segmentation": "gold_customer_segmentation",
}


@dataclass(frozen=True)
class DashboardQuery:
    """One named SELECT statement from dashboard_queries.sql."""

    name: str
    sql: str


def dashboard_sql_path() -> Path:
    return Path(__file__).resolve().parent / "dashboard_queries.sql"


def load_dashboard_queries(path: Path | None = None) -> list[DashboardQuery]:
    """Parse dashboard_queries.sql into named query blocks."""
    sql_file = path or dashboard_sql_path()
    content = sql_file.read_text(encoding="utf-8")
    matches = list(QUERY_HEADER_PATTERN.finditer(content))
    if not matches:
        raise ValueError(f"No dashboard queries found in {sql_file}")

    queries: list[DashboardQuery] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[start:end].strip()
        select_sql = _extract_select_statement(block)
        queries.append(DashboardQuery(name=match.group("name"), sql=select_sql))
    return queries


def _extract_select_statement(block: str) -> str:
    """Return the SELECT statement from a query block (skip header comments)."""
    lines = block.splitlines()
    select_lines: list[str] = []
    in_select = False
    for line in lines:
        stripped = line.strip()
        if not in_select and stripped.upper().startswith("SELECT"):
            in_select = True
        if in_select:
            select_lines.append(line)
    if not select_lines:
        raise ValueError("Query block missing SELECT statement")
    return "\n".join(select_lines).strip().rstrip(";")


def localize_sql(sql: str, catalog: str | None = None, gold_schema: str = "gold") -> str:
    """Replace catalog-qualified Gold table names for local temp views."""
    localized = sql
    if catalog:
        prefix = f"{catalog}.{gold_schema}."
        for table in GOLD_TABLE_REPLACEMENTS:
            localized = localized.replace(f"{prefix}{table.split('.')[1]}", GOLD_TABLE_REPLACEMENTS[table])
    for source, target in GOLD_TABLE_REPLACEMENTS.items():
        localized = localized.replace(source, target)
    return localized
