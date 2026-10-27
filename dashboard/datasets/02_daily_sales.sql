-- Line: sale_date x revenue_brl; optional second measure sales_count.
SELECT sale_date, SUM(net_revenue) AS revenue_brl,
       SUM(sale_count) AS sales_count
FROM workspace.mottainai_gold.sales_daily_kpis
WHERE sale_date BETWEEN :period.min AND :period.max
  AND (:store_id IS NULL OR store_id = CAST(:store_id AS BIGINT))
GROUP BY sale_date
ORDER BY sale_date;
