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


def counter(name, title, expression, target=None, fmt=None):
    fields = [field("value", expression)]
    encoding = {"value": {"fieldName": "value", "displayName": title}}
    if fmt:
        encoding["value"]["format"] = fmt
    if target:
        fields.append(field("previous", target))
        encoding["target"] = {"fieldName": "previous", "displayName": "Período anterior"}
    return chart(name, "ds_period", "counter", 2, fields, encoding, title)


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
    {"name": "ds_period", "displayName": "KPIs por loja e período", "queryLines": [sql_file("01_kpi_period.sql")],
     "parameters": [{"keyword": "period", "displayName": "Período das vendas", "dataType": "DATE", "complexType": "RANGE",
                     "defaultSelection": {"range": {"dataType": "DATE",
                                                    "min": {"value": "now-30d/d"},
                                                    "max": {"value": "now/d"}}}}]},
    {"name": "ds_sales", "displayName": "Vendas diárias", "queryLines": [sql_file("02_daily_sales.sql")]},
    {"name": "ds_tickets", "displayName": "Tickets concluídos", "queryLines": [sql_file("04_ticket_distribution.sql")]},
    {"name": "ds_risk", "displayName": "Risco de estoque", "queryLines": [sql_file("05_stock_risk.sql")]},
    {"name": "ds_geo", "displayName": "Lojas geográficas", "queryLines": [sql_file("06_store_map.sql")]},
    {"name": "ds_freshness", "displayName": "Frescor do lote", "queryLines": [sql_file("07_freshness.sql")]},
]

executive = [
    layout(text_widget("executive-header", ["# Mottainai | Visão executiva\n", "\n", "Fotografia diária do banco analítico. Corte efetivo e lote no rodapé."]), 0, 0, 12, 2),
    layout(counter("revenue", "Receita líquida", "SUM(`revenue_brl`)", "SUM(`previous_revenue_brl`)", BRL), 0, 2, 3, 3),
    layout(counter("sales", "Vendas", "SUM(`sales_count`)", "SUM(`previous_sales_count`)"), 3, 2, 3, 3),
    layout(counter("ticket", "Ticket médio", "TRY_DIVIDE(SUM(`revenue_brl`), SUM(`sales_count`))", fmt=BRL), 6, 2, 3, 3),
    layout(counter("revenue-delta", "Variação de receita", "TRY_DIVIDE(SUM(`revenue_brl`) - SUM(`previous_revenue_brl`), SUM(`previous_revenue_brl`))", fmt=PERCENT), 9, 2, 3, 3),
    layout(chart("daily-trend", "ds_sales", "line", 3,
                 [field("sale_date"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "sale_date", "scale": {"type": "temporal"}},
                  "y": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL}},
                 "Receita por dia"), 0, 5, 8, 6),
    layout(chart("store-bars", "ds_sales", "bar", 3,
                 [field("store_name"), field("revenue", "SUM(`revenue_brl`)")],
                 {"x": {"fieldName": "revenue", "scale": {"type": "quantitative"}, "format": BRL},
                  "y": {"fieldName": "store_name", "scale": {"type": "categorical"}}},
                 "Receita por loja"), 8, 5, 4, 6),
    layout(chart("publication", "ds_freshness", "table", 2,
                 [field("batch_id"), field("source_cutoff_at"), field("source_published_at"), field("refreshed_at")],
                 {"columns": [{"fieldName": "batch_id", "displayName": "Lote"},
                              {"fieldName": "source_cutoff_at", "displayName": "Corte da origem"},
                              {"fieldName": "source_published_at", "displayName": "Publicação no analítico"},
                              {"fieldName": "refreshed_at", "displayName": "Atualização do BI"}]},
                 "Lote e frescor", aggregated=False), 0, 11, 12, 4),
]

stock_and_tickets = [
    layout(text_widget("detail-header", ["# Estoque e distribuição de vendas\n", "\n", "Estoque é uma fotografia; filtros de data afetam somente vendas. O mapa requer coordenadas cadastradas."]), 0, 0, 12, 2),
    layout(chart("risk-bars", "ds_risk", "bar", 3,
                 [field("consolidated_risk"), field("products", "COUNT(*)")],
                 {"x": {"fieldName": "consolidated_risk", "scale": {"type": "categorical",
                        "sort": {"by": "custom-order", "orderedValues": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]}}},
                  "y": {"fieldName": "products", "scale": {"type": "quantitative"}}},
                 "Produtos por nível de risco"), 0, 2, 6, 6),
    layout(chart("ticket-hist", "ds_tickets", "histogram", 3,
                 [field("ticket_bin", "BIN_FLOOR(`ticket_amount`, 5)"), field("frequency", "COUNT(*)")],
                 {"x": {"fieldName": "ticket_bin", "scale": {"type": "quantitative"}},
                  "y": {"fieldName": "frequency", "scale": {"type": "quantitative"}}},
                 "Distribuição dos tickets (faixas de R$ 5)"), 6, 2, 6, 6),
    layout(chart("ticket-box", "ds_tickets", "box", 1,
                 [field("store_name"), field("ticket_amount")],
                 {"x": {"fieldName": "store_name", "displayName": "Loja"},
                  "y": {"fieldName": "ticket_amount", "displayName": "Ticket (BRL)", "scale": {"type": "quantitative"}}},
                 "Variação do ticket por loja", aggregated=False), 0, 8, 6, 6),
    layout(chart("store-map", "ds_geo", "symbol-map", 2,
                 [field("store_name"), field("latitude"), field("longitude"), field("store_id")],
                 {"coordinates": {"latitude": {"fieldName": "latitude"},
                                  "longitude": {"fieldName": "longitude"}}},
                 "Lojas com coordenadas", aggregated=False), 6, 8, 6, 6),
    layout(chart("risk-details", "ds_risk", "table", 2,
                 [field("store_name"), field("product_name"), field("consolidated_risk"),
                  field("current_stock"), field("days_of_coverage")],
                 {"columns": [{"fieldName": "store_name", "displayName": "Loja"},
                              {"fieldName": "product_name", "displayName": "Produto"},
                              {"fieldName": "consolidated_risk", "displayName": "Risco"},
                              {"fieldName": "current_stock", "displayName": "Estoque atual"},
                              {"fieldName": "days_of_coverage", "displayName": "Cobertura (dias)"}]},
                 "Detalhes do risco", aggregated=False), 0, 14, 12, 5),
]

filters = [
    layout(filter_widget("filter-period", "filter-date-range-picker", "Período das vendas",
                         [("ds_period", "period", True), ("ds_sales", "sale_date", False),
                          ("ds_tickets", "sale_date", False)]), 0, 0, 5, 2),
    layout(filter_widget("filter-store", "filter-multi-select", "Loja",
                         [(name, "store_id", False) for name in
                          ("ds_period", "ds_sales", "ds_tickets", "ds_risk", "ds_geo")]), 5, 0, 5, 2),
]

dashboard = {
    "datasets": datasets,
    "pages": [
        {"name": "executive", "displayName": "Visão executiva", "layout": executive,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "stock-tickets", "displayName": "Estoque e tickets", "layout": stock_and_tickets,
         "pageType": "PAGE_TYPE_CANVAS", "layoutVersion": "GRID_V1"},
        {"name": "filters", "displayName": "Filtros", "layout": filters,
         "pageType": "PAGE_TYPE_GLOBAL_FILTERS", "layoutVersion": "GRID_V1"},
    ],
    "uiSettings": {"theme": {"visualizationColors": ["#235347", "#A9C86C", "#DF9C46", "#D75D52", "#548B9B"],
                             "widgetHeaderAlignment": "LEFT"}},
}

OUT.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUT)
