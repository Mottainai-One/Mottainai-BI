# Mottainai BI — Databricks

Camada de BI do Mottainai que transforma a fotografia publicada no PostgreSQL analítico em dados Delta e um dashboard no Databricks. O operacional é consultado no preflight para verificar a conexão; os gráficos usam somente os dados analíticos publicados.

## Visão geral

O RPA carrega o banco `MOTTAINAI_ANALITICO` a partir do operacional. O job de BI busca um lote concluído e executa cinco tarefas sequenciais:

```text
preflight → bronze → silver → gold → refresh_dashboard
```

| Etapa | Responsabilidade |
|---|---|
| Preflight | Verifica as conexões e a existência de publicação analítica válida. |
| Bronze | Lê os dados analíticos por `remote_query` e os copia para tabelas Delta, reconciliando contagens. |
| Silver | Tipifica, limpa e valida dimensões e fatos antes de publicar a camada. |
| Gold | Cria métricas de vendas e estoque com um único lote visível ao dashboard. |
| Dashboard | Atualiza o painel publicado após a conclusão de Gold. |

As camadas ficam nos schemas `bronze`, `silver` e `gold` do catálogo gerenciado; `control` guarda os marcadores de publicação. A configuração padrão do repositório usa `motta_analytics` como catálogo de destino.

## Publicação e qualidade

O pipeline considera o `batch_id` e o contrato `analytics_mart_v1` do `job_log` analítico, com status `SUCCEEDED`. Se não houver lote válido, os notebooks preservam a publicação anterior. As etapas usam marcadores por lote para permitir reexecução e não avançam Gold quando a qualidade ou a reconciliação falham.

O dashboard consulta views Gold, incluindo `sales_daily`, `sales_tickets`, `product_sales_daily`, `inventory_health`, `inventory_batches` e `dashboard_freshness`. A definição dos datasets, filtros e páginas está em [dashboard/README.md](dashboard/README.md).

## Dashboard e limites dos dados

O painel tem três páginas: visão executiva, estoque, e distribuição/qualidade. Os filtros globais são período e loja; estoque representa a fotografia mais recente, não uma série histórica de vendas.

O relatório de entrega registra que a amostra validada em 29/10/2026 tinha um dia de vendas e uma loja vendedora. Ela não sustenta conclusões sobre tendência, sazonalidade ou comparação ampla entre lojas. O mapa é condicional porque a origem consultada não tinha coordenadas válidas. O [relatório de entrega](docs/ENTREGA_BI.md) também registra que a verificação visual dos widgets e filtros com uma sessão autenticada ainda precisava ser feita.

## Tecnologias

- Databricks Asset Bundles, Unity Catalog e consultas PostgreSQL via `remote_query`.
- Notebooks Python/PySpark e tabelas Delta.
- PostgreSQL analítico como fonte de dados de negócio.
- Dashboard Databricks e SQL Warehouse para visualização.
- Python 3.11 e GitHub Actions para as verificações do repositório.

## Estrutura

```text
.
├── databricks.yml                     # job, parâmetros e agenda
├── notebooks/
│   ├── 01_preflight.py
│   ├── 00_bronze_analitico.py
│   ├── 01_silver.py
│   └── 02_gold.py
├── dashboard/
│   ├── build_dashboard.py
│   ├── datasets/
│   └── mottainai_bi.lvdash.json
├── docs/
│   ├── RUNBOOK.md
│   ├── ENTREGA_BI.md
│   └── RELATORIO_GERENCIAL.md
└── .github/workflows/ci.yml
```

## Configuração e execução

O [bundle](databricks.yml) declara as conexões e os bancos operacional e analítico, além do catálogo de destino. As credenciais são administradas nas conexões do Unity Catalog e não devem ser incluídas em notebooks ou no Git.

Antes de executar, confirme o acesso ao workspace, às duas conexões distintas, ao catálogo gerenciado, ao SQL Warehouse e a um lote analítico publicado. O job está configurado para 02:30 em `America/Sao_Paulo`, com uma execução simultânea.

Com o Databricks CLI autenticado, o [runbook](docs/RUNBOOK.md) documenta validação, implantação, execução manual e consultas de conferência. Para regenerar a definição versionada do painel:

```bash
python dashboard/build_dashboard.py
```

Uma carga publicada fora da janela diária requer execução do job após a confirmação do lote, conforme o runbook. Não há comprovação nesta revisão de um gatilho automático por evento.

## Testes e CI

O [workflow de CI](.github/workflows/ci.yml) compila os notebooks, regenera e valida o JSON do dashboard e verifica a configuração e a ordem das tarefas do bundle. Essas verificações estáticas não substituem a execução no workspace.

## Links úteis

- [Dashboard publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354/published?o=7474654317437663)
- [Job Databricks](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663)
- [Execução registrada em 29/10/2026](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/97850894011189?o=7474654317437663)
- [Runbook](docs/RUNBOOK.md), [relatório gerencial](docs/RELATORIO_GERENCIAL.md) e [matriz de evidências](docs/ENTREGA_BI.md).

Os registros de execução descrevem o resultado daquela data; acesso, dados e estado atual do workspace devem ser confirmados no ambiente.
