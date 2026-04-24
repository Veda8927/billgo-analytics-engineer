"""Generate raw_interchange_rates, raw_smbs, raw_acquisitions."""
import random
from datetime import datetime, timedelta
from faker import Faker
import numpy as np
from generator.db import get_connection, bulk_insert

# Reproducibility: same seed means same fake data every run.
random.seed(42)
np.random.seed(42)
fake = Faker()
Faker.seed(42)

# -------- Config --------
START_DATE = datetime(2024, 10, 1)
MONTHS = 18

INDUSTRIES = ["healthcare", "construction", "nonprofit", "services", "retail"]
STATES = ["CO", "CA", "TX", "NY", "WA", "FL", "IL", "MA", "GA", "OR"]
SIZE_TIERS = ["small", "mid", "large"]
SIZE_WEIGHTS = [0.60, 0.30, 0.10]

CHANNELS = ["direct_sales", "paid_search", "partner_referral", "organic", "webinar"]
CHANNEL_WEIGHTS = [0.30, 0.25, 0.20, 0.15, 0.10]

CHANNEL_CAC = {
    "direct_sales": 420,
    "paid_search": 180,
    "partner_referral": 90,
    "organic": 15,
    "webinar": 140,
}


def generate_interchange_rates():
    """Generate visa/mastercard rates by industry."""
    rows = []
    rate_id = 1

    for network in ["visa", "mastercard"]:
        for industry in INDUSTRIES:
            base = 220 if industry == "healthcare" else 260
            variance = random.randint(-15, 15)

            rows.append((
                f"rate_{rate_id:03d}",
                network,
                industry,
                base + variance,
                START_DATE.date(),
            ))

            rate_id += 1

    return rows


def generate_smbs_and_acquisitions():
    """Generate fake SMBs and one acquisition record per SMB."""
    smbs = []
    acquisitions = []

    smb_counter = 1
    acq_counter = 1

    for month_offset in range(MONTHS):
        month_start = START_DATE + timedelta(days=30 * month_offset)

        # Enrollment ramp: about 50 SMBs/month at start, 500/month by the end.
        enrollments_this_month = int(50 + (450 * month_offset / (MONTHS - 1)))

        for _ in range(enrollments_this_month):
            smb_id = f"smb_{smb_counter:06d}"

            enrolled_at = month_start + timedelta(
                days=random.randint(0, 27),
                hours=random.randint(8, 18),
            )

            # 80% of SMBs activate within 14 days.
            if random.random() < 0.80:
                activated_at = enrolled_at + timedelta(days=random.randint(0, 14))
            else:
                activated_at = None

            smbs.append((
                smb_id,
                fake.company()[:200],
                random.choice(INDUSTRIES),
                random.choice(STATES),
                enrolled_at,
                activated_at,
                None,
                np.random.choice(SIZE_TIERS, p=SIZE_WEIGHTS),
            ))

            channel = np.random.choice(CHANNELS, p=CHANNEL_WEIGHTS)
            cost = CHANNEL_CAC[channel] * random.uniform(0.7, 1.3)

            acquisitions.append((
                f"acq_{acq_counter:06d}",
                smb_id,
                channel,
                f"{channel}_{enrolled_at.strftime('%Y%m')}",
                round(cost, 2),
                enrolled_at - timedelta(days=random.randint(1, 30)),
            ))

            smb_counter += 1
            acq_counter += 1

    return smbs, acquisitions


def main():
    print("Generating SMBs and acquisitions...")

    conn = get_connection()

    try:
        rates = generate_interchange_rates()
        bulk_insert(
            conn,
            "raw_interchange_rates",
            ["rate_id", "card_network", "industry", "rate_bps", "effective_from"],
            rates,
        )

        smbs, acquisitions = generate_smbs_and_acquisitions()

        bulk_insert(
            conn,
            "raw_smbs",
            ["smb_id", "business_name", "industry", "state", "enrolled_at", "activated_at", "churned_at", "size_tier"],
            smbs,
        )

        bulk_insert(
            conn,
            "raw_acquisitions",
            ["acquisition_id", "smb_id", "channel", "campaign", "cost_usd", "acquired_at"],
            acquisitions,
        )

        print(f"\nTotal: {len(smbs):,} SMBs, {len(acquisitions):,} acquisitions, {len(rates)} rate rows")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
