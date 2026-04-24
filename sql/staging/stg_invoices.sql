CREATE OR REPLACE VIEW stg_invoices AS
SELECT
    invoice_id,
    smb_id,
    payer_id,
    invoice_amount::DECIMAL(12,2)    AS invoice_amount,
    invoice_sent_at::TIMESTAMP       AS invoice_sent_at,
    due_date::DATE                   AS due_date,
    (due_date - invoice_sent_at::DATE) AS net_days
FROM raw_invoices;
