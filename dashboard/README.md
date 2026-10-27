# Dashboard Mottainai — contrato de publicação

## Página 1: Visão executiva

| Elemento | Dataset | Configuração |
|---|---|---|
| Receita líquida | `01_kpi_period.sql` | Counter `revenue_brl`, moeda BRL |
| Vendas | `01_kpi_period.sql` | Counter `sales_count` |
| Ticket médio | `01_kpi_period.sql` | Counter `average_ticket_brl`, BRL; vazio se não houver vendas |
| Desvio de receita | `01_kpi_period.sql` | Counter `revenue_change_pct`, percentual; referência é período anterior de mesma duração |
| Evolução diária | `02_daily_sales.sql` | Line: X `sale_date`, Y `revenue_brl`; tooltip `sales_count` |
| Comparação entre lojas | `03_store_comparison.sql` | Bar: X `store_name`, Y `revenue_brl`, ordenação descendente |
| Frescor da fotografia | `07_freshness.sql` | Table/text: `source_cutoff_at`, `source_published_at`, `refreshed_at`, `batch_id`, `age_days` |

## Página 2: Estoque e distribuição

| Elemento | Dataset | Configuração |
|---|---|---|
| Risco por severidade | `05_stock_risk.sql` | Bar: X `consolidated_risk`, Y `products`; tooltip `expiration_value_brl` |
| Distribuição dos tickets | `04_ticket_distribution.sql` | Histogram: X `ticket_amount`, count no eixo Y, faixa automática |
| Variação do ticket por loja | `04_ticket_distribution.sql` | Box: X `store_name`, Y `ticket_amount`; exibir mediana e quartis |
| Lojas geográficas | `06_store_map.sql` | Point map: latitude/longitude; tamanho `revenue_brl`; mostrar apenas se houver coordenadas |

## Filtros interativos

- `:period`: **Date Range**, padrão de 30 dias (`now-30d/d` a `now/d`). Conecte às seis consultas que o usam. O filtro age antes da agregação, portanto KPIs e gráficos respondem ao mesmo intervalo.
- `:store_id`: **Numeric Integer**, seleção única, vazio = todas as lojas. Criar uma lista de opções com `SELECT store_id, store_name FROM workspace.mottainai_gold.stores ORDER BY store_name`; não permitir entrada de nome de tabela ou catálogo.
- Estoque e frescor são fotografias do lote mais recente. O filtro de período não altera seu valor; explicar isso na legenda para evitar confusão.

As consultas de distribuição usam vendas concluídas. `04_ticket_distribution.sql` liga à view `stores`, que inclui lojas sem coordenadas. O mapa, por definição, só usa `store_geography`. Se as consultas não retornarem linhas, mostrar “Sem dados para o período” e o horário da última publicação; nunca criar métricas sintéticas no painel principal.

## Critérios de aceite do painel publicado

1. Cada dataset usa somente `workspace.mottainai_gold`, sem consulta ao operacional nem à conexão federada.
2. Alterar período e loja modifica cards, linha, barras, histograma e boxplot de maneira coerente.
3. Cartões de desvio não exibem percentual quando o denominador anterior é zero.
4. O `batch_id` mostrado é igual ao de `MOTTAINAI_ANALITICO.mottainai_analytics.vw_published_batch`.
5. Um run falho não muda o `batch_id` de Gold; um run bem-sucedido publica todas as visualizações do mesmo lote.
6. O dashboard exibe legenda “Fotografia diária, corte às 02:00 de São Paulo (horário efetivo na tabela de frescor)”.
7. Guardar o link publicado e imagens da configuração e dos resultados no documento de entrega. Publicar com as permissões mínimas necessárias à equipe; não habilitar acesso público sem decisão explícita.

**Estado:** datasets e especificação versionados. O painel no workspace e sua execução com dados reais devem ser validados antes de marcar este item como concluído.
