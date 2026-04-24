"""Chart 2: VC first-time success rate over time."""
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from generator.db import get_connection
from dashboards.style import (
    apply_style,
    COLOR_ACCENT,
    COLOR_ACCENT_SOFT,
    COLOR_TEXT,
    COLOR_TEXT_MUTED,
    COLOR_GRID,
)

apply_style()
OUTPUT_PATH = "docs/charts/02_vc_success_rate_trend.png"


def fetch_data():
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT issue_month,
                   card_network,
                   SUM(original_vcs) AS original_vcs,
                   SUM(first_time_successes) AS successes
            FROM mart_virtual_card_lifecycle
            WHERE issue_month <= '2026-03-01'
            GROUP BY issue_month, card_network
            ORDER BY issue_month, card_network
        """, conn)
    finally:
        conn.close()

    df["success_rate_pct"] = 100.0 * df["successes"] / df["original_vcs"]
    return df


def build(df):
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax2 = ax1.twinx()
    volume = df.groupby("issue_month")["original_vcs"].sum().reset_index()
    ax2.bar(
        volume["issue_month"],
        volume["original_vcs"],
        alpha=0.2,
        color=COLOR_GRID,
        width=20,
        zorder=1,
    )
    ax2.set_ylabel("VCs issued / month", color=COLOR_TEXT_MUTED)
    ax2.tick_params(axis="y", labelcolor=COLOR_TEXT_MUTED)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    network_colors = {
        "mastercard": COLOR_ACCENT,
        "visa": COLOR_ACCENT_SOFT,
    }

    for network, grp in df.groupby("card_network"):
        ax1.plot(
            grp["issue_month"],
            grp["success_rate_pct"],
            marker="o",
            markersize=5,
            linewidth=1.8,
            color=network_colors.get(network, COLOR_ACCENT),
            label=network.title(),
            zorder=3,
        )

    ax1.axhline(
        y=78,
        color=COLOR_TEXT_MUTED,
        linestyle="--",
        linewidth=1,
        alpha=0.7,
        zorder=2,
    )

    ax1.text(
        pd.Timestamp("2024-10-15"),
        77.3,
        "target 78%",
        fontsize=8,
        color=COLOR_TEXT_MUTED,
        ha="left",
    )

    ax1.annotate(
        "early-period sampling noise\n(low volume)",
        xy=(pd.Timestamp("2024-11-15"), 72),
        xytext=(pd.Timestamp("2025-01-15"), 68),
        fontsize=8,
        color=COLOR_TEXT_MUTED,
        arrowprops=dict(
            arrowstyle="->",
            color=COLOR_TEXT_MUTED,
            lw=0.7,
            alpha=0.6,
        ),
    )

    ax1.set_ylim(65, 92)
    ax1.set_ylabel("First-time success rate (%)")
    ax1.set_xlabel("Issue month")
    ax1.grid(True, alpha=0.7, axis="y")
    ax1.set_zorder(ax2.get_zorder() + 1)
    ax1.set_frame_on(False)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right")

    ax1.set_title("Virtual card first-time success rate", color=COLOR_TEXT)
    ax1.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH)
    plt.close()
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build(fetch_data())
