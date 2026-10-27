# Entrega da disciplina de Business Intelligence

**Data da verificação:** 27/10/2026 (America/Sao_Paulo)  
**Workspace:** [Databricks Mottainai](https://dbc-38ac8920-cbf4.cloud.databricks.com/?o=7474654317437663)  
**Código:** [PR de BI #3](https://github.com/Mottainai-One/Mottainai-BI/pull/3)

## Requisitos e evidências

| Requisito do PDF | Entrega | Evidência verificável |
|---|---|---|
| Conexão com dados gerados pela aplicação | O RPA copia `MOTTAINAI` para `MOTTAINAI_ANALITICO`; Databricks lê o lote publicado do analítico e grava Delta Bronze, Silver e Gold. | [Run RPA bem-sucedido](https://github.com/Mottainai-One/Mottanai-RPA/actions/runs/40545866446), [run Databricks bem-sucedido](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/589643529061201?o=7474654317437663), `databricks.yml` e notebooks. |
| Barra, linha, cards de KPI e desvios | Receita por loja, risco de estoque, receita diária, receita, vendas, ticket médio e variação em relação ao período anterior. | [Dashboard publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663), `dashboard/mottainai_bi.lvdash.json`. |
| Histograma e boxplot | Distribuição dos tickets em faixas de R$ 5 e distribuição por loja. | Página “Estoque e tickets” do dashboard e dataset `dashboard/datasets/04_ticket_distribution.sql`. |
| Mapa, quando aplicável | Mapa de lojas com coordenadas válidas. | Widget e dataset `dashboard/datasets/06_store_map.sql`; atualmente retorna zero pontos, pois não há latitude/longitude na fonte. |
| Filtros interativos | Período e loja como filtros globais; estoque é fotografia do último lote, independente do filtro de data. | Página de filtros globais na definição publicada. |
| Relatório gerencial | Base, problema, tratamento, métricas, interpretação, limites e linhagem. | `docs/RELATORIO_GERENCIAL.md`. |
| Pipeline Databricks (extra) | Preflight, ingestão Bronze, limpeza Silver, cálculo Gold e atualização do dashboard. | [Job 731348243647869](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663), `databricks.yml` e notebooks. |
| Job manual/agendado (extra) | Execução automática diária às 02:30 em São Paulo, uma execução por vez, mais `run-now` para cargas fora do horário. | Configuração do job; [run de quatro tarefas SUCCESS](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/533702856364216?o=7474654317437663). |
| Dashboard usa a base final do pipeline (extra) | Os seis datasets do painel usam exclusivamente `workspace.mottainai_gold`. | `dashboard/datasets/` e definição publicada pela [Lakeview API](https://docs.databricks.com/api/lakeview/v1/published-dashboard). |
| Evidências de configuração, histórico, status e resultado (extra) | Links para job e runs, contagens e identificação do lote nesta página. | Seção “Resultado observado” abaixo. |

## Resultado observado

- Lote publicado no PostgreSQL analítico e em Gold: `aaff5e35-d32d-428c-abde-6924fb47b74a`. A comparação foi feita em 27/10/2026 pelo SQL Warehouse; ambos retornaram o mesmo `batch_id`, corte `2026-10-27T16:57:04.558Z` e publicação `2026-10-27T16:57:06.390Z`.
- Bronze `fact_sales`: **101** registros; Silver `fact_sales`: **101**; Gold `ticket_distribution`: **101**; Gold `stores`: **100**. Silver: **0** rejeições.
- Receita de vendas concluídas: **R$ 1.515,00**, em **101** vendas de 20/10/2026. Há apenas uma loja com vendas e todos os tickets valem R$ 15,00. O mapa tem **0** lojas com coordenadas.
- O [run de carga 589643529061201](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/589643529061201?o=7474654317437663) terminou `SUCCESS`. O [run 533702856364216](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/533702856364216?o=7474654317437663) terminou `SUCCESS` nas quatro tarefas, incluindo `refresh_dashboard`.
- O painel foi publicado sem embutir credenciais (`embed_credentials=false`). A API confirmou 2 páginas de visualização, 1 página global de filtros, 6 datasets e 16 elementos. Todos os seis datasets SQL foram executados com `SUCCEEDED`; o dataset do mapa retornou zero linhas legitimamente.

## Limites e passagem para a equipe

1. A inspeção visual dos widgets na interface Databricks ainda precisa ser registrada pela equipe. A verificação automatizada cobriu publicação, estrutura, consultas e execução do job; não constitui prova de aparência ou interação manual dos filtros.
2. A [PR RPA #11](https://github.com/Mottainai-One/Mottanai-RPA/pull/11) contém a correção que passou no teste manual. O agendamento das 02:00 só executará essa versão depois da revisão e do merge. A [PR BI #3](https://github.com/Mottainai-One/Mottainai-BI/pull/3) também aguarda revisão; seu CI passou e a versão já foi implantada no workspace.
3. O job Databricks de 02:30 lê o último lote publicado. Se o RPA atrasar ou falhar, o dashboard continuará com o lote anterior e mostrará o horário real de corte; não apresenta o atraso como atualização nova. Após publicação fora do horário, use `run-now` conforme `docs/RUNBOOK.md`.
4. O histórico atual é pequeno demais para sustentar conclusões de tendência ou dispersão. O mapa depende de coordenadas reais da aplicação. Não usar números sintéticos como se fossem produção.

## Roteiro curto para apresentação

1. Abrir o [job](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663) e mostrar agenda, sequência e histórico do run `533702856364216`.
2. No SQL Editor, executar as consultas de contagem e frescor em `docs/RUNBOOK.md`, mostrando que o `batch_id` Gold coincide com o marcador analítico.
3. Abrir o [dashboard publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663), testar os filtros de período e loja e mostrar barras, linha, cards, histograma, boxplot e a ausência justificada de pontos no mapa.
4. Explicar as regras de limpeza, as métricas e as limitações usando `docs/RELATORIO_GERENCIAL.md`.
