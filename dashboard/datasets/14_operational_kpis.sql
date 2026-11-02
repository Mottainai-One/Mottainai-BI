-- Uma linha por lote publicado. Ausência de eventos retorna NULL, não zero observado.
SELECT
  (SELECT TRY_DIVIDE(SUM(matching_positions), SUM(counted_positions))
   FROM motta_analytics.gold.inventory_count_accuracy) AS inventory_accuracy,
  (SELECT CASE WHEN COUNT(*)=0 THEN NULL ELSE SUM(absolute_quantity_difference) END
   FROM motta_analytics.gold.inventory_count_accuracy) AS inventory_difference_units,
  (SELECT TRY_DIVIDE(SUM(completed_transfers), SUM(transfers_with_items))
   FROM motta_analytics.gold.transfer_execution) AS transfer_completion_rate,
  (SELECT CASE WHEN COUNT(*)=0 THEN NULL ELSE SUM(completed_transfers) END
   FROM motta_analytics.gold.transfer_execution) AS completed_transfers,
  (SELECT TRY_DIVIDE(SUM(completed_quantity), SUM(suggested_quantity))
   FROM motta_analytics.gold.replenishment_fulfillment
   WHERE completed_lines > 0) AS observed_replenishment_rate,
  (SELECT CASE WHEN COUNT(*)=0 THEN NULL ELSE SUM(quantity) END
   FROM motta_analytics.gold.product_destinations
   WHERE destination_type='DOACAO' AND status='COMPLETED') AS donated_units,
  (SELECT CASE WHEN COUNT(*)=0 THEN NULL ELSE SUM(quantity) END
   FROM motta_analytics.gold.product_destinations
   WHERE destination_type='DESCARTE') AS disposed_units,
  (SELECT TRY_DIVIDE(SUM(resolved_alerts), SUM(alerts))
   FROM motta_analytics.gold.alert_action_funnel) AS alert_resolution_rate,
  (SELECT CASE WHEN COUNT(*)=0 THEN NULL ELSE SUM(suggested_actions) END
   FROM motta_analytics.gold.alert_action_funnel) AS suggested_actions
