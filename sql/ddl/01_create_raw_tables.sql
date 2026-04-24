DROP TABLE IF EXISTS raw_reconciliations CASCADE;
DROP TABLE IF EXISTS raw_payment_events CASCADE;
DROP TABLE IF EXISTS raw_invoices CASCADE;
DROP TABLE IF EXISTS raw_acquisitions CASCADE;
DROP TABLE IF EXISTS raw_interchange_rates CASCADE;
DROP TABLE IF EXISTS raw_smbs CASCADE;

CREATE TABLE raw_smbs (
    smb_id           VARCHAR(20) PRIMARY KEY,
    business_name    VARCHAR(200),
    industry         VARCHAR(50),
    state            VARCHAR(2),
    enrolled_at      TIMESTAMP NOT NULL,
    activated_at     TIMESTAMP,
    churned_at       TIMESTAMP,
    size_tier        VARCHAR(10)
);

CREATE TABLE raw_acquisitions (
    acquisition_id   VARCHAR(20) PRIMARY KEY,
    smb_id           VARCHAR(20) REFERENCES raw_smbs(smb_id),
    channel          VARCHAR(30),
    campaign         VARCHAR(100),
    cost_usd         DECIMAL(10,2),
    acquired_at      TIMESTAMP NOT NULL
);

CREATE TABLE raw_interchange_rates (
    rate_id          VARCHAR(20) PRIMARY KEY,
    card_network     VARCHAR(20),
    industry         VARCHAR(50),
    rate_bps         INT,
    effective_from   DATE
);

CREATE TABLE raw_invoices (
    invoice_id       VARCHAR(20) PRIMARY KEY,
    smb_id           VARCHAR(20) REFERENCES raw_smbs(smb_id),
    payer_id         VARCHAR(20),
    invoice_amount   DECIMAL(12,2),
    invoice_sent_at  TIMESTAMP NOT NULL,
    due_date         DATE
);

CREATE TABLE raw_payment_events (
    event_id             VARCHAR(20) PRIMARY KEY,
    invoice_id           VARCHAR(20) REFERENCES raw_invoices(invoice_id),
    smb_id               VARCHAR(20),
    virtual_card_id      VARCHAR(20),
    event_type           VARCHAR(20),
    event_ts             TIMESTAMP NOT NULL,
    amount               DECIMAL(12,2),
    interchange_fee      DECIMAL(12,4),
    decline_reason       VARCHAR(50),
    chargeback_reason    VARCHAR(50)
);

CREATE TABLE raw_reconciliations (
    reconciliation_id        VARCHAR(20) PRIMARY KEY,
    invoice_id               VARCHAR(20) REFERENCES raw_invoices(invoice_id),
    payment_amount_received  DECIMAL(12,2),
    reconciled_at            TIMESTAMP,
    reconciliation_status    VARCHAR(20),
    source_system            VARCHAR(20)
);

CREATE INDEX idx_events_invoice ON raw_payment_events(invoice_id);
CREATE INDEX idx_events_vc ON raw_payment_events(virtual_card_id);
CREATE INDEX idx_events_ts ON raw_payment_events(event_ts);
CREATE INDEX idx_invoices_smb ON raw_invoices(smb_id);
