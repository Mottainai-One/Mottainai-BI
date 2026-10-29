# Databricks notebook source
"""Normalize the published Bronze snapshot and validate business keys and measures."""

import re
import uuid

from pyspark.sql import functions as F


MODEL_VERSION = "5"


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


dbutils.widgets.text("target_catalog", "motta_analytics")
catalog = identifier(dbutils.widgets.get("target_catalog"))
bronze = f"`{catalog}`.`bronze`"
silver = f"`{catalog}`.`silver`"
control = f"`{catalog}`.`control`"
bronze_marker = f"{control}.`bronze_publication`"
silver_marker = f"{control}.`silver_publication`"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {silver}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {control}")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {silver_marker} (
  pipeline STRING, batch_id STRING, model_version STRING, validated_at TIMESTAMP
) USING DELTA
""")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {silver}.`quality_results` (
  batch_id STRING, model_version STRING, relation_name STRING,
  checked_rows BIGINT, invalid_rows BIGINT, checked_at TIMESTAMP
) USING DELTA
""")

markers = spark.sql(
    f"SELECT batch_id FROM {bronze_marker} "
    "WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if len(markers) != 1:
    raise RuntimeError("Expected exactly one published Bronze batch")
batch = str(uuid.UUID(str(markers[0]["batch_id"])))
old = spark.sql(
    f"SELECT batch_id, model_version FROM {silver_marker} "
    "WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if len(old) > 1:
    raise RuntimeError("Duplicate Silver publication marker")
if old and old[0]["batch_id"] == batch and old[0]["model_version"] == MODEL_VERSION:
    dbutils.notebook.exit("SILVER_ALREADY_VALIDATED")


def staged(name):
    return spark.table(f"{bronze}.`{name}`").where(F.col("_batch_id") == batch)


frames = {
    "dim_store": staged("dim_store").selectExpr(
        "_batch_id", "cast(store_id as long) store_id",
        "cast(company_id as long) company_id", "trim(name) store_name",
        "trim(city) city", "upper(trim(state_code)) state_code",
        "cast(latitude as double) latitude", "cast(longitude as double) longitude",
        "cast(active as boolean) active",
    ),
    "dim_category": staged("dim_category").selectExpr(
        "_batch_id", "cast(category_id as long) category_id",
        "cast(parent_category_id as long) parent_category_id",
        "trim(name) category_name", "cast(active as boolean) active",
    ),
    "dim_product": staged("dim_product").selectExpr(
        "_batch_id", "cast(product_id as long) product_id",
        "cast(category_id as long) category_id", "trim(sku) sku",
        "trim(name) product_name", "trim(brand) brand",
        "trim(unit_of_measure) unit_of_measure",
        "cast(avg_cost as decimal(20,4)) avg_cost",
        "cast(suggested_price as decimal(20,4)) suggested_price",
        "cast(active as boolean) active",
    ),
    "fact_sales": staged("fact_sales").selectExpr(
        "_batch_id", "cast(sale_id as long) sale_id",
        "cast(sale_date as date) sale_date",
        "cast(company_id as long) company_id", "cast(store_id as long) store_id",
        "upper(trim(status)) status", "cast(item_count as long) item_count",
        "cast(gross_amount as decimal(20,2)) gross_amount",
        "cast(discount_amount as decimal(20,2)) discount_amount",
        "cast(net_amount as decimal(20,2)) net_amount",
    ),
    "fact_sale_item": staged("fact_sale_item").selectExpr(
        "_batch_id", "cast(sale_item_id as long) sale_item_id",
        "cast(sale_id as long) sale_id", "cast(sale_date as date) sale_date",
        "cast(store_id as long) store_id", "cast(product_id as long) product_id",
        "cast(batch_id as long) source_batch_id",
        "cast(quantity as decimal(20,3)) quantity",
        "cast(unit_price as decimal(20,4)) unit_price",
        "cast(discount_amount as decimal(20,2)) discount_amount",
        "cast(subtotal as decimal(20,2)) subtotal",
    ),
    "fact_sale_payment": staged("fact_sale_payment").selectExpr(
        "_batch_id", "cast(payment_id as long) payment_id",
        "cast(sale_id as long) sale_id", "cast(sale_date as date) sale_date",
        "cast(store_id as long) store_id", "upper(trim(payment_method)) payment_method",
        "cast(amount as decimal(20,2)) amount",
        "cast(installments as int) installments",
    ),
    "fact_inventory_snapshot": staged("fact_inventory_snapshot").selectExpr(
        "_batch_id", "cast(inventory_id as long) inventory_id",
        "cast(snapshot_date as date) snapshot_date",
        "cast(company_id as long) company_id", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id", "cast(batch_id as long) source_batch_id",
        "upper(trim(inventory_type)) inventory_type",
        "cast(quantity as decimal(20,3)) quantity",
        "cast(reserved_quantity as decimal(20,3)) reserved_quantity",
        "cast(average_cost as decimal(20,4)) average_cost",
        "cast(expiration_date as date) expiration_date",
        "cast(minimum_quantity as decimal(20,3)) minimum_quantity",
    ),
}

invalid = {
    "dim_store": lambda f: (
        F.col("store_id").isNull() | F.col("company_id").isNull()
        | F.col("store_name").isNull() | (F.length("store_name") == 0)
        | (F.col("latitude").isNull() != F.col("longitude").isNull())
        | (F.abs(F.col("latitude")) > 90) | (F.abs(F.col("longitude")) > 180)
    ),
    "dim_category": lambda f: F.col("category_id").isNull() | F.col("category_name").isNull(),
    "dim_product": lambda f: (
        F.col("product_id").isNull() | F.col("product_name").isNull()
        | (F.length("product_name") == 0)
        | (F.col("avg_cost") < 0) | (F.col("suggested_price") < 0)
    ),
    "fact_sales": lambda f: (
        F.col("sale_id").isNull() | F.col("sale_date").isNull()
        | F.col("company_id").isNull() | F.col("store_id").isNull()
        | F.col("status").isNull() | F.col("net_amount").isNull()
        | (F.col("item_count") < 0) | (F.col("gross_amount") < 0)
        | (F.col("discount_amount") < 0)
        | ((F.col("status") == "COMPLETED") & (F.col("net_amount") < 0))
    ),
    "fact_sale_item": lambda f: (
        F.col("sale_item_id").isNull() | F.col("sale_id").isNull()
        | F.col("sale_date").isNull() | F.col("store_id").isNull()
        | F.col("product_id").isNull() | F.col("quantity").isNull()
        | (F.col("quantity") <= 0) | (F.col("unit_price") < 0)
        | (F.col("discount_amount") < 0) | (F.col("subtotal") < 0)
    ),
    "fact_sale_payment": lambda f: (
        F.col("payment_id").isNull() | F.col("sale_id").isNull()
        | F.col("sale_date").isNull() | F.col("store_id").isNull()
        | F.col("payment_method").isNull() | (F.length("payment_method") == 0)
        | F.col("amount").isNull() | (F.col("amount") < 0)
        | ((F.col("installments").isNotNull()) & (F.col("installments") < 1))
    ),
    "fact_inventory_snapshot": lambda f: (
        F.col("inventory_id").isNull() | F.col("snapshot_date").isNull()
        | F.col("company_id").isNull() | F.col("store_id").isNull()
        | F.col("product_id").isNull() | F.col("quantity").isNull()
        | F.col("reserved_quantity").isNull() | F.col("minimum_quantity").isNull()
        | (F.col("quantity") < 0) | (F.col("reserved_quantity") < 0)
        | (F.col("reserved_quantity") > F.col("quantity"))
        | (F.col("minimum_quantity") < 0) | (F.col("average_cost") < 0)
    ),
}
keys = {
    "dim_store": ["store_id"], "dim_category": ["category_id"],
    "dim_product": ["product_id"], "fact_sales": ["sale_id", "sale_date"],
    "fact_sale_item": ["sale_item_id"], "fact_sale_payment": ["payment_id"],
    "fact_inventory_snapshot": ["inventory_id", "snapshot_date"],
}

quality = []
for name, frame in frames.items():
    total = frame.count()
    bad = frame.where(invalid[name](frame)).count()
    duplicates = frame.groupBy(*keys[name]).count().where("count > 1").count()
    quality.append((batch, MODEL_VERSION, name, total, bad + duplicates))

store_ids = frames["dim_store"].select("store_id").distinct()
product_ids = frames["dim_product"].select("product_id").distinct()
sale_ids = frames["fact_sales"].select("sale_id", "sale_date", "store_id").distinct()
relationships = {
    "sales_without_store": frames["fact_sales"].select("store_id").join(store_ids, "store_id", "left_anti").count(),
    "items_without_sale": frames["fact_sale_item"].join(sale_ids, ["sale_id", "sale_date", "store_id"], "left_anti").count(),
    "items_without_product": frames["fact_sale_item"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
    "payments_without_sale": frames["fact_sale_payment"].join(sale_ids, ["sale_id", "sale_date", "store_id"], "left_anti").count(),
    "inventory_without_store": frames["fact_inventory_snapshot"].select("store_id").join(store_ids, "store_id", "left_anti").count(),
    "inventory_without_product": frames["fact_inventory_snapshot"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
}
quality.extend((batch, MODEL_VERSION, name, 0, count) for name, count in relationships.items())

quality_table = f"{silver}.`quality_results`"
spark.sql(f"DELETE FROM {quality_table} WHERE batch_id = {literal(batch)} AND model_version = {literal(MODEL_VERSION)}")
spark.createDataFrame(
    quality,
    "batch_id STRING, model_version STRING, relation_name STRING, checked_rows LONG, invalid_rows LONG",
).withColumn("checked_at", F.current_timestamp()).write.mode("append").saveAsTable(quality_table)
failures = [(name, count) for _, _, name, _, count in quality if count]
if failures:
    raise RuntimeError(f"Silver quality failed for batch {batch}: {failures}")

for name, frame in frames.items():
    table = f"{silver}.`{name}`"
    if spark.catalog.tableExists(f"{catalog}.silver.{name}"):
        spark.sql(f"DELETE FROM {table} WHERE _batch_id = {literal(batch)}")
    frame.write.format("delta").mode("append").saveAsTable(table)
    actual = spark.table(table).where(F.col("_batch_id") == batch).count()
    if actual != frame.count():
        raise RuntimeError(f"Silver {name}: written count {actual} differs from source")
    print(f"Silver {name}: {actual} rows")

spark.createDataFrame(
    [("operational_to_analytics_daily", batch, MODEL_VERSION)],
    "pipeline STRING, batch_id STRING, model_version STRING",
).createOrReplaceTempView("_next_silver_publication")
spark.sql(f"""
MERGE INTO {silver_marker} t USING _next_silver_publication s
ON t.pipeline = s.pipeline
WHEN MATCHED THEN UPDATE SET batch_id=s.batch_id, model_version=s.model_version,
  validated_at=current_timestamp()
WHEN NOT MATCHED THEN INSERT (pipeline,batch_id,model_version,validated_at)
VALUES (s.pipeline,s.batch_id,s.model_version,current_timestamp())
""")
print(f"Silver validated batch {batch}, model {MODEL_VERSION}")
