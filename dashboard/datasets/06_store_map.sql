-- Lojas com coordenadas; o mapa permanece vazio quando a origem não tem lat/lon.
SELECT store_id, store_name, city, state_code, latitude, longitude
FROM motta_analytics.gold.stores
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
