"""
Tests that catch the two planted data quality bugs in the synthetic generator.

These tests are expected to FAIL initially. That is intentional.
The red failure proves the bugs exist before we fix them.
"""
from tests.conftest import run_scalar, run_query


def test_interchange_fee_within_expected_range(db):
    """
    Interchange fees should not exceed 10% of the captured amount.
    Our normal synthetic rates are around 2%-3%.
    """
    bad_rows = run_query(db, """
        SELECT event_id,
               invoice_id,
               amount,
               interchange_fee,
               ROUND((interchange_fee / amount * 100)::numeric, 2) AS fee_pct
        FROM raw_payment_events
        WHERE event_type = 'captured'
          AND amount > 0
          AND interchange_fee / amount > 0.10
        ORDER BY fee_pct DESC
        LIMIT 5
    """)

    assert len(bad_rows) == 0, (
        "Found captures with interchange_fee > 10% of amount. "
        "Likely decimal-scale bug. First offenders:\n"
        + "\n".join(f"  {row}" for row in bad_rows)
    )


def test_interchange_fee_total_count_of_bugged_rows(db):
    """
    Count all captured events where interchange_fee is clearly too large.
    """
    bad_count = run_scalar(db, """
        SELECT COUNT(*)
        FROM raw_payment_events
        WHERE event_type = 'captured'
          AND amount > 0
          AND interchange_fee / amount > 0.10
    """)

    assert bad_count == 0, (
        f"{bad_count} captured events have interchange_fee > 10% of amount."
    )


def test_every_vc_has_issuance_event(db):
    """
    Every virtual card should have at least one vc_issued or reissued event.
    """
    orphan_vcs = run_query(db, """
        WITH vc_has_issuance AS (
            SELECT
                virtual_card_id,
                BOOL_OR(event_type IN ('vc_issued', 'reissued')) AS has_issuance,
                COUNT(*) AS event_count,
                MIN(event_ts) AS first_event_ts
            FROM raw_payment_events
            GROUP BY virtual_card_id
        )
        SELECT virtual_card_id,
               event_count,
               first_event_ts
        FROM vc_has_issuance
        WHERE has_issuance = FALSE
        LIMIT 5
    """)

    assert len(orphan_vcs) == 0, (
        "Found virtual cards with no issuance event. First offenders:\n"
        + "\n".join(f"  {row}" for row in orphan_vcs)
    )


def test_orphan_vc_count_matches_planted_rate(db):
    """
    Count all orphan VCs. This should fail before cleanup.
    """
    orphan_count = run_scalar(db, """
        WITH vc_has_issuance AS (
            SELECT
                virtual_card_id,
                BOOL_OR(event_type IN ('vc_issued', 'reissued')) AS has_issuance
            FROM raw_payment_events
            GROUP BY virtual_card_id
        )
        SELECT COUNT(*)
        FROM vc_has_issuance
        WHERE has_issuance = FALSE
    """)

    assert orphan_count == 0, (
        f"{orphan_count} virtual cards missing issuance event."
    )
