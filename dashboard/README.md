# Dashboard Mottainai — contrato de publicação

O painel publicado usa apenas as views em `motta_analytics.gold`. A definição é gerada por `python dashboard/build_dashboard.py` em `mottainai_bi.lvdash.json` e mantém o mesmo ID no workspace.

## Páginas

| Página | Elementos | Fonte |
|---|---|---|
| Visão executiva | Receita líquida, vendas concluídas, ticket médio, comparação com período anterior, evolução diária, receita por loja, produtos vendidos, frescor | `sales_daily`, `sales_tickets`, `product_sales_daily`, `dashboard_freshness` |
| Comercial | Lojas e produtos com vendas, unidades vendidas, métodos usados, receita por produto e pagamentos conciliados | `sales_daily`, `product_sales_daily`, `payment_mix` |
| Estoque | Produtos com alerta por loja, unidades disponíveis, valor a custo médio, vencimento em 30 dias, situação por produto e lotes | `inventory_health`, `inventory_batches` |
| Operações e perdas | Acuracidade de posições contadas, divergência, transferências, reposição, doações, descartes e alertas; detalhes de contagem e destinação | `inventory_count_accuracy`, `transfer_execution`, `replenishment_fulfillment`, `product_destinations`, `alert_action_funnel` |
| Distribuição e qualidade | Histograma e boxplot de tickets, contagens de validação Silver e limites da amostra | `sales_tickets`, `quality_summary` |
| Dados e KPIs | Fórmula, interpretação, fonte e estado de cada indicador | Dataset `ds_kpi_dictionary` na aba Data |

Os cartões agora trazem uma análise curta na mesma página. A visão executiva destaca também itens por venda, posições de estoque em alerta, validações com falha e idade dos dados. Estoque separa quantidade a vencer, quantidade vencida e lotes sem custo; o valor monetário agregado permanece vazio quando o custo de algum lote estiver ausente. A página de confiabilidade apresenta regras verificadas, regras com falha, achados inválidos e horas desde o corte da origem.

Na **aba Data** do dashboard, `ds_period`, `ds_inventory` e `ds_payment` expõem os dados que alimentam os KPIs comerciais e de estoque. `ds_operations`, `ds_counts` e `ds_destinations` expõem os KPIs e detalhes operacionais; `ds_reliability` e `ds_kpi_dictionary` mostram a confiabilidade e o contrato semântico. O dicionário não contém valores simulados. Os novos indicadores permanecem sem valor até que a carga diária publique eventos reais.

Filtros globais: período e loja. O período afeta métricas de vendas; estoque representa o lote mais recente e não deve mudar quando a data da venda muda. A variação percentual de receita fica nula quando o período anterior tem receita zero.

## Regras de interpretação

- Venda = transação `COMPLETED`; receita = `net_amount` reconciliada com subtotais dos itens e pagamentos por venda.
- Estoque = soma dos lotes publicados; valor = quantidade em mãos vezes custo médio. É valor de estoque, não receita.
- A situação do estoque indica vencido, vencimento em 30 dias ou abaixo do mínimo informado pela origem. É sinal de atenção, não previsão de perda.
- Frescor expõe `batch_id`, corte e publicação, para distinguir fotografia diária de tempo real.
- A origem tem somente um dia de vendas e uma loja vendedora. Linha, barras, histograma e boxplot funcionam, mas não justificam tendência ou dispersão de mercado.
- Nenhuma loja possui coordenadas. O mapa é condicional no requisito da disciplina e foi omitido do painel até haver geocodificação confiável; `06_store_map.sql` permanece como consulta opcional.

## Aceite

Em 30/10/2026, a versão com 14 datasets e seis páginas canvas foi publicada no mesmo dashboard. O [job de validação 158784198667118](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/158784198667118?o=7474654317437663) concluiu preflight, Bronze, Silver, Gold e refresh com sucesso. Os datasets `ds_operations`, `ds_counts`, `ds_destinations` e o dicionário passaram no SQL Warehouse. Os oito fatos novos ainda tinham zero linhas na origem analítica; cartões de eventos retornaram `NULL` e as tabelas de detalhe, zero linhas. A inspeção visual no navegador continua pendente porque o console bloqueia controle automatizado.

Na versão anterior, os nove datasets embutidos e as duas consultas opcionais foram executados no SQL Warehouse com parâmetros explícitos; o mapa opcional retornou zero pontos. O redesenho contém onze datasets; os dois novos passaram no SQL Warehouse, a definição passou na CI e o [run 416769418123456](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/416769418123456?o=7474654317437663) concluiu as cinco tarefas, inclusive atualização do dashboard. A publicação usa `embed_credentials=false`; cada leitor deve receber acesso ao dashboard, ao warehouse e `SELECT` em Gold. O console Databricks bloqueou a inspeção por navegador automatizado, portanto falta revisão visual manual de widgets e filtros.
