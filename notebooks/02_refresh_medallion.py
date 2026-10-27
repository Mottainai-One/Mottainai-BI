# Databricks notebook source
"""Validate one Bronze batch and atomically expose a business-facing Gold snapshot."""

import re
import uuid

from pyspark.sql import functions as F


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


for name, default in (
    ("analytics_connection", "motta_analytics"),
    ("analytics_database", "MOTTAINAI_ANALITICO"),
    ("target_catalog", "workspace"),
):
    dbutils.widgets.text(name, default)

connection = identifier(dbutils.widgets.get("analytics_connection"))
database = identifier(dbutils.widgets.get("analytics_database"))
catalog = identifier(dbutils.widgets.get("target_catalog"))
bronze = f"`{catalog}`.`mottainai_bronze`"
silver = f"`{catalog}`.`mottainai_silver`"
gold = f"`{catalog}`.`mottainai_gold`"
control = f"`{catalog}`.`mottainai_control`.`publication`"
bronze_control = f"`{catalog}`.`mottainai_control`.`bronze_publication`"

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {control} (
  pipeline STRING, batch_id STRING, source_cutoff_at TIMESTAMP,
  source_published_at TIMESTAMP, refreshed_at TIMESTAMP
) USING DELTA
""")
if not spark.catalog.tableExists(f"{catalog}.mottainai_control.bronze_publication"):
    print("Bronze has no published analytical batch; Gold remains unchanged")
    dbutils.notebook.exit("WAITING_FOR_ANALYTICAL_PUBLICATION")
bronze_rows = spark.sql(
    f"SELECT batch_id, source_cutoff_at, source_published_at FROM {bronze_control} "
    "WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if not bronze_rows:
    print("Bronze has no published analytical batch; Gold remains unchanged")
    dbutils.notebook.exit("WAITING_FOR_ANALYTICAL_PUBLICATION")
if len(bronze_rows) != 1:
    raise RuntimeError("Bronze control has duplicate pipeline rows")

batch = str(uuid.UUID(str(bronze_rows[0]["batch_id"])))
previous = spark.sql(
    f"SELECT batch_id FROM {control} WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if len(previous) > 1:
    raise RuntimeError("Gold control has duplicate pipeline rows")
if previous and previous[0]["batch_id"] == batch:
    print(f"Gold already exposes batch {batch}")
    dbutils.notebook.exit("NO_NEW_BATCH")

# Read only the commit marker from PostgreSQL. All transformations below use
# the complete Bronze copy, not live operational data or a foreign catalog.
def published_batch():
    source_sql = (
        "SELECT batch_id FROM mottainai_analytics.job_log "
        "WHERE job_name = 'operational_to_analytics_daily' "
        "AND status = 'SUCCEEDED' AND batch_id IS NOT NULL "
        "AND cutoff_at IS NOT NULL "
        "AND metadata ->> 'publication_contract' = 'analytics_mart_v1' "
        "ORDER BY finished_at DESC, job_id DESC LIMIT 1"
    )
    rows = spark.sql(
        "SELECT * FROM remote_query("
        f"{literal(connection)}, database => {literal(database)}, "
        f"query => {literal(source_sql)})"
    ).collect()
    return str(rows[0]["batch_id"]) if len(rows) == 1 and rows[0]["batch_id"] else None


if published_batch() != batch:
    raise RuntimeError("Bronze batch is not the latest committed analytical publication")


def staged(name: str):
    return spark.table(f"{bronze}.`{name}`").where(F.col("_batch_id") == batch)


def duplicates(frame, keys):
    return frame.groupBy(*keys).count().where(F.col("count") > 1).limit(1).count() > 0


sales = staged("vw_sales_daily_kpis").selectExpr(
    "_batch_id", "cast(sale_date as date) AS sale_date",
    "cast(company_id as long) AS company_id", "cast(store_id as long) AS store_id",
    "trim(store_name) AS store_name", "cast(sale_count as long) AS sale_count",
    "cast(item_count as long) AS item_count",
    "cast(gross_revenue as decimal(20,2)) AS gross_revenue",
    "cast(discount_amount as decimal(20,2)) AS discount_amount",
    "cast(net_revenue as decimal(20,2)) AS net_revenue",
    "cast(average_ticket as decimal(20,2)) AS average_ticket",
)
monthly = staged("vw_monthly_summary").selectExpr(
    "_batch_id", "cast(month_start as date) AS month_start",
    "cast(store_id as long) AS store_id", "trim(store_name) AS store_name",
    "cast(total_sales as long) AS total_sales",
    "cast(total_revenue as decimal(20,2)) AS total_revenue",
    "cast(avg_ticket as decimal(20,2)) AS avg_ticket",
    "cast(active_sellers as long) AS active_sellers",
    "cast(units_sold as decimal(20,3)) AS units_sold",
)
stock = staged("vw_critical_stock").selectExpr(
    "_batch_id", "cast(inventory_id as long) AS inventory_id",
    "cast(product_id as long) AS product_id", "trim(product) AS product",
    "cast(store_id as long) AS store_id", "trim(store) AS store",
    "cast(current_quantity as decimal(20,3)) AS current_quantity",
    "cast(minimum_quantity as decimal(20,3)) AS minimum_quantity",
)
transactions = staged("fact_sales").selectExpr(
    "_batch_id", "cast(sale_id as long) AS sale_id",
    "cast(sale_date as date) AS sale_date", "cast(company_id as long) AS company_id",
    "cast(store_id as long) AS store_id", "upper(trim(status)) AS status",
    "cast(item_count as long) AS item_count",
    "cast(gross_amount as decimal(20,2)) AS gross_amount",
    "cast(discount_amount as decimal(20,2)) AS discount_amount",
    "cast(net_amount as decimal(20,2)) AS net_amount",
)
stores = staged("dim_store").selectExpr(
    "_batch_id", "cast(store_id as long) AS store_id",
    "cast(company_id as long) AS company_id", "trim(name) AS store_name",
    "trim(city) AS city", "trim(state_code) AS state_code",
    "cast(latitude as double) AS latitude", "cast(longitude as double) AS longitude",
    "cast(active as boolean) AS active",
)
risk = staged("vw_product_risk_ranking").selectExpr(
    "_batch_id", "cast(store_id as long) AS store_id", "trim(store_name) AS store_name",
    "cast(product_id as long) AS product_id", "trim(product_name) AS product_name",
    "upper(trim(stockout_risk)) AS stockout_risk",
    "cast(current_stock as decimal(20,3)) AS current_stock",
    "cast(days_of_coverage as decimal(20,3)) AS days_of_coverage",
    "cast(quantity_at_expiration_risk as decimal(20,3)) AS quantity_at_expiration_risk",
    "cast(value_at_expiration_risk as decimal(20,2)) AS value_at_expiration_risk",
    "cast(nearest_expiration_days as int) AS nearest_expiration_days",
    "upper(trim(consolidated_risk)) AS consolidated_risk",
)

# A duplicate business key is a source contract violation, not a row to silently
# discard. Failing here protects every Gold chart from double counting.
for name, frame, keys in (
    ("sales_daily_kpis", sales, ["sale_date", "company_id", "store_id"]),
    ("monthly_summary", monthly, ["month_start", "store_id"]),
    ("fact_sales", transactions, ["sale_id", "sale_date"]),
    ("dim_store", stores, ["store_id"]),
    ("product_risk_ranking", risk, ["store_id", "product_id"]),
):
    if duplicates(frame, keys):
        raise RuntimeError(f"Duplicate business key in {name}")

checks = {
    "sales_daily_kpis": (
        sales, F.col("sale_date").isNull() | F.col("company_id").isNull()
        | F.col("store_id").isNull() | F.col("sale_count").isNull()
        | ((F.col("sale_count") > 0) & F.col("net_revenue").isNull())
        | (F.col("sale_count") < 0)
        | (F.col("item_count") < 0) | (F.col("gross_revenue") < 0)
        | (F.col("discount_amount") < 0) | (F.col("net_revenue") < 0)
    ),
    "monthly_summary": (
        monthly, F.col("month_start").isNull() | F.col("store_id").isNull()
        | F.col("total_sales").isNull() | (F.col("total_sales") < 0)
        | (F.col("total_revenue") < 0) | (F.col("active_sellers") < 0)
        | (F.col("units_sold") < 0)
    ),
    "critical_stock": (
        stock, F.col("product_id").isNull() | F.col("store_id").isNull()
        | F.col("current_quantity").isNull() | F.col("minimum_quantity").isNull()
        | (F.col("minimum_quantity") < 0)
        | (F.col("current_quantity") >= F.col("minimum_quantity"))
    ),
    "fact_sales": (
        transactions, F.col("sale_id").isNull() | F.col("sale_date").isNull()
        | F.col("company_id").isNull() | F.col("store_id").isNull()
        | F.col("status").isNull() | F.col("net_amount").isNull()
        | ((F.col("status") == "COMPLETED") & (F.col("net_amount") < 0))
    ),
    "dim_store": (
        stores, F.col("store_id").isNull() | F.col("company_id").isNull()
        | F.col("store_name").isNull() | (F.length("store_name") == 0)
        | (F.col("latitude").isNotNull() & (F.abs("latitude") > 90))
        | (F.col("longitude").isNotNull() & (F.abs("longitude") > 180))
        | (F.col("latitude").isNull() != F.col("longitude").isNull())
    ),
    "product_risk_ranking": (
        risk, F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("consolidated_risk").isNull()
        | (~F.col("consolidated_risk").isin("LOW", "MEDIUM", "HIGH", "CRITICAL"))
    ),
}

quarantine = f"{silver}.`rejected_rows`"
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {quarantine} (
  source_relation STRING, batch_id STRING, error_code STRING,
  rejected_count BIGINT, recorded_at TIMESTAMP
) USING DELTA
""")
spark.sql(f"DELETE FROM {quarantine} WHERE batch_id = {literal(batch)}")
failures = []
for name, (frame, invalid) in checks.items():
    bad = frame.where(invalid).count()
    if bad:
        failures.append((name, batch, "invalid_key_or_measure", bad))
if failures:
    spark.createDataFrame(
        failures,
        "source_relation STRING, batch_id STRING, error_code STRING, rejected_count LONG",
    ).withColumn("recorded_at", F.current_timestamp()).write.mode("append").saveAsTable(quarantine)
    raise RuntimeError(f"Batch {batch} failed data quality checks: {failures}")

# This controls referential integrity without loading personal data into Gold.
store_ids = stores.select("store_id").distinct()
unknown_sales_stores = transactions.select("store_id").distinct().join(
    store_ids, "store_id", "left_anti"
).count()
if unknown_sales_stores:
    raise RuntimeError(f"{unknown_sales_stores} sales stores are absent from dim_store")

for name, frame in (
    ("sales_daily_kpis", sales), ("monthly_summary", monthly),
    ("critical_stock", stock), ("fact_sales", transactions),
    ("dim_store", stores), ("product_risk_ranking", risk),
):
    table = f"{silver}.`{name}`"
    if spark.catalog.tableExists(f"{catalog}.mottainai_silver.{name}"):
        spark.sql(f"DELETE FROM {table} WHERE _batch_id = {literal(batch)}")
    frame.write.format("delta").mode("append").saveAsTable(table)
    written = spark.table(table).where(F.col("_batch_id") == batch).count()
    expected = frame.count()
    if written != expected:
        raise RuntimeError(f"Silver {name}: {written} rows written, expected {expected}")
    print(f"Silver {name}: {written} rows")

if published_batch() != batch:
    raise RuntimeError("A newer PostgreSQL analytical publication appeared during refresh")

# A single pointer switch exposes every Gold dataset at the same published batch.
for name in ("sales_daily_kpis", "monthly_summary", "critical_stock", "product_risk_ranking"):
    spark.sql(f"""
    CREATE OR REPLACE VIEW {gold}.`{name}` AS
    SELECT s.* FROM {silver}.`{name}` s
    JOIN {control} p ON p.pipeline = 'operational_to_analytics_daily'
      AND s._batch_id = p.batch_id
    """)
spark.sql(f"""
CREATE OR REPLACE VIEW {gold}.`ticket_distribution` AS
SELECT s.sale_date, s.company_id, s.store_id, s.net_amount AS ticket_amount,
       s.item_count, s._batch_id
FROM {silver}.`fact_sales` s
JOIN {control} p ON p.pipeline = 'operational_to_analytics_daily'
 AND s._batch_id = p.batch_id
WHERE s.status = 'COMPLETED'
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {gold}.`stores` AS
SELECT s.store_id, s.company_id, s.store_name, s.city, s.state_code,
       s.latitude, s.longitude, s.active, s._batch_id
FROM {silver}.`dim_store` s
JOIN {control} p ON p.pipeline = 'operational_to_analytics_daily'
 AND s._batch_id = p.batch_id
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {gold}.`store_geography` AS
SELECT s.store_id, s.company_id, s.store_name, s.city, s.state_code,
       s.latitude, s.longitude, s.active, s._batch_id
FROM {silver}.`dim_store` s
JOIN {control} p ON p.pipeline = 'operational_to_analytics_daily'
 AND s._batch_id = p.batch_id
WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
""")
spark.sql(f"""
CREATE OR REPLACE VIEW {gold}.`dashboard_freshness` AS
SELECT batch_id, source_cutoff_at, source_published_at, refreshed_at
FROM {control} WHERE pipeline = 'operational_to_analytics_daily'
""")

spark.createDataFrame(
    [("operational_to_analytics_daily", batch,
      bronze_rows[0]["source_cutoff_at"], bronze_rows[0]["source_published_at"])],
    "pipeline STRING, batch_id STRING, source_cutoff_at TIMESTAMP, source_published_at TIMESTAMP",
).createOrReplaceTempView("_mottainai_next_publication")
spark.sql(f"""
MERGE INTO {control} AS target
USING _mottainai_next_publication AS source
ON target.pipeline = source.pipeline
WHEN MATCHED THEN UPDATE SET
  batch_id = source.batch_id,
  source_cutoff_at = source.source_cutoff_at,
  source_published_at = source.source_published_at,
  refreshed_at = current_timestamp()
WHEN NOT MATCHED THEN INSERT
  (pipeline, batch_id, source_cutoff_at, source_published_at, refreshed_at)
  VALUES (source.pipeline, source.batch_id, source.source_cutoff_at,
          source.source_published_at, current_timestamp())
""")
print(f"Gold published batch {batch}")
