-- Use ticket_amount for a Histogram and a Box chart grouped by store_id.
-- Only completed transactions are exposed by the Gold view.
SELECT t.sale_date, t.store_id, s.store_name, t.ticket_amount,
       t.item_count
FROM workspace.mottainai_gold.ticket_distribution t
JOIN workspace.mottainai_gold.stores s
  ON s.store_id = t.store_id
WHERE t.sale_date BETWEEN :period.min AND :period.max
  AND (:store_id IS NULL OR t.store_id = CAST(:store_id AS BIGINT));
