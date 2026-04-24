DROP TABLE IF EXISTS dim_date CASCADE;

CREATE TABLE dim_date AS
SELECT
    d::DATE                                AS date_key,
    EXTRACT(YEAR FROM d)::INT              AS year,
    EXTRACT(QUARTER FROM d)::INT           AS quarter,
    EXTRACT(MONTH FROM d)::INT             AS month,
    TO_CHAR(d, 'Mon')                      AS month_name,
    EXTRACT(WEEK FROM d)::INT              AS week_of_year,
    EXTRACT(DOW FROM d)::INT               AS day_of_week,
    TO_CHAR(d, 'Dy')                       AS day_name,
    EXTRACT(DAY FROM d)::INT               AS day_of_month,
    DATE_TRUNC('month', d)::DATE           AS month_start_date,
    DATE_TRUNC('quarter', d)::DATE         AS quarter_start_date,
    DATE_TRUNC('year', d)::DATE            AS year_start_date,
    CASE
        WHEN EXTRACT(DOW FROM d) IN (0, 6) THEN TRUE
        ELSE FALSE
    END                                    AS is_weekend,
    TO_CHAR(d, 'YYYY-MM')                  AS year_month
FROM generate_series(
    '2024-10-01'::DATE,
    '2027-12-31'::DATE,
    '1 day'::INTERVAL
) AS d;

CREATE UNIQUE INDEX idx_dim_date_key ON dim_date(date_key);
CREATE INDEX idx_dim_date_month ON dim_date(month_start_date);
