# Databricks notebook source
"""Validate both PostgreSQL connections and the committed analytical snapshot."""

import re


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


for name, default in (
    ("operational_connection", "conection_motta_operacional"),
    ("operational_database", "MOTTAINAI"),
    ("analytics_connection", "motta_analytics"),
    ("analytics_database", "MOTTAINAI_ANALITICO"),
    ("target_catalog", "motta_analytics"),
):
    dbutils.widgets.text(name, default)

operational_connection = identifier(dbutils.widgets.get("operational_connection"))
operational_database = identifier(dbutils.widgets.get("operational_database"))
analytics_connection = identifier(dbutils.widgets.get("analytics_connection"))
analytics_database = identifier(dbutils.widgets.get("analytics_database"))
target_catalog = identifier(dbutils.widgets.get("target_catalog"))

if (operational_connection, operational_database) == (analytics_connection, analytics_database):
    raise ValueError("Operational and analytical sources must be distinct")


def remote_query(connection: str, database: str, sql: str):
    return spark.sql(
        "SELECT * FROM remote_query("
        f"{literal(connection)}, database => {literal(database)}, "
        f"query => {literal(sql)})"
    )


for connection, database in (
    (operational_connection, operational_database),
    (analytics_connection, analytics_database),
):
    actual = remote_query(connection, database, "SELECT current_database() AS database_name").first()[
        "database_name"
    ]
    if actual != database:
        raise RuntimeError(f"Connection {connection} reached {actual}, expected {database}")
    print(f"Connection OK: {connection} -> {actual}")

# Operational data is never copied to Databricks. It is used only to verify
# connectivity; the published analytical database is the sole BI source.
remote_query(
    operational_connection,
    operational_database,
    "SELECT 1 AS operational_connection_ok FROM mottainai.company LIMIT 1",
).collect()

published = remote_query(
    analytics_connection,
    analytics_database,
    "SELECT batch_id, cutoff_at AS source_cutoff_at, finished_at AS published_at "
    "FROM mottainai_analytics.job_log "
    "WHERE job_name = $$operational_to_analytics_daily$$ "
    "AND status = $$SUCCEEDED$$ AND batch_id IS NOT NULL "
    "AND cutoff_at IS NOT NULL "
    "AND metadata ->> $$publication_contract$$ = $$analytics_mart_v1$$ "
    "ORDER BY finished_at DESC, job_id DESC LIMIT 1",
).collect()
if len(published) > 1:
    raise RuntimeError("Analytical publication view returned more than one batch")

for schema in ("bronze", "silver", "gold", "control"):
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{target_catalog}`.`{schema}`")

if not published or published[0]["batch_id"] is None:
    print("No analytics_mart_v1 batch published yet; downstream notebooks will exit without changing Gold")
else:
    print(f"Published analytical batch: {published[0]['batch_id']}")
