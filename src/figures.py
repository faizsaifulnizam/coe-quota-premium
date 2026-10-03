"""S3 figures — code-generated, series style, light + dark (theme-adaptive). Run: python src/figures.py (repo root).

Produces (reports/figures/), each as a light/dark pair for `<picture>` README embeds:
  f1_quota_premium[-dark].png  — two panels (Cat A, B): quota premium (left) vs quota (right), May-2022 line
  f2_pressure[-dark].png       — two panels: bids-per-quota (top) and success rate (bottom), Cat A & B
  f3_scatter[-dark].png        — two panels: quota vs premium scatter, pre/post May 2022 colored

Reads the parquet via DuckDB; re-runs sql/02 so figures always match the SQL. Long titles and
footnotes are width-checked at render size by pixel extent (not eyeballed); text clearance,
in-bounds clipping and annotation overlaps are asserted in-code; every visible text artist
must sit inside the canvas. Re-render twice and hash-compare before committing.
"""
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.style import use_series_style  # noqa: E402

use_series_style()

import duckdb  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402
from matplotlib.textpath import TextPath  # noqa: E402

from src.analysis import run_script  # noqa: E402

PARQUET = (ROOT / "data/processed/coe_exercises.parquet").as_posix()
FIGDIR = ROOT / "reports/figures"
DPI = 200
MARGIN_PX = 40  # keep text this far from the canvas edge

LIGHT = dict(ink="#14293D", petrol="#22607B", burnt="#C0552B", teal="#2E7D6B",
             violet="#8A6EAF", brass="#B9975B", muted="#5C6B79", light="#C9C6BF",
             edge="white", suffix="")
DARK = dict(ink="#E7E3DC", petrol="#4C93B5", burnt="#D97E4F", teal="#45A08B",
            violet="#A78FC8", brass="#D4B87A", muted="#8B98A5", light="#435D73",
            edge="#14293D", suffix="-dark")
T = LIGHT

MANIFEST = ROOT / "data/raw/pull_manifest.json"


def use_palette(p):
    global T
    T = p


def _source_date():
    try:
        ts = json.loads(MANIFEST.read_text(encoding="utf-8")).get("retrieved_at", "")
        return ts[:10] or None
    except Exception:
        return None


SRC = f"Source: LTA COE bidding results (data.gov.sg), pulled {_source_date() or 'n/a'}"
PREMIUM_NOTE = "Premium = quota premium — the lowest successful bid price for the exercise (not the PQP, the renewal price)"
BREAK_LABEL = "Category A/B redefined\nfrom May 2022 1st exercise"
BREAK_DATE = "2022-05-01"


def q(con, sql):
    return con.sql(sql).fetchall()


def foot(fig, text):
    return fig.text(0.01, 0.012, text, fontsize=7.5, color=T["muted"], va="bottom")


def drawn_title(ax):
    """The title artist that actually renders. The style sets `axes.titlelocation: left`,
    so the visible title is `ax._left_title` — `ax.title` is the never-drawn centre one
    (its window extent is degenerate; checking it silently passes)."""
    for t in (ax._left_title, ax.title, ax._right_title):
        if t.get_text().strip():
            return t
    return ax.title


def assert_clear(fig, pairs, label):
    """Receipt for text clearance: none of these (artist, artist) bboxes may overlap."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for a, b in pairs:
        ba, bb = a.get_window_extent(r), b.get_window_extent(r)
        ok = not ba.overlaps(bb)
        print(f"   [{'PASS' if ok else 'FAIL'}] clearance {label}")
        assert ok, f"{label}: text boxes overlap"


def assert_inbounds(fig, label, pad=3):
    """Receipt: every visible text artist sits fully inside the canvas (no clipping)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    w, h = fig.canvas.get_width_height()
    bad = []
    for t in fig.findobj(matplotlib.text.Text):
        if not t.get_text().strip() or not t.get_visible():
            continue
        bb = t.get_window_extent(r)
        if bb.x0 < pad or bb.y0 < pad - 2 or bb.x1 > w - pad or bb.y1 > h - pad:
            bad.append((t.get_text()[:44].replace("\n", " / "), round(bb.x0), round(bb.y0), round(bb.x1), round(bb.y1)))
    ok = not bad
    print(f"   [{'PASS' if ok else 'FAIL'}] in-bounds {label} ({len(bad)} clipped)")
    for b in bad[:6]:
        print("       clipped:", b)
    assert ok, f"{label}: {len(bad)} text artist(s) clipped"


def assert_texts_clear(fig, label):
    """Receipt: no two annotation texts inside the same axes overlap."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bad = []
    for ax in fig.axes:
        texts = [t for t in ax.texts if t.get_text().strip() and t.get_visible()]
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if texts[i].get_window_extent(r).overlaps(texts[j].get_window_extent(r)):
                    bad.append((texts[i].get_text()[:32], texts[j].get_text()[:32]))
    ok = not bad
    print(f"   [{'PASS' if ok else 'FAIL'}] annotation overlaps {label} ({len(bad)})")
    for b in bad[:6]:
        print("       overlap:", b)
    assert ok, f"{label}: {len(bad)} annotation overlap(s)"


def assert_legend_clear(fig, label):
    """Receipt: no legend box overlaps an annotation text in the same axes."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bad = []
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None:
            continue
        lb = leg.get_window_extent(r)
        for t in ax.texts:
            if t.get_text().strip() and t.get_visible() and lb.overlaps(t.get_window_extent(r)):
                bad.append((t.get_text()[:30], "legend"))
    ok = not bad
    print(f"   [{'PASS' if ok else 'FAIL'}] legend vs annotations {label} ({len(bad)})")
    for b in bad[:6]:
        print("       overlap:", b)
    assert ok, f"{label}: {len(bad)} legend/annotation overlap(s)"


def save(fig, name):
    p = FIGDIR / name.replace(".png", T["suffix"] + ".png")
    fig.savefig(p)
    plt.close(fig)
    print(f"wrote {p.as_posix()}  ({p.stat().st_size} bytes)")


def text_px(s, size_pt):
    """Rendered width of `s` in pixels at the figure DPI (Inter)."""
    fp = FontProperties(family="Inter", size=size_pt)
    return TextPath((0, 0), s, prop=fp).get_extents().width / 72 * DPI


def assert_fits(s, size_pt, label, canvas_in):
    px = max(text_px(line, size_pt) for line in s.split("\n"))
    limit = canvas_in * DPI - MARGIN_PX
    ok = px <= limit
    print(f"   [{'PASS' if ok else 'FAIL'}] width {label}: {px:.0f}px vs {limit:.0f}px limit")
    assert ok, f"{label} too wide: {px:.0f}px > {limit:.0f}px"


def series(con, cat):
    return q(con, f"""SELECT month, quota, bids_received, bids_per_quota, success_rate, premium
                      FROM exercise WHERE category = '{cat}' ORDER BY month, round_no""")


def fig1_quota_premium(con, canvas_in=9.0):
    title = "Premiums climb to records while quotas cycle — Category A and B, 2010–2026"
    foottext = (f"{PREMIUM_NOTE}\nNo exercises Apr–Jun 2020 (bidding pause) · vertical line: A/B redefinition · {SRC}")
    assert_fits(title, 12.5, "F1 title", canvas_in)
    assert_fits(foottext, 7.5, "F1 footnote", canvas_in)

    fig, axs = plt.subplots(2, 1, figsize=(canvas_in, 7.0), sharex=True)
    st = fig.suptitle(title, x=0.012, y=0.985, ha="left", fontsize=12.5, color=T["ink"])
    summary = []

    for ax, cat, ylim_p, ylim_q in ((axs[0], "Category A", (15000, 142000), (300, 2400)),
                                    (axs[1], "Category B", (15000, 160000), (280, 1650))):
        rows = series(con, cat)
        xs = [r[0] for r in rows]
        prem = [float(r[5]) for r in rows]
        quota = [float(r[1]) for r in rows]

        ax.plot(xs, prem, color=T["petrol"], lw=1.9, label="quota premium (S$, left)")
        ax.set_ylim(*ylim_p)
        ax.set_ylabel("S$ (premium)", fontsize=9)
        axr = ax.twinx()
        axr.plot(xs, quota, color=T["teal"], lw=1.4, ls="--", label="quota (certificates, right)")
        axr.set_ylim(*ylim_q)
        axr.set_ylabel("certificates per exercise", fontsize=9)
        for sp in axr.spines.values():
            sp.set_visible(False)
        axr.tick_params(axis="y", length=0)
        axr.grid(False)

        ax.axvline(mdates.datestr2num(BREAK_DATE), color=T["ink"], lw=0.9, ls=":", alpha=0.9)
        ax.set_title(f"Category {cat[-1]}", fontsize=10, color=T["muted"])

        i_max = prem.index(max(prem))
        summary.append((cat, prem[0], prem[-1], max(prem)))
        ax.annotate(f"record {prem[i_max]:,.0f}", (xs[i_max], prem[i_max]), xytext=(-10, 10),
                    textcoords="offset points", ha="right", fontsize=8, color=T["ink"])
        ax.annotate(f"{prem[-1]:,.0f}", (xs[-1], prem[-1]), xytext=(6, -2),
                    textcoords="offset points", fontsize=8, color=T["ink"], va="top")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axr.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="best", fontsize=8)

    axs[0].annotate(BREAK_LABEL, (mdates.datestr2num(BREAK_DATE), 142000 * 0.995), xytext=(4, -12),
                    textcoords="offset points", fontsize=8, color=T["muted"], va="top")
    axs[1].set_xlim(mdates.date2num(rows[0][0]), mdates.date2num(rows[-1][0]) + 420)
    axs[1].set_xticks([date(y, 1, 1) for y in range(2010, 2027, 2)])
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.105, right=0.915, top=0.895, bottom=0.10, hspace=0.24)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, drawn_title(axs[0])), (st, drawn_title(axs[1])),
                       (ftxt, axs[1].get_xticklabels()[-1])], "F1 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F1")
    assert_texts_clear(fig, "F1")
    assert_legend_clear(fig, "F1")
    for cat, p0, p1, pmax in summary:
        print(f"F1 {cat}: premium {p0:,.0f} → {p1:,.0f} · record {pmax:,.0f}")
    save(fig, "f1_quota_premium.png")


def fig2_pressure(con, canvas_in=9.0):
    title = "Bids per quota and the success rate — the same pressure read two ways, Category A and B"
    foottext = (f"Bids per quota = bids received ÷ quota · success rate = successful bids ÷ bids received\n"
                f"No exercises Apr–Jun 2020 · vertical line: A/B redefinition · {SRC}")
    assert_fits(title, 12.5, "F2 title", canvas_in)
    assert_fits(foottext, 7.5, "F2 footnote", canvas_in)

    fig, axs = plt.subplots(2, 1, figsize=(canvas_in, 6.4), sharex=True)
    st = fig.suptitle(title, x=0.012, y=0.98, ha="left", fontsize=12.5, color=T["ink"])

    colors = {"Category A": T["petrol"], "Category B": T["burnt"]}
    for ax, field, ylim, ylab in ((axs[0], "bids_per_quota", (1.0, 3.4), "bids received ÷ quota"),
                                  (axs[1], "success_rate", (0.40, 0.92), "successful ÷ received")):
        for cat in ("Category A", "Category B"):
            rows = series(con, cat)
            ax.plot([r[0] for r in rows], [float(r[3]) if field == "bids_per_quota" else float(r[4]) for r in rows],
                    color=colors[cat], lw=1.1, alpha=0.9, label=f"Category {cat[-1]}")
        ax.set_ylim(*ylim)
        ax.set_ylabel(ylab, fontsize=9)
        ax.axvline(mdates.datestr2num(BREAK_DATE), color=T["ink"], lw=0.9, ls=":", alpha=0.9)
        ax.legend(loc="best", fontsize=8, ncol=2)
    axs[0].set_title("Count pressure: bids per quota", fontsize=10, color=T["muted"])
    axs[1].set_title("Outcome: share of bids that won a certificate", fontsize=10, color=T["muted"])
    axs[1].set_xticks([date(y, 1, 1) for y in range(2010, 2027, 2)])
    axs[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.subplots_adjust(left=0.105, right=0.985, top=0.885, bottom=0.115, hspace=0.26)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, drawn_title(axs[0])), (st, drawn_title(axs[1])),
                       (ftxt, axs[1].get_xticklabels()[-1])], "F2 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F2")
    assert_texts_clear(fig, "F2")
    assert_legend_clear(fig, "F2")
    print("F2: two panels rendered (bids-per-quota, success rate)")
    save(fig, "f2_pressure.png")


def fig3_scatter(con, canvas_in=9.0):
    title = "Same quota, higher price — premium vs quota before and after the May 2022 redefinition"
    foottext = (f"One dot = one exercise · colour: pre-redefinition vs from May 2022 1st exercise\n{PREMIUM_NOTE} · {SRC}")
    assert_fits(title, 12.5, "F3 title", canvas_in)
    assert_fits(foottext, 7.5, "F3 footnote", canvas_in)

    fig, axs = plt.subplots(1, 2, figsize=(canvas_in, 4.9), sharey=False)
    st = fig.suptitle(title, x=0.012, y=0.98, ha="left", fontsize=12.5, color=T["ink"])

    for ax, cat, xlim, ylim, xticks in ((axs[0], "Category A", (300, 2400), (15000, 142000), (500, 1000, 1500, 2000)),
                                        (axs[1], "Category B", (280, 1650), (15000, 160000), (400, 800, 1200, 1600))):
        rows = q(con, f"""SELECT month, quota, premium, regime FROM exercise
                          WHERE category = '{cat}' ORDER BY month, round_no""")
        for regime, color, lbl in (("pre", T["muted"], "before May 2022"), ("post", T["teal"], "from May 2022")):
            pts = [(float(r[1]), float(r[2])) for r in rows if r[3] == regime]
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=13, color=color,
                       edgecolors=T["edge"], linewidths=0.4, alpha=0.8, label=lbl)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_xticks(list(xticks))  # explicit — the default locator emits out-of-range edge ticks
        ax.set_xlabel("quota (certificates per exercise)", fontsize=9)
        if ax is axs[0]:
            ax.set_ylabel("quota premium (S$)", fontsize=9)
        ax.set_title(f"Category {cat[-1]}", fontsize=10, color=T["muted"])
        ax.legend(loc="best", fontsize=8)
        last = rows[-1]
        ax.annotate(f"{str(last[0])[:7]}: {float(last[2]):,.0f}", (float(last[1]), float(last[2])),
                    xytext=(-6, 8), textcoords="offset points", ha="right", fontsize=8, color=T["ink"])

    fig.subplots_adjust(left=0.10, right=0.985, top=0.845, bottom=0.135, wspace=0.16)
    ftxt = foot(fig, foottext)
    assert_clear(fig, [(st, drawn_title(axs[0])), (st, drawn_title(axs[1])),
                       (ftxt, axs[1].get_xticklabels()[-1])], "F3 suptitle/title + footnote/ticks")
    assert_inbounds(fig, "F3")
    assert_texts_clear(fig, "F3")
    assert_legend_clear(fig, "F3")
    print("F3: two scatter panels rendered (pre/post coloured)")
    save(fig, "f3_scatter.png")


def main():
    import os

    os.chdir(ROOT)
    FIGDIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW exercise AS SELECT * FROM read_parquet('{PARQUET}')")
    run_script(con, ROOT / "sql/02_metrics.sql")
    for palette in (LIGHT, DARK):
        use_palette(palette)
        use_series_style(dark=(palette is DARK))
        print(f"-- rendering {'dark' if palette['suffix'] else 'light'} set --")
        fig1_quota_premium(con)
        fig2_pressure(con)
        fig3_scatter(con)
    print("figures done — light + dark")


if __name__ == "__main__":
    main()
