# Mottainai BI — Databricks

Este repositório versiona o pipeline e as consultas do dashboard de Business Intelligence. A fonte de negócio é o banco físico `MOTTAINAI_ANALITICO` no Aiven. O banco `MOTTAINAI` recebe transações; o RPA publica uma fotografia no analítico às 02:00 de São Paulo. O Databricks lê **apenas um lote analítico concluído**, transforma Bronze → Silver → Gold e o dashboard consulta somente Gold.

```text
MOTTAINAI → RPA transacional → MOTTAINAI_ANALITICO
                               → preflight → Bronze → Silver → Gold → dashboard
```

## Entrega acadêmica

- [Relatório gerencial](docs/RELATORIO_GERENCIAL.md): base, problema, limpeza, definições de KPIs, limites e evidências.
- [Datasets e especificação do dashboard](dashboard/README.md): cards, linha, barras, histograma, boxplot, mapa condicional, filtros.
- [Runbook](docs/RUNBOOK.md): implantação, execução, validação e recuperação.
- [Bundle Databricks](databricks.yml): job serverless com três tarefas sequenciais e agenda de contingência às 02:30 `America/Sao_Paulo`, **pausada** até validação real.

Os notebooks usam `remote_query` nas conexões Unity Catalog `conection_motta_operacional` e `motta_analytics`, indicando explicitamente os databases `MOTTAINAI` e `MOTTAINAI_ANALITICO`. Isso evita o limite de 100 objetos por schema do catálogo estrangeiro no Free Edition. Usuário e senha permanecem na conexão do Databricks, não neste repositório.

## Estado verificável

O código está versionado e a CI confirma sintaxe/estrutura. A execução do job, a publicação do dashboard e as evidências dos resultados **dependem de acesso autenticado ao workspace**. O último teste informado em 26/10/2026 mostrou `fact_sales=0` e `fact_inventory_snapshot=0` no analítico; portanto, receitas e distribuições não podem ser apresentadas como observadas sem nova carga ou eventos de QA. Não misturar dados demonstrativos com produção.

Uma atualização fora das 02:00 exige chamar o job Databricks após o commit do RPA. A agenda 02:30 é uma contingência, não garante atualização por evento. Depois de criar e publicar o dashboard, adicione uma tarefa `Dashboard` ao job dependente de `refresh_medallion` para atualizar o cache; o dashboard exige warehouse serverless ou pro.
