# Entrega da disciplina de Business Intelligence

**Verificação:** 29/10/2026 · **Código:** [PR BI #3](https://github.com/Mottainai-One/Mottainai-BI/pull/3) · **Painel:** [Databricks publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663).

| Requisito | Implementação | Evidência |
|---|---|---|
| Dados da aplicação | RPA operacional → analítico; Databricks copia apenas lote publicado | `vw_published_batch`, Bronze e [job](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663) |
| Medallion | Schemas e tarefas Bronze, Silver e Gold distintos; qualidade antes da publicação | `notebooks/00_bronze_analitico.py`, `01_silver.py`, `02_gold.py` |
| KPIs, linha e barras | Receita, vendas, ticket, variação, evolução diária, loja, produto, estoque | `dashboard/mottainai_bi.lvdash.json` |
| Histograma e boxplot | Distribuição de tickets concluídos | Página Distribuição e qualidade |
| Mapa se aplicável | Consulta opcional preparada; 0 coordenadas válidas na origem | `dashboard/datasets/06_store_map.sql` |
| Filtros | Período e loja globais; estoque é fotografia independente da data da venda | Definição do dashboard |
| Relatório gerencial | Definições, limpeza, linhagem, limites e interpretação | `docs/RELATORIO_GERENCIAL.md` |
| Job agendado | Cinco tarefas sequenciais, 02:30 São Paulo, uma execução simultânea | `databricks.yml` e [run 97850894011189](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/97850894011189?o=7474654317437663) |

## Resultado observado

Em 29/10/2026, o job de cinco tarefas terminou `SUCCESS` após a nova publicação do dashboard. Consultas no SQL Warehouse confirmaram: 101 vendas concluídas, R$ 1.515,00 de receita, ticket médio R$ 15,00, 101 unidades vendidas, 210 unidades disponíveis e R$ 2.100,00 de estoque estimado a custo médio. Silver registrou zero falhas de qualidade. Os oito datasets do painel e as duas consultas opcionais terminaram `SUCCEEDED`.

A amostra comercial contém somente 20/10/2026, uma loja vendedora e um produto vendido. O inventário possui dois lotes do mesmo produto e loja, sem vencimento em 30 dias. Não há base para inferir tendência, sazonalidade, comparação real entre lojas ou dispersão de ticket. A ausência de coordenadas impede um mapa útil.

## Limites de aceite

O painel foi atualizado e publicado no mesmo ID com `embed_credentials=false`, e o job de atualização concluiu `SUCCESS`. O navegador integrado chegou à tela de login do Databricks; a inspeção visual de cada widget e a interação manual dos filtros ainda precisam ser registradas por alguém autenticado. A [PR RPA #11](https://github.com/Mottainai-One/Mottanai-RPA/pull/11) e a PR BI aguardam o fluxo de revisão da equipe. O agendamento de 02:00 depende do merge da RPA.

Para apresentação, mostre o run de cinco tarefas, execute as consultas do [runbook](RUNBOOK.md), abra o dashboard, altere os filtros e destaque os limites da amostra.
