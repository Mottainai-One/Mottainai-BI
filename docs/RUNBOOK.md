# Operação do job BI

## Antes do primeiro uso

O catálogo estrangeiro `mottainai_analitico` foi ligado ao banco físico
`MOTTAINAI_ANALITICO`. Em 26/10/2026, o Databricks retornou os mesmos dois
lotes `PUBLISHED` vistos diretamente no PostgreSQL (datas de negócio 18 e
19/10/2026), mas as tabelas `fact_sales` e `fact_inventory_snapshot` estavam
vazias. Esses lotes não comprovam que o data mart foi carregado. A migração
`14_publish_mart_view.sql` do repositório do banco altera a view para mostrar
somente a carga confirmada pela RPA na mesma transação dos fatos. Depois da
migração, a view permanecerá vazia até a primeira execução real bem-sucedida.
O catálogo Regular `motta_analytics` não representa o PostgreSQL analítico.

No SQL Editor do Databricks, confirme o catálogo operacional e as views de origem:

```sql
SHOW CATALOGS;
SELECT count(*) FROM <catalogo_operacional>.mottainai.company;
SELECT batch_id, source_cutoff_at, published_at
FROM mottainai_analitico.mottainai_analytics.vw_published_batch;
SELECT count(*)
FROM mottainai_analitico.mottainai_analytics.vw_sales_daily_kpis;
SELECT count(*)
FROM mottainai_analitico.mottainai_analytics.vw_monthly_summary;
SELECT count(*)
FROM mottainai_analitico.mottainai_analytics.vw_critical_stock;
```

O primeiro `count` valida a conexão operacional, sem copiar seus dados. A view `vw_published_batch` deve mostrar **no máximo um** lote atual; sem lote publicado, o refresh não altera Gold.

Para implantar com o Databricks CLI autenticado no workspace:

```powershell
databricks bundle validate --var="operational_catalog=NOME" --var="target_catalog=workspace"
databricks bundle deploy --var="operational_catalog=NOME" --var="target_catalog=workspace"
databricks bundle run analytics_to_medallion
```

A agenda fica pausada no bundle até a equipe validar uma execução manual. A agenda de contingência é 02:30, no fuso `America/Sao_Paulo`; caso o RPA publique depois desse horário, acione o job manualmente ou pelo gatilho do RPA. Não mova a RPA para o Databricks: ela já gerencia a transação entre os dois PostgreSQLs.

## Publicação e qualidade

1. O job lê o `batch_id` da view `vw_published_batch` do banco analítico. Se esse lote já consta em `mottainai_control.publication`, encerra sem reprocessar.
2. Bronze recebe cópias das três views selecionadas, identificadas pelo lote. Uma tentativa falha pode repetir o mesmo lote sem duplicar linhas.
3. Silver tipa, limpa e valida os campos. Linhas inválidas entram em `mottainai_silver.rejected_rows` e o lote **não é publicado** para Gold até a correção da origem ou da regra.
4. Antes de publicar, o job confere novamente o `batch_id` no analítico. Gold mostra apenas o lote apontado pela tabela de controle, trocada ao fim de todas as etapas.

Consultas após a execução:

```sql
SELECT * FROM workspace.mottainai_gold.dashboard_freshness;
SELECT count(*) FROM workspace.mottainai_gold.sales_daily_kpis;
SELECT count(*) FROM workspace.mottainai_gold.monthly_summary;
SELECT count(*) FROM workspace.mottainai_gold.critical_stock;
SELECT source_view, error_code, count(*)
FROM workspace.mottainai_silver.rejected_rows
GROUP BY source_view, error_code;
```

Se `rejected_rows` ainda não existir, nenhuma linha foi rejeitada. Troque `workspace` pelo catálogo gerenciado escolhido. O dashboard deve exibir `source_cutoff_at` e `source_published_at` de `dashboard_freshness` para que a equipe saiba a idade dos dados.

## Atualização do dashboard

O gatilho de atualização é a **publicação concluída** no banco analítico, não qualquer alteração em andamento nas tabelas. Depois de criar e publicar o dashboard, acrescente ao mesmo job uma tarefa `Dashboard` dependente de `refresh_medallion`. Configure o RPA para chamar `run-now` após confirmar `PUBLISHED`; mantenha a agenda das 02:30 apenas como contingência. Um gatilho `table update` do Databricks não observa alterações diretamente no PostgreSQL federado, pois acompanha tabelas do Unity Catalog. Até a ligação do RPA, não há atualização automática garantida fora da agenda.

No Free Edition, use uma execução por vez e monitore as cotas serverless. O ambiente é adequado para desenvolvimento e demonstração; sua disponibilidade não possui SLA.
