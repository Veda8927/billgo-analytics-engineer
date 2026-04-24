DROP TABLE IF EXISTS mart_smb_cohort_retention CASCADE;

CREATE TABLE mart_smb_cohort_retention AS
WITH cohort_sizes AS (
    SELECT
        enrollment_cohort_month AS cohort_month,
        COUNT(*) AS smbs_enrolled
    FROM dim_smb
    WHERE activated_at IS NOT NULL
    GROUP BY enrollment_cohort_month
),
smb_first_capture AS (
    SELECT
        s.smb_id,
        s.enrollment_cohort_month AS cohort_month,
        MIN(DATE_TRUNC('month', i.invoice_sent_at)::DATE) AS first_capture_month
    FROM dim_smb s
    JOIN fct_invoices i USING (smb_id)
    WHERE s.activated_at IS NOT NULL
      AND i.was_captured = TRUE
    GROUP BY s.smb_id, s.enrollment_cohort_month
),
smb_last_activity AS (
    SELECT
        s.smb_id,
        s.enrollment_cohort_month AS cohort_month,
        MAX(DATE_TRUNC('month', i.invoice_sent_at)::DATE) AS last_capture_month
    FROM dim_smb s
    JOIN fct_invoices i USING (smb_id)
    WHERE s.activated_at IS NOT NULL
      AND i.was_captured = TRUE
    GROUP BY s.smb_id, s.enrollment_cohort_month
),
month_spine AS (
    SELECT
        cs.cohort_month,
        cs.smbs_enrolled,
        month_offset,
        (cs.cohort_month + (month_offset || ' months')::INTERVAL)::DATE AS target_month
    FROM cohort_sizes cs
    CROSS JOIN generate_series(0, 17) AS month_offset
),
retention_counts AS (
    SELECT
        ms.cohort_month,
        ms.month_offset,
        ms.target_month,
        ms.smbs_enrolled,
        CASE
            WHEN ms.month_offset = 0 THEN ms.smbs_enrolled
            ELSE COUNT(DISTINCT sfc.smb_id)
        END AS smbs_active
    FROM month_spine ms
    LEFT JOIN smb_first_capture sfc
        ON sfc.cohort_month = ms.cohort_month
       AND sfc.first_capture_month <= ms.target_month
    LEFT JOIN smb_last_activity sla
        ON sla.smb_id = sfc.smb_id
       AND sla.last_capture_month >= ms.target_month
    WHERE ms.month_offset = 0
       OR sla.smb_id IS NOT NULL
       OR sfc.smb_id IS NULL
    GROUP BY ms.cohort_month, ms.month_offset, ms.target_month, ms.smbs_enrolled
)
SELECT
    cohort_month,
    month_offset AS months_since_enrollment,
    target_month AS activity_month,
    smbs_enrolled,
    smbs_active,
    ROUND(100.0 * smbs_active / NULLIF(smbs_enrolled, 0), 2) AS retention_pct
FROM retention_counts
WHERE target_month <= '2026-03-31'::DATE
ORDER BY cohort_month, month_offset;

CREATE INDEX idx_cohort_retention_cohort ON mart_smb_cohort_retention(cohort_month);
CREATE INDEX idx_cohort_retention_offset ON mart_smb_cohort_retention(months_since_enrollment);
