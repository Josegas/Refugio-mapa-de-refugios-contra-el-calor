"""Charts for the write-up, drawn from web/data/<city>/stats.json (so they redraw when the data changes).

  K6  docs/assets/k6_bands.png      older adults by walking minutes to the nearest refuge, one bar per city
  K7  docs/assets/k7_coverage.png   % of older adults within 10 min vs number of proposed buildings (greedy)

Colors: K6 uses the map's own 5-step blue ramp (RAMP in pipeline/render_html.py); K7 uses three
categorical colors checked for color blindness. Every series is also labeled in text.

Usage:  python docs/diagrams/charts.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
from render_html import BAND_LABELS, INK as RAMP_INK, RAMP  # same colors and labels as the map

ASSETS = ROOT / "docs" / "assets"
CITIES = ["culiacan", "hermosillo", "mexicali"]
CITY_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]  # categorical slots 1-3, validated all-pairs
SURFACE, TEXT, TEXT2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#6b6a65", "#e1e0d9"
SOURCE = "Source: Overture Maps Foundation (release {release}) and Meta/CIESIN HRSL; walking network at 3.6 km/h."

plt.rcParams.update({"font.family": ["Noto Sans", "DejaVu Sans"],  # DejaVu fills in symbols like ≤ and →
                     "font.size": 12, "text.color": TEXT, "axes.edgecolor": GRID, "axes.labelcolor": TEXT2,
                     "xtick.color": TEXT2, "ytick.color": TEXT2, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def load():
    return [json.loads((ROOT / "web" / "data" / c / "stats.json").read_text()) for c in CITIES]


def header(fig, title, subtitle):
    fig.text(0.035, 0.94, title, fontsize=17, fontweight="bold", color=TEXT, va="top")
    fig.text(0.035, 0.865, subtitle, fontsize=12, color=TEXT2, va="top")


def bands_chart(stats):
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(left=0.16, right=0.97, top=0.66, bottom=0.2)
    header(fig, "How far older adults live from the nearest cool refuge, on foot",
           "Share of people aged 60+ by walking minutes to the nearest refuge (mall, store, library, museum, "
           "community center)")
    names = [f"{s['city']}\n{s['population']['pop60']:,} aged 60+" for s in stats]
    for row, s in enumerate(stats):
        bands = s["map_bands"]["refugio"]
        total = s["population"]["pop60"]
        left = 0.0
        for i, key in enumerate(BAND_LABELS):
            share = 100 * bands[key]["pop60"] / total
            # 2 px surface gap between segments (edgecolor = surface)
            ax.barh(row, share, left=left, height=0.62, color=RAMP[i], edgecolor=SURFACE, linewidth=2)
            if share >= 8:
                ax.text(left + share / 2, row, f"{share:.0f}%", ha="center", va="center", fontsize=11.5,
                        fontweight="bold", color=RAMP_INK[i])
            left += share
    ax.set_yticks(range(len(stats)), names, fontsize=12)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.tick_params(length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    # Legend in one row above the bars, lightest (closest) first
    handles = [plt.Rectangle((0, 0), 1, 1, color=RAMP[i]) for i in range(len(RAMP))]
    fig.legend(handles, list(BAND_LABELS.values()), loc="upper left", bbox_to_anchor=(0.155, 0.79), ncol=5,
               frameon=False, fontsize=11.5, handlelength=1.2, columnspacing=1.6,
               title="Walking minutes to the nearest refuge", title_fontsize=11, alignment="left")
    fig.text(0.035, 0.04, SOURCE.format(release=stats[0]["sources"]["overture_release"]), fontsize=9.5, color=MUTED)
    return fig


def coverage_chart(stats):
    fig, ax = plt.subplots(figsize=(10, 5.8))
    fig.subplots_adjust(left=0.09, right=0.8, top=0.75, bottom=0.23)
    c0 = stats[0]["proposals"]["coverage_curve_pct60"]
    first, last = c0[1] - c0[0], c0[-1] - c0[-2]
    header(fig, "Ten public buildings opened as refuges: who they would bring within 10 minutes",
           f"% of older adults within a 10-minute walk of a refuge, as proposed buildings are added one at a time "
           f"(greedy).\nReturns shrink as the biggest gaps get covered: in {stats[0]['city']}, the 1st building "
           f"adds {first:.1f} points and the 10th adds {last:.1f}.")
    for s, color in zip(stats, CITY_COLORS):
        curve = s["proposals"]["coverage_curve_pct60"]
        x = list(range(len(curve)))
        ax.plot(x, curve, color=color, linewidth=2.2, marker="o", markersize=6.5,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=s["city"], zorder=3)
        # Direct label at the end of each line (text in ink, the colored line carries identity)
        ax.text(x[-1] + 0.3, curve[-1], f"{s['city']} {curve[-1]}%", va="center", fontsize=11.5,
                color=TEXT)
    # Separate end labels that would overlap (the three cities end within ~0.4 points)
    texts = [t for t in ax.texts]
    texts.sort(key=lambda t: t.get_position()[1], reverse=True)
    for i, t in enumerate(texts):
        xpos, ypos = t.get_position()
        t.set_position((xpos, texts[0].get_position()[1] - i * 1.1 if i else ypos))
    ax.set_xlim(-0.3, 10.3)
    ax.set_xticks(range(11))
    ax.set_xlabel("Proposed public buildings opened as refuges")
    lo = min(min(s["proposals"]["coverage_curve_pct60"]) for s in stats)
    hi = max(max(s["proposals"]["coverage_curve_pct60"]) for s in stats)
    ax.set_ylim(int(lo // 5) * 5, int(hi // 5) * 5 + 5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=11, ncol=3)
    fig.text(0.035, 0.035, SOURCE.format(release=stats[0]["sources"]["overture_release"])
             + "\nCandidates: existing public schools, district offices, community and sports centers.",
             fontsize=9.5, color=MUTED, linespacing=1.5)
    return fig


def main():
    stats = load()
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, fig in (("k6_bands", bands_chart(stats)), ("k7_coverage", coverage_chart(stats))):
        fig.savefig(ASSETS / f"{name}.png", dpi=200)
        plt.close(fig)
        print(f"wrote docs/assets/{name}.png")


if __name__ == "__main__":
    main()
