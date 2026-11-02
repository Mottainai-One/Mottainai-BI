# Dados necessários para concluir a análise de BI

Este documento registra quais tabelas ainda precisam receber dados reais para que os indicadores deixem de ser apenas tecnicamente calculáveis e passem a sustentar análises gerenciais. Não é uma autorização para fabricar registros: os eventos devem ser gerados pelo sistema, pelo fluxo operacional ou por uma carga de demonstração identificada.

## 1. Prioridade imediata — ampliar a amostra comercial

| Módulo | Tabelas operacionais | Para que os dados serão usados | Mínimo recomendado |
|---|---|---|---|
| Vendas | `sales_transaction`, `sale_item`, `sale_payment` | Receita, vendas, ticket médio, tendência, mix de produtos e pagamentos | Pelo menos 7 dias, 3 lojas, 10 produtos e 3 meios de pagamento |
| Cadastro comercial | `retail_store`, `product`, `product_category` | Comparação entre lojas, cobertura de produtos e nomes consistentes no dashboard | 3 lojas ativas e 10 produtos ativos |
| Estoque | `inventory`, `batch`, `store_product_price` | Saldo, custo, risco, validade e valor de estoque | Vários lotes, custos distintos, itens normais, vencidos e a vencer |

Sem essa diversidade, o painel funciona, mas não permite concluir tendência, sazonalidade, comparação entre lojas ou comportamento de pagamento.

## 2. Prioridade alta — preencher os fatos operacionais vazios

| Indicador | Tabelas operacionais necessárias | Tabela Gold alimentada | Dados necessários |
|---|---|---|---|
| Acuracidade de inventário | `inventory_count`, `inventory_count_item` | `inventory_count_accuracy` | Contagens concluídas, quantidade esperada, quantidade encontrada e divergência |
| Transferências | `transfer`, `transfer_item` | `transfer_execution` | Solicitações, origem, destino, itens, quantidades, status e conclusão |
| Reposição | `replenishment_pre_list`, `replenishment_pre_list_item`, `replenishment_execution`, `replenishment_execution_item` | `replenishment_fulfillment` | Sugestões, execução, quantidades sugeridas/atendidas e datas |
| Doações | `donation`, `donation_item` | `product_destinations` | Destino, produto, lote, quantidade, motivo e data |
| Descartes | `disposal`, `disposal_item` | `product_destinations` | Motivo, lote, quantidade, custo conhecido e data |
| Alertas e ações | `alert`, `suggested_action` | `alert_action_funnel` | Alertas gerados, ações sugeridas, status, resolução e datas |

Para cada fato operacional, recomenda-se registrar pelo menos 10 eventos reais ou de demonstração identificada antes de interpretar percentuais. Sem eventos, os cartões devem permanecer como “sem dados suficientes”, e não como zero operacional.

## 3. Prioridade média — mapa e análise geográfica

| Tabelas | Campos necessários | Uso |
|---|---|---|
| `address`, `retail_store`, `company` | `latitude`, `longitude`, cidade e estado válidos | Publicar o mapa de lojas e análises regionais |

O mapa só deve ser publicado quando houver coordenadas válidas. Se a origem não possuir esses dados, a ausência deve ser documentada como “não aplicável nesta versão”.

## 4. Dados para evoluções futuras do BI

Estes módulos não são necessários para os KPIs atuais, mas são necessários caso o escopo inclua comportamento de clientes, fidelidade ou sustentabilidade:

- `customer`, `customer_auth`, `customer_consent` — clientes ativos e consentimentos válidos;
- `loyalty_account`, `loyalty_transaction`, `loyalty_reward`, `loyalty_redemption` — pontos, resgates e recompensas;
- `customer_geofence` — presença ou interação geográfica, quando houver consentimento;
- `pos_shift`, `pos_cash_movement`, `pos_terminal` — operação de caixa e turnos;
- `fiscal_document`, `pos_cancel_request` — cancelamentos e documentos fiscais.

Esses dados só devem entrar no BI após validação de privacidade, consentimento e regras de anonimização.

## 5. Critério de prontidão da carga

Antes de considerar os KPIs gerenciais prontos, validar:

1. O lote foi publicado no `MOTTAINAI_ANALITICO` pelo RPA.
2. As contagens operacional → analítico conferem.
3. Bronze, Silver e Gold processaram o mesmo `batch_id`.
4. Não existem falhas de chave, duplicidade ou medidas inválidas.
5. Há dados em múltiplas datas, lojas, produtos e meios de pagamento.
6. Os oito fatos operacionais deixaram de estar vazios ou foram explicitamente marcados como sem eventos.
7. O dashboard foi atualizado e os filtros foram testados.

## 6. Resumo para o time

O bloqueio atual não é a estrutura do dashboard. É a falta de massa histórica e de eventos operacionais suficientes para interpretar os indicadores. A carga deve priorizar vendas, estoque e os oito fatos operacionais; clientes, fidelidade e sustentabilidade ficam como expansão posterior.

