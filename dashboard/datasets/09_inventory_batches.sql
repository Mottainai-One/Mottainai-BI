SELECT snapshot_date, store_id, store_name, product_id, product_name,
       source_batch_id, inventory_type, quantity, reserved_quantity,
       available_quantity, stock_value, minimum_quantity, expiration_date, days_to_expiry
FROM motta_analytics.gold.inventory_batches;
