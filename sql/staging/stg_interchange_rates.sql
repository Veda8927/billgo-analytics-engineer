CREATE OR REPLACE VIEW stg_interchange_rates AS
SELECT
    rate_id,
    LOWER(card_network)              AS card_network,
    LOWER(industry)                  AS industry,
    rate_bps,
    rate_bps / 10000.0               AS rate_decimal,
    effective_from
FROM raw_interchange_rates;
