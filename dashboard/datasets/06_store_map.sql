-- Lojas com coordenadas; o mapa permanece vazio quando a origem não tem lat/lon.
SELECT store_id, store_name, city, state_code, latitude, longitude
FROM workspace.mottainai_gold.store_geography;
