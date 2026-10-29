-- Product sales derive from validated sale items, not a source summary view.
SELECT sale_date, store_id, store_name, product_id, product_name,
       category_name, units_sold, net_revenue, sales_with_product
FROM motta_analytics.gold.product_sales_daily;
