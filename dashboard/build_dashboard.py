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
]

commercial = [
    layout(text_widget("commercial-header", ["# Comercial  |  Cobertura e composição\n", "\n", "Lojas e produtos com vendas no período; métodos de pagamento das vendas concluídas. Base pequena indica cobertura limitada."]), 0, 0, 12, 2),
    layout(counter("selling-stores", "Lojas com vendas", "COUNT(DISTINCT `store_id`)", dataset="ds_sales"), 0, 2, 3, 3),
    layout(counter("selling-products", "Produtos vendidos", "COUNT(DISTINCT `product_id`)", dataset="ds_product"), 3, 2, 3, 3),
    layout(counter("units-sold", "Unidades vendidas", "SUM(`units_sold`)", dataset="ds_product"), 6, 2, 3, 3),
    layout(counter("payment-methods", "Métodos de pagamento", "COUNT(DISTINCT `payment_method`)", dataset="ds_payment"), 9, 2, 3, 3),
    layout(chart("payment-bars", "ds_payment", "bar", 3,
                 [field("payment_method"), field("paid", "SUM(`paid_amount`)")],
                 {"x": {"fieldName": "paid", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "payment_method", "scale": {"type": "categorical"}}},
                 "Valor pago por método"), 0, 5, 6, 6),
    layout(chart("product-bars", "ds_product", "bar", 3,
                 [field("product_name"), field("revenue", "SUM(`net_revenue`)")],
                 {"x": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "product_name", "scale": {"type": "categorical"}}},
                 "Receita por produto"), 6, 5, 6, 6),
    layout(chart("payment-table", "ds_payment", "table", 2,
                 [field("sale_date"), field("store_name"), field("payment_method"),
                  field("payment_count"), field("sales_with_method"), field("paid_amount")],
                 {"columns": [{"fieldName": "sale_date", "displayName": "Data"},
                              {"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "payment_method", "displayName": "Método"},
                              {"fieldName": "payment_count", "displayName": "Pagamentos"},
                              {"fieldName": "sales_with_method", "displayName": "Vendas com método"},
                              {"fieldName": "paid_amount", "displayName": "Valor (BRL)", "format": BRL}]},
                 "Pagamentos conciliados", aggregated=False), 0, 11, 12, 5),
]

executive = [
    layout(text_widget("executive-header", ["# Mottainai  |  Visão executiva\n", "\n", "Vendas concluídas do último lote analítico. Filtros de período e loja no topo; estoque usa a fotografia mais recente."]), 0, 0, 12, 2),
    layout(counter("revenue", "Receita líquida · BRL", "SUM(`revenue_brl`)", fmt=BRL), 0, 2, 3, 3),
    layout(counter("sales", "Vendas concluídas", "SUM(`sales_count`)"), 3, 2, 3, 3),
    layout(counter("ticket", "Ticket médio · BRL", "TRY_DIVIDE(SUM(`revenue_brl`), SUM(`sales_count`))", fmt=BRL), 6, 2, 3, 3),
    layout(counter("revenue-delta", "Variação vs. período anterior", "TRY_DIVIDE(SUM(`revenue_brl`) - SUM(`previous_revenue_brl`), SUM(`previous_revenue_brl`))", fmt=PERCENT), 9, 2, 3, 3),
    layout(text_widget("history-note", ["**Leitura responsável:** o histórico atual tem somente um dia de vendas e uma loja com movimento. A variação fica sem valor enquanto o período anterior não tiver receita; não interprete a linha como tendência antes de haver mais datas."]), 0, 5, 12, 2),
    layout(chart("daily-trend", "ds_sales", "line", 3,
                 [field("sale_date"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "sale_date", "scale": {"type": "temporal"}},
                  "y": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL}},
                 "Receita por dia"), 0, 7, 6, 6),
    layout(chart("store-bars", "ds_sales", "bar", 3,
                 [field("store_name"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "store_name", "scale": {"type": "categorical"}}},
                 "Receita por loja com vendas"), 6, 7, 6, 6),
    layout(chart("product-sales", "ds_product", "table", 2,
                 [field("product_name"), field("category_name"), field("units_sold"), field("net_revenue")],
                 {"columns": [{"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "category_name", "displayName": "Categoria"},
                              {"fieldName": "units_sold", "displayName": "Unidades"},
                              {"fieldName": "net_revenue", "displayName": "Receita (BRL)", "format": BRL}]},
                 "Produtos vendidos", aggregated=False), 0, 13, 12, 4),
    layout(chart("publication", "ds_freshness", "table", 2,
                 [field("batch_id"), field("model_version"), field("source_cutoff_at"), field("source_published_at"), field("refreshed_at")],
                 {"columns": [{"fieldName": "batch_id", "displayName": "Lote"},
                              {"fieldName": "model_version", "displayName": "Modelo"},
                              {"fieldName": "source_cutoff_at", "displayName": "Corte da origem"},
                              {"fieldName": "source_published_at", "displayName": "Publicação no analítico"},
                              {"fieldName": "refreshed_at", "displayName": "Atualização do BI"}]},
                 "Linhagem e frescor", aggregated=False), 0, 17, 12, 4),
]

stock = [
    layout(text_widget("stock-header", ["# Estoque  |  Disponibilidade e valor\n", "\n", "Fotografia do produto por loja e lote; usa a data mais recente de cada produto. O filtro de data afeta vendas, não esta página."]), 0, 0, 12, 2),
    layout(counter("risk-products", "Produtos com alerta por loja", "COUNT_IF(`risk_status` <> 'Sem alerta')", dataset="ds_inventory"), 0, 2, 3, 3),
    layout(counter("available", "Unidades disponíveis", "SUM(`available_quantity`)", dataset="ds_inventory"), 3, 2, 3, 3),
    layout(counter("stock-value", "Valor em estoque · BRL", "SUM(`stock_value`)", fmt=BRL, dataset="ds_inventory"), 6, 2, 3, 3),
    layout(counter("expiring", "Vence em 30 dias · BRL", "SUM(`value_expiring_30d`)", fmt=BRL, dataset="ds_inventory"), 9, 2, 3, 3),
    layout(chart("stock-bars", "ds_inventory", "bar", 3,
                 [field("product_name"), field("available", "SUM(`available_quantity`)")],
                 {"x": {"fieldName": "available", "scale": {"type": "quantitative"}},
                  "y": {"fieldName": "product_name", "scale": {"type": "categorical"}}},
                 "Disponível por produto"), 0, 5, 12, 5),
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
                 "Prioridade por loja e produto", aggregated=False), 0, 10, 12, 6),
    layout(chart("batch-details", "ds_batches", "table", 2,
                 [field("store_name"), field("product_name"), field("source_batch_id"),
                  field("available_quantity"), field("stock_value"), field("expiration_date")],
                 {"columns": [{"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "source_batch_id", "displayName": "Lote"},
                              {"fieldName": "available_quantity", "displayName": "Disponível"},
                              {"fieldName": "stock_value", "displayName": "Valor (BRL)", "format": BRL},
                              {"fieldName": "expiration_date", "displayName": "Validade"}]},
                 "Lotes e vencimentos", aggregated=False), 0, 16, 12, 6),
]

distribution = [
    layout(text_widget("distribution-header", ["# Distribuição e qualidade\n", "\n", "Histograma e boxplot mostram os tickets observados. Com apenas um preço e uma loja vendedora, ainda não há dispersão real; a qualidade registra o que a Silver validou."]), 0, 0, 12, 2),
    layout(chart("ticket-hist", "ds_tickets", "histogram", 3,
                 [field("ticket_bin", "BIN_FLOOR(`ticket_amount`, 5)"), field("frequency", "COUNT(*)")],
                 {"x": {"fieldName": "ticket_bin", "scale": {"type": "quantitative"}},
                  "y": {"fieldName": "frequency", "scale": {"type": "quantitative"}}},
                 "Tickets por faixa de R$ 5"), 0, 2, 6, 6),
    layout(chart("ticket-box", "ds_tickets", "box", 1,
                 [field("store_name"), field("ticket_amount")],
                 {"x": {"fieldName": "store_name", "displayName": "Loja"},
                  "y": {"fieldName": "ticket_amount", "displayName": "Ticket (BRL)", "scale": {"type": "quantitative"}}},
                 "Ticket por loja", aggregated=False), 6, 2, 6, 6),
    layout(chart("quality-table", "ds_quality", "table", 2,
                 [field("relation_name"), field("checked_rows"), field("invalid_rows"), field("checked_at")],
                 {"columns": [{"fieldName": "relation_name", "displayName": "Regra / relação"},
                              {"fieldName": "checked_rows", "displayName": "Linhas verificadas"},
                              {"fieldName": "invalid_rows", "displayName": "Falhas"},
                              {"fieldName": "checked_at", "displayName": "Verificado em"}]},
                 "Validação da Silver", aggregated=False), 0, 8, 12, 7),
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
        {"name": "distribution", "displayName": "Distribuição e qualidade", "layout": distribution,
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
