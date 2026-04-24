"""Chart 3: Channel acquisition efficiency."""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

import matplotlib.pyplot as plt
import pandas as pd
from generator.db import get_connection
from dashboards.style import (
    apply_style,
    COLOR_ACCENT,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_WARN,
)

apply_style()
OUTPUT_PATH = "docs/charts/03_channel_unit_economics.png"


def fetch_data():
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT channel,
                   SUM(smbs_acquired) AS acquired,
                   SUM(activated_smbs) AS activated,
                   SUM(total_cac) AS total_cac,
                   SUM(total_revenue) AS total_revenue
            FROM mart_channel_unit_economics
            GROUP BY channel
        """, conn)
    finally:
        conn.close()

    df["blended_cac"] = df["total_cac"] / df["acquired"]
    df["activation_rate_pct"] = 100.0 * df["activated"] / df["acquired"]
    df["wasted_cac"] = (df["acquired"] - df["activated"]) * df["blended_cac"]
    return df


def build(df):
    fig, ax = plt.subplots(figsize=(12, 7))

    max_waste = df["wasted_cac"].max()
    sizes = 80 + (df["wasted_cac"] / max_waste) * 3500

    colors = [
        COLOR_WARN if channel == "direct_sales" else COLOR_ACCENT
        for channel in df["channel"]
    ]

    ax.scatter(
        df["blended_cac"],
        df["activation_rate_pct"],
        s=sizes,
        c=colors,
        alpha=0.55,
        edgecolors=COLOR_TEXT,
        linewidth=1.2,
    )

    for _, row in df.iterrows():
        ax.annotate(
            f"{row['channel']}\nCAC ${int(row['blended_cac'])}, wasted ${int(row['wasted_cac'] / 1000)}K",
            xy=(row["blended_cac"], row["activation_rate_pct"]),
            xytext=(12, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
            color=COLOR_TEXT,
        )

    ax.set_xlim(-30, 500)
    ax.set_ylim(76, 82.5)
    ax.set_xlabel("Blended CAC per SMB (USD)")
    ax.set_ylabel("Activation rate (%)")
    ax.set_title("Channel acquisition efficiency", color=COLOR_TEXT)
    ax.grid(True, alpha=0.7)

    ax.text(
        0.99,
        -0.15,
        "Bubble area = wasted CAC on SMBs acquired but never activated.",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        color=COLOR_TEXT_MUTED,
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH)
    plt.close()
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build(fetch_data())
