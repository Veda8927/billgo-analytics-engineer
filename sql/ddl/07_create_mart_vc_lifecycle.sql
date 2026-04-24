DROP TABLE IF EXISTS mart_virtual_card_lifecycle CASCADE;

CREATE TABLE mart_virtual_card_lifecycle AS
WITH vc_with_dims AS (
    SELECT
        l.virtual_card_id,
        l.invoice_id,
        l.smb_id,
        s.industry,

        CASE
            WHEN (ABS(HASHTEXT(l.virtual_card_id)) % 2) = 0
            THEN 'visa'
            ELSE 'mastercard'
        END AS card_network,

        DATE_TRUNC('month', COALESCE(l.issued_at, l.reissued_at))::DATE AS issue_month,

        l.final_status,
        l.was_first_time_success,
        l.is_reissued_vc,
        l.invoice_had_reissue,
        l.hours_to_capture,
        l.amount,
        l.interchange_fee,
        l.decline_reason,
        l.chargeback_reason

    FROM fct_payment_lifecycle l
    JOIN dim_smb s USING (smb_id)
    WHERE COALESCE(l.issued_at, l.reissued_at) IS NOT NULL
)
SELECT
    issue_month,
    industry,
    card_network,

    COUNT(*) AS total_vcs,
    COUNT(*) FILTER (WHERE NOT is_reissued_vc) AS original_vcs,
    COUNT(*) FILTER (WHERE is_reissued_vc) AS reissued_vcs,

    COUNT(*) FILTER (WHERE was_first_time_success) AS first_time_successes,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE was_first_time_success)
        / NULLIF(COUNT(*) FILTER (WHERE NOT is_reissued_vc), 0),
        2
    ) AS first_time_success_rate_pct,

    COUNT(*) FILTER (WHERE final_status = 'declined') AS declined_count,
    COUNT(*) FILTER (WHERE final_status = 'expired') AS expired_count,
    COUNT(*) FILTER (WHERE final_status = 'chargebacked') AS chargebacked_count,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE invoice_had_reissue AND NOT is_reissued_vc)
        / NULLIF(COUNT(*) FILTER (WHERE NOT is_reissued_vc), 0),
        2
    ) AS reissue_rate_pct,

    ROUND(AVG(hours_to_capture)::numeric, 2) AS avg_hours_to_capture,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours_to_capture)::numeric,
        2
    ) AS median_hours_to_capture,

    SUM(amount) FILTER (WHERE final_status = 'captured') AS gmv_captured,
    SUM(interchange_fee) FILTER (WHERE final_status = 'captured') AS total_interchange_fees,
    ROUND(AVG(amount) FILTER (WHERE final_status = 'captured')::numeric, 2) AS avg_captured_amount

FROM vc_with_dims
GROUP BY issue_month, industry, card_network
ORDER BY issue_month, industry, card_network;

CREATE INDEX idx_mart_vc_month ON mart_virtual_card_lifecycle(issue_month);
CREATE INDEX idx_mart_vc_industry ON mart_virtual_card_lifecycle(industry);
