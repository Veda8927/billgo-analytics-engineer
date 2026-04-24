DROP TABLE IF EXISTS dim_smb CASCADE;

CREATE TABLE dim_smb AS
SELECT
    s.smb_id,
    s.business_name,
    s.industry,
    s.state_code,
    s.size_tier,

    s.enrolled_at,
    s.activated_at,
    s.churned_at,
    s.smb_status,

    a.channel                                         AS acquisition_channel,
    a.campaign                                        AS acquisition_campaign,
    a.cac_usd,
    a.acquired_at,

    (s.enrolled_at::DATE - a.acquired_at::DATE)       AS days_acquisition_to_enroll,

    CASE
        WHEN s.activated_at IS NOT NULL
        THEN (s.activated_at::DATE - s.enrolled_at::DATE)
    END                                               AS days_enroll_to_activate,

    CASE
        WHEN s.churned_at IS NOT NULL
        THEN (s.churned_at::DATE - s.enrolled_at::DATE)
        ELSE (CURRENT_DATE - s.enrolled_at::DATE)
    END                                               AS tenure_days,

    DATE_TRUNC('month', s.enrolled_at)::DATE          AS enrollment_cohort_month

FROM stg_smbs s
LEFT JOIN stg_acquisitions a USING (smb_id);

CREATE UNIQUE INDEX idx_dim_smb_pk ON dim_smb(smb_id);
CREATE INDEX idx_dim_smb_cohort ON dim_smb(enrollment_cohort_month);
CREATE INDEX idx_dim_smb_channel ON dim_smb(acquisition_channel);
CREATE INDEX idx_dim_smb_status ON dim_smb(smb_status);
