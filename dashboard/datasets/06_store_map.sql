-- Map when store coordinates exist. A store without coordinates is omitted.
SELECT g.store_id, g.store_name, g.city, g.state_code,
       g.latitude, g.longitude,
       COALESCE(SUM(k.net_revenue), 0) AS revenue_brl
FROM workspace.mottainai_gold.store_geography g
LEFT JOIN workspace.mottainai_gold.sales_daily_kpis k
  ON k.store_id = g.store_id
 AND k.sale_date BETWEEN :period.min AND :period.max
WHERE :store_id IS NULL OR g.store_id = CAST(:store_id AS BIGINT)
GROUP BY g.store_id, g.store_name, g.city, g.state_code,
         g.latitude, g.longitude;
