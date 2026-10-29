# Dashboard Mottainai — contrato de publicação

O painel publicado usa apenas as views em `motta_analytics.gold`. A definição é gerada por `python dashboard/build_dashboard.py` em `mottainai_bi.lvdash.json` e mantém o mesmo ID no workspace.

## Páginas

| Página | Elementos | Fonte |
|---|---|---|
| Visão executiva | Receita líquida, vendas concluídas, ticket médio, comparação com período anterior, evolução diária, receita por loja, produtos vendidos, frescor | `sales_daily`, `sales_tickets`, `product_sales_daily`, `dashboard_freshness` |
| Estoque | Unidades em mãos, disponíveis, valor estimado a custo médio, vencimento em 30 dias, produtos e lotes | `inventory_health`, `inventory_batches` |
| Distribuição e qualidade | Histograma e boxplot de tickets, contagens de validação Silver e limites da amostra | `sales_tickets`, `quality_summary` |

Filtros globais: período e loja. O período afeta métricas de vendas; estoque representa o lote mais recente e não deve mudar quando a data da venda muda. A variação percentual de receita fica nula quando o período anterior tem receita zero.

## Regras de interpretação

- Venda = transação `COMPLETED`; receita = `net_amount` reconciliada com subtotais dos itens.
- Estoque = soma dos lotes publicados; valor = quantidade disponível vezes custo médio. É valor de estoque, não receita.
- Frescor expõe `batch_id`, corte e publicação, para distinguir fotografia diária de tempo real.
- A origem tem somente um dia de vendas e uma loja vendedora. Linha, barras, histograma e boxplot funcionam, mas não justificam tendência ou dispersão de mercado.
- Nenhuma loja possui coordenadas. O mapa é condicional no requisito da disciplina e foi omitido do painel até haver geocodificação confiável; `06_store_map.sql` permanece como consulta opcional.

## Aceite

Os oito datasets embutidos foram executados no SQL Warehouse. O job [97850894011189](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/97850894011189?o=7474654317437663) concluiu as cinco tarefas, inclusive atualização do painel. A publicação usa `embed_credentials=false`; cada leitor deve receber acesso ao dashboard, ao warehouse e `SELECT` em Gold. Ainda falta registrar teste visual e dos filtros na interface com uma sessão autenticada.
