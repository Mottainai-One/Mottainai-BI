# Databricks notebook source
"""Build business-facing Gold marts from validated Silver and publish one batch."""

import re
import uuid


MODEL_VERSION = "2"


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


for name, default in (
    ("target_catalog", "motta_analytics"),
    ("analytics_connection", "motta_analytics"),
    ("analytics_database", "MOTTAINAI_ANALITICO"),
):
    dbutils.widgets.text(name, default)

catalog = identifier(dbutils.widgets.get("target_catalog"))
connection = identifier(dbutils.widgets.get("analytics_connection"))
database = identifier(dbutils.widgets.get("analytics_database"))
silver = f"`{catalog}`.`silver`"
gold = f"`{catalog}`.`gold`"
control = f"`{catalog}`.`control`"
bronze_marker = f"{control}.`bronze_publication`"
silver_marker = f"{control}.`silver_publication`"
publication = f"{control}.`publication`"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {gold}")
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {publication} (
  pipeline STRING, batch_id STRING, model_version STRING,
  source_cutoff_at TIMESTAMP, source_published_at TIMESTAMP,
  refreshed_at TIMESTAMP
) USING DELTA
""")

rows = spark.sql(f"""
SELECT s.batch_id, s.model_version, b.source_cutoff_at, b.source_published_at
FROM {silver_marker} s JOIN {bronze_marker} b
 ON s.pipeline=b.pipeline AND s.batch_id=b.batch_id
WHERE s.pipeline='operational_to_analytics_daily'
""").collect()
if len(rows) != 1:
    raise RuntimeError("Gold needs one fully validated Silver/ Bronze batch")
batch = str(uuid.UUID(str(rows[0]["batch_id"])))
if rows[0]["model_version"] != MODEL_VERSION:
    raise RuntimeError("Silver model version differs from Gold")


def published_batch():
    pg = (
        "SELECT batch_id FROM mottainai_analytics.job_log "
        "WHERE job_name=$$operational_to_analytics_daily$$ "
        "AND status=$$SUCCEEDED$$ AND batch_id IS NOT NULL "
        "AND cutoff_at IS NOT NULL "
        "AND metadata ->> $$publication_contract$$ = $$analytics_mart_v1$$ "
        "ORDER BY finished_at DESC, job_id DESC LIMIT 1"
    )
    found = spark.sql(
        "SELECT * FROM remote_query("
        f"{literal(connection)}, database => {literal(database)}, query => {literal(pg)})"
    ).collect()
    return str(found[0]["batch_id"]) if len(found) == 1 else None


if published_batch() != batch:
    raise RuntimeError("A newer analytical source batch exists; restart the job")

old = spark.sql(
    f"SELECT batch_id, model_version FROM {publication} "
    "WHERE pipeline='operational_to_analytics_daily'"
).collect()
if len(old) > 1:
    raise RuntimeError("Duplicate Gold publication marker")
if old and old[0]["batch_id"] == batch and old[0]["model_version"] == MODEL_VERSION:
    dbutils.notebook.exit("GOLD_ALREADY_PUBLISHED")

sales = spark.sql(f"""
SELECT coalesce(sum(net_amount),0) AS total
FROM {silver}.`fact_sales` WHERE _batch_id={literal(batch)} AND status='COMPLETED'
""").first()["total"]
items = spark.sql(f"""
SELECT coalesce(sum(i.subtotal),0) AS total
FROM {silver}.`fact_sale_item` i JOIN {silver}.`fact_sales` s
 ON i.sale_id=s.sale_id AND i.sale_date=s.sale_date AND i.store_id=s.store_id
 AND i._batch_id=s._batch_id
WHERE i._batch_id={literal(batch)} AND s.status='COMPLETED'
""").first()["total"]
if abs(sales - items) > 0.01:
    raise RuntimeError(f"Sales and item revenue do not reconcile: {sales} vs {items}")

# Gold views are computed from Silver facts and dimensions, with no direct
# dependency on PostgreSQL business views. The publication pointer is their
# only batch selector, so every widget sees the same coherent snapshot.
views = {
    "sales_daily": f"""
        SELECT s.sale_date, s.company_id, s.store_id, st.store_name,
               count(*) AS sale_count, sum(s.item_count) AS item_count,
               sum(s.gross_amount) AS gross_revenue,
               sum(s.net_amount) AS net_revenue,
               try_divide(sum(s.net_amount), count(*)) AS average_ticket,
               s._batch_id
        FROM {silver}.`fact_sales` s
        JOIN {silver}.`dim_store` st ON st.store_id=s.store_id AND st._batch_id=s._batch_id
        JOIN {publication} p ON p.batch_id=s._batch_id
          AND p.pipeline='operational_to_analytics_daily'
        WHERE s.status='COMPLETED'
        GROUP BY s.sale_date,s.company_id,s.store_id,st.store_name,s._batch_id
    """,
    "sales_tickets": f"""
        SELECT s.sale_id,s.sale_date,s.company_id,s.store_id,st.store_name,
               s.net_amount AS ticket_amount,s.item_count,s._batch_id
        FROM {silver}.`fact_sales` s
        JOIN {silver}.`dim_store` st ON st.store_id=s.store_id AND st._batch_id=s._batch_id
        JOIN {publication} p ON p.batch_id=s._batch_id
          AND p.pipeline='operational_to_analytics_daily'
        WHERE s.status='COMPLETED'
    """,
    "product_sales_daily": f"""
        SELECT i.sale_date,i.store_id,st.store_name,i.product_id,
               pr.product_name,pr.category_id,coalesce(c.category_name,'Sem categoria') category_name,
               sum(i.quantity) units_sold,sum(i.subtotal) net_revenue,
               count(DISTINCT i.sale_id) sales_with_product,i._batch_id
        FROM {silver}.`fact_sale_item` i
        JOIN {silver}.`fact_sales` s ON s.sale_id=i.sale_id AND s.sale_date=i.sale_date
          AND s.store_id=i.store_id AND s._batch_id=i._batch_id
        JOIN {silver}.`dim_product` pr ON pr.product_id=i.product_id AND pr._batch_id=i._batch_id
        JOIN {silver}.`dim_store` st ON st.store_id=i.store_id AND st._batch_id=i._batch_id
        LEFT JOIN {silver}.`dim_category` c ON c.category_id=pr.category_id AND c._batch_id=i._batch_id
        JOIN {publication} p ON p.batch_id=i._batch_id
          AND p.pipeline='operational_to_analytics_daily'
        WHERE s.status='COMPLETED'
        GROUP BY i.sale_date,i.store_id,st.store_name,i.product_id,pr.product_name,
                 pr.category_id,c.category_name,i._batch_id
    """,
    "inventory_batches": f"""
        WITH latest AS (
          SELECT store_id,product_id,max(snapshot_date) snapshot_date
          FROM {silver}.`fact_inventory_snapshot` i JOIN {publication} p
            ON p.batch_id=i._batch_id AND p.pipeline='operational_to_analytics_daily'
          GROUP BY store_id,product_id
        )
        SELECT i.snapshot_date,i.company_id,i.store_id,st.store_name,
               i.product_id,pr.product_name,i.source_batch_id,i.inventory_id,
               i.inventory_type,i.quantity,i.reserved_quantity,
               greatest(i.quantity-i.reserved_quantity,0) AS available_quantity,
               i.average_cost,i.quantity*i.average_cost AS stock_value,
               i.minimum_quantity,i.expiration_date,
               datediff(i.expiration_date,i.snapshot_date) AS days_to_expiry,i._batch_id
        FROM {silver}.`fact_inventory_snapshot` i JOIN latest l
          ON l.store_id=i.store_id AND l.product_id=i.product_id
         AND l.snapshot_date=i.snapshot_date
        JOIN {silver}.`dim_product` pr ON pr.product_id=i.product_id AND pr._batch_id=i._batch_id
        JOIN {silver}.`dim_store` st ON st.store_id=i.store_id AND st._batch_id=i._batch_id
        JOIN {publication} p ON p.batch_id=i._batch_id
          AND p.pipeline='operational_to_analytics_daily'
    """,
    "inventory_health": f"""
        SELECT snapshot_date,company_id,store_id,store_name,product_id,product_name,
               sum(quantity) on_hand_quantity,sum(reserved_quantity) reserved_quantity,
               sum(available_quantity) available_quantity,
               sum(stock_value) stock_value,max(minimum_quantity) minimum_quantity,
               sum(CASE WHEN days_to_expiry BETWEEN 0 AND 30
                        THEN stock_value ELSE 0 END) value_expiring_30d,
               sum(CASE WHEN days_to_expiry < 0 THEN stock_value ELSE 0 END) expired_value,
               CASE WHEN sum(available_quantity) < max(minimum_quantity)
                    THEN true ELSE false END below_minimum,
               count(*) batch_count,_batch_id
        FROM {gold}.`inventory_batches`
        GROUP BY snapshot_date,company_id,store_id,store_name,product_id,product_name,_batch_id
    """,
    "stores": f"""
        SELECT s.store_id,s.company_id,s.store_name,s.city,s.state_code,
               s.latitude,s.longitude,s.active,s._batch_id
        FROM {silver}.`dim_store` s JOIN {publication} p ON p.batch_id=s._batch_id
         AND p.pipeline='operational_to_analytics_daily'
    """,
    "dashboard_freshness": f"""
        SELECT batch_id,model_version,source_cutoff_at,source_published_at,refreshed_at
        FROM {publication} WHERE pipeline='operational_to_analytics_daily'
    """,
    "quality_summary": f"""
        SELECT q.relation_name,q.checked_rows,q.invalid_rows,q.checked_at,p.batch_id
        FROM {silver}.`quality_results` q JOIN {publication} p
          ON p.batch_id=q.batch_id AND p.model_version=q.model_version
         AND p.pipeline='operational_to_analytics_daily'
    """,
}

for name, sql in views.items():
    spark.sql(f"CREATE OR REPLACE VIEW {gold}.`{name}` AS {sql}")

if published_batch() != batch:
    raise RuntimeError("Source changed while Gold views were being prepared")

spark.createDataFrame(
    [("operational_to_analytics_daily",batch,MODEL_VERSION,
      rows[0]["source_cutoff_at"],rows[0]["source_published_at"])],
    "pipeline STRING,batch_id STRING,model_version STRING,"
    "source_cutoff_at TIMESTAMP,source_published_at TIMESTAMP",
).createOrReplaceTempView("_next_gold_publication")
spark.sql(f"""
MERGE INTO {publication} t USING _next_gold_publication s
ON t.pipeline=s.pipeline
WHEN MATCHED THEN UPDATE SET batch_id=s.batch_id,model_version=s.model_version,
  source_cutoff_at=s.source_cutoff_at,source_published_at=s.source_published_at,
  refreshed_at=current_timestamp()
WHEN NOT MATCHED THEN INSERT
  (pipeline,batch_id,model_version,source_cutoff_at,source_published_at,refreshed_at)
  VALUES (s.pipeline,s.batch_id,s.model_version,s.source_cutoff_at,
          s.source_published_at,current_timestamp())
""")
print(f"Gold published batch {batch}, model {MODEL_VERSION}")
