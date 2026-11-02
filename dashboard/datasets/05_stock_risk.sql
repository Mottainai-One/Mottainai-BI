-- Snapshot risk. Only the store filter applies; this is not a time series.
SELECT snapshot_date, store_id, store_name, product_id, product_name,
       on_hand_quantity, reserved_quantity, available_quantity, stock_value,
       minimum_quantity, cost_missing_lot_count, nearest_expiry_days, quantity_expiring_30d,
       expired_quantity, value_expiring_30d, expired_value,
       below_minimum, risk_status, batch_count
FROM motta_analytics.gold.inventory_health;
