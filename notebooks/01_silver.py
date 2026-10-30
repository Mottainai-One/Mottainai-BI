# Databricks notebook source
"""Normalize the published Bronze snapshot and validate business keys and measures."""

import re
import uuid

from pyspark.sql import functions as F


MODEL_VERSION = "6"


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
    "fact_inventory_count_line": staged("fact_inventory_count_line").selectExpr(
        "_batch_id", "cast(inventory_count_item_id as long) inventory_count_item_id",
        "cast(count_date as date) count_date", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id", "upper(trim(status)) status",
        "cast(system_quantity as decimal(20,3)) system_quantity",
        "cast(counted_quantity as decimal(20,3)) counted_quantity",
        "cast(unit_cost as decimal(20,4)) unit_cost",
    ),
    "fact_transfer_line": staged("fact_transfer_line").selectExpr(
        "_batch_id", "cast(transfer_item_id as long) transfer_item_id",
        "cast(transfer_id as long) transfer_id", "cast(request_date as date) request_date",
        "cast(source_store_id as long) source_store_id",
        "cast(destination_store_id as long) destination_store_id",
        "cast(product_id as long) product_id", "upper(trim(status)) status",
        "cast(transferred_quantity as decimal(20,3)) transferred_quantity",
        "cast(requested_at as timestamp) requested_at",
        "cast(completed_at as timestamp) completed_at",
    ),
    "fact_replenishment_plan_line": staged("fact_replenishment_plan_line").selectExpr(
        "_batch_id", "cast(pre_list_item_id as long) pre_list_item_id",
        "cast(pre_list_id as long) pre_list_id", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id", "cast(generated_at as timestamp) generated_at",
        "upper(trim(status)) status",
        "cast(suggested_quantity as decimal(20,3)) suggested_quantity",
    ),
    "fact_replenishment_execution_line": staged("fact_replenishment_execution_line").selectExpr(
        "_batch_id", "cast(execution_item_id as long) execution_item_id",
        "cast(pre_list_id as long) pre_list_id", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id", "cast(completed_at as timestamp) completed_at",
        "cast(replenished_quantity as decimal(20,3)) replenished_quantity",
    ),
    "fact_donation_line": staged("fact_donation_line").selectExpr(
        "_batch_id", "cast(donation_item_id as long) donation_item_id",
        "cast(donation_date as date) donation_date", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id", "upper(trim(status)) status",
        "cast(donated_quantity as decimal(20,3)) donated_quantity",
        "cast(unit_cost as decimal(20,4)) unit_cost",
    ),
    "fact_disposal_line": staged("fact_disposal_line").selectExpr(
        "_batch_id", "cast(disposal_item_id as long) disposal_item_id",
        "cast(disposal_date as date) disposal_date", "cast(store_id as long) store_id",
        "cast(product_id as long) product_id",
        "cast(disposed_quantity as decimal(20,3)) disposed_quantity",
        "cast(unit_cost as decimal(20,4)) unit_cost",
    ),
    "fact_alert_lifecycle": staged("fact_alert_lifecycle").selectExpr(
        "_batch_id", "cast(alert_id as long) alert_id", "cast(store_id as long) store_id",
        "upper(trim(alert_type)) alert_type", "upper(trim(priority)) priority",
        "upper(trim(status)) status", "cast(generated_at as timestamp) generated_at",
        "cast(resolved_at as timestamp) resolved_at",
    ),
    "fact_action_lifecycle": staged("fact_action_lifecycle").selectExpr(
        "_batch_id", "cast(suggested_action_id as long) suggested_action_id",
        "cast(alert_id as long) alert_id", "cast(store_id as long) store_id",
        "upper(trim(action_type)) action_type", "upper(trim(status)) status",
        "cast(generated_at as timestamp) generated_at",
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
    "fact_inventory_count_line": lambda f: (
        F.col("inventory_count_item_id").isNull() | F.col("count_date").isNull()
        | F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("status").isNull() | F.col("system_quantity").isNull()
        | F.col("counted_quantity").isNull() | (F.col("system_quantity") < 0)
        | (F.col("counted_quantity") < 0) | (F.col("unit_cost") < 0)
    ),
    "fact_transfer_line": lambda f: (
        F.col("transfer_item_id").isNull() | F.col("transfer_id").isNull()
        | F.col("request_date").isNull() | F.col("source_store_id").isNull()
        | F.col("destination_store_id").isNull() | F.col("product_id").isNull()
        | F.col("status").isNull() | F.col("requested_at").isNull()
        | F.col("transferred_quantity").isNull()
        | (F.col("transferred_quantity") <= 0)
        | (F.col("source_store_id") == F.col("destination_store_id"))
        | (F.col("completed_at") < F.col("requested_at"))
    ),
    "fact_replenishment_plan_line": lambda f: (
        F.col("pre_list_item_id").isNull() | F.col("pre_list_id").isNull()
        | F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("generated_at").isNull() | F.col("status").isNull()
        | F.col("suggested_quantity").isNull() | (F.col("suggested_quantity") <= 0)
    ),
    "fact_replenishment_execution_line": lambda f: (
        F.col("execution_item_id").isNull() | F.col("pre_list_id").isNull()
        | F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("replenished_quantity").isNull()
        | (F.col("replenished_quantity") <= 0)
    ),
    "fact_donation_line": lambda f: (
        F.col("donation_item_id").isNull() | F.col("donation_date").isNull()
        | F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("status").isNull() | F.col("donated_quantity").isNull()
        | (F.col("donated_quantity") <= 0) | (F.col("unit_cost") < 0)
    ),
    "fact_disposal_line": lambda f: (
        F.col("disposal_item_id").isNull() | F.col("disposal_date").isNull()
        | F.col("store_id").isNull() | F.col("product_id").isNull()
        | F.col("disposed_quantity").isNull() | (F.col("disposed_quantity") <= 0)
        | (F.col("unit_cost") < 0)
    ),
    "fact_alert_lifecycle": lambda f: (
        F.col("alert_id").isNull() | F.col("store_id").isNull()
        | F.col("alert_type").isNull() | F.col("priority").isNull()
        | F.col("status").isNull() | F.col("generated_at").isNull()
        | (F.col("resolved_at") < F.col("generated_at"))
    ),
    "fact_action_lifecycle": lambda f: (
        F.col("suggested_action_id").isNull() | F.col("alert_id").isNull()
        | F.col("store_id").isNull() | F.col("action_type").isNull()
        | F.col("status").isNull() | F.col("generated_at").isNull()
    ),
}
keys = {
    "dim_store": ["store_id"], "dim_category": ["category_id"],
    "dim_product": ["product_id"], "fact_sales": ["sale_id", "sale_date"],
    "fact_sale_item": ["sale_item_id"], "fact_sale_payment": ["payment_id"],
    "fact_inventory_snapshot": ["inventory_id", "snapshot_date"],
    "fact_inventory_count_line": ["inventory_count_item_id"],
    "fact_transfer_line": ["transfer_item_id"],
    "fact_replenishment_plan_line": ["pre_list_item_id"],
    "fact_replenishment_execution_line": ["execution_item_id"],
    "fact_donation_line": ["donation_item_id"],
    "fact_disposal_line": ["disposal_item_id"],
    "fact_alert_lifecycle": ["alert_id"],
    "fact_action_lifecycle": ["suggested_action_id"],
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
    "counts_without_product": frames["fact_inventory_count_line"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
    "transfers_without_product": frames["fact_transfer_line"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
    "donations_without_product": frames["fact_donation_line"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
    "disposals_without_product": frames["fact_disposal_line"].select("product_id").join(product_ids, "product_id", "left_anti").count(),
    "actions_without_alert": frames["fact_action_lifecycle"].select("alert_id").join(
        frames["fact_alert_lifecycle"].select("alert_id").distinct(), "alert_id", "left_anti"
    ).count(),
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
