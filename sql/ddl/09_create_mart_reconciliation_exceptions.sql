DROP TABLE IF EXISTS mart_reconciliation_exceptions CASCADE;

CREATE TABLE mart_reconciliation_exceptions AS
SELECT
    i.invoice_id,
    i.smb_id,
    s.business_name,
    s.industry,
    s.size_tier,
    i.invoice_amount,
    i.first_captured_at AS captured_at,
    i.reconciled_at,
    i.reconciliation_status,
    i.amount_received,
    i.source_system,

    (i.amount_received - i.invoice_amount) AS reconciliation_delta,

    CASE
        WHEN i.reconciled_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (i.reconciled_at - i.first_captured_at)) / 3600.0
    END AS hours_to_reconcile,

    EXTRACT(EPOCH FROM (
        COALESCE(i.reconciled_at, '2026-03-31'::TIMESTAMP) - i.first_captured_at
    )) / 3600.0 AS hours_since_capture,

    CASE
        WHEN i.reconciliation_status IS NULL THEN 'no_rec_record'
        WHEN i.reconciliation_status = 'unmatched' THEN 'unmatched'
        WHEN i.reconciliation_status = 'partial'
            AND ABS(i.amount_received - i.invoice_amount) > (i.invoice_amount * 0.02)
            THEN 'partial_large_delta'
        WHEN i.reconciliation_status = 'partial' THEN 'partial_small_delta'
        WHEN i.reconciled_at IS NOT NULL
            AND EXTRACT(EPOCH FROM (i.reconciled_at - i.first_captured_at)) / 3600.0 > 96
            THEN 'slow_reconciliation'
        ELSE 'ok'
    END AS exception_type

FROM fct_invoices i
JOIN dim_smb s USING (smb_id)
WHERE i.was_captured = TRUE
  AND (
      i.reconciliation_status IS NULL
      OR i.reconciliation_status IN ('unmatched', 'partial')
      OR (
          i.reconciled_at IS NOT NULL
          AND EXTRACT(EPOCH FROM (i.reconciled_at - i.first_captured_at)) / 3600.0 > 96
      )
  )
ORDER BY hours_since_capture DESC;

CREATE INDEX idx_mart_rec_exc_smb ON mart_reconciliation_exceptions(smb_id);
CREATE INDEX idx_mart_rec_exc_type ON mart_reconciliation_exceptions(exception_type);
