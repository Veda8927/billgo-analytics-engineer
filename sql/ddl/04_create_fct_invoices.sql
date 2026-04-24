DROP TABLE IF EXISTS fct_invoices CASCADE;

CREATE TABLE fct_invoices AS
WITH invoice_outcomes AS (
    SELECT
        invoice_id,
        BOOL_OR(event_type = 'captured')    AS was_captured,
        BOOL_OR(event_type = 'chargeback')  AS was_chargebacked,
        BOOL_OR(event_type = 'expired')     AS had_expiry,
        BOOL_OR(event_type = 'reissued')    AS had_reissue,
        COUNT(DISTINCT virtual_card_id)     AS vc_count,
        MIN(event_ts) FILTER (WHERE event_type = 'vc_issued')   AS first_issued_at,
        MIN(event_ts) FILTER (WHERE event_type = 'captured')    AS first_captured_at,
        SUM(interchange_fee) FILTER (WHERE event_type = 'captured') AS total_interchange_fee
    FROM stg_payment_events
    GROUP BY invoice_id
),
invoice_reconciliation AS (
    SELECT
        invoice_id,
        MAX(amount_received)            AS amount_received,
        MAX(reconciliation_status)      AS reconciliation_status,
        MAX(reconciled_at)              AS reconciled_at,
        MAX(source_system)              AS source_system
    FROM stg_reconciliations
    GROUP BY invoice_id
)
SELECT
    i.invoice_id,
    i.smb_id,
    i.payer_id,
    d.date_key                          AS invoice_date,
    d.month_start_date                  AS invoice_month,

    i.invoice_amount,
    i.invoice_sent_at,
    i.due_date,
    i.net_days,

    COALESCE(o.was_captured, FALSE)     AS was_captured,
    COALESCE(o.was_chargebacked, FALSE) AS was_chargebacked,
    COALESCE(o.had_expiry, FALSE)       AS had_expiry,
    COALESCE(o.had_reissue, FALSE)      AS had_reissue,
    COALESCE(o.vc_count, 0)             AS vc_count,

    o.first_issued_at,
    o.first_captured_at,

    CASE
        WHEN o.first_captured_at IS NOT NULL
        THEN (o.first_captured_at::DATE - i.invoice_sent_at::DATE)
    END                                 AS days_to_cash,

    o.total_interchange_fee,

    r.amount_received,
    r.reconciliation_status,
    r.reconciled_at,
    r.source_system,

    CASE
        WHEN o.was_chargebacked THEN 'chargebacked'
        WHEN o.was_captured THEN 'captured'
        WHEN o.first_issued_at IS NOT NULL THEN 'in_flight'
        ELSE 'no_payment_attempt'
    END                                 AS invoice_outcome

FROM stg_invoices i
LEFT JOIN invoice_outcomes o USING (invoice_id)
LEFT JOIN invoice_reconciliation r USING (invoice_id)
LEFT JOIN dim_date d ON d.date_key = i.invoice_sent_at::DATE;

CREATE UNIQUE INDEX idx_fct_invoices_pk ON fct_invoices(invoice_id);
CREATE INDEX idx_fct_invoices_smb ON fct_invoices(smb_id);
CREATE INDEX idx_fct_invoices_month ON fct_invoices(invoice_month);
CREATE INDEX idx_fct_invoices_outcome ON fct_invoices(invoice_outcome);
