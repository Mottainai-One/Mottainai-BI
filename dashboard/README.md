# Dashboard Mottainai — contrato de publicação

O painel publicado usa apenas as views em `motta_analytics.gold`. A definição é gerada por `python dashboard/build_dashboard.py` em `mottainai_bi.lvdash.json` e mantém o mesmo ID no workspace.

## Páginas

| Página | Elementos | Fonte |
|---|---|---|
| Visão executiva | Receita líquida, vendas concluídas, ticket médio, comparação com período anterior, evolução diária, receita por loja, produtos vendidos, frescor | `sales_daily`, `sales_tickets`, `product_sales_daily`, `dashboard_freshness` |
| Comercial | Lojas e produtos com vendas, unidades vendidas, métodos usados, receita por produto e pagamentos conciliados | `sales_daily`, `product_sales_daily`, `payment_mix` |
| Estoque | Produtos com alerta por loja, unidades disponíveis, valor a custo médio, vencimento em 30 dias, situação por produto e lotes | `inventory_health`, `inventory_batches` |
| Distribuição e qualidade | Histograma e boxplot de tickets, contagens de validação Silver e limites da amostra | `sales_tickets`, `quality_summary` |
| Dados e KPIs | Fórmula, interpretação, fonte e estado de cada indicador | Dataset `ds_kpi_dictionary` na aba Data |

Os cartões agora trazem uma análise curta na mesma página. A visão executiva destaca também itens por venda, posições de estoque em alerta, validações com falha e idade dos dados. Estoque separa quantidade a vencer, quantidade vencida e lotes sem custo; o valor monetário agregado permanece vazio quando o custo de algum lote estiver ausente. A página de confiabilidade apresenta regras verificadas, regras com falha, achados inválidos e horas desde o corte da origem.

Na **aba Data** do dashboard, `ds_period`, `ds_inventory` e `ds_payment` expõem os dados que alimentam os KPIs comerciais e de estoque. Os novos datasets `ds_reliability` e `ds_kpi_dictionary` mostram, respectivamente, métricas de confiabilidade e o contrato semântico de cada KPI, inclusive os ainda indisponíveis. O dicionário não contém valores simulados.

Filtros globais: período e loja. O período afeta métricas de vendas; estoque representa o lote mais recente e não deve mudar quando a data da venda muda. A variação percentual de receita fica nula quando o período anterior tem receita zero.

## Regras de interpretação

- Venda = transação `COMPLETED`; receita = `net_amount` reconciliada com subtotais dos itens e pagamentos por venda.
- Estoque = soma dos lotes publicados; valor = quantidade em mãos vezes custo médio. É valor de estoque, não receita.
- A situação do estoque indica vencido, vencimento em 30 dias ou abaixo do mínimo informado pela origem. É sinal de atenção, não previsão de perda.
- Frescor expõe `batch_id`, corte e publicação, para distinguir fotografia diária de tempo real.
- A origem tem somente um dia de vendas e uma loja vendedora. Linha, barras, histograma e boxplot funcionam, mas não justificam tendência ou dispersão de mercado.
- Nenhuma loja possui coordenadas. O mapa é condicional no requisito da disciplina e foi omitido do painel até haver geocodificação confiável; `06_store_map.sql` permanece como consulta opcional.

## Aceite

Na versão anterior, os nove datasets embutidos e as duas consultas opcionais foram executados no SQL Warehouse com parâmetros explícitos; o mapa opcional retornou zero pontos. O [run 906604160409285](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/906604160409285?o=7474654317437663) validou o modelo 5 e o [run 608262702654119](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/608262702654119?o=7474654317437663) atualizou aquela publicação. O redesenho contém onze datasets e exige nova validação no SQL Warehouse e revisão visual após publicação. A publicação usa `embed_credentials=false`; cada leitor deve receber acesso ao dashboard, ao warehouse e `SELECT` em Gold.
