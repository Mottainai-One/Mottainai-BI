# Databricks notebook source
"""Testa a conexão PostgreSQL e copia um lote publicado para Bronze Delta."""

import re
import uuid

from pyspark.sql import functions as F


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador inválido: {value!r}")
    return value


def quoted(value: str) -> str:
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
bronze_schema = f"`{catalog}`.`mottainai_bronze`"
control_schema = f"`{catalog}`.`mottainai_control`"
control_table = f"{control_schema}.`bronze_publication`"


def remote_query(query: str):
    return spark.sql(
        "SELECT * FROM remote_query("
        f"{quoted(connection)}, database => {quoted(database)}, query => {quoted(query)})"
    )


def remote_table(relation: str):
    relation = identifier(relation)
    return spark.sql(
        "SELECT * FROM remote_query("
        f"{quoted(connection)}, database => {quoted(database)}, "
        f"dbtable => {quoted('mottainai_analytics.' + relation)})"
    )


# A consulta direta evita a cota de 100 tabelas por schema que impede a
# sincronização do catálogo estrangeiro neste workspace Free Edition.
database_name = remote_query("SELECT current_database() AS database_name").first()[
    "database_name"
]
if database_name != database:
    raise RuntimeError(f"Conexão apontou para {database_name}, esperado {database}")
print(f"Conexão PostgreSQL confirmada: {database_name}")

# Lotes antigos de etl_daily_batch/vw_published_batch não comprovam que fatos
# e dimensões foram publicados juntos. O contrato novo está no job_log.
publication = remote_query("""
    SELECT batch_id, cutoff_at AS source_cutoff_at, finished_at AS published_at
    FROM mottainai_analytics.job_log
    WHERE job_name = 'operational_to_analytics_daily'
      AND status = 'SUCCEEDED'
      AND batch_id IS NOT NULL
      AND cutoff_at IS NOT NULL
      AND metadata ->> 'publication_contract' = 'analytics_mart_v1'
    ORDER BY finished_at DESC, job_id DESC
    LIMIT 1
""").collect()
if not publication:
    print("Ainda não há carga analítica publicada pelo contrato analytics_mart_v1.")
    dbutils.notebook.exit("WAITING_FOR_ANALYTICAL_PUBLICATION")

batch = str(uuid.UUID(str(publication[0]["batch_id"])))
source_cutoff_at = publication[0]["source_cutoff_at"]
published_at = publication[0]["published_at"]

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {bronze_schema}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {control_schema}")
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {control_table} (
      pipeline STRING,
      batch_id STRING,
      source_cutoff_at TIMESTAMP,
      source_published_at TIMESTAMP,
      bronze_refreshed_at TIMESTAMP
    ) USING DELTA
""")

previous = spark.sql(
    f"SELECT batch_id FROM {control_table} "
    "WHERE pipeline = 'operational_to_analytics_daily'"
).collect()
if len(previous) > 1:
    raise RuntimeError("Controle Bronze contém publicações duplicadas")
if previous and previous[0]["batch_id"] == batch:
    print(f"Lote {batch} já está na Bronze")
    dbutils.notebook.exit("NO_NEW_BATCH")

# Inclui as quatro tabelas centrais e as sete relações solicitadas para BI.
relations = (
    "dim_company",
    "dim_store",
    "fact_sales",
    "fact_inventory_snapshot",
    "vw_sales_daily_kpis",
    "mv_dashboard_metrics",
    "vw_monthly_summary",
    "vw_critical_stock",
    "vw_stockout_analysis",
    "vw_product_risk_ranking",
    "vw_executive_dashboard",
)

# Confere todas as origens antes de gravar qualquer tabela Bronze.
frames = {}
source_counts = {}
for relation in relations:
    # Sale, customer and employee IDs are unnecessary for the BI dashboard.
    # Minimize the Bronze copy rather than relying on Gold alone to hide them.
    if relation == "fact_sales":
        frame = remote_query("""
            SELECT sale_id, sale_date, company_id, store_id, status,
                   item_count, gross_amount, discount_amount, net_amount
            FROM mottainai_analytics.fact_sales
        """)
    else:
        frame = remote_table(relation)
    source_counts[relation] = frame.count()
    frames[relation] = frame

for relation, frame in frames.items():
    table = f"{bronze_schema}.`{relation}`"
    if spark.catalog.tableExists(f"{catalog}.mottainai_bronze.{relation}"):
        spark.sql(f"DELETE FROM {table} WHERE _batch_id = {quoted(batch)}")
    (
        frame.withColumn("_batch_id", F.lit(batch))
        .withColumn("_source_cutoff_at", F.lit(source_cutoff_at))
        .withColumn("_source_published_at", F.lit(published_at))
        .withColumn("_ingested_at", F.current_timestamp())
        .write.format("delta")
        .mode("append")
        .saveAsTable(table)
    )
    written = spark.table(table).where(F.col("_batch_id") == batch).count()
    if written != source_counts[relation]:
        raise RuntimeError(
            f"Bronze {relation}: origem={source_counts[relation]}, destino={written}"
        )
    print(f"Bronze {relation}: {written} linhas")

latest = remote_query("""
    SELECT batch_id FROM mottainai_analytics.job_log
    WHERE job_name = 'operational_to_analytics_daily'
      AND status = 'SUCCEEDED'
      AND metadata ->> 'publication_contract' = 'analytics_mart_v1'
    ORDER BY finished_at DESC, job_id DESC LIMIT 1
""").first()
if latest is None or str(latest["batch_id"]) != batch:
    raise RuntimeError("Novo lote analítico surgiu durante a cópia; execute novamente")

spark.createDataFrame(
    [("operational_to_analytics_daily", batch, source_cutoff_at, published_at)],
    "pipeline STRING, batch_id STRING, source_cutoff_at TIMESTAMP, "
    "source_published_at TIMESTAMP",
).createOrReplaceTempView("_bronze_next_publication")
spark.sql(f"""
    MERGE INTO {control_table} AS target
    USING _bronze_next_publication AS source
    ON target.pipeline = source.pipeline
    WHEN MATCHED THEN UPDATE SET
      batch_id = source.batch_id,
      source_cutoff_at = source.source_cutoff_at,
      source_published_at = source.source_published_at,
      bronze_refreshed_at = current_timestamp()
    WHEN NOT MATCHED THEN INSERT
      (pipeline, batch_id, source_cutoff_at, source_published_at,
       bronze_refreshed_at)
      VALUES (source.pipeline, source.batch_id, source.source_cutoff_at,
              source.source_published_at, current_timestamp())
""")
print(f"Lote Bronze publicado: {batch}")
