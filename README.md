# Mottainai BI — Databricks

Este repositório versiona o pipeline e as consultas do dashboard de Business Intelligence. A fonte de negócio é o banco físico `MOTTAINAI_ANALITICO` no Aiven. O banco `MOTTAINAI` recebe transações; o RPA publica uma fotografia no analítico às 02:00 de São Paulo. O Databricks lê **apenas um lote analítico concluído**, transforma Bronze → Silver → Gold e o dashboard consulta somente Gold.

```text
MOTTAINAI → RPA transacional → MOTTAINAI_ANALITICO
                               → preflight → Bronze → Silver → Gold → dashboard
```

## Entrega acadêmica

- [Relatório gerencial](docs/RELATORIO_GERENCIAL.md): base, problema, limpeza, definições de KPIs, limites e evidências.
- [Entrega e evidências por requisito](docs/ENTREGA_BI.md): matriz da disciplina, links para os runs e resultados observados.
- [Datasets e especificação do dashboard](dashboard/README.md): cards, linha, barras, histograma, boxplot, mapa condicional, filtros.
- [Runbook](docs/RUNBOOK.md): implantação, execução, validação e recuperação.
- [Bundle Databricks](databricks.yml): job serverless com quatro tarefas sequenciais e agenda ativa às 02:30 `America/Sao_Paulo`.

Os notebooks usam `remote_query` nas conexões Unity Catalog `conection_motta_operacional` e `motta_analytics`, indicando explicitamente os databases `MOTTAINAI` e `MOTTAINAI_ANALITICO`. Isso evita o limite de 100 objetos por schema do catálogo estrangeiro no Free Edition. Usuário e senha permanecem na conexão do Databricks, não neste repositório.

## Estado verificável

O [job 731348243647869](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663) foi implantado e o [run de quatro tarefas](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/533702856364216?o=7474654317437663) terminou `SUCCESS`, incluindo `refresh_dashboard`. O [dashboard publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663) possui duas páginas de visualização e filtros globais. Bronze e Silver contêm 101 vendas do lote publicado; a origem e Gold têm o mesmo `batch_id`. Os detalhes e limites da amostra estão em [ENTREGA_BI](docs/ENTREGA_BI.md).

Uma atualização fora das 02:00 exige chamar o job Databricks após o commit do RPA. A agenda 02:30 cobre o ciclo diário, mas não garante atualização por evento. A tarefa `Dashboard` já depende de `refresh_medallion` e atualiza o resultado publicado. A correção do RPA está na [PR #11](https://github.com/Mottainai-One/Mottanai-RPA/pull/11) e precisa de revisão/merge para entrar no agendamento da branch principal.
