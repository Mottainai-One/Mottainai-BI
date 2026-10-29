-- One completed sale per row. Dashboard date and store filters use this raw grain.
SELECT sale_id, sale_date, store_id, store_name, ticket_amount, item_count
FROM motta_analytics.gold.sales_tickets;
