-- One completed sale per row. Dashboard date and store filters use this raw grain.
SELECT t.sale_date, t.store_id, s.store_name, t.ticket_amount, t.item_count
FROM workspace.mottainai_gold.ticket_distribution t
JOIN workspace.mottainai_gold.stores s ON s.store_id = t.store_id;
