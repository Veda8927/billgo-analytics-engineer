"""
Generate raw_invoices and raw_payment_events.

For each activated SMB, generate invoices from activation date to a cutoff.
For each invoice, walk the payment state machine and emit events.

Two bugs are deliberately planted:
1. Decimal scale bug in interchange_fee
2. Orphan VC events that skip vc_issued
"""
import random
from datetime import datetime, timedelta
from generator.db import get_connection, bulk_insert

random.seed(42)

DATA_CUTOFF = datetime(2026, 3, 31)

INVOICES_PER_MONTH = {
    "small": (1, 3),
    "mid": (3, 8),
    "large": (10, 25),
}

INVOICE_AMOUNT = {
    "small": (50, 2000),
    "mid": (500, 15000),
    "large": (2000, 75000),
}

DECLINE_REASONS = ["insufficient_funds", "risk_decline", "card_not_found", "expired_card"]
CHARGEBACK_REASONS = ["fraud", "product_not_received", "duplicate_charge", "authorization_issue"]
CARD_NETWORKS = ["visa", "mastercard"]

DECIMAL_BUG_RATE = 0.005
ORPHAN_BUG_RATE = 0.002


def fetch_active_smbs(conn):
    """Get all SMBs that activated."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT smb_id, industry, size_tier, activated_at
            FROM raw_smbs
            WHERE activated_at IS NOT NULL
            ORDER BY activated_at
        """)
        return cur.fetchall()


def fetch_rate_lookup(conn):
    """Build {(network, industry): rate_bps} lookup."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT card_network, industry, rate_bps
            FROM raw_interchange_rates
        """)
        return {(network, industry): rate_bps for network, industry, rate_bps in cur.fetchall()}


def generate_invoices_for_smb(smb_id, size_tier, activated_at, invoice_counter):
    """Generate invoices month by month for one SMB."""
    invoices = []
    current = activated_at

    min_inv, max_inv = INVOICES_PER_MONTH[size_tier]
    amt_min, amt_max = INVOICE_AMOUNT[size_tier]

    will_churn = random.random() < 0.20
    churn_month = None

    if will_churn:
        months_active = max(1, (DATA_CUTOFF - activated_at).days // 30)
        churn_month = activated_at + timedelta(days=30 * random.randint(1, months_active))

    while current < DATA_CUTOFF:
        if churn_month and current > churn_month:
            break

        n_invoices = random.randint(min_inv, max_inv)

        for _ in range(n_invoices):
            sent_at = current + timedelta(
                days=random.randint(0, 27),
                hours=random.randint(8, 18),
                minutes=random.randint(0, 59),
            )

            if sent_at >= DATA_CUTOFF:
                continue

            amount = round(random.uniform(amt_min, amt_max), 2)
            invoice_id = f"inv_{invoice_counter:08d}"

            invoices.append((
                invoice_id,
                smb_id,
                f"payer_{random.randint(1, 50000):06d}",
                amount,
                sent_at,
                (sent_at + timedelta(days=30)).date(),
            ))

            invoice_counter += 1

        current += timedelta(days=30)

    return invoices, invoice_counter


def generate_events_for_invoice(
    invoice_id,
    smb_id,
    amount,
    sent_at,
    industry,
    rate_lookup,
    event_counter,
    vc_counter,
):
    """Generate payment lifecycle events for one invoice."""
    events = []
    roll = random.random()
    card_network = random.choice(CARD_NETWORKS)
    rate_bps = rate_lookup.get((card_network, industry), 250)

    def new_vc_id():
        nonlocal vc_counter
        vc_id = f"vc_{vc_counter:08d}"
        vc_counter += 1
        return vc_id

    def new_event_id():
        nonlocal event_counter
        event_id = f"evt_{event_counter:09d}"
        event_counter += 1
        return event_id

    def emit(vc_id, event_type, ts, amount=None, interchange=None, decline=None, chargeback=None):
        events.append((
            new_event_id(),
            invoice_id,
            smb_id,
            vc_id,
            event_type,
            ts,
            amount,
            interchange,
            decline,
            chargeback,
        ))

    def compute_interchange(amt):
        fee_dollars = round(amt * rate_bps / 10000, 4)

        # BUG 1: sometimes write the fee at the wrong decimal scale.
        if random.random() < DECIMAL_BUG_RATE:
            return float(rate_bps * amt / 100)

        return fee_dollars

    vc_id = new_vc_id()
    issue_ts = sent_at + timedelta(minutes=random.randint(1, 60))

    # BUG 2: sometimes skip vc_issued.
    skip_issued = random.random() < ORPHAN_BUG_RATE

    if not skip_issued:
        emit(vc_id, "vc_issued", issue_ts, amount=amount)

    # 78% happy path: issued -> authorized -> captured
    if roll < 0.78:
        auth_ts = issue_ts + timedelta(hours=random.randint(1, 48))
        cap_ts = auth_ts + timedelta(minutes=random.randint(1, 30))

        emit(vc_id, "authorized", auth_ts, amount=amount)
        emit(vc_id, "captured", cap_ts, amount=amount, interchange=compute_interchange(amount))

        if random.random() < 0.01:
            cb_ts = cap_ts + timedelta(days=random.randint(10, 60))
            emit(vc_id, "chargeback", cb_ts, amount=amount, chargeback=random.choice(CHARGEBACK_REASONS))

    # 7% decline
    elif roll < 0.85:
        decline_ts = issue_ts + timedelta(hours=random.randint(1, 48))
        emit(vc_id, "declined", decline_ts, amount=amount, decline=random.choice(DECLINE_REASONS))

    # 12% expire -> reissue -> captured
    elif roll < 0.97:
        expire_ts = issue_ts + timedelta(days=random.randint(1, 5))
        emit(vc_id, "expired", expire_ts)

        new_vc = new_vc_id()
        reissue_ts = expire_ts + timedelta(minutes=random.randint(5, 60))

        emit(new_vc, "reissued", reissue_ts, amount=amount)

        auth_ts = reissue_ts + timedelta(hours=random.randint(1, 24))
        cap_ts = auth_ts + timedelta(minutes=random.randint(1, 30))

        emit(new_vc, "authorized", auth_ts, amount=amount)
        emit(new_vc, "captured", cap_ts, amount=amount, interchange=compute_interchange(amount))

    # 3% expire -> reissue -> fail
    else:
        expire_ts = issue_ts + timedelta(days=random.randint(1, 5))
        emit(vc_id, "expired", expire_ts)

        new_vc = new_vc_id()
        reissue_ts = expire_ts + timedelta(minutes=random.randint(5, 60))

        emit(new_vc, "reissued", reissue_ts, amount=amount)

        if random.random() < 0.5:
            emit(
                new_vc,
                "declined",
                reissue_ts + timedelta(hours=2),
                amount=amount,
                decline=random.choice(DECLINE_REASONS),
            )
        else:
            emit(new_vc, "expired", reissue_ts + timedelta(days=random.randint(1, 5)))

    return events, event_counter, vc_counter


def main():
    print("Generating invoices and payment events...")

    conn = get_connection()

    try:
        smbs = fetch_active_smbs(conn)
        rate_lookup = fetch_rate_lookup(conn)

        print(f"  {len(smbs):,} activated SMBs to process")

        all_invoices = []
        invoice_counter = 1

        for smb_id, industry, size_tier, activated_at in smbs:
            invoices, invoice_counter = generate_invoices_for_smb(
                smb_id,
                size_tier,
                activated_at,
                invoice_counter,
            )
            all_invoices.extend(invoices)

        print(f"  generated {len(all_invoices):,} invoices")

        bulk_insert(
            conn,
            "raw_invoices",
            ["invoice_id", "smb_id", "payer_id", "invoice_amount", "invoice_sent_at", "due_date"],
            all_invoices,
        )

        smb_industry = {smb_id: industry for smb_id, industry, _, _ in smbs}

        all_events = []
        event_counter = 1
        vc_counter = 1

        for invoice_id, smb_id, _, amount, sent_at, _ in all_invoices:
            events, event_counter, vc_counter = generate_events_for_invoice(
                invoice_id,
                smb_id,
                float(amount),
                sent_at,
                smb_industry[smb_id],
                rate_lookup,
                event_counter,
                vc_counter,
            )
            all_events.extend(events)

        print(f"  generated {len(all_events):,} events across {vc_counter:,} VCs")

        batch_size = 50000

        for i in range(0, len(all_events), batch_size):
            bulk_insert(
                conn,
                "raw_payment_events",
                [
                    "event_id",
                    "invoice_id",
                    "smb_id",
                    "virtual_card_id",
                    "event_type",
                    "event_ts",
                    "amount",
                    "interchange_fee",
                    "decline_reason",
                    "chargeback_reason",
                ],
                all_events[i:i + batch_size],
            )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
