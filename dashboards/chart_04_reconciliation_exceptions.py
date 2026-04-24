"""Chart 4: Reconciliation exception queue."""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

import matplotlib.pyplot as plt
import pandas as pd
from generator.db import get_connection
from dashboards.style import apply_style, SLATE_3, COLOR_TEXT

apply_style()
OUTPUT_PATH = "docs/charts/04_reconciliation_exceptions.png"


def fetch_data():
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT exception_type,
                   size_tier,
                   COUNT(*) AS exceptions
            FROM mart_reconciliation_exceptions
            GROUP BY exception_type, size_tier
        """, conn)
    finally:
        conn.close()

    return df


def build(df):
    pivot = df.pivot(
        index="exception_type",
        columns="size_tier",
        values="exceptions",
    ).fillna(0)

    exception_order = ["unmatched", "partial_large_delta", "partial_small_delta"]
    pivot = pivot.reindex([x for x in exception_order if x in pivot.index])

    tier_order = ["small", "mid", "large"]
    pivot = pivot[[x for x in tier_order if x in pivot.columns]]

    fig, ax = plt.subplots(figsize=(12, 5.5))

    pivot.plot(
        kind="barh",
        stacked=True,
        ax=ax,
        color=SLATE_3,
        edgecolor="white",
        linewidth=1.5,
        width=0.65,
    )

    for i, (_, row) in enumerate(pivot.iterrows()):
        total = int(row.sum())
        ax.text(
            total + 60,
            i,
            f"{total:,}",
            va="center",
            fontsize=10,
            fontweight="semibold",
            color=COLOR_TEXT,
        )

    ax.set_xlabel("Number of exceptions")
    ax.set_ylabel("")
    ax.set_title("Reconciliation exception queue", color=COLOR_TEXT)
    ax.legend(title="SMB size tier", loc="lower right")
    ax.grid(True, axis="x", alpha=0.7)

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH)
    plt.close()
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build(fetch_data())
