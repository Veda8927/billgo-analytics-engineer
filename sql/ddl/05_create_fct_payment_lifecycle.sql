DROP TABLE IF EXISTS fct_payment_lifecycle CASCADE;

CREATE TABLE fct_payment_lifecycle AS
WITH vc_timestamps AS (
    SELECT
        virtual_card_id,

        MIN(invoice_id) AS invoice_id,
        MIN(smb_id) AS smb_id,

        MIN(event_ts) FILTER (WHERE event_type = 'vc_issued') AS issued_at,
        MIN(event_ts) FILTER (WHERE event_type = 'authorized') AS authorized_at,
        MIN(event_ts) FILTER (WHERE event_type = 'captured') AS captured_at,
        MIN(event_ts) FILTER (WHERE event_type = 'declined') AS declined_at,
        MIN(event_ts) FILTER (WHERE event_type = 'expired') AS expired_at,
        MIN(event_ts) FILTER (WHERE event_type = 'reissued') AS reissued_at,
        MIN(event_ts) FILTER (WHERE event_type = 'chargeback') AS chargeback_at,

        COALESCE(
            MAX(amount) FILTER (WHERE event_type = 'captured'),
            MAX(amount) FILTER (WHERE event_type = 'vc_issued'),
            MAX(amount) FILTER (WHERE event_type = 'reissued')
        ) AS amount,

        MAX(interchange_fee) FILTER (WHERE event_type = 'captured') AS interchange_fee,

        MAX(decline_reason) FILTER (WHERE event_type = 'declined') AS decline_reason,
        MAX(chargeback_reason) FILTER (WHERE event_type = 'chargeback') AS chargeback_reason,

        COUNT(*) AS event_count
    FROM stg_payment_events
    GROUP BY virtual_card_id
),
invoice_reissue_flag AS (
    SELECT DISTINCT invoice_id
    FROM stg_payment_events
    WHERE event_type = 'reissued'
)
SELECT
    v.virtual_card_id,
    v.invoice_id,
    v.smb_id,

    v.issued_at,
    v.authorized_at,
    v.captured_at,
    v.declined_at,
    v.expired_at,
    v.reissued_at,
    v.chargeback_at,

    v.amount,
    v.interchange_fee,
    v.decline_reason,
    v.chargeback_reason,

    v.event_count,

    (v.reissued_at IS NOT NULL) AS is_reissued_vc,

    (irf.invoice_id IS NOT NULL) AS invoice_had_reissue,

    CASE
        WHEN v.captured_at IS NOT NULL AND v.issued_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (v.captured_at - v.issued_at)) / 3600.0
        WHEN v.captured_at IS NOT NULL AND v.reissued_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (v.captured_at - v.reissued_at)) / 3600.0
    END AS hours_to_capture,

    CASE
        WHEN v.captured_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (v.captured_at - COALESCE(v.issued_at, v.reissued_at))) / 3600.0
        WHEN v.expired_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (v.expired_at - COALESCE(v.issued_at, v.reissued_at))) / 3600.0
        WHEN v.declined_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (v.declined_at - COALESCE(v.issued_at, v.reissued_at))) / 3600.0
    END AS vc_lifetime_hours,

    CASE
        WHEN v.chargeback_at IS NOT NULL THEN 'chargebacked'
        WHEN v.captured_at IS NOT NULL THEN 'captured'
        WHEN v.expired_at IS NOT NULL THEN 'expired'
        WHEN v.declined_at IS NOT NULL THEN 'declined'
        WHEN v.issued_at IS NOT NULL THEN 'in_flight'
        WHEN v.reissued_at IS NOT NULL THEN 'in_flight_post_reissue'
        ELSE 'unknown_orphan'
    END AS final_status,

    (v.captured_at IS NOT NULL AND v.reissued_at IS NULL) AS was_first_time_success,

    (v.issued_at IS NULL AND v.reissued_at IS NULL) AS is_orphan_vc

FROM vc_timestamps v
LEFT JOIN invoice_reissue_flag irf USING (invoice_id);

CREATE UNIQUE INDEX idx_fct_lifecycle_pk ON fct_payment_lifecycle(virtual_card_id);
CREATE INDEX idx_fct_lifecycle_invoice ON fct_payment_lifecycle(invoice_id);
CREATE INDEX idx_fct_lifecycle_smb ON fct_payment_lifecycle(smb_id);
CREATE INDEX idx_fct_lifecycle_status ON fct_payment_lifecycle(final_status);
CREATE INDEX idx_fct_lifecycle_issued ON fct_payment_lifecycle(issued_at);
