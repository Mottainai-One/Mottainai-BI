# Mottainai BI no Databricks

## Onde encontrar

| Componente | Local ou acesso | Função |
|---|---|---|
| Artefatos do BI | `Workspace > Users > ana.costa@institutojef.org.br > MOTTAINAI > BI` | Notebooks, documentação operacional e definição versionada do dashboard |
| Dashboard publicado | [Mottainai — Inteligência Comercial, Estoque e Operações](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663) | Indicadores e análises gerenciais |
| Job de atualização | [mottainai-analytics-to-medallion](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663) | Orquestra preflight, Bronze, Silver, Gold e atualização do dashboard |
| Conexões PostgreSQL | `Catalog > Connect > Connections` | Conexões Unity Catalog usadas pelo job |
| Catálogo analítico Delta | `motta_analytics` | Catálogo gerenciado das camadas e tabelas de BI |

## Conexões e fontes

| Nome da conexão | Banco PostgreSQL | Uso pelo BI |
|---|---|---|
| `conection_motta_operacional` | `MOTTAINAI` | Preflight: valida disponibilidade/conectividade do operacional; não alimenta datasets do dashboard diretamente |
| `motta_analytics` | `MOTTAINAI_ANALITICO` | Fonte da fotografia publicada pelo RPA e lida pela Bronze |

As conexões são objetos globais do Unity Catalog. Elas não podem ser colocadas fisicamente dentro de uma pasta do Workspace. Usuário, senha, certificado e host não devem ser copiados para notebooks ou documentação; gerencie credenciais na configuração das conexões.

## Fluxo de publicação

```text
MOTTAINAI (operacional)
    └─ RPA operacional → analítico — diariamente às 02:00, America/Sao_Paulo
          └─ MOTTAINAI_ANALITICO (publicação PostgreSQL)
                └─ Databricks BI — diariamente às 02:30, America/Sao_Paulo
                      ├─ preflight: conexões e lote publicado
                      ├─ Bronze: cópia do lote imutável e metadados de origem
                      ├─ Silver: tipos, normalização e verificações de qualidade
                      ├─ Gold: fatos agregados e KPIs reconciliados
                      └─ refresh_dashboard: atualização do dashboard publicado
```

O intervalo de 30 minutos permite que o RPA termine e publique um lote antes do início do BI. Os notebooks só promovem uma publicação marcada como `analytics_mart_v1`; Bronze, Silver e Gold guardam o `batch_id`, e Gold só publica após as reconciliações. O dashboard consulta exclusivamente Gold, para que todos os widgets mostrem o mesmo lote confirmado. O job é um workflow multi-tarefa do Databricks que implementa a orquestração do pipeline; não existe um segundo Lakeflow Declarative Pipeline paralelo.

## Camadas e responsabilidades

| Schema Unity Catalog | Conteúdo |
|---|---|
| `motta_analytics.bronze` | Cópia Delta das dimensões, fatos e views de referência do lote PostgreSQL publicado, com `batch_id`, corte, horário de publicação e ingestão |
| `motta_analytics.silver` | Dimensões e fatos normalizados, chaves tipadas e resultados de qualidade/reconciliação |
| `motta_analytics.gold` | Conjuntos de dados semânticos usados pelo dashboard: vendas, ticket, mix de pagamentos, produtos, estoque e eventos operacionais |
| `motta_analytics.control` | Marcadores de publicação por camada, versão do modelo e controle de consistência do lote |

O dashboard não consulta o PostgreSQL operacional nem o analítico diretamente para métricas. A cópia para Bronze vem do banco analítico, que já recebeu a carga diária do operacional via RPA. Isso preserva o corte, evita consultas ad hoc ao banco transacional e mantém a linhagem do indicador.

## Operação e validação

- Agenda do RPA: 02:00 no fuso `America/Sao_Paulo`.
- Agenda do Databricks: 02:30 no fuso `America/Sao_Paulo`; `max_concurrent_runs=1`.
- Job ID: `731348243647869`.
- Dashboard ID: `01f1d22904b81b738aef457d6a67f354`.
- Warehouse do refresh: `64bc14de5692c645`.
- Em execução manual, confirme primeiro um novo lote `SUCCEEDED` com contrato `analytics_mart_v1` em `MOTTAINAI_ANALITICO`.
- A publicação Gold deve permanecer no lote anterior quando Bronze/Silver ou reconciliação falhar; corrija a origem e reexecute o job após nova publicação.
- A execução bem-sucedida mais recente precisa ser conferida no histórico do job; uma execução histórica não comprova que a próxima carga diária ou as permissões de todos os leitores funcionarão.

### Estado verificado em 31/10/2026

- Execução manual de validação `909464105670105`: as cinco tarefas concluíram com sucesso usando os notebooks em `MOTTAINAI/BI`; o refresh do dashboard concluiu.
- Lote selecionado: `e9c132d3-9eda-46cd-b7c4-955ea0f8f83f`, versão do modelo Silver/Gold `6`.
- As duas conexões PostgreSQL constam ativas no Unity Catalog.
- Na fonte analítica, `dim_company` e `dim_store` têm 500 linhas cada; `dim_product`, vendas, itens de venda, pagamentos, inventário, contagens e transferências estão vazios.
- Consequentemente, `gold.sales_daily` e `gold.inventory_health` retornam zero linhas. A orquestração e o refresh funcionaram, mas os KPIs comerciais e de estoque ainda não representam atividade real até as tabelas fato receberem dados válidos no operacional e esse dado ser publicado pelo RPA.

O acesso de outros membros da equipe depende das permissões da pasta `MOTTAINAI`, do dashboard, do SQL Warehouse e das tabelas Gold. A organização dos artefatos não amplia essas permissões automaticamente.
