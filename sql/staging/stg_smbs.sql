CREATE OR REPLACE VIEW stg_smbs AS
SELECT
    smb_id,
    TRIM(business_name)              AS business_name,
    LOWER(industry)                  AS industry,
    UPPER(state)                     AS state_code,
    enrolled_at::TIMESTAMP           AS enrolled_at,
    activated_at::TIMESTAMP          AS activated_at,
    churned_at::TIMESTAMP            AS churned_at,
    size_tier,
    CASE
        WHEN activated_at IS NULL THEN 'never_activated'
        WHEN churned_at IS NOT NULL THEN 'churned'
        ELSE 'active'
    END                              AS smb_status
FROM raw_smbs;
