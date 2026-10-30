-- Only completed sales; reconciled payment records in Gold.
SELECT sale_date, store_id, store_name, payment_method,
       payment_count, sales_with_method, paid_amount
FROM motta_analytics.gold.payment_mix;
