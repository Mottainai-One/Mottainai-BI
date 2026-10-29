# Relatório gerencial — Business Intelligence Mottainai

**Referência:** 29/10/2026 · **Responsável:** Ana Costa · **Fonte:** `MOTTAINAI` → RPA → `MOTTAINAI_ANALITICO` → Databricks Delta.

## Problema e arquitetura

O banco operacional recebe alterações ao longo do dia. O BI precisa de uma fotografia consistente, publicada diariamente, para evitar que gráficos consultem dados transacionais em diferentes momentos. O RPA publica no banco analítico às 02:00 de São Paulo; o job de BI lê o lote publicado às 02:30. Uma carga concluída depois dessa janela requer execução manual do job. O horário real de corte é mostrado no painel.

| Camada | Conteúdo | Controle |
|---|---|---|
| Bronze | Cópia Delta de dimensões, fatos e metadados do lote analítico | Contagem por relação e `batch_id` |
| Silver | Dimensões loja, categoria e produto; fatos vendas, itens e lotes de inventário tipados e limpos | Chaves, unicidade, medidas, coordenadas, relações e `quality_results` |
| Gold | Views de vendas diárias, tickets, produtos, estoque, frescor e qualidade sobre Silver | Reconciliação de itens, pagamentos e vendas; marcador Gold só avança após validação |

Bronze, Silver e Gold são schemas separados em `motta_analytics`, com notebooks e tarefas distintos. O painel consulta exclusivamente Gold. Nenhuma informação pessoal direta é necessária nos KPIs.

## Regras de negócio e indicadores

| Indicador | Cálculo | Leitura correta |
|---|---|---|
| Receita líquida | Soma de `net_amount` das vendas `COMPLETED`, reconciliada com subtotais dos itens e pagamentos por venda | BRL por período/loja |
| Vendas | Contagem de vendas `COMPLETED` | Transações, não itens |
| Ticket médio | Receita ÷ vendas | Nulo se não há venda |
| Variação de receita | (Receita atual ÷ receita do período anterior equivalente) − 1 | Nula se base anterior é zero |
| Valor por método de pagamento | Soma dos pagamentos vinculados a vendas concluídas | BRL; uma venda pode ter mais de um método |
| Unidades vendidas | Soma da quantidade de itens vendidos | Não confundir com número de linhas |
| Estoque disponível | Quantidade atual menos reservada, por lote | Fotografia do último lote |
| Valor de estoque | Quantidade em mãos × custo médio | Estimativa a custo, não preço de venda |
| Vencimento em 30 dias | Quantidade em lotes com validade no horizonte de 30 dias | Indicador de atenção operacional |
| Frescor | `batch_id`, corte, publicação e atualização | Indica atraso e rastreabilidade |

Filtros de período e loja afetam as vendas; estoque permanece a fotografia do último lote. Variação percentual sem período anterior é `NULL`, nunca infinito nem uma afirmação de crescimento. Histogramas e boxplots mostram tickets, mas exigem amostra variada para interpretação. O mapa do PDF é condicional: não há coordenadas válidas na origem, portanto não foi exibido um mapa vazio.

## Resultado e revisão crítica

A [execução 906604160409285](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/906604160409285?o=7474654317437663) concluiu as cinco tarefas com `SUCCESS`. No SQL Warehouse, Gold retornou **101 vendas**, **R$ 1.515,00** de receita, **R$ 15,00** de ticket médio e **101 unidades vendidas**. O inventário contém **210 unidades disponíveis**, estimadas em **R$ 2.100,00** a custo médio; os **101 pagamentos** somam **R$ 1.515,00**, todos em PIX; não há lote vencendo em 30 dias. Silver registrou **zero falhas de qualidade**.

Todos os tickets comerciais são do dia 20/10/2026, de uma loja e de um produto. O inventário tem dois lotes do mesmo produto e loja. Esses números provam que o fluxo e as fórmulas funcionam, mas não permitem inferir tendência, sazonalidade, dispersão representativa, desempenho comparativo das lojas ou risco global de estoque. O projeto deve priorizar histórico real e cobertura de produtos/lojas antes de fazer recomendações estratégicas.

## Publicação e governança

O [dashboard](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663) tem páginas executiva, comercial, estoque e distribuição/qualidade, com filtros globais. Foi publicado sem embutir credenciais; leitores precisam de acesso próprio. Os nove datasets embutidos e as duas consultas opcionais passaram no warehouse, e o job fez o refresh após Gold. A aparência e a interação dos widgets ainda dependem de inspeção manual em sessão autenticada; o navegador integrado deste ambiente abriu a tela de login.

O alerta de validade depende da quantidade, mesmo que o custo médio não esteja preenchido. Se algum lote não tiver custo, o valor monetário agregado fica indisponível e a tabela indica quantos lotes precisam de correção; não se registra uma perda fictícia de R$ 0,00.

A [execução 608262702654119](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/608262702654119?o=7474654317437663) atualizou a revisão final do dashboard após a publicação; as cinco tarefas terminaram com `SUCCESS`.

A [PR da RPA #11](https://github.com/Mottainai-One/Mottanai-RPA/pull/11) ainda precisa do fluxo de revisão/merge para ativar a correção diária na branch principal. A definição e o estado de cada indicador constam do [catálogo de KPIs](KPI_CATALOG.md). A configuração e recuperação do BI estão no [runbook](RUNBOOK.md).
