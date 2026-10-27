-- Bar: risk level x distinct products; the analytical snapshot is current
-- until the next successful 02:00 publication.
SELECT consolidated_risk,
       COUNT(DISTINCT CONCAT(CAST(store_id AS STRING), ':',
                             CAST(product_id AS STRING))) AS products,
       SUM(value_at_expiration_risk) AS expiration_value_brl
FROM workspace.mottainai_gold.product_risk_ranking
WHERE :store_id IS NULL OR store_id = CAST(:store_id AS BIGINT)
GROUP BY consolidated_risk
ORDER BY CASE consolidated_risk WHEN 'CRITICAL' THEN 1
         WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END;
