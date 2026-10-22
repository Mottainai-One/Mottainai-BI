# Databricks notebook source
"""Check both PostgreSQL foreign catalogs and prepare the managed BI schemas."""

import re


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid Unity Catalog identifier: {value!r}")
    return value


for name in ("operational_catalog", "analytics_catalog", "target_catalog"):
    dbutils.widgets.text(name, "")

operational = identifier(dbutils.widgets.get("operational_catalog"))
analytics = identifier(dbutils.widgets.get("analytics_catalog"))
target = identifier(dbutils.widgets.get("target_catalog"))

if operational == analytics:
    raise ValueError("Operational and analytical foreign catalogs must be distinct")
if target in (operational, analytics):
    raise ValueError("Managed BI tables cannot be created in a foreign catalog")

# The operational catalog is checked only. No BI data is ingested from it.
operational_count = spark.sql(
    f"SELECT count(*) AS rows_total FROM `{operational}`.`mottainai`.`company`"
).first()["rows_total"]
print(f"Operational connection OK; company rows: {operational_count}")

source_schema = f"`{analytics}`.`mottainai_analytics`"
batch_rows = spark.sql(
    f"SELECT batch_id, source_cutoff_at, published_at "
    f"FROM {source_schema}.`vw_published_batch`"
).collect()
if len(batch_rows) > 1:
    raise RuntimeError("vw_published_batch must expose at most one current publication")

for relation in ("vw_sales_daily_kpis", "vw_monthly_summary", "vw_critical_stock"):
    spark.sql(f"SELECT * FROM {source_schema}.`{relation}` LIMIT 0").collect()
print(f"Analytics connection OK; published batch rows: {len(batch_rows)}")

for schema in ("mottainai_bronze", "mottainai_silver", "mottainai_gold", "mottainai_control"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{target}`.`{schema}`")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS `{target}`.`mottainai_control`.`publication` (
  pipeline STRING,
  batch_id STRING,
  source_cutoff_at TIMESTAMP,
  source_published_at TIMESTAMP,
  refreshed_at TIMESTAMP
) USING DELTA
""")
print("BI schemas and publication control are ready")
