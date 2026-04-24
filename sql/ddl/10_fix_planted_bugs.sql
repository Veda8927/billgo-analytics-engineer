-- Fix planted data quality bugs:
-- 1. Decimal-scale interchange_fee bug
-- 2. Orphan virtual cards missing vc_issued/reissued event

BEGIN;

DO $$
DECLARE
    bad_fee_count INT;
BEGIN
    SELECT COUNT(*)
    INTO bad_fee_count
    FROM raw_payment_events
    WHERE event_type = 'captured'
      AND amount > 0
      AND interchange_fee / amount > 0.10;

    RAISE NOTICE 'Fixing % rows with decimal-scale bug', bad_fee_count;
END $$;

-- Bug 1 fix:
-- Bugged fee was written 100x too large.
-- Example: 268% of amount should be 2.68%.
UPDATE raw_payment_events
SET interchange_fee = ROUND((interchange_fee / 100.0)::numeric, 4)
WHERE event_type = 'captured'
  AND amount > 0
  AND interchange_fee / amount > 0.10;

COMMIT;


BEGIN;

DO $$
DECLARE
    orphan_count INT;
BEGIN
    WITH vc_has_issuance AS (
        SELECT
            virtual_card_id,
            BOOL_OR(event_type IN ('vc_issued', 'reissued')) AS has_issuance
        FROM raw_payment_events
        GROUP BY virtual_card_id
    )
    SELECT COUNT(*)
    INTO orphan_count
    FROM vc_has_issuance
    WHERE has_issuance = FALSE;

    RAISE NOTICE 'Synthesizing vc_issued events for % orphan VCs', orphan_count;
END $$;

-- Bug 2 fix:
-- For each orphan VC, synthesize a vc_issued event one minute before
-- its first observed event.
WITH orphan_vcs AS (
    SELECT
        virtual_card_id
    FROM raw_payment_events
    GROUP BY virtual_card_id
    HAVING BOOL_OR(event_type IN ('vc_issued', 'reissued')) = FALSE
),
first_orphan_event AS (
    SELECT DISTINCT ON (e.virtual_card_id)
        e.virtual_card_id,
        e.invoice_id,
        e.smb_id,
        e.event_ts,
        e.amount
    FROM raw_payment_events e
    JOIN orphan_vcs o USING (virtual_card_id)
    ORDER BY e.virtual_card_id, e.event_ts
),
numbered AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY virtual_card_id) AS rn,
        *
    FROM first_orphan_event
)
INSERT INTO raw_payment_events (
    event_id,
    invoice_id,
    smb_id,
    virtual_card_id,
    event_type,
    event_ts,
    amount,
    interchange_fee,
    decline_reason,
    chargeback_reason
)
SELECT
    'fixevt_' || LPAD(rn::TEXT, 6, '0') AS event_id,
    invoice_id,
    smb_id,
    virtual_card_id,
    'vc_issued' AS event_type,
    event_ts - INTERVAL '1 minute' AS event_ts,
    amount,
    NULL AS interchange_fee,
    NULL AS decline_reason,
    NULL AS chargeback_reason
FROM numbered;

COMMIT;
