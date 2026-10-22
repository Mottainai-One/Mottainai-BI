# Databricks notebook source
"""Publish a consistent BI snapshot only after the analytical batch is published."""

import re
import uuid

from pyspark.sql.functions import (
    col,
    current_timestamp,
    lit,
    struct,
    to_json,
    when,
)


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid Unity Catalog identifier: {value!r}")
    return value


for name in ("analytics_catalog", "target_catalog"):
    dbutils.widgets.text(name, "")

analytics = identifier(dbutils.widgets.get("analytics_catalog"))
target = identifier(dbutils.widgets.get("target_catalog"))
source = f"`{analytics}`.`mottainai_analytics`"
control = f"`{target}`.`mottainai_control`.`publication`"

published = spark.sql(
    f"SELECT batch_id, source_cutoff_at, published_at FROM {source}.`vw_published_batch`"
).collect()
if not published:
    print("No published analytical batch; leaving the current dashboard snapshot intact")
    dbutils.notebook.exit("NO_NEW_BATCH")
if len(published) != 1 or published[0]["batch_id"] is None:
    raise RuntimeError("Expected exactly one published analytical batch with a batch_id")

batch = str(uuid.UUID(str(published[0]["batch_id"])))
previous = spark.sql(
    f"SELECT batch_id FROM {control} WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if len(previous) > 1:
    raise RuntimeError("Publication control has duplicate pipeline rows")
if previous and previous[0]["batch_id"] == batch:
    print(f"Batch {batch} is already published in BI")
    dbutils.notebook.exit("NO_NEW_BATCH")

sources = {
    "sales_daily_kpis": "vw_sales_daily_kpis",
    "monthly_summary": "vw_monthly_summary",
    "critical_stock": "vw_critical_stock",
}


def replace_unpublished_batch(table: str) -> None:
    if spark.catalog.tableExists(table.replace("`", "")):
        spark.sql(f"DELETE FROM {table} WHERE _batch_id = '{batch}'")


def append_table(frame, table: str) -> None:
    frame.write.format("delta").mode("append").saveAsTable(table)


# Bronze preserves the selected analytical views as received. The published
# batch ID is the replay key; a failed, unpublished attempt can be retried.
for dataset, relation in sources.items():
    bronze = f"`{target}`.`mottainai_bronze`.`{dataset}`"
    replace_unpublished_batch(bronze)
    frame = (
        spark.table(f"{source}.`{relation}`")
        .withColumn("_batch_id", lit(batch))
        .withColumn("_source_published_at", lit(published[0]["published_at"]))
        .withColumn("_ingested_at", current_timestamp())
    )
    append_table(frame, bronze)
    rows_written = spark.table(bronze).where(col("_batch_id") == batch).count()
    print(f"Bronze {dataset}: {rows_written} rows")

bronze_sales = spark.table(f"`{target}`.`mottainai_bronze`.`sales_daily_kpis`").where(
    col("_batch_id") == batch
)
sales = bronze_sales.selectExpr(
    "_batch_id", "cast(sale_date as date) as sale_date",
    "cast(company_id as bigint) as company_id", "cast(store_id as bigint) as store_id",
    "trim(store_name) as store_name", "coalesce(cast(sale_count as bigint), 0) as sale_count",
    "coalesce(cast(item_count as bigint), 0) as item_count",
    "coalesce(cast(gross_revenue as decimal(20,2)), 0) as gross_revenue",
    "coalesce(cast(discount_amount as decimal(20,2)), 0) as discount_amount",
    "coalesce(cast(net_revenue as decimal(20,2)), 0) as net_revenue",
    "coalesce(cast(average_ticket as decimal(20,2)), 0) as average_ticket",
)
if sales.groupBy("_batch_id", "sale_date", "company_id", "store_id").count().where(col("count") > 1).limit(1).count():
    raise RuntimeError("Duplicate daily sales keys in the analytical source")
sales = sales.withColumn(
    "_quality_error",
    when(
        col("sale_date").isNull() | col("company_id").isNull() |
        col("store_id").isNull() | (col("sale_count") < 0) |
        (col("item_count") < 0) | (col("gross_revenue") < 0) |
        (col("discount_amount") < 0) | (col("net_revenue") < 0),
        lit("invalid_sales_key_or_measure"),
    ),
)

bronze_monthly = spark.table(f"`{target}`.`mottainai_bronze`.`monthly_summary`").where(
    col("_batch_id") == batch
)
monthly = bronze_monthly.selectExpr(
    "_batch_id", "cast(month_start as date) as month_start",
    "cast(store_id as bigint) as store_id", "trim(store_name) as store_name",
    "cast(total_sales as bigint) as total_sales",
    "coalesce(cast(total_revenue as decimal(20,2)), 0) as total_revenue",
    "coalesce(cast(avg_ticket as decimal(20,2)), 0) as avg_ticket",
    "cast(active_sellers as bigint) as active_sellers",
    "coalesce(cast(units_sold as decimal(20,3)), 0) as units_sold",
)
if monthly.groupBy("_batch_id", "month_start", "store_id").count().where(col("count") > 1).limit(1).count():
    raise RuntimeError("Duplicate monthly summary keys in the analytical source")
monthly = monthly.withColumn(
    "_quality_error",
    when(
        col("month_start").isNull() | col("store_id").isNull() |
        col("total_sales").isNull() | col("active_sellers").isNull() |
        (col("total_sales") < 0) | (col("total_revenue") < 0) |
        (col("active_sellers") < 0) | (col("units_sold") < 0),
        lit("invalid_monthly_key_or_measure"),
    ),
)

bronze_stock = spark.table(f"`{target}`.`mottainai_bronze`.`critical_stock`").where(
    col("_batch_id") == batch
)
stock = bronze_stock.selectExpr(
    "_batch_id", "cast(inventory_id as bigint) as inventory_id",
    "cast(product_id as bigint) as product_id", "trim(product) as product",
    "cast(store_id as bigint) as store_id", "trim(store) as store",
    "cast(current_quantity as decimal(20,3)) as current_quantity",
    "cast(minimum_quantity as decimal(20,3)) as minimum_quantity",
).dropDuplicates()
stock = stock.withColumn("negative_stock_flag", col("current_quantity") < 0).withColumn(
    "_quality_error",
    when(
        col("product_id").isNull() | col("store_id").isNull() |
        col("current_quantity").isNull() | col("minimum_quantity").isNull() |
        (col("minimum_quantity") < 0),
        lit("invalid_stock_key_or_threshold"),
    ),
)

quality_failures = 0
quarantine = f"`{target}`.`mottainai_silver`.`rejected_rows`"
replace_unpublished_batch(quarantine)
for dataset, frame in (("sales_daily_kpis", sales), ("monthly_summary", monthly), ("critical_stock", stock)):
    silver = f"`{target}`.`mottainai_silver`.`{dataset}`"
    replace_unpublished_batch(silver)
    rejected = frame.where(col("_quality_error").isNotNull())
    count = rejected.count()
    quality_failures += count
    if count:
        append_table(
            rejected.select(
                lit(dataset).alias("source_view"), col("_batch_id"),
                col("_quality_error").alias("error_code"),
                to_json(struct(*[col(c) for c in frame.columns if c != "_quality_error"])).alias("row_json"),
                current_timestamp().alias("recorded_at"),
            ),
            quarantine,
        )
    append_table(frame.where(col("_quality_error").isNull()).drop("_quality_error"), silver)
    print(f"Silver {dataset}: {count} rejected rows")

if quality_failures:
    raise RuntimeError(f"BI batch {batch} has {quality_failures} quarantined rows; publication withheld")

# Detect a newer analytical publication before exposing this snapshot.
latest = spark.sql(f"SELECT batch_id FROM {source}.`vw_published_batch`").first()
if latest is None or str(latest["batch_id"]) != batch:
    raise RuntimeError("Analytical publication changed during refresh; retry the BI job")

# Gold is a business-facing projection over cleaned, batch-versioned Silver.
# The control pointer switches only after all three datasets are ready.
for dataset in sources:
    spark.sql(f"""
    CREATE OR REPLACE VIEW `{target}`.`mottainai_gold`.`{dataset}` AS
    SELECT s.* FROM `{target}`.`mottainai_silver`.`{dataset}` s
    JOIN {control} p ON p.pipeline = 'operational_to_analytics_daily'
      AND s._batch_id = p.batch_id
    """)

spark.sql(f"""
CREATE OR REPLACE VIEW `{target}`.`mottainai_gold`.`dashboard_freshness` AS
SELECT batch_id, source_cutoff_at, source_published_at, refreshed_at
FROM {control} WHERE pipeline = 'operational_to_analytics_daily'
""")

spark.createDataFrame(
    [("operational_to_analytics_daily", batch, published[0]["source_cutoff_at"], published[0]["published_at"])],
    "pipeline string, batch_id string, source_cutoff_at timestamp, source_published_at timestamp",
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
print(f"Published BI batch {batch}")
