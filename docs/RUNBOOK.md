# Runbook — BI Databricks

## Operação diária

O RPA publica o lote de `MOTTAINAI` em `MOTTAINAI_ANALITICO` às 02:00 de São Paulo. O job `mottainai-analytics-to-medallion` começa às 02:30, com `max_concurrent_runs=1`. Ordem: `preflight → bronze → silver → gold → refresh_dashboard`. A execução fora do horário só deve ocorrer depois de `mottainai_analytics.vw_published_batch` mostrar novo lote publicado.

O workspace usa as conexões Unity Catalog `conection_motta_operacional` e `motta_analytics`; os bancos físicos são respectivamente `MOTTAINAI` e `MOTTAINAI_ANALITICO`. Usuário e senha são administrados nessas conexões, nunca nos notebooks.

## Implantação e execução

```powershell
databricks bundle validate -p mottainai-bi
databricks bundle deploy -p mottainai-bi
databricks jobs run-now 731348243647869 -p mottainai-bi
```

O catálogo gerenciado de destino é `motta_analytics`. Os schemas `bronze`, `silver`, `gold` e `control` são criados pelo preflight. O dashboard mantém ID `01f1d22904b81b738aef457d6a67f354` e usa warehouse `64bc14de5692c645`. Após alterar SQL ou visualizações, regenere o JSON com `python dashboard/build_dashboard.py`, atualize e publique o **mesmo** dashboard; o job faz o refresh do publicado.

## Verificação no SQL Warehouse

```sql
SELECT * FROM motta_analytics.gold.dashboard_freshness;
SELECT count(*) AS vendas FROM motta_analytics.gold.sales_tickets;
SELECT sum(revenue_brl) AS receita FROM motta_analytics.gold.sales_daily;
SELECT sum(available_quantity) AS unidades_disponiveis,
       sum(stock_value) AS valor_estoque
FROM motta_analytics.gold.inventory_health;
SELECT * FROM motta_analytics.gold.quality_summary;
SELECT * FROM motta_analytics.control.silver_publication;
SELECT * FROM motta_analytics.control.publication;
```

No PostgreSQL, conecte-se **ao database `MOTTAINAI_ANALITICO`** e execute `SELECT batch_id, source_cutoff_at, published_at FROM mottainai_analytics.vw_published_batch;`. Compare esse `batch_id` com `dashboard_freshness`. PostgreSQL não aceita `database.schema.table` para consultar outro database.

## Falhas

- **Lote ausente ou RPA atrasado:** o dashboard mantém o último lote; confirme a publicação analítica e reexecute o job.
- **Falha de qualidade Silver:** consulte `motta_analytics.silver.quality_results`; corrija a origem e publique novo lote. Gold preserva o lote anterior.
- **Falha de reconciliação Gold:** compare subtotal dos itens com receita das vendas concluídas; Gold não deve avançar o marcador.
- **Dashboard vazio:** verifique lote, filtros e a permissão individual para Gold e warehouse. Zero vendas pode ser legítimo.
- **Reprocessamento:** execute novamente o job após a correção. As tabelas por lote e marcadores tornam o processo idempotente; não apague o lote anterior manualmente.

O dashboard representa a fotografia do corte efetivo, não tempo real. O painel foi publicado sem credenciais embutidas (`embed_credentials=false`); conceda somente as permissões necessárias aos leitores. O [run 97850894011189](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/97850894011189?o=7474654317437663) concluiu as cinco tarefas em 29/10/2026.
