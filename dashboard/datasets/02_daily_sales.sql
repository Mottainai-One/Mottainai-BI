-- Date and store filters are applied by the dashboard on this raw daily grain.
SELECT sale_date, company_id, store_id, store_name,
       net_revenue AS revenue_brl, sale_count, item_count, average_ticket
FROM motta_analytics.gold.sales_daily;
