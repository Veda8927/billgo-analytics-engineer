"""Chart 1: SMB cohort retention heatmap."""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from generator.db import get_connection
from dashboards.style import apply_style, HEATMAP_CMAP, COLOR_TEXT

apply_style()
OUTPUT_PATH = "docs/charts/01_cohort_retention_heatmap.png"


def fetch_data():
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT cohort_month,
                   months_since_enrollment,
                   retention_pct
            FROM mart_smb_cohort_retention
            WHERE months_since_enrollment <= 12
            ORDER BY cohort_month, months_since_enrollment
        """, conn)
    finally:
        conn.close()
    return df


def build(df):
    pivot = df.pivot(
        index="cohort_month",
        columns="months_since_enrollment",
        values="retention_pct",
    )

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".0f",
        cmap=HEATMAP_CMAP,
        vmin=60,
        vmax=100,
        cbar_kws={"label": "Retention %"},
        linewidths=1,
        linecolor="white",
        annot_kws={"size": 9},
        ax=ax,
    )

    ax.set_title("SMB cohort retention", color=COLOR_TEXT)
    ax.set_xlabel("Months since enrollment")
    ax.set_ylabel("Enrollment cohort")
    ax.set_yticklabels([c.strftime("%Y-%m") for c in pivot.index], rotation=0)

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH)
    plt.close()
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build(fetch_data())
