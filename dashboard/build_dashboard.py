"""Build the versioned Mottainai AI/BI dashboard from reviewed Gold SQL."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "mottainai_bi.lvdash.json"
BRL = {"type": "number-currency", "currencyCode": "BRL", "decimalPlaces": {"type": "max", "places": 2}}
PERCENT = {"type": "number-percent", "decimalPlaces": {"type": "max", "places": 1}}


def sql_file(name):
    lines = (ROOT / "datasets" / name).read_text(encoding="utf-8-sig").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("--")).strip().rstrip(";")


def field(name, expression=None):
    return {"name": name, "expression": expression or f"`{name}`"}


def layout(widget, x, y, width, height):
    return {"widget": widget, "position": {"x": x, "y": y, "width": width, "height": height}}


def text_widget(name, lines):
    return {"name": name, "multilineTextboxSpec": {"lines": lines}}


def chart(name, dataset, kind, version, fields, encodings, title, aggregated=True):
    return {
        "name": name,
        "queries": [{"name": "main_query", "query": {
            "datasetName": dataset, "fields": fields, "disaggregated": not aggregated,
        }}],
        "spec": {"version": version, "widgetType": kind, "encodings": encodings,
                 "frame": {"showTitle": True, "title": title}},
    }


def counter(name, title, expression, target=None, fmt=None, dataset="ds_period"):
    fields = [field("value", expression)]
    encoding = {"value": {"fieldName": "value", "displayName": title}}
    if fmt:
        encoding["value"]["format"] = fmt
    if target:
        fields.append(field("previous", target))
        encoding["target"] = {"fieldName": "previous", "displayName": "Período anterior"}
    return chart(name, dataset, "counter", 2, fields, encoding, title)


def filter_widget(name, kind, title, bindings):
    queries = []
    encodings = []
    for dataset, binding, is_parameter in bindings:
        query_name = f"q_{dataset}"
        query = {"datasetName": dataset, "disaggregated": False}
        if is_parameter:
            query["parameters"] = [{"name": binding, "keyword": binding}]
            encodings.append({"parameterName": binding, "queryName": query_name})
        else:
            query["fields"] = [field(binding)]
            encodings.append({"fieldName": binding, "queryName": query_name})
        queries.append({"name": query_name, "query": query})
    spec = {"version": 2, "widgetType": kind, "encodings": {"fields": encodings},
            "frame": {"showTitle": True, "title": title}}
    if name == "filter-period":
        spec["selection"] = {"defaultSelection": {"range": {
            "dataType": "DATE", "min": {"value": "now-30d/d"},
            "max": {"value": "now/d"},
        }}}
    return {"name": name, "queries": queries, "spec": spec}


datasets = [
    {"name": "ds_period", "displayName": "KPIs de vendas por período", "queryLines": [sql_file("01_kpi_period.sql")],
     "parameters": [{"keyword": "period", "displayName": "Período das vendas", "dataType": "DATE", "complexType": "RANGE",
                     "defaultSelection": {"range": {"dataType": "DATE",
                                                    "min": {"value": "now-30d/d"},
                                                    "max": {"value": "now/d"}}}}]},
    {"name": "ds_sales", "displayName": "Vendas diárias", "queryLines": [sql_file("02_daily_sales.sql")]},
    {"name": "ds_tickets", "displayName": "Tickets concluídos", "queryLines": [sql_file("04_ticket_distribution.sql")]},
    {"name": "ds_inventory", "displayName": "Saúde do estoque", "queryLines": [sql_file("05_stock_risk.sql")]},
    {"name": "ds_product", "displayName": "Vendas por produto", "queryLines": [sql_file("08_product_sales.sql")]},
    {"name": "ds_payment", "displayName": "Pagamentos conciliados", "queryLines": [sql_file("11_payment_mix.sql")]},
    {"name": "ds_batches", "displayName": "Lotes de estoque", "queryLines": [sql_file("09_inventory_batches.sql")]},
    {"name": "ds_freshness", "displayName": "Frescor do lote", "queryLines": [sql_file("07_freshness.sql")]},
    {"name": "ds_quality", "displayName": "Qualidade Silver", "queryLines": [sql_file("10_quality.sql")]},
    {"name": "ds_reliability", "displayName": "KPIs de confiabilidade da publicação", "queryLines": [sql_file("12_kpi_reliability.sql")]},
    {"name": "ds_kpi_dictionary", "displayName": "Dicionário de KPIs e análise", "queryLines": [sql_file("13_kpi_dictionary.sql")]},
    {"name": "ds_operations", "displayName": "KPIs de operações e perdas", "queryLines": [sql_file("14_operational_kpis.sql")]},
    {"name": "ds_counts", "displayName": "Conferências físicas", "queryLines": [sql_file("15_inventory_counts.sql")]},
    {"name": "ds_destinations", "displayName": "Destinações registradas", "queryLines": [sql_file("16_operational_events.sql")]},
]

commercial = [
    layout(text_widget("commercial-header", ["# Comercial  |  Cobertura e composição\n", "\n", "O que vende, onde vende e como é pago. O filtro de período e loja se aplica a esta página."]), 0, 0, 12, 2),
    layout(counter("selling-stores", "Lojas com vendas", "COUNT(DISTINCT `store_id`)", dataset="ds_sales"), 0, 2, 3, 3),
    layout(counter("selling-products", "Produtos vendidos", "COUNT(DISTINCT `product_id`)", dataset="ds_product"), 3, 2, 3, 3),
    layout(counter("units-sold", "Unidades vendidas", "SUM(`units_sold`)", dataset="ds_product"), 6, 2, 3, 3),
    layout(counter("payment-methods", "Métodos de pagamento", "COUNT(DISTINCT `payment_method`)", dataset="ds_payment"), 9, 2, 3, 3),
    layout(text_widget("commercial-analysis-1", ["**Lojas com vendas**\n", "Cobertura observada; lojas sem venda podem estar sem operação ou sem dados."]), 0, 5, 3, 2),
    layout(text_widget("commercial-analysis-2", ["**Produtos vendidos**\n", "Amplitude do mix efetivamente vendido; não mede disponibilidade do catálogo."]), 3, 5, 3, 2),
    layout(text_widget("commercial-analysis-3", ["**Unidades vendidas**\n", "Volume dos itens conciliados; comparar com receita para entender composição."]), 6, 5, 3, 2),
    layout(text_widget("commercial-analysis-4", ["**Métodos usados**\n", "Variedade observada, sem inferir preferência com a amostra atual."]), 9, 5, 3, 2),
    layout(chart("payment-bars", "ds_payment", "bar", 3,
                 [field("payment_method"), field("paid", "SUM(`paid_amount`)")],
                 {"x": {"fieldName": "paid", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "payment_method", "scale": {"type": "categorical"}}},
                 "Valor pago por método"), 0, 7, 6, 6),
    layout(chart("product-bars", "ds_product", "bar", 3,
                 [field("product_name"), field("revenue", "SUM(`net_revenue`)")],
                 {"x": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "product_name", "scale": {"type": "categorical"}}},
                 "Receita por produto"), 6, 7, 6, 6),
    layout(text_widget("commercial-chart-note", ["**Leitura:** valores por método são pagamentos conciliados; receita por produto vem dos itens vendidos. Uma venda pode conter vários produtos ou métodos. Ainda não há base para margem por produto."]), 0, 13, 12, 2),
    layout(chart("payment-table", "ds_payment", "table", 2,
                 [field("sale_date"), field("store_name"), field("payment_method"),
                  field("payment_count"), field("sales_with_method"), field("paid_amount")],
                 {"columns": [{"fieldName": "sale_date", "displayName": "Data"},
                              {"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "payment_method", "displayName": "Método"},
                              {"fieldName": "payment_count", "displayName": "Pagamentos"},
                              {"fieldName": "sales_with_method", "displayName": "Vendas com método"},
                              {"fieldName": "paid_amount", "displayName": "Valor (BRL)", "format": BRL}]},
                 "Pagamentos conciliados", aggregated=False), 0, 15, 12, 5),
]

executive = [
    layout(text_widget("executive-header", ["# Mottainai  |  Visão executiva\n", "\n", "Resultado comercial no recorte selecionado e sinais de confiabilidade do último lote publicado."]), 0, 0, 12, 2),
    layout(counter("revenue", "Receita líquida · BRL", "SUM(`revenue_brl`)", fmt=BRL), 0, 2, 3, 3),
    layout(counter("sales", "Vendas concluídas", "SUM(`sales_count`)"), 3, 2, 3, 3),
    layout(counter("ticket", "Ticket médio · BRL", "TRY_DIVIDE(SUM(`revenue_brl`), SUM(`sales_count`))", fmt=BRL), 6, 2, 3, 3),
    layout(counter("revenue-delta", "Variação vs. período anterior", "TRY_DIVIDE(SUM(`revenue_brl`) - SUM(`previous_revenue_brl`), SUM(`previous_revenue_brl`))", fmt=PERCENT), 9, 2, 3, 3),
    layout(text_widget("executive-analysis-1", ["**Receita líquida**\n", "Vendas concluídas e conciliadas; valor realizado, sem cancelamentos."]), 0, 5, 3, 2),
    layout(text_widget("executive-analysis-2", ["**Vendas**\n", "Número de compras concluídas; não equivale a clientes distintos."]), 3, 5, 3, 2),
    layout(text_widget("executive-analysis-3", ["**Ticket médio**\n", "Receita por compra; fica sem valor quando não há vendas."]), 6, 5, 3, 2),
    layout(text_widget("executive-analysis-4", ["**Variação**\n", "Exige receita no período anterior de mesma duração."]), 9, 5, 3, 2),
    layout(counter("items-per-sale", "Itens por venda", "TRY_DIVIDE(SUM(`items_count`), SUM(`sales_count`))"), 0, 7, 3, 3),
    layout(counter("executive-stock-alerts", "Posições de estoque em alerta", "COUNT_IF(`risk_status` <> 'Sem alerta')", dataset="ds_inventory"), 3, 7, 3, 3),
    layout(counter("executive-quality", "Validações com falha", "MAX(`failing_validations`)", dataset="ds_reliability"), 6, 7, 3, 3),
    layout(counter("executive-data-age", "Idade dos dados · horas", "MAX(`data_age_hours`)", dataset="ds_reliability"), 9, 7, 3, 3),
    layout(text_widget("executive-analysis-5", ["**Itens por venda:** tamanho da cesta. **Estoque:** fotografia atual, sem filtro de data. **Validação:** falha nas regras Silver, sem provar acuracidade física. **Idade:** horas desde o corte da origem; aumenta até a próxima carga."]), 0, 10, 12, 2),
    layout(text_widget("history-note", ["**Limite da amostra:** há somente um dia com vendas e uma loja vendedora. A variação permanece vazia sem receita anterior; a linha abaixo mostra registros, não uma tendência comprovada."]), 0, 12, 12, 2),
    layout(chart("daily-trend", "ds_sales", "line", 3,
                 [field("sale_date"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "sale_date", "scale": {"type": "temporal"}},
                  "y": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL}},
                 "Receita por dia"), 0, 14, 6, 6),
    layout(chart("store-bars", "ds_sales", "bar", 3,
                 [field("store_name"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "store_name", "scale": {"type": "categorical"}}},
                 "Receita por loja com vendas"), 6, 14, 6, 6),
    layout(chart("product-sales", "ds_product", "table", 2,
                 [field("product_name"), field("category_name"), field("units_sold"), field("net_revenue")],
                 {"columns": [{"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "category_name", "displayName": "Categoria"},
                              {"fieldName": "units_sold", "displayName": "Unidades"},
                              {"fieldName": "net_revenue", "displayName": "Receita (BRL)", "format": BRL}]},
                 "Produtos vendidos", aggregated=False), 0, 20, 12, 4),
    layout(chart("publication", "ds_freshness", "table", 2,
                 [field("batch_id"), field("model_version"), field("source_cutoff_at"), field("source_published_at"), field("refreshed_at")],
                 {"columns": [{"fieldName": "batch_id", "displayName": "Lote"},
                              {"fieldName": "model_version", "displayName": "Modelo"},
                              {"fieldName": "source_cutoff_at", "displayName": "Corte da origem"},
                              {"fieldName": "source_published_at", "displayName": "Publicação no analítico"},
                              {"fieldName": "refreshed_at", "displayName": "Atualização do BI"}]},
                 "Linhagem e frescor", aggregated=False), 0, 24, 12, 4),
]

stock = [
    layout(text_widget("stock-header", ["# Estoque  |  Prioridade de ação\n", "\n", "Fotografia mais recente por loja e produto. O filtro de loja se aplica; o de data de venda não altera estoque."]), 0, 0, 12, 2),
    layout(counter("risk-products", "Produtos com alerta por loja", "COUNT_IF(`risk_status` <> 'Sem alerta')", dataset="ds_inventory"), 0, 2, 3, 3),
    layout(counter("available", "Unidades disponíveis", "SUM(`available_quantity`)", dataset="ds_inventory"), 3, 2, 3, 3),
    layout(counter("stock-value", "Valor em estoque · BRL", "CASE WHEN SUM(`cost_missing_lot_count`) > 0 THEN NULL ELSE SUM(`stock_value`) END", fmt=BRL, dataset="ds_inventory"), 6, 2, 3, 3),
    layout(counter("expiring", "Vence em 30 dias · BRL", "CASE WHEN SUM(`cost_missing_lot_count`) > 0 THEN NULL ELSE SUM(`value_expiring_30d`) END", fmt=BRL, dataset="ds_inventory"), 9, 2, 3, 3),
    layout(text_widget("stock-analysis-1", ["**Alerta**\n", "Posições vencidas, a vencer ou abaixo do mínimo; confirmar no local."]), 0, 5, 3, 2),
    layout(text_widget("stock-analysis-2", ["**Disponível**\n", "Saldo em mãos menos reservas; não é quantidade em gôndola."]), 3, 5, 3, 2),
    layout(text_widget("stock-analysis-3", ["**Valor a custo**\n", "Capital em estoque, não receita; fica indisponível se faltar custo."]), 6, 5, 3, 2),
    layout(text_widget("stock-analysis-4", ["**A vencer**\n", "Exposição em até 30 dias, não perda prevista nem economia."]), 9, 5, 3, 2),
    layout(counter("expiring-quantity", "Unidades a vencer em 30 dias", "SUM(`quantity_expiring_30d`)", dataset="ds_inventory"), 0, 7, 4, 3),
    layout(counter("expired-quantity", "Unidades já vencidas", "SUM(`expired_quantity`)", dataset="ds_inventory"), 4, 7, 4, 3),
    layout(counter("missing-cost", "Lotes sem custo", "SUM(`cost_missing_lot_count`)", dataset="ds_inventory"), 8, 7, 4, 3),
    layout(text_widget("stock-secondary-note", ["**Ação:** priorize lote vencido e validade próxima; confira saldo e custo ausente antes de decidir preço ou destinação. As quantidades seguem visíveis mesmo quando o valor monetário não pode ser calculado."]), 0, 10, 12, 2),
    layout(chart("stock-bars", "ds_inventory", "bar", 3,
                 [field("product_name"), field("available", "SUM(`available_quantity`)")],
                 {"x": {"fieldName": "available", "scale": {"type": "quantitative"}},
                  "y": {"fieldName": "product_name", "scale": {"type": "categorical"}}},
                 "Disponível por produto"), 0, 12, 12, 5),
    layout(chart("stock-actions", "ds_inventory", "table", 2,
                 [field("store_name"), field("product_name"), field("risk_status"),
                  field("available_quantity"), field("minimum_quantity"), field("cost_missing_lot_count"),
                  field("nearest_expiry_days"), field("quantity_expiring_30d")],
                 {"columns": [{"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "risk_status", "displayName": "Situação"},
                              {"fieldName": "available_quantity", "displayName": "Disponível"},
                              {"fieldName": "minimum_quantity", "displayName": "Mínimo"},
                              {"fieldName": "cost_missing_lot_count", "displayName": "Lotes sem custo"},
                              {"fieldName": "nearest_expiry_days", "displayName": "Dias até validade"},
                              {"fieldName": "quantity_expiring_30d", "displayName": "Unid. a vencer"}]},
                 "Prioridade por loja e produto", aggregated=False), 0, 17, 12, 6),
    layout(chart("batch-details", "ds_batches", "table", 2,
                 [field("store_name"), field("product_name"), field("source_batch_id"),
                  field("available_quantity"), field("stock_value"), field("expiration_date")],
                 {"columns": [{"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "source_batch_id", "displayName": "Lote"},
                              {"fieldName": "available_quantity", "displayName": "Disponível"},
                              {"fieldName": "stock_value", "displayName": "Valor (BRL)", "format": BRL},
                              {"fieldName": "expiration_date", "displayName": "Validade"}]},
                 "Lotes e vencimentos", aggregated=False), 0, 23, 12, 6),
]

distribution = [
    layout(text_widget("distribution-header", ["# Confiabilidade e distribuição\n", "\n", "Regras de validação e idade do último lote publicado. Distribuição de tickets requer amostra mais diversa para conclusões."]), 0, 0, 12, 2),
    layout(counter("validated-rules", "Regras verificadas", "MAX(`validation_count`)", dataset="ds_reliability"), 0, 2, 3, 3),
    layout(counter("failing-rules", "Regras com falha", "MAX(`failing_validations`)", dataset="ds_reliability"), 3, 2, 3, 3),
    layout(counter("invalid-findings", "Achados inválidos", "MAX(`invalid_findings`)", dataset="ds_reliability"), 6, 2, 3, 3),
    layout(counter("data-age", "Idade dos dados · horas", "MAX(`data_age_hours`)", dataset="ds_reliability"), 9, 2, 3, 3),
    layout(text_widget("quality-analysis", ["**Interpretação:** regras com falha e achados vêm das verificações Silver; um registro pode violar várias regras. Zero falhas não prova acuracidade do inventário físico. A idade conta desde o corte da origem e cresce até a próxima publicação."]), 0, 5, 12, 2),
    layout(chart("ticket-hist", "ds_tickets", "histogram", 3,
                 [field("ticket_bin", "BIN_FLOOR(`ticket_amount`, 5)"), field("frequency", "COUNT(*)")],
                 {"x": {"fieldName": "ticket_bin", "scale": {"type": "quantitative"}},
                  "y": {"fieldName": "frequency", "scale": {"type": "quantitative"}}},
                 "Tickets por faixa de R$ 5"), 0, 7, 6, 6),
    layout(chart("ticket-box", "ds_tickets", "box", 1,
                 [field("store_name"), field("ticket_amount")],
                 {"x": {"fieldName": "store_name", "displayName": "Loja"},
                  "y": {"fieldName": "ticket_amount", "displayName": "Ticket (BRL)", "scale": {"type": "quantitative"}}},
                 "Ticket por loja", aggregated=False), 6, 7, 6, 6),
    layout(text_widget("ticket-analysis", ["**Leitura:** faixa de ticket e dispersão descrevem somente as compras observadas. Com uma loja vendedora e um dia de vendas, não há comparação confiável entre lojas ou evolução temporal."]), 0, 13, 12, 2),
    layout(chart("quality-table", "ds_quality", "table", 2,
                 [field("relation_name"), field("checked_rows"), field("invalid_rows"), field("checked_at")],
                 {"columns": [{"fieldName": "relation_name", "displayName": "Regra / relação"},
                              {"fieldName": "checked_rows", "displayName": "Linhas verificadas"},
                              {"fieldName": "invalid_rows", "displayName": "Falhas"},
                              {"fieldName": "checked_at", "displayName": "Verificado em"}]},
                 "Validação da Silver", aggregated=False), 0, 15, 12, 7),
]

dictionary = [
    layout(text_widget("dictionary-header", ["# Dados e definições dos KPIs\n", "\n", "Cada indicador informa fórmula, uso e condição de publicação. Esta tabela também está na aba Data como dataset independente."]), 0, 0, 12, 2),
    layout(chart("dictionary-table", "ds_kpi_dictionary", "table", 2,
                 [field("module"), field("kpi"), field("definition"), field("analysis"), field("source_dataset"), field("status")],
                 {"columns": [{"fieldName": "module", "displayName": "Módulo"},
                              {"fieldName": "kpi", "displayName": "KPI"},
                              {"fieldName": "definition", "displayName": "Cálculo"},
                              {"fieldName": "analysis", "displayName": "Como analisar"},
                              {"fieldName": "source_dataset", "displayName": "Dataset / fonte"},
                              {"fieldName": "status", "displayName": "Situação"}]},
                 "Catálogo de indicadores", aggregated=False), 0, 2, 12, 18),
    layout(text_widget("dictionary-note", ["**Sem fonte** e **sem eventos** significam que o KPI ainda não deve mostrar número. Métricas condicionais exigem dados suficientes e denominadores válidos. Os filtros comerciais não alteram este dicionário."]), 0, 20, 12, 2),
]

operations = [
    layout(text_widget("operations-header", ["# Operações  |  Resultado observado\n", "\n", "Contagens concluídas, transferências, reposição e destinações da última publicação. Campos vazios indicam que ainda não houve eventos elegíveis."]), 0, 0, 12, 2),
    layout(counter("count-accuracy", "Acuracidade das posições contadas", "MAX(`inventory_accuracy`)", fmt=PERCENT, dataset="ds_operations"), 0, 2, 3, 3),
    layout(counter("count-difference", "Divergência absoluta · un.", "MAX(`inventory_difference_units`)", dataset="ds_operations"), 3, 2, 3, 3),
    layout(counter("transfer-completion", "Transferências concluídas · %", "MAX(`transfer_completion_rate`)", fmt=PERCENT, dataset="ds_operations"), 6, 2, 3, 3),
    layout(counter("replenishment", "Reposição observada · %", "MAX(`observed_replenishment_rate`)", fmt=PERCENT, dataset="ds_operations"), 9, 2, 3, 3),
    layout(text_widget("operations-explain", ["**Acuracidade:** posições com quantidade igual / posições concluídas; não mede cobertura de todo o estoque. **Divergência:** soma absoluta em unidades. **Transferências:** concluídas / solicitadas. **Reposição:** quantidade executada / sugerida apenas onde há execução concluída; não representa todas as pré-listas."]), 0, 5, 12, 3),
    layout(counter("donated-units", "Unidades doadas", "MAX(`donated_units`)", dataset="ds_operations"), 0, 8, 3, 3),
    layout(counter("disposed-units", "Unidades descartadas", "MAX(`disposed_units`)", dataset="ds_operations"), 3, 8, 3, 3),
    layout(counter("alert-resolution", "Alertas resolvidos · %", "MAX(`alert_resolution_rate`)", fmt=PERCENT, dataset="ds_operations"), 6, 8, 3, 3),
    layout(counter("suggested-actions", "Ações sugeridas", "MAX(`suggested_actions`)", dataset="ds_operations"), 9, 8, 3, 3),
    layout(text_widget("operations-limits", ["**Destinações:** volume registrado, sem afirmar economia ou perda evitada. **Alertas:** estado atual por coorte de geração; a taxa de resolução não mede precisão da IA. Números entram apenas após a RPA publicar o lote no analítico e o job Bronze → Silver → Gold terminar."]), 0, 11, 12, 3),
    layout(chart("count-table", "ds_counts", "table", 2,
                 [field("count_date"), field("store_name"), field("counted_positions"), field("matching_positions"), field("accuracy_rate"), field("absolute_quantity_difference"), field("positions_without_cost")],
                 {"columns": [{"fieldName": "count_date", "displayName": "Data"}, {"fieldName": "store_name", "displayName": "Loja"}, {"fieldName": "counted_positions", "displayName": "Posições"}, {"fieldName": "matching_positions", "displayName": "Sem divergência"}, {"fieldName": "accuracy_rate", "displayName": "Acuracidade", "format": PERCENT}, {"fieldName": "absolute_quantity_difference", "displayName": "Divergência · un."}, {"fieldName": "positions_without_cost", "displayName": "Sem custo"}]},
                 "Contagem física por loja", aggregated=False), 0, 14, 12, 6),
    layout(chart("destinations-table", "ds_destinations", "table", 2,
                 [field("event_date"), field("store_name"), field("product_name"), field("destination_type"), field("status"), field("quantity"), field("value_at_cost")],
                 {"columns": [{"fieldName": "event_date", "displayName": "Data"}, {"fieldName": "store_name", "displayName": "Loja"}, {"fieldName": "product_name", "displayName": "Produto"}, {"fieldName": "destination_type", "displayName": "Destino"}, {"fieldName": "status", "displayName": "Estado"}, {"fieldName": "quantity", "displayName": "Quantidade"}, {"fieldName": "value_at_cost", "displayName": "Valor a custo", "format": BRL}]},
                 "Doações e descartes registrados", aggregated=False), 0, 20, 12, 6),
]

filters = [
    layout(filter_widget("filter-period", "filter-date-range-picker", "Período das vendas",
                         [("ds_period", "period", True), ("ds_sales", "sale_date", False),
                          ("ds_tickets", "sale_date", False), ("ds_product", "sale_date", False),
                          ("ds_payment", "sale_date", False)]), 0, 0, 6, 2),
    layout(filter_widget("filter-store", "filter-multi-select", "Loja",
                         [(name, "store_id", False) for name in
                          ("ds_period", "ds_sales", "ds_tickets", "ds_product", "ds_payment", "ds_inventory", "ds_batches")]), 6, 0, 6, 2),
]

dashboard = {
    "datasets": datasets,
    "pages": [
        {"name": "executive", "displayName": "Visão executiva", "layout": executive,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "commercial", "displayName": "Comercial", "layout": commercial,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "stock", "displayName": "Estoque", "layout": stock,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "operations", "displayName": "Operações e perdas", "layout": operations,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "distribution", "displayName": "Distribuição e qualidade", "layout": distribution,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "dictionary", "displayName": "Dados e KPIs", "layout": dictionary,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "filters", "displayName": "Filtros", "layout": filters,
         "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1"},
    ],
    "uiSettings": {"theme": {
        "canvasBackgroundColor": {"light": "#F4F7F5", "dark": "#17221D"},
        "widgetBackgroundColor": {"light": "#FFFFFF", "dark": "#1E2D26"},
        "widgetBorderColor": {"light": "#FFFFFF", "dark": "#1E2D26"},
        "fontColor": {"light": "#18352A", "dark": "#ECF4EF"},
        "selectionColor": {"light": "#147D64", "dark": "#72D6AF"},
        "visualizationColors": ["#147D64", "#3A7C9A", "#E5A64A", "#A15A89", "#D6705A", "#6B8A54"],
        "widgetHeaderAlignment": "LEFT", "widgetCornerRadius": 10,
    }},
}

OUT.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUT)
