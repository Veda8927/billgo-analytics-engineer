"""
Generate raw_reconciliations and backfill raw_smbs.churned_at.

Reconciliation logic:
  - For each captured event, create a reconciliation record later
  - 90% matched
  - 8% partial
  - 2% unmatched

Churn logic:
  - An SMB is churned if their last captured payment is more than 60 days
    before the dataset's latest captured event.
"""
import random
from datetime import timedelta
import numpy as np
from generator.db import get_connection, bulk_insert

random.seed(42)
np.random.seed(42)

SOURCE_SYSTEMS = ["quickbooks", "netsuite", "manual"]
SOURCE_WEIGHTS = [0.65, 0.25, 0.10]


def fetch_captured_events(conn):
    """Pull every captured event with invoice and amount."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_id, invoice_id, amount, event_ts
            FROM raw_payment_events
            WHERE event_type = 'captured'
            ORDER BY event_ts
        """)
        return cur.fetchall()


def generate_reconciliations(captures):
    """Create one reconciliation row per captured event."""
    rows = []

    for i, (event_id, invoice_id, amount, event_ts) in enumerate(captures):
        reconciliation_id = f"rec_{i + 1:08d}"

        reconciled_at = event_ts + timedelta(
            hours=random.randint(12, 72),
            minutes=random.randint(0, 59),
        )

        roll = random.random()

        if roll < 0.90:
            status = "matched"
            received = amount

        elif roll < 0.98:
            status = "partial"
            received = round(float(amount) * random.uniform(0.95, 1.02), 2)

        else:
            status = "unmatched"
            received = None

        source_system = np.random.choice(SOURCE_SYSTEMS, p=SOURCE_WEIGHTS)

        rows.append((
            reconciliation_id,
            invoice_id,
            received,
            reconciled_at,
            status,
            source_system,
        ))

    return rows


def backfill_churn(conn):
    """
    Mark SMBs as churned if their last captured payment was more than 60 days
    before the latest captured event in the dataset.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH last_capture AS (
                SELECT smb_id,
                       MAX(event_ts) AS last_captured_at
                FROM raw_payment_events
                WHERE event_type = 'captured'
                GROUP BY smb_id
            ),
            cutoff AS (
                SELECT MAX(event_ts) AS data_cutoff
                FROM raw_payment_events
                WHERE event_type = 'captured'
            )
            UPDATE raw_smbs s
            SET churned_at = lc.last_captured_at + INTERVAL '60 days'
            FROM last_capture lc, cutoff c
            WHERE s.smb_id = lc.smb_id
              AND lc.last_captured_at < c.data_cutoff - INTERVAL '60 days'
              AND s.activated_at IS NOT NULL
        """)

        rows_updated = cur.rowcount
        conn.commit()
        return rows_updated


def main():
    print("Generating reconciliations and backfilling churn...")

    conn = get_connection()

    try:
        captures = fetch_captured_events(conn)
        print(f"  {len(captures):,} captured events to reconcile")

        reconciliations = generate_reconciliations(captures)

        batch_size = 50000

        for i in range(0, len(reconciliations), batch_size):
            bulk_insert(
                conn,
                "raw_reconciliations",
                [
                    "reconciliation_id",
                    "invoice_id",
                    "payment_amount_received",
                    "reconciled_at",
                    "reconciliation_status",
                    "source_system",
                ],
                reconciliations[i:i + batch_size],
            )

        churned_count = backfill_churn(conn)
        print(f"  ✓ marked {churned_count:,} SMBs as churned")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
