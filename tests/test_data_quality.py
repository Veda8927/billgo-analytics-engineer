"""
Generic data quality tests: row counts, uniqueness, referential integrity,
and value ranges.
"""
from tests.conftest import run_scalar


def test_smbs_have_expected_row_count(db):
    """SMBs should be around 4,900-5,000 per our generator config."""
    count = run_scalar(db, "SELECT COUNT(*) FROM raw_smbs")
    assert 4_800 <= count <= 5_100, f"Unexpected SMB count: {count}"


def test_events_exist(db):
    """Event stream should not be empty."""
    count = run_scalar(db, "SELECT COUNT(*) FROM raw_payment_events")
    assert count > 100_000, f"Event stream too small: {count}"


def test_all_tables_non_empty(db):
    """Every raw table should have data."""
    tables = [
        "raw_smbs",
        "raw_acquisitions",
        "raw_interchange_rates",
        "raw_invoices",
        "raw_payment_events",
        "raw_reconciliations",
    ]

    for table in tables:
        count = run_scalar(db, f"SELECT COUNT(*) FROM {table}")
        assert count > 0, f"Table {table} is empty"


def test_smb_id_is_unique(db):
    """smb_id must be unique."""
    dup_count = run_scalar(db, """
        SELECT COUNT(*) FROM (
            SELECT smb_id
            FROM raw_smbs
            GROUP BY smb_id
            HAVING COUNT(*) > 1
        ) d
    """)
    assert dup_count == 0, f"{dup_count} duplicate smb_ids found"


def test_event_id_is_unique(db):
    """event_id must be unique."""
    dup_count = run_scalar(db, """
        SELECT COUNT(*) FROM (
            SELECT event_id
            FROM raw_payment_events
            GROUP BY event_id
            HAVING COUNT(*) > 1
        ) d
    """)
    assert dup_count == 0, f"{dup_count} duplicate event_ids found"


def test_invoice_id_is_unique(db):
    """invoice_id must be unique."""
    dup_count = run_scalar(db, """
        SELECT COUNT(*) FROM (
            SELECT invoice_id
            FROM raw_invoices
            GROUP BY invoice_id
            HAVING COUNT(*) > 1
        ) d
    """)
    assert dup_count == 0, f"{dup_count} duplicate invoice_ids found"


def test_no_orphan_events(db):
    """Every payment event must reference an existing invoice."""
    orphan_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_payment_events e
        LEFT JOIN raw_invoices i USING (invoice_id)
        WHERE i.invoice_id IS NULL
    """)
    assert orphan_count == 0, f"{orphan_count} events reference missing invoices"


def test_no_orphan_invoices(db):
    """Every invoice must belong to an existing SMB."""
    orphan_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_invoices i
        LEFT JOIN raw_smbs s USING (smb_id)
        WHERE s.smb_id IS NULL
    """)
    assert orphan_count == 0, f"{orphan_count} invoices reference missing SMBs"


def test_invoice_amounts_are_positive(db):
    """Negative or zero invoices would corrupt GMV."""
    bad_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_invoices
        WHERE invoice_amount <= 0
    """)
    assert bad_count == 0, f"{bad_count} invoices with non-positive amount"


def test_activation_after_enrollment(db):
    """No SMB can activate before enrolling."""
    bad_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_smbs
        WHERE activated_at IS NOT NULL
          AND activated_at < enrolled_at
    """)
    assert bad_count == 0, f"{bad_count} SMBs activated before enrollment"


def test_event_timestamps_within_data_window(db):
    """
    Events should fall within the synthetic data window.

    Chargebacks are allowed to occur later because the generator creates
    chargebacks 10-60 days after capture.
    """
    bad_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_payment_events
        WHERE (
            event_ts < '2024-10-01'
            OR event_ts > '2026-05-01'
        )
        AND event_type != 'chargeback'
    """)
    assert bad_count == 0, f"{bad_count} non-chargeback events outside data window"
