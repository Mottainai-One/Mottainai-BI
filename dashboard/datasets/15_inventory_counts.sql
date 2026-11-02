SELECT count_date,store_id,store_name,counted_positions,matching_positions,
       accuracy_rate,absolute_quantity_difference,absolute_difference_value,
       positions_without_cost
FROM motta_analytics.gold.inventory_count_accuracy
