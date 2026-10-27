-- Bar: store_name x revenue_brl. Group by stable store_id as names can repeat.
SELECT store_id, MAX(store_name) AS store_name,
       SUM(net_revenue) AS revenue_brl,
       SUM(sale_count) AS sales_count
FROM workspace.mottainai_gold.sales_daily_kpis
WHERE sale_date BETWEEN :period.min AND :period.max
  AND (:store_id IS NULL OR store_id = CAST(:store_id AS BIGINT))
GROUP BY store_id
ORDER BY revenue_brl DESC;
