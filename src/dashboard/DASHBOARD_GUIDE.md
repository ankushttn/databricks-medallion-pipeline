# Dashboard Guide

## Purpose

Connect a BI tool (Databricks SQL Dashboard, Power BI, or similar) to Gold tables for e-commerce KPIs.

## Prerequisites

- Gold tables created via `src/gold/create_gold_tables.py`
- Read access to `gold` schema

## Planned Visualizations

| Dashboard Panel | Source Table / Query | Metric |
|-----------------|----------------------|--------|
| Top Products | `gold.sales_by_product` | Revenue by product |
| Top Customers | `gold.revenue_by_customer` | Revenue by customer |
| Trend Line | `gold.daily_weekly_trends` | Daily/weekly revenue |
| Segment Breakdown | `gold.customer_segmentation` | KPIs by segment |

## Setup Steps

1. Run all Gold SQL scripts.
2. Open `dashboard_queries.sql` in Databricks SQL.
3. Create a dashboard and pin each query as a visualization.
4. Refresh on schedule aligned with pipeline runs.

## Status

_Not implemented — foundation phase only._
