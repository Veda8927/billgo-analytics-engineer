CREATE OR REPLACE VIEW stg_acquisitions AS
SELECT
    acquisition_id,
    smb_id,
    LOWER(channel)                   AS channel,
    campaign,
    cost_usd::DECIMAL(10,2)          AS cac_usd,
    acquired_at::TIMESTAMP           AS acquired_at
FROM raw_acquisitions;
