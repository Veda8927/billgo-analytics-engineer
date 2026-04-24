CREATE OR REPLACE VIEW stg_payment_events AS
SELECT
    event_id,
    invoice_id,
    smb_id,
    virtual_card_id,
    LOWER(event_type)                AS event_type,
    event_ts::TIMESTAMP              AS event_ts,
    amount::DECIMAL(12,2)            AS amount,
    interchange_fee::DECIMAL(12,4)   AS interchange_fee,
    decline_reason,
    chargeback_reason
FROM raw_payment_events;
