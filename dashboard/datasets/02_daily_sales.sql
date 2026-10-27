-- Date and store filters are applied by the dashboard on this raw daily grain.
SELECT sale_date, store_id, store_name, net_revenue AS revenue_brl,
       sale_count, item_count
FROM workspace.mottainai_gold.sales_daily_kpis;
