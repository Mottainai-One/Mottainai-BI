-- Text/table widget: make the business cutoff and BI refresh visible.
SELECT batch_id, model_version, source_cutoff_at, source_published_at, refreshed_at,
       datediff(current_date(), CAST(source_cutoff_at AS DATE)) AS age_days
FROM motta_analytics.gold.dashboard_freshness;
