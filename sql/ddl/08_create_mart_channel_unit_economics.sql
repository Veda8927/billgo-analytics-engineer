DROP TABLE IF EXISTS mart_channel_unit_economics CASCADE;

CREATE TABLE mart_channel_unit_economics AS
WITH cohort_base AS (
    SELECT
        acquisition_channel,
        enrollment_cohort_month,
        smb_id,
        activated_at,
        churned_at,
        cac_usd
    FROM dim_smb
    WHERE acquisition_channel IS NOT NULL
),
cohort_smbs AS (
    SELECT
        acquisition_channel,
        enrollment_cohort_month,
        COUNT(*) AS smbs_acquired,
        COUNT(*) FILTER (WHERE activated_at IS NOT NULL) AS activated_smbs,
        COUNT(*) FILTER (WHERE churned_at IS NOT NULL) AS churned_smbs,
        SUM(cac_usd) AS total_cac,
        AVG(cac_usd) AS avg_cac_per_smb
    FROM cohort_base
    GROUP BY acquisition_channel, enrollment_cohort_month
),
smb_revenue AS (
    SELECT
        i.smb_id,
        SUM(i.invoice_amount) FILTER (WHERE i.was_captured) AS gmv,
        SUM(i.total_interchange_fee) AS revenue
    FROM fct_invoices i
    GROUP BY i.smb_id
),
cohort_revenue AS (
    SELECT
        cb.acquisition_channel,
        cb.enrollment_cohort_month,
        SUM(COALESCE(sr.gmv, 0)) AS total_gmv,
        SUM(COALESCE(sr.revenue, 0)) AS total_revenue
    FROM cohort_base cb
    LEFT JOIN smb_revenue sr USING (smb_id)
    GROUP BY cb.acquisition_channel, cb.enrollment_cohort_month
),
cohort_tenure AS (
    SELECT
        acquisition_channel,
        enrollment_cohort_month,
        ((DATE '2026-03-31' - enrollment_cohort_month) / 30.0) AS months_observed
    FROM cohort_base
    GROUP BY acquisition_channel, enrollment_cohort_month
)
SELECT
    cs.acquisition_channel AS channel,
    cs.enrollment_cohort_month AS cohort_month,

    cs.smbs_acquired,
    cs.activated_smbs,
    cs.churned_smbs,
    ROUND(
        100.0 * cs.activated_smbs / NULLIF(cs.smbs_acquired, 0),
        2
    ) AS activation_rate_pct,

    ROUND(cs.total_cac::numeric, 2) AS total_cac,
    ROUND(cs.avg_cac_per_smb::numeric, 2) AS avg_cac_per_smb,

    ROUND(cr.total_gmv::numeric, 2) AS total_gmv,
    ROUND(cr.total_revenue::numeric, 2) AS total_revenue,
    ROUND(
        (cr.total_revenue / NULLIF(cs.activated_smbs, 0))::numeric,
        2
    ) AS revenue_per_activated_smb,

    ROUND(
        LEAST(
            (cr.total_revenue / NULLIF(cs.activated_smbs, 0))
                * (24.0 / NULLIF(ct.months_observed, 0)),
            (cr.total_revenue / NULLIF(cs.activated_smbs, 0)) * 2.0
        )::numeric,
        2
    ) AS ltv_estimate,

    ROUND(
        (LEAST(
            (cr.total_revenue / NULLIF(cs.activated_smbs, 0))
                * (24.0 / NULLIF(ct.months_observed, 0)),
            (cr.total_revenue / NULLIF(cs.activated_smbs, 0)) * 2.0
        ) / NULLIF(cs.avg_cac_per_smb, 0))::numeric,
        2
    ) AS ltv_cac_ratio,

    ROUND(ct.months_observed::numeric, 1) AS months_observed

FROM cohort_smbs cs
JOIN cohort_revenue cr
    USING (acquisition_channel, enrollment_cohort_month)
JOIN cohort_tenure ct
    USING (acquisition_channel, enrollment_cohort_month)
ORDER BY cs.enrollment_cohort_month, cs.acquisition_channel;

CREATE INDEX idx_mart_unit_econ_channel ON mart_channel_unit_economics(channel);
CREATE INDEX idx_mart_unit_econ_cohort ON mart_channel_unit_economics(cohort_month);
