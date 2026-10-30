# Catálogo de indicadores do BI Mottainai

**Referência dos dados:** lote analítico disponível em 29/10/2026. **Fonte oficial do painel:** views Delta em `motta_analytics.gold`, alimentadas por Silver e pelo banco físico `MOTTAINAI_ANALITICO`. **Frequência:** fotografia diária após a carga das 02:00 de São Paulo e o job BI das 02:30. O corte efetivo aparece em `dashboard_freshness`.

Este catálogo separa indicadores calculáveis e verificáveis hoje daqueles que dependem de instrumentação. A existência de uma view antiga ou de uma tabela vazia não autoriza apresentar seu resultado como desempenho real.

## Indicadores publicados

| Pergunta de decisão | KPI | Fórmula e população | Grão, unidade e limite |
|---|---|---|---|
| Quanto vendemos? | Receita líquida | Soma de `net_amount` em `fact_sales` com `status='COMPLETED'`; concilia com subtotais de itens e pagamentos por venda | Período e loja; BRL. Não inclui vendas canceladas |
| Quantas compras ocorreram? | Vendas concluídas | Contagem distinta das vendas concluídas | Período e loja; transações |
| Como evolui o valor por compra? | Ticket médio | Receita líquida ÷ vendas concluídas | BRL por venda; nulo se não há vendas |
| Qual o tamanho da cesta? | Itens por venda | Soma de `item_count` das vendas concluídas ÷ vendas concluídas | Itens registrados por compra; nulo sem vendas. Diferente de unidades vendidas |
| Houve crescimento? | Variação da receita | (Receita atual − receita do período anterior de mesma duração) ÷ receita anterior | Fração/percentual; nulo se denominador zero; marcar período parcial |
| Quais lojas e produtos participam? | Lojas com vendas e produtos vendidos | Contagem distinta de loja e produto com venda concluída | Contagens de cobertura do período, não taxa de conversão; exibir junto ao volume |
| O que gera receita? | Receita e unidades por produto | Soma de subtotal e quantidade dos itens de vendas concluídas | Produto, loja e dia; BRL e unidades; sem margem confiável |
| Como o cliente pagou? | Valor por método | Soma dos pagamentos das vendas concluídas, após conciliação por venda com `net_amount` | Método, loja e dia; BRL. Uma venda pode ter mais de um método; não somar `sales_with_method` como vendas únicas |
| Quanto temos para vender? | Estoque em mãos e disponível | Soma de quantidade; disponível = quantidade − reservada | Última fotografia por loja e produto; unidades |
| Quantas unidades exigem atenção por validade? | Unidades a vencer e vencidas | Soma das quantidades dos lotes com validade em até 30 dias ou já ultrapassada, na data da fotografia | Unidades; exposição física, não perda prevista |
| Onde agir no estoque? | Abaixo do mínimo, vencido, vence em 30 dias | Compara disponível ao mínimo da origem; agrupa valor dos lotes pela validade relativa à data da fotografia | Produto e loja; status explícito. O horizonte de 30 dias é regra operacional do painel, não previsão de perda |
| Qual o valor exposto? | Valor de estoque e a vencer | Quantidade em mãos × custo médio; valor em lotes com validade em até 30 dias | BRL a custo; não é receita, margem nem perda realizada |
| Quão atual é o painel? | Frescor e qualidade | Identifica `batch_id`, corte/publicação da origem, atualização Gold e falhas Silver | Lote e relação; distinguir zero, ausência de dados e falha de consulta |
| Quanto tempo passou desde o corte? | Idade dos dados | Horas entre `source_cutoff_at` e o instante da consulta | Horas; cresce até a próxima carga, não indica tempo real |
| As regras de transformação passaram? | Validações com falha e achados inválidos | Conta regras Silver com `invalid_rows > 0` e soma achados | Regras e achados; um registro pode aparecer em várias regras. Zero falhas não prova acuracidade física |

O alerta de validade depende da **quantidade do lote**, mesmo quando o custo médio está ausente. Nesse caso, a quantidade em risco permanece visível e o valor monetário fica indisponível; não converter custo desconhecido em perda igual a zero.

**Comportamento dos filtros:** período e loja afetam vendas, produto e pagamento. Estoque usa a última fotografia e recebe apenas o filtro de loja. Uma seleção de data não altera estoque.

O dashboard inclui uma página **Dados e KPIs** e, na aba **Data**, os datasets `ds_reliability` e `ds_kpi_dictionary`. O dicionário apresenta fórmula, interpretação, fonte e situação de publicação, inclusive para indicadores ainda sem fonte; esses não recebem números fictícios.

## O que os dados permitem afirmar agora

O analítico tem 101 vendas e 101 itens de venda, todos em um dia; 101 pagamentos, todos em PIX; 100 lojas carregadas, mas apenas uma com venda; um produto vendido; dois lotes de inventário. A receita é R$ 1.515,00, o ticket médio R$ 15,00 e o valor de estoque R$ 2.100,00. Esses dados validam o cálculo e a conciliação. Não demonstram tendência, sazonalidade, diferença entre lojas, preferência de pagamento ou variedade de catálogo.

Também foram conferidas contagens no banco operacional: movimento de estoque, transferências, execuções de reposição e clientes retornaram zero. Portanto, ampliar a cópia dessas fontes hoje não criaria novos resultados; será útil quando a aplicação passar a registrar esses eventos.

## Indicadores preparados, mas ainda indisponíveis para decisão

| Área e views antigas | Dependência para publicar com rigor | Situação observada |
|---|---|---|
| Comercial: `vw_sales_trend`, `vw_store_performance` | Várias datas e lojas com vendas; períodos equivalentes | Um dia e uma loja vendedora. Gráficos técnicos existem, leitura de tendência bloqueada |
| Estoque: `vw_inventory_turnover`, `vw_stockout_analysis`, `vw_product_risk_ranking` | Movimentos e vendas por SKU/loja durante janela suficiente; estoques sucessivos; regra de ruptura | Movimento: 0 linhas; inventário: 2 lotes de um SKU. Expor apenas situação atual |
| Estoque: `vw_expiration_loss_forecast` | Histórico de validade, venda e descarte, método de previsão validado | Descartes: 0. Expor valor a vencer, sem chamar de perda prevista |
| Operacional: `vw_replenishment_performance`, `vw_transfer_analysis`, `vw_transfer_effectiveness` | Solicitação, execução, status, datas e resultado por ação | Reposição e transferência: 0 linhas |
| IA: `vw_ai_performance`, `vw_ai_recommendation_effectiveness`, `vw_saved_value` | Previsões, recomendações, aceites, execução e grupo comparável/contrafactual | 3 modelos cadastrados, 0 previsões/recomendações/feedback. Valor salvo não pode ser inferido |
| Sustentabilidade: `vw_sustainability_impact`, `vw_sustainability_dashboard` | Perdas realizadas, destino, peso/unidade e fator de conversão com fonte | Destinos de perda e resultados de promoção: 0 linhas |
| Cliente: `vw_customer_loyalty_analysis`, `vw_customer_purchase_behavior` | Identificador pseudonimizado estável, consentimento e histórico de recompra | Dimensão cliente e eventos de fidelidade: 0 linhas. Nenhum dado pessoal é copiado ao BI atual |

## Próximos dados a instrumentar

1. Confirmar que a carga operacional → analítico continua publicando pagamentos por venda e adicionar testes de reconciliação ao contrato RPA. O fato já existe no analítico, portanto não foi necessário ler o operacional diretamente para o novo KPI.
2. Alimentar `fact_inventory_movement`, `fact_transfer`, `fact_replenishment` e `fact_loss_destination` com eventos reais, estados e datas. Só então calcular giro, atendimento de reposição, eficácia de transferência e perda.
3. Ligar recomendações de IA a ações e resultados observados; definir comparação apropriada antes de reportar valor economizado.
4. Para análises de cliente, aprovar finalidade e minimização de dados, usar chave pseudonimizada e garantir histórico suficiente. Não copiar email ou telefone para Gold.

**Regra de promoção:** todo KPI novo deve ter dono, fórmula, população, grão, unidade, janela, fonte, teste de reconciliação e estado de dado insuficiente. O dashboard só recebe indicadores que passaram nesses critérios.
