# Relatório gerencial — Business Intelligence Mottainai

**Referência:** 27/10/2026 · **Responsável:** Ana Costa · **Fonte:** PostgreSQL operacional `MOTTAINAI`, PostgreSQL analítico `MOTTAINAI_ANALITICO` e camadas Delta no Databricks.

## 1. Problema e decisão de negócio

O operacional muda durante o dia. Consultá-lo diretamente em cada gráfico gera carga transacional e mistura momentos diferentes do negócio. O objetivo do BI é acompanhar vendas, ticket médio, lojas e risco de ruptura/validade sobre **uma fotografia publicada**, para priorizar decisões de estoque e acompanhar a evolução comercial. Os números não representam tempo real. O corte é o instante em que o RPA começa a leitura diária, nominalmente às 02:00 em `America/Sao_Paulo`, incluindo mudanças até esse instante.

## 2. Base e linhagem

```text
MOTTAINAI (transacional)
  └─ RPA operacional → analítico, transação e reconciliação
       └─ MOTTAINAI_ANALITICO.mottainai_analytics
            ├─ dimensões dim_store/dim_company
            ├─ fatos fact_sales/fact_inventory_snapshot
            ├─ views de negócio e vw_published_batch
            └─ Databricks Job: preflight → Bronze → Silver → Gold
                 └─ AI/BI Dashboard (somente Gold)
```

O marcador de publicação consumido pelo pipeline é o registro mais recente de `job_log` com `status='SUCCEEDED'`, `cutoff_at` preenchido e `metadata.publication_contract='analytics_mart_v1'`. A view `vw_published_batch` é uma interface auxiliar do mart e deve apontar para o mesmo lote. O pipeline não usa os lotes legados nem lê o operacional para calcular métricas. A conexão operacional aparece apenas no preflight. O mesmo serviço Aiven hospeda os dois bancos físicos; a separação é por database, não por host.

**Granularidade:** `fact_sales` = uma venda por `sale_id` e `sale_date`; `vw_sales_daily_kpis` = data/empresa/loja; `vw_monthly_summary` = mês/loja; `vw_critical_stock` = item de estoque abaixo do mínimo. `dim_store` fornece atributos de localização e ligação com a empresa. As chaves do mart preservam as chaves operacionais; dados pessoais diretos não entram nas consultas Gold. A cópia Bronze de `fact_sales` exclui `customer_id` e `employee_id`.

## 3. Tratamento e controles

| Etapa | Regra | Falha |
|---|---|---|
| Preflight | Confere `current_database()` nas duas conexões, sem copiar o operacional | Job falha antes da ingestão |
| Bronze | Copia o lote publicado e compara contagens de cada relação | Não move o ponteiro Bronze |
| Silver | Tipos, texto sem espaços nas pontas, chaves obrigatórias, medidas válidas, coordenadas no intervalo e unicidade das chaves de negócio | Registra contagem em `rejected_rows`; Gold antigo permanece publicado |
| Relações | Cada loja com venda deve existir em `dim_store` | Gold antigo permanece publicado |
| Gold | Views apontam apenas ao `batch_id` de `mottainai_control.publication` | Ponteiro só muda após todas as tabelas Silver passarem |
| Frescor | Expõe horário de corte, publicação da origem e atualização BI | Usuário identifica fotografia defasada |

Valores negativos em `current_quantity` são preservados para investigação; `minimum_quantity` negativo é rejeitado. Um dia com todas as vendas canceladas pode ter medidas de receita nulas na view de origem e zero vendas válidas; o relatório interpreta isso como ausência de vendas, sem fabricar receita. `discount_amount` do mart é preenchido com zero pelo RPA por falta de fonte operacional confiável; **não é apresentado como desconto real**.

## 4. KPIs e interpretação

| KPI | Definição | Grão e unidade | Limite |
|---|---|---|---|
| Receita líquida | Soma de `net_revenue` da view diária (vendas `COMPLETED`) | Período, loja; BRL | Fatos podem estar vazios se ainda não houve venda na aplicação |
| Vendas | Soma de `sale_count` | Período, loja; transações | Canceladas/devolvidas excluídas |
| Ticket médio | Receita líquida ÷ número de vendas | Período, loja; BRL | Nulo quando não há venda |
| Variação de receita | (Receita atual − receita do período anterior equivalente) ÷ receita anterior | % | Nula quando base anterior é zero |
| Itens em venda | Soma de `item_count` | Período; linhas de item | Não equivale necessariamente à soma das quantidades vendidas |
| Risco de estoque | Contagem de pares loja/produto por `consolidated_risk` | Fotografia mais recente | Depende de inventário e vendas alimentados |
| Distribuição de ticket | `net_amount` de vendas concluídas | Venda; BRL | Histogramas e boxplots só fazem sentido com amostra suficiente |
| Frescor | Horários de corte/publicação/atualização e idade em dias | Lote | Deve aparecer no dashboard |

Para evitar conclusões falsas, cartões devem mostrar **“Sem dados”** quando a base de vendas estiver vazia e não tratar `0` como prova de desempenho comercial. O mapa usa apenas lojas com latitude/longitude válidas e deve indicar quantas lojas ficaram fora por ausência de coordenadas.

## 5. Dashboard

O dashboard é especificado em `dashboard/README.md`; cada dataset SQL versionado lê apenas `workspace.mottainai_gold`. Ele deve conter cards de receita, vendas e ticket médio com desvios; linha da evolução diária; barras de comparação por loja e risco; histograma e boxplot de ticket; mapa de lojas quando houver coordenadas; filtro de período e loja; indicador do lote e horário de corte. Os parâmetros de período e loja são aplicados **antes** das agregações, de modo que cards e gráficos respondam aos mesmos filtros.

## 6. Automação e evidência exigida

O bundle `databricks.yml` define um job serverless de três tarefas com concorrência máxima de uma execução. O RPA publica o analítico às 02:00; a agenda de contingência do Databricks está definida às 02:30 em São Paulo e fica pausada até o primeiro teste real. A publicação fora do horário deve acionar o job via `run-now` **após** o commit do RPA. A versão de Gold só muda após todas as validações.

Para comprovar a entrega no workspace, guardar: URL e ID do job, tela da configuração das três tarefas e agenda; histórico do run com status e durações; consultas de contagem Bronze/Silver/Gold; `dashboard_freshness.batch_id` igual ao PostgreSQL; URL do dashboard publicado, filtros e gráficos funcionando. **Código e CI não substituem esse teste com dados reais.**

## 7. Revisão crítica atual

A última verificação informada pela equipe em 26/10/2026 mostrou `dim_company=101`, `dim_store=100`, `fact_sales=0` e `fact_inventory_snapshot=0` no analítico. Isso não prova falha: as fontes de venda e estoque podem ainda não ter registros válidos. Também não permite apresentar gráficos de distribuição e receita como resultados observados. Antes da apresentação, executar uma carga publicada pelo contrato `analytics_mart_v1`, conferir as contagens com a origem e produzir vendas/estoque de teste **identificados como QA** se o sistema ainda não gerou eventos reais. Não usar valores inventados como produção.

O acesso ao workspace Databricks ainda precisa confirmar a execução do job e o dashboard. O estado de implantação deve ser atualizado neste relatório apenas com os IDs e evidências reais.
