-- AI/BI dataset: cards for the selected period and comparison with the preceding period.
-- Configure :period as Date Range (default now-30d/d to now/d) and
-- :store_id as optional Numeric (integer). All currency values are BRL.
WITH limits AS (
  SELECT CAST(:period.min AS DATE) AS start_date,
         CAST(:period.max AS DATE) AS end_date,
         CAST(:store_id AS BIGINT) AS selected_store
), scoped AS (
  SELECT s.*,
         CASE WHEN s.sale_date BETWEEN l.start_date AND l.end_date
              THEN 'current' ELSE 'previous' END AS period_name
  FROM workspace.mottainai_gold.sales_daily_kpis s
  CROSS JOIN limits l
  WHERE s.sale_date BETWEEN
        date_sub(l.start_date, datediff(l.end_date, l.start_date) + 1)
        AND l.end_date
    AND (l.selected_store IS NULL OR s.store_id = l.selected_store)
), totals AS (
  SELECT period_name, SUM(net_revenue) AS revenue_brl,
         SUM(sale_count) AS sales_count, SUM(item_count) AS items_count
  FROM scoped GROUP BY period_name
)
SELECT COALESCE(c.revenue_brl, 0) AS revenue_brl,
       COALESCE(c.sales_count, 0) AS sales_count,
       COALESCE(c.items_count, 0) AS items_count,
       CASE WHEN COALESCE(c.sales_count, 0) = 0 THEN NULL
            ELSE c.revenue_brl / c.sales_count END AS average_ticket_brl,
       CASE WHEN COALESCE(p.revenue_brl, 0) = 0 THEN NULL
            ELSE (c.revenue_brl - p.revenue_brl) / p.revenue_brl END
            AS revenue_change_pct,
       CASE WHEN COALESCE(p.sales_count, 0) = 0 THEN NULL
            ELSE (c.sales_count - p.sales_count) * 1.0 / p.sales_count END
            AS sales_change_pct
FROM (SELECT 1) seed
LEFT JOIN totals c ON c.period_name = 'current'
LEFT JOIN totals p ON p.period_name = 'previous';
