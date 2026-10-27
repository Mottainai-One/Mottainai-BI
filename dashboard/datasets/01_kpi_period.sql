-- One row per store. Date range is a dashboard parameter; store filter binds store_id.
WITH limits AS (
  SELECT CAST(:period.min AS DATE) AS start_date,
         CAST(:period.max AS DATE) AS end_date
), scoped AS (
  SELECT s.store_id, s.net_revenue, s.sale_count, s.item_count,
         s.sale_date BETWEEN l.start_date AND l.end_date AS is_current
  FROM workspace.mottainai_gold.sales_daily_kpis s
  CROSS JOIN limits l
  WHERE s.sale_date BETWEEN
    date_sub(l.start_date, datediff(l.end_date, l.start_date) + 1)
    AND l.end_date
)
SELECT store_id,
       SUM(CASE WHEN is_current THEN net_revenue ELSE 0 END) AS revenue_brl,
       SUM(CASE WHEN NOT is_current THEN net_revenue ELSE 0 END) AS previous_revenue_brl,
       SUM(CASE WHEN is_current THEN sale_count ELSE 0 END) AS sales_count,
       SUM(CASE WHEN NOT is_current THEN sale_count ELSE 0 END) AS previous_sales_count,
       SUM(CASE WHEN is_current THEN item_count ELSE 0 END) AS items_count
FROM scoped GROUP BY store_id;
