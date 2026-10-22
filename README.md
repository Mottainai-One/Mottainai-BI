# Mottainai BI no Databricks

Este repositório versiona a camada de BI. O RPA existente publica a carga diária das 02:00 no PostgreSQL **analítico físico**; o Databricks lê apenas a publicação concluída, prepara tabelas Delta em Bronze e Silver e expõe views Gold para dashboards. O PostgreSQL operacional é consultado somente no teste de conexão.

```text
PostgreSQL operacional ──RPA 02:00──> PostgreSQL analítico
          │                                  │
          └── teste de conexão               └── catálogo federado, somente leitura
                                                │
                                                ▼
                                   Bronze → Silver → Gold → dashboard
```

O job está em [databricks.yml](databricks.yml). Ele possui preflight e refresh, com agenda de contingência às **02:30 em America/Sao_Paulo**, inicialmente pausada até a validação das conexões. Executar manualmente o job após uma publicação analítica também é seguro: o `batch_id` evita processamento duplicado. A atualização por evento após qualquer publicação fora do horário exige conectar o final bem-sucedido do RPA à API `run-now` do job; essa integração depende do ID do job implantado e ainda não está ativa.

## Preparação do workspace

1. Confirme que existem dois catálogos estrangeiros PostgreSQL distintos: um aponta ao banco operacional, outro ao banco analítico físico. Eles são somente leitura no Databricks. A conexão ao analítico precisa enxergar `mottainai_analytics.vw_published_batch`, `vw_sales_daily_kpis`, `vw_monthly_summary` e `vw_critical_stock`.
2. Escolha um catálogo gerenciado existente para as tabelas Delta, por exemplo `workspace` no Free Edition. O preflight cria os schemas `mottainai_bronze`, `mottainai_silver`, `mottainai_gold` e `mottainai_control` nesse catálogo.
3. Configure as variáveis do bundle `operational_catalog`, `analytics_catalog` e `target_catalog`. Nunca coloque usuário, senha ou host dos bancos no Git; as conexões Unity Catalog já guardam essas informações.
4. Valide o bundle e execute o job manualmente após existir um lote `PUBLISHED` no analítico. Confira a view Gold `dashboard_freshness` e compare seu `batch_id` com a view PostgreSQL `vw_published_batch`.
5. Depois de validar a duração da carga das 02:00, ative a agenda de contingência no job. Para atualização por evento, configure a chamada do RPA ao job **somente depois** da publicação do lote e crie a tarefa de refresh do dashboard publicado como dependente do refresh Gold.

O preflight e as regras de limpeza estão nos [notebooks](notebooks). O [runbook](docs/RUNBOOK.md) traz as consultas de verificação e as condições de publicação.

## Datasets iniciais

| Origem no banco analítico | Bronze | Silver | Gold |
|---|---|---|---|
| `vw_sales_daily_kpis` | cópia por lote | datas, IDs e medidas tipadas; rejeita valores negativos e chaves nulas | vendas diárias por loja |
| `vw_monthly_summary` | cópia por lote | mês e medidas tipadas; rejeita chaves nulas e medidas negativas | resumo mensal |
| `vw_critical_stock` | cópia por lote | quantidades tipadas; sinaliza estoque negativo e rejeita limiar inválido | estoque crítico |

As demais views prioritárias (`vw_stockout_analysis`, `vw_product_risk_ranking`, `vw_executive_dashboard` e `mv_dashboard_metrics`) serão incluídas após conferir os respectivos contratos e uma execução real no workspace. O dashboard deve consultar **somente Gold**, nunca o operacional nem os catálogos federados.

## Estado

Os arquivos estão preparados no Git. A implantação, a execução real contra os dois catálogos e a criação do dashboard dependem de acesso ao workspace Databricks. Sem essa execução, não há confirmação de conectividade ou de dados publicados.
