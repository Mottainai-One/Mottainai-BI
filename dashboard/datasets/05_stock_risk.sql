-- Snapshot risk. Only the store filter applies; this is not a time series.
SELECT store_id, store_name, product_id, product_name, consolidated_risk,
       current_stock, days_of_coverage, value_at_expiration_risk
FROM workspace.mottainai_gold.product_risk_ranking;
