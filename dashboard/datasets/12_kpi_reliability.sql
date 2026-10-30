-- One row for the last published batch. A missing publication stays NULL.
WITH publication AS (
  SELECT batch_id, source_cutoff_at, source_published_at, refreshed_at
  FROM motta_analytics.gold.dashboard_freshness
  ORDER BY refreshed_at DESC
  LIMIT 1
), validations AS (
  SELECT COUNT(*) AS validation_count,
         SUM(CASE WHEN invalid_rows > 0 THEN 1 ELSE 0 END) AS failing_validations,
         SUM(invalid_rows) AS invalid_findings
  FROM motta_analytics.gold.quality_summary
)
SELECT p.batch_id, p.source_cutoff_at, p.source_published_at, p.refreshed_at,
       TIMESTAMPDIFF(HOUR, p.source_cutoff_at, p.refreshed_at) AS pipeline_delay_hours,
       TIMESTAMPDIFF(HOUR, p.source_cutoff_at, current_timestamp()) AS data_age_hours,
       v.validation_count, v.failing_validations, v.invalid_findings
FROM publication p CROSS JOIN validations v;
