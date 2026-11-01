# Mottainai BI — Databricks

O BI consome a fotografia diária de `MOTTAINAI_ANALITICO`, publicada pelo RPA a partir de `MOTTAINAI` às 02:00 em São Paulo. O job Databricks inicia às 02:30 e executa cinco tarefas sequenciais:

```text
preflight → bronze → silver → gold → refresh_dashboard
```

- **Bronze:** cópia Delta do lote analítico publicado, com contagens reconciliadas.
- **Silver:** dimensões e fatos tipados, limpeza e testes de qualidade, com marcador de publicação próprio.
- **Gold:** métricas comerciais e de estoque derivadas do Silver, com um único lote visível ao dashboard.

As três camadas ficam em `motta_analytics.bronze`, `motta_analytics.silver` e `motta_analytics.gold`; `motta_analytics.control` guarda os marcadores. O dashboard consulta apenas Gold. O banco operacional é usado no preflight para conferir a conexão, sem alimentar os gráficos diretamente. Credenciais ficam nas conexões Unity Catalog.

## Organização no workspace

Os arquivos do bundle são implantados em `Workspace/Users/ana.costa@institutojef.org.br/MOTTAINAI/BI`: `notebooks/` contém as etapas do medalhão, `dashboard/` contém a definição versionada e os datasets SQL, e `docs/` contém o runbook, o catálogo de KPIs e os critérios de publicação. O dashboard publicado permanece no mesmo diretório `MOTTAINAI` e é atualizado pelo job existente.

Conexões Unity Catalog e Jobs & Pipelines são objetos globais do workspace, não itens que possam ser aninhados numa pasta do Workspace. O guia [`docs/WORKSPACE_GUIDE.md`](docs/WORKSPACE_GUIDE.md) registra os nomes, bancos, IDs, horários e links de acesso sem guardar credenciais.

## Entregáveis

- [PR #5 da revisão de indicadores](https://github.com/Mottainai-One/Mottainai-BI/pull/5), continuação da PR #3 mesclada.
- [Dashboard publicado](https://dbc-38ac8920-cbf4.cloud.databricks.com/sql/dashboardsv3/01f1d22904b81b738aef457d6a67f354?o=7474654317437663)
- [Job Databricks](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869?o=7474654317437663)
- [Execução validada, cinco tarefas](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/906604160409285?o=7474654317437663)
- [Atualização da versão publicada](https://dbc-38ac8920-cbf4.cloud.databricks.com/jobs/731348243647869/runs/608262702654119?o=7474654317437663)
- [Catálogo de indicadores](docs/KPI_CATALOG.md), [relatório gerencial](docs/RELATORIO_GERENCIAL.md), [matriz de evidências](docs/ENTREGA_BI.md), [especificação do painel](dashboard/README.md) e [runbook](docs/RUNBOOK.md).

O dashboard apresenta quatro páginas: visão executiva, comercial, estoque e distribuição/qualidade. Há filtros globais de período e loja. A amostra atual contém somente um dia de vendas e uma loja vendedora; comparação temporal e dispersão devem ser interpretadas como testes de visualização até que exista histórico suficiente. O mapa permanece condicional porque a origem não possui coordenadas.

Uma carga concluída fora da janela diária exige executar o job Databricks manualmente após confirmar o novo lote publicado no banco analítico.
