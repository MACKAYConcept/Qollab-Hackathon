"""Generate publication-quality, WCAG 2.1 AA compliant comparative charts for QUASAR."""

import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Ensure target directories exist
output_dir = Path("data/charts")
output_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# WCAG 2.1 AA COMPLIANT COLOR PALETTE & DESIGN SYSTEM
# -----------------------------------------------------------------------------
# Background: #0d0d10 (Dark Slate)
# Foreground text: #f7f4ef (Cream) -> 17.8:1 contrast (Passes AAA)
# Muted text: #b5b3ad -> 7.2:1 contrast (Passes AAA)
# Accent Gold (QUASAR): #ffd700 -> 13.5:1 contrast (Passes AAA)
# Accent Cyan (Simulated Annealing): #00e5ff -> 11.2:1 contrast (Passes AAA)
# Accent Coral (Greedy Trajectory): #ff5252 -> 5.8:1 contrast (Passes AA)
# Knapsack Baseline: #94a3b8 -> 6.1:1 contrast (Passes AA)

BG_COLOR = "#0d0d10"
CARD_BG = "#16161a"
TEXT_COLOR = "#f7f4ef"
MUTED_TEXT = "#b5b3ad"
GRID_COLOR = "#2b2b33"

COLORS = {
    "QUASAR (QAOA)": "#ffd700",              # High-contrast Gold
    "Simulated Annealing": "#00e5ff",        # High-contrast Electric Cyan
    "Greedy Trajectory": "#ff5252",          # High-contrast Coral Red
    "Greedy Knapsack (Upper Bound)": "#94a3b8", # High-contrast Slate
}

HATCHES = {
    "QUASAR (QAOA)": "///",
    "Simulated Annealing": "\\\\\\",
    "Greedy Trajectory": "xx",
    "Greedy Knapsack (Upper Bound)": "..",
}

# -----------------------------------------------------------------------------
# BENCHMARK DATASET (Winter Park Resort Empirical Results)
# -----------------------------------------------------------------------------
scenarios = ["1.0-Hour (Sprint)", "2.0-Hour (Half Day)", "4.0-Hour (Full Day)"]
x = np.arange(len(scenarios))
width = 0.20

data_vertical = {
    "QUASAR (QAOA)": [10220, 16580, 17280],
    "Simulated Annealing": [6840, 13280, 14980],
    "Greedy Trajectory": [6800, 15300, 30600],
    "Greedy Knapsack (Upper Bound)": [13160, 17280, 17280],
}

data_uniqueness = {
    "QUASAR (QAOA)": [100.0, 100.0, 100.0],
    "Simulated Annealing": [100.0, 90.0, 83.3],
    "Greedy Trajectory": [60.0, 30.0, 15.8],
    "Greedy Knapsack (Upper Bound)": [100.0, 100.0, 100.0],
}


def apply_wcag_theme(fig, ax):
    """Applies high-contrast dark theme meeting WCAG 2.1 AA specifications."""
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(CARD_BG)
    ax.tick_params(colors=TEXT_COLOR, labelsize=11)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
        spine.set_linewidth(1.2)
    ax.grid(axis="y", color=GRID_COLOR, linestyle="--", alpha=0.7, linewidth=0.8)


# -----------------------------------------------------------------------------
# CHART 1: VERTICAL DESCENT COMPARISON
# -----------------------------------------------------------------------------
def plot_vertical_descent():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    apply_wcag_theme(fig, ax)

    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for i, (name, values) in enumerate(data_vertical.items()):
        bars = ax.bar(
            x + offsets[i],
            values,
            width,
            label=name,
            color=COLORS[name],
            hatch=HATCHES[name],
            edgecolor=TEXT_COLOR,
            linewidth=0.8,
        )
        # Value labels above bars for accessibility
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:,.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
                color=TEXT_COLOR,
            )

    ax.set_ylabel("Cumulative Vertical Descent (feet)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_title("QUASAR vs. Classical Baselines: Vertical Descent by Session Duration\n(Winter Park Resort Topology)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 36000)

    # Annotated callout for greedy loop trap
    ax.annotate(
        "Greedy Short-Loop Trap:\nRepeated Hughes 18 times!",
        xy=(2 + offsets[2], 30600),
        xytext=(1.4, 31000),
        arrowprops=dict(facecolor="#ff5252", edgecolor=TEXT_COLOR, arrowstyle="->", lw=1.5),
        color="#ff5252",
        fontsize=9.5,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor=CARD_BG, edgecolor="#ff5252", lw=1.2),
    )

    legend = ax.legend(loc="upper left", facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9.5)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    plt.tight_layout()
    chart_path = output_dir / "vertical_descent_comparison.png"
    plt.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {chart_path}")


# -----------------------------------------------------------------------------
# CHART 2: RUN UNIQUENESS INDEX COMPARISON
# -----------------------------------------------------------------------------
def plot_uniqueness_index():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    apply_wcag_theme(fig, ax)

    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for i, (name, values) in enumerate(data_uniqueness.items()):
        bars = ax.bar(
            x + offsets[i],
            values,
            width,
            label=name,
            color=COLORS[name],
            hatch=HATCHES[name],
            edgecolor=TEXT_COLOR,
            linewidth=0.8,
        )
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.1f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
                color=TEXT_COLOR,
            )

    # Highlight 100% Target Line
    ax.axhline(100.0, color="#ffd700", linestyle="--", linewidth=1.8, label="100% Uniqueness Target (Zero Repetition)")

    ax.set_ylabel("Run Uniqueness Index (%)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_title("QUASAR vs. Classical Baselines: Run Uniqueness Preservation\n(Avoiding Trail Monotony & Overlap)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 120)

    # Annotation for greedy collapse
    ax.annotate(
        "Severe Loop Degradation:\nUniqueness plummets to 15.8%",
        xy=(2 + offsets[2], 15.8),
        xytext=(1.35, 35),
        arrowprops=dict(facecolor="#ff5252", edgecolor=TEXT_COLOR, arrowstyle="->", lw=1.5),
        color="#ff5252",
        fontsize=9.5,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor=CARD_BG, edgecolor="#ff5252", lw=1.2),
    )

    legend = ax.legend(loc="lower left", facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9.5)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    plt.tight_layout()
    chart_path = output_dir / "uniqueness_index_comparison.png"
    plt.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {chart_path}")


# -----------------------------------------------------------------------------
# CHART 3: COMBINED BENCHMARK DASHBOARD
# -----------------------------------------------------------------------------
def plot_combined_dashboard():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5), dpi=300)
    apply_wcag_theme(fig, ax1)
    apply_wcag_theme(fig, ax2)

    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]

    # Panel 1: Vertical Descent
    for i, (name, values) in enumerate(data_vertical.items()):
        bars = ax1.bar(
            x + offsets[i],
            values,
            width,
            label=name,
            color=COLORS[name],
            hatch=HATCHES[name],
            edgecolor=TEXT_COLOR,
            linewidth=0.8,
        )
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(
                f"{height/1000:.1f}k",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color=TEXT_COLOR,
            )
    ax1.set_ylabel("Vertical Descent (feet)", fontsize=12, fontweight="bold")
    ax1.set_title("(A) Cumulative Vertical Yield", fontsize=13, fontweight="bold", pad=12)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, fontsize=10, fontweight="bold")
    ax1.set_ylim(0, 36000)

    # Panel 2: Uniqueness Index
    for i, (name, values) in enumerate(data_uniqueness.items()):
        bars = ax2.bar(
            x + offsets[i],
            values,
            width,
            label=name,
            color=COLORS[name],
            hatch=HATCHES[name],
            edgecolor=TEXT_COLOR,
            linewidth=0.8,
        )
        for bar in bars:
            height = bar.get_height()
            ax2.annotate(
                f"{height:.0f}%",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
                color=TEXT_COLOR,
            )
    ax2.axhline(100.0, color="#ffd700", linestyle="--", linewidth=1.5, alpha=0.8)
    ax2.set_ylabel("Run Uniqueness (%)", fontsize=12, fontweight="bold")
    ax2.set_title("(B) Run Uniqueness Index", fontsize=13, fontweight="bold", pad=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios, fontsize=10, fontweight="bold")
    ax2.set_ylim(0, 115)

    legend = ax1.legend(loc="upper left", facecolor=CARD_BG, edgecolor=GRID_COLOR, fontsize=9)
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    fig.suptitle(
        "QUASAR vs. Classical Benchmarks: Winter Park Resort Algorithmic Performance\n"
        "WCAG 2.1 AA Compliant Visualization (High Contrast & Pattern Textures)",
        fontsize=15,
        fontweight="bold",
        color=TEXT_COLOR,
        y=0.98,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    chart_path = output_dir / "benchmark_dashboard.png"
    plt.savefig(chart_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated: {chart_path}")


if __name__ == "__main__":
    plot_vertical_descent()
    plot_uniqueness_index()
    plot_combined_dashboard()

    # Sync to docs/charts for GitHub Pages if directory exists
    docs_charts = Path("docs/charts")
    if docs_charts.exists():
        import shutil
        for f in output_dir.glob("*.png"):
            shutil.copy(f, docs_charts / f.name)
        print("Synchronized benchmark charts to docs/charts for GitHub Pages.")
