# Runbook — pipeline BI Databricks

## Pré-requisitos

1. No PostgreSQL analítico físico `MOTTAINAI_ANALITICO`, aplicar `database/analytics/14_publish_mart_view.sql` e confirmar que `mottainai_analytics.vw_published_batch` expõe **no máximo um** lote do contrato `analytics_mart_v1`.
2. Conexões Unity Catalog somente leitura: `conection_motta_operacional` para `MOTTAINAI` e `motta_analytics` para `MOTTAINAI_ANALITICO`. O job fornece o nome do database em cada `remote_query`; ambas as conexões podem usar o mesmo host Aiven.
3. Catálogo gerenciado com permissão de criação de schemas e tabelas Delta (padrão `workspace`). Não usar catálogo estrangeiro para destino.
4. Warehouse serverless ou pro para dashboard publicado. No Free Edition, observar cotas do workspace e deixar o job sem concorrência.

## Implantação

Instalar/autenticar o Databricks CLI no workspace e, na raiz deste repositório:

```powershell
databricks bundle validate
databricks bundle deploy
databricks bundle run analytics_to_medallion
```

O job implantado tem quatro tarefas na ordem `preflight` → `bronze` → `refresh_medallion` → `refresh_dashboard`. O dashboard está publicado com ID `01f1d22904b81b738aef457d6a67f354`. O cron de 02:30 em `America/Sao_Paulo` está ativo. O RPA é o dono da publicação às 02:00; a margem de 30 minutos permite concluir sua carga antes da leitura do Databricks. Se a carga terminar depois, execute novamente `databricks jobs run-now 731348243647869` após confirmar `vw_published_batch`.

## Validação de dados

No editor SQL do Databricks, execute após o job:

```sql
SELECT * FROM workspace.mottainai_gold.dashboard_freshness;
SELECT count(*) AS bronze_sales
FROM workspace.mottainai_bronze.fact_sales
WHERE _batch_id = (SELECT batch_id FROM workspace.mottainai_gold.dashboard_freshness);
SELECT count(*) AS silver_sales
FROM workspace.mottainai_silver.fact_sales
WHERE _batch_id = (SELECT batch_id FROM workspace.mottainai_gold.dashboard_freshness);
SELECT count(*) AS gold_tickets FROM workspace.mottainai_gold.ticket_distribution;
SELECT source_relation, SUM(rejected_count) AS rejected
FROM workspace.mottainai_silver.rejected_rows
GROUP BY source_relation;
```

Compare o `batch_id` com o banco analítico físico:

```sql
SELECT batch_id, source_cutoff_at, published_at
FROM mottainai_analytics.vw_published_batch;
SELECT (metadata ->> 'publication_contract') AS contract,
       metadata -> 'dataset_counts' AS dataset_counts
FROM mottainai_analytics.job_log
WHERE job_name = 'operational_to_analytics_daily'
  AND status = 'SUCCEEDED'
ORDER BY job_id DESC LIMIT 1;
```

Essas duas consultas PostgreSQL devem ser executadas no database `MOTTAINAI_ANALITICO` pelo pgAdmin ou via `remote_query`; PostgreSQL não aceita `database.schema.table` entre bancos. Não confundir um `job_log` antigo `SUCCEEDED` com o novo contrato. Salve também URL, status e duração de cada tarefa do run Databricks.

## Dashboard

O dashboard já está publicado: [Mottainai | BI Executivo e Estoque](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663). A fonte versionada é `dashboard/mottainai_bi.lvdash.json`; execute `python dashboard/build_dashboard.py` para regenerá-la após alterar os SQLs. O job atualiza o painel após publicar Gold. A publicação usa permissões de dados individuais (`embed_credentials=false`); conceda a cada leitor `SELECT` nas views Gold e uso do SQL warehouse, além de acesso ao dashboard. Não habilite compartilhamento público por padrão.

## Falha e reprocessamento

- **Sem lote publicado:** preflight prepara schemas; Bronze sai com `WAITING_FOR_ANALYTICAL_PUBLICATION`; Gold anterior não muda. Rode o RPA e confirme o marcador.
- **Conexão incorreta:** `current_database()` não coincide com o nome esperado. Corrija a conexão Unity Catalog, sem colocar senha no notebook.
- **Falha de qualidade:** veja `mottainai_silver.rejected_rows`. Corrija a origem/regra, publique novo lote analítico e reexecute o job. O ponteiro Gold preserva o lote anterior.
- **Interrupção após Bronze/Silver:** reexecute o mesmo job. O lote usa `batch_id` para regravar apenas suas linhas não publicadas. Não apague o lote Gold anterior.
- **Dashboard vazio:** cheque `dashboard_freshness`, contagem de `fact_sales` e filtros. Zero vendas no operacional produz zero fatos legítimos; não invente dados.
- **Lote novo durante ingestão:** o job falha fechado; reexecute para a publicação mais recente.

O dashboard representa o último lote publicado, não leitura em tempo real. O lote do RPA inclui alterações até o corte efetivo, inclusive as ocorridas entre 00:00 e 02:00.
