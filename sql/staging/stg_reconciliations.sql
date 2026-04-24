CREATE OR REPLACE VIEW stg_reconciliations AS
SELECT
    reconciliation_id,
    invoice_id,
    payment_amount_received::DECIMAL(12,2) AS amount_received,
    reconciled_at::TIMESTAMP               AS reconciled_at,
    LOWER(reconciliation_status)           AS reconciliation_status,
    LOWER(source_system)                   AS source_system
FROM raw_reconciliations;
