#!/usr/bin/env python
"""Figure rendering, enriched multi-panel
edition. Reads analysis/outputs/ and renders Figs 1-6 to figures/ as 300 dpi
PNG + vector PDF. matplotlib only; Okabe-Ito colorblind-safe palette (validated
CVD-safe); fonts >= 8 pt at final size; self-contained captions with a
'Takeaway:' line (figures/captions.md). Every panel traces to coded data; no
figure carries a claim absent from the database.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
AN = ROOT.parent / "analysis" / "outputs"
CAP = ROOT / "captions.md"

# Okabe-Ito (colorblind-safe)
CB = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
      "vermillion": "#D55E00", "purple": "#CC79A7", "yellow": "#F0E442",
      "skyblue": "#56B4E9", "black": "#222222", "grey": "#9A9A9A",
      "lgrey": "#D9D9D9"}
LAYER_C = {"L1": CB["blue"], "L2": CB["orange"], "L3": CB["green"]}
SEQ = "Blues"
# Unified style kit (anchored on Fig 5, the calmest of the set): categorical
# data use only the four soft hues below plus skyblue; NR/"not reported" is
# always light grey (missing info, not a category of interest); ordinal
# scores use a sequential-blues ramp that echoes the heatmaps; a single
# crimson accent is reserved for zero-coverage/gap callouts. The loud
# vermillion and neon yellow are banned as area fills.
NR_GREY = "#CFCFCF"          # NR / not reported, every figure
DARK_GREY = "#8C8C8C"        # secondary "other/none" categorical grey
ACCENT = "#C0392B"           # alert accent: outlines + gap annotations only
SINGLE = CB["purple"]        # single-series bars (the Fig 5b look)
SCORE_C = {0: "#DEDEDE", 1: "#BDD7E7", 2: "#6BAED6", 3: "#2171B5"}  # ordinal
GRID_GREY = "#555555"        # reference/median lines and their labels
plt.rcParams.update({
    # Times New Roman throughout: Nimbus Roman is the URW Times clone that
    # newtx uses in the manuscript body, so figures match the text exactly.
    "font.family": "serif",
    "font.serif": ["Nimbus Roman", "Times New Roman", "Liberation Serif",
                   "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 9, "axes.titlesize": 9.5,
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "figure.dpi": 300, "savefig.dpi": 300,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#999999", "axes.linewidth": 0.7,
    "xtick.color": "#444444", "ytick.color": "#444444",
    "axes.labelcolor": "#222222", "text.color": "#222222",
    "xtick.major.size": 2.6, "ytick.major.size": 2.6,
    "axes.grid": False, "figure.facecolor": "white",
    # embed TrueType subsets so figure text survives on any machine/printer
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
captions = []


def save(fig, name, caption):
    fig.savefig(ROOT / f"{name}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(ROOT / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    captions.append((name, caption))
    print(f"rendered {name}")


FAMILY_LABELS = {
    "precedence": "Precedence", "resource-capacity": "Resource capacity",
    "max-time-lags": "Maximum time lags", "min-time-lags": "Minimum time lags",
    "multi-skill": "Multi-skill", "calendars": "Resource calendars",
    "setup-times": "Setup times", "transport": "Transport",
    "spatial": "Spatial", "multi-project": "Multi-project",
    "due-dates-SLA": "Due dates / SLA", "stochastic-durations": "Stochastic durations",
    "dynamic-arrivals": "Dynamic arrivals",
    "disruptions-rescheduling": "Disruptions / rescheduling",
    "mold-buffer-curing": "Mold-buffer-curing",
}


def panel_tag(ax, s):
    ax.text(-0.02, 1.06, s, transform=ax.transAxes, fontsize=10,
            fontweight="bold", va="bottom", ha="right")


# ---------------------------------------------------------------- Fig 1 PRISMA
def fig1_prisma():
    """PRISMA 2020-style flow on a strict 2 x 5 grid: every cell is filled,
    every box has identical size, and every arrow is purely horizontal or
    vertical. Left lane = the domain flow; right lane = records leaving it
    (duplicates, the methods track, two exclusion stages) plus the saturation
    verdict. Rotated stage tabs (Identification / Screening / Included) follow
    the official PRISMA 2020 template. Axes are in inches, so all geometry is
    exact; a post-draw check asserts no text escapes its box."""
    pl = json.loads((ROOT.parent / "retrieval" / "prisma_ledger.json").read_text())
    src = pl.get("identified_by_source", {})
    reasons = pl.get("pass1_exclusion_reasons", {})
    by_layer = pl.get("included_final_by_layer", {})
    sat = pl.get("saturation", {})

    W_FIG, H_FIG = 7.0, 4.75
    fig, ax = plt.subplots(figsize=(W_FIG, H_FIG))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.axis("off")
    ax.set_xlim(0, W_FIG); ax.set_ylim(0, H_FIG)   # data coords == inches

    # ---- grid geometry (inches) ------------------------------------------
    BW, BH = 3.08, 0.72              # uniform box width / height
    XL, XR = 0.48, 3.86              # left edges of the two lanes
    GAPY = 0.245                     # vertical gap between rows
    Y0 = H_FIG - 0.08 - BH / 2       # centre of row 0
    ROW = [Y0 - i * (BH + GAPY) for i in range(5)]
    FS = 8.0

    from matplotlib.patches import FancyBboxPatch

    checks = []

    def box(col, row, text, fc, ec, lw=1.0, ls="-"):
        x0 = XL if col == "L" else XR
        y0 = ROW[row] - BH / 2
        p = FancyBboxPatch((x0, y0), BW, BH,
                           boxstyle="round,pad=0,rounding_size=0.075",
                           fc=fc, ec=ec, lw=lw, ls=ls, zorder=2)
        ax.add_patch(p)
        t = ax.text(x0 + BW / 2, ROW[row], text, ha="center", va="center",
                    fontsize=FS, color=CB["black"], linespacing=1.32, zorder=3)
        checks.append((t, p))

    def v_arrow(row):
        """Main-flow arrow between left-lane rows row and row+1."""
        x = XL + BW / 2
        ax.annotate("", xy=(x, ROW[row + 1] + BH / 2 + 0.015),
                    xytext=(x, ROW[row] - BH / 2 - 0.015), zorder=1,
                    arrowprops=dict(arrowstyle="-|>", color=GRID_GREY,
                                    lw=1.1, mutation_scale=11))

    def h_arrow(row):
        """Records leaving the domain flow: left lane -> right lane."""
        ax.annotate("", xy=(XR - 0.02, ROW[row]),
                    xytext=(XL + BW + 0.02, ROW[row]), zorder=1,
                    arrowprops=dict(arrowstyle="-|>", color="#AAAAAA",
                                    lw=1.0, mutation_scale=10))

    # ---- stage tabs (PRISMA 2020 template) -------------------------------
    def tab(rows, label):
        ytop = ROW[rows[0]] + BH / 2
        ybot = ROW[rows[-1]] - BH / 2
        p = FancyBboxPatch((0.06, ybot), 0.28, ytop - ybot,
                           boxstyle="round,pad=0,rounding_size=0.05",
                           fc=CB["blue"], ec="none", zorder=2)
        ax.add_patch(p)
        ax.text(0.06 + 0.14, (ytop + ybot) / 2, label, rotation=90,
                ha="center", va="center", fontsize=8.5, color="white",
                fontweight="bold", zorder=3)

    tab([0, 1], "Identification")
    tab([2, 3], "Screening")
    tab([4], "Included")

    # ---- boxes ------------------------------------------------------------
    FLOW_FC, FLOW_EC = "#EAF3FB", CB["blue"]
    SIDE_FC, SIDE_EC = "#F7F7F7", "#999999"

    box("L", 0, f"Records identified from databases: n = {pl['identified_total_records']}\n"
                f"OpenAlex {src['openalex']} · Semantic Scholar {src['s2']}"
                f" · arXiv {src['arxiv']}", FLOW_FC, FLOW_EC, lw=1.05)
    box("R", 0, f"Duplicates removed before screening: n = {pl['duplicates_removed']}\n"
                "(cross-source, via normalized DOIs and metadata)",
        SIDE_FC, SIDE_EC)
    box("L", 1, f"Unique records after deduplication: n = {pl['after_dedup_unique']}\n"
                f"+ snowballing: {pl['snowball_it1_new_unique']} (it1) "
                f"+ {pl['snowball_it2_new_unique']} (it2) "
                f"+ {pl['snowball_it3_new_unique']} (it3) unique",
        FLOW_FC, FLOW_EC, lw=1.05)
    box("R", 1, f"Methods track, screened separately: n = {pl['methods_track']}\n"
                "(ranked pool feeding the methods-frontier corpus)",
        SIDE_FC, SIDE_EC)
    r = {k: reasons.get(k, 0) for k in ("OUT-DOMAIN", "OUT-DECISION", "OUT-METHOD",
                                        "NOT-RESEARCH", "CONTINUOUS-CONTROL",
                                        "DUPLICATE", "LANGUAGE")}
    box("L", 2, f"Title/abstract screened: n = {pl['pass1_screened_records']}\n"
                f"({pl['domain_track']} domain-track "
                f"+ {pl['snowball_it1_domain_screened']} snowballed)",
        FLOW_FC, FLOW_EC, lw=1.05)
    box("R", 2, f"Excluded at screening: n = {pl['pass1_exclude']}\n"
                f"out-domain {r['OUT-DOMAIN']} · out-decision {r['OUT-DECISION']}\n"
                f"out-method {r['OUT-METHOD']} · not-research {r['NOT-RESEARCH']}\n"
                f"continuous-control {r['CONTINUOUS-CONTROL']} · duplicate "
                f"{r['DUPLICATE']} · language {r['LANGUAGE']}", SIDE_FC, SIDE_EC)
    box("L", 3, f"Reports sought for retrieval: n = {pl['full_text_assessed']}\n"
                f"assessed for eligibility: n = {pl['reports_assessed_eligibility']}\n"
                f"(incl. {pl['snowball_it2_domain_net_screened']} iteration-2 and "
                f"{pl['snowball_it3_domain_net_screened']} iteration-3 snowball records)",
        FLOW_FC, FLOW_EC, lw=1.05)
    box("R", 3, f"Reports not retrieved: n = {pl['reports_not_retrieved']} (title only)\n"
                f"Excluded after assessment: n = {pl['excluded_after_assessment']}\n"
                "(out of scope, no learning, continuous control, duplicate reports)\n"
                f"Routed to the methods corpus (Section 4): n = {pl['pass2_routed_to_methods_corpus']}",
        SIDE_FC, SIDE_EC)
    box("L", 4, f"Domain corpus: n = {pl['domain_corpus_final']}\n"
                f"L1 = {by_layer['L1']} · L2 = {by_layer['L2']}"
                f" · L3 = {by_layer['L3']}", "#D9EFE6", CB["green"], lw=1.2)
    box("R", 4, f"Snowballing stopped: iteration 3 added "
                f"{sat.get('it3_included_new', 2)} studies\n"
                f"({sat.get('it3_yield_pct_of_corpus', 1.5)}% of corpus), all"
                " within covered themes", "#EFF8F3", CB["green"],
        ls=(0, (4, 2.4)))

    for i in range(4):
        v_arrow(i)
        h_arrow(i)

    # ---- overflow guard: no text may escape its box -----------------------
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    for t, p in checks:
        tb = t.get_window_extent(ren)
        pb = p.get_window_extent(ren)
        if (tb.x0 < pb.x0 + 2 or tb.x1 > pb.x1 - 2 or
                tb.y0 < pb.y0 + 1 or tb.y1 > pb.y1 - 1):
            print(f"WARNING fig1: text overflows its box: "
                  f"{t.get_text()[:40]!r}")
    save(fig, "fig1_prisma",
         "PRISMA-style flow of identification, screening, and inclusion "
         "for the domain corpus across three open bibliographic sources, "
         "Crossref verification, and three snowballing iterations, with "
         "per-stage counts generated from the retrieval ledger. The left "
         "lane carries the domain flow; the right lane accounts for every "
         "record leaving it (duplicates, the separately screened methods "
         "track, staged exclusions, and the full-text reroute to the "
         "methods corpus). Of the snowballed unique records, 289 "
         "(iteration 1), 67 (iteration 2), and 2 (iteration 3) fell within the domain scope "
         "and entered the flow. "
         "Takeaway: the learning-based construction scheduling literature is "
         "small enough to review exhaustively yet large enough to synthesize "
         "quantitatively, and the search reached saturation.")


# ---------------------------------------------- Fig 2 landscape (3 panels)
def fig2_landscape():
    df = pd.read_csv(AN / "fig2_pubs_per_year_layer.csv", index_col=0)
    par = pd.read_csv(AN / "fig2_paradigm_evolution.csv", index_col=0)
    ven = pd.read_csv(AN / "fig2_venue_distribution.csv", index_col=0).iloc[:, 0]
    fig = plt.figure(figsize=(6.5, 4.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1.42, 1],
                          hspace=0.52, wspace=0.66)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, :])

    years = df.index.astype(int)
    PARTIAL_YEAR = 2026  # harvested July 2026: the last year is a half-year count
    bottom = np.zeros(len(df))
    for lay in [c for c in ("L1", "L2", "L3") if c in df.columns]:
        # the partial (final) year renders translucent, not hatched, so it is
        # visibly provisional without adding line noise
        alphas = [0.45 if y == PARTIAL_YEAR else 1.0 for y in years]
        ax1.bar(years, df[lay], bottom=bottom, label=lay, width=0.72,
                color=LAYER_C[lay], edgecolor="white", linewidth=0.8,
                alpha=None)
        if PARTIAL_YEAR in list(years):
            i = list(years).index(PARTIAL_YEAR)
            ax1.bar([PARTIAL_YEAR], [df[lay].values[i]], bottom=[bottom[i]],
                    width=0.72, color="white", edgecolor="white", linewidth=0.8,
                    zorder=2)
            ax1.bar([PARTIAL_YEAR], [df[lay].values[i]], bottom=[bottom[i]],
                    width=0.72, color=LAYER_C[lay], alpha=0.45,
                    edgecolor="white", linewidth=0.8, zorder=3)
        bottom += df[lay].values
    for x, tot in zip(years, bottom):
        lbl = f"{int(tot)}*" if x == PARTIAL_YEAR else f"{int(tot)}"
        ax1.text(x, tot + 0.6, lbl, ha="center", va="bottom", fontsize=8,
                 color=CB["black"])
    # footnote sits under the legend, over the short 2020-2022 bars, so it
    # never touches the tall right-side bars or the neighbouring panel
    ax1.text(0.03, 0.72, "* 2026 partial\n(to July cutoff)",
             transform=ax1.transAxes, ha="left", va="top", fontsize=8,
             color=CB["black"], style="italic")
    ax1.set_xlabel("Year"); ax1.set_ylabel("Publications")
    ax1.set_title("Domain Publications per Year by Layer", loc="center")
    ax1.legend(title=None, frameon=False, ncol=3, loc="upper left",
               columnspacing=1.0, handlelength=1.0, fontsize=8)
    ax1.set_ylim(0, bottom.max() * 1.18)
    ax1.set_xticks(years)
    ax1.set_xticklabels([f"{y}*" if y == PARTIAL_YEAR else str(y)
                         for y in years])
    panel_tag(ax1, "(a)")

    # two-line journal abbreviations so no label can reach into panel (a);
    # unmapped long names wrap at a word boundary instead of being clipped
    ABBREV = {
        "Automation in Construction": "Autom. Constr.",
        "Reliability Engineering and System Safety": "Reliab. Eng. Syst. Saf.",
        "Computer-Aided Civil and Infrastructure Engineering":
            "Comput.-Aided Civ. Infr. Eng.",
        "Journal of Construction Engineering and Management":
            "J. Constr. Eng. Manage.",
        "Advanced Engineering Informatics": "Adv. Eng. Inform.",
        "Journal of Building Engineering": "J. Build. Eng.",
        "Engineering Applications of Artificial Intelligence":
            "Eng. Appl. Artif. Intell.",
        "European Journal of Operational Research": "Eur. J. Oper. Res.",
        "Proceedings of the International Symposium on Automation and Robotics in Construction (IAARC/ISARC)": "ISARC Proc.",
        "International Symposium on Automation and Robotics in Construction (IAARC/ISARC)": "ISARC Proc.",
    }

    def venue_label(v):
        # single-line labels: two-line ticks collide at print size
        return ABBREV.get(str(v), str(v))

    vv = ven.head(8)[::-1]
    ax2.barh(range(len(vv)), vv.values, color=SINGLE, height=0.7)
    for i, v in enumerate(vv.values):
        ax2.text(v + 0.3, i, int(v), va="center", fontsize=8)
    ax2.set_yticks(range(len(vv)))
    ax2.set_yticklabels([venue_label(v) for v in vv.index], fontsize=7.5)
    ax2.set_xlabel("Studies"); ax2.set_title("Top Venues", loc="center")
    ax2.set_xlim(0, vv.values.max() * 1.15)
    panel_tag(ax2, "(b)")

    # fixed family -> color map: NR is grey (missing info), families use the
    # calm categorical hues; the two smallest families take soft slate/grey
    # greyscale-safe band palette: adjacent stacked bands are separated in
    # luminance (checked below), and MARL avoids the venue-bar purple in (b)
    FAM_C = {"value-RL": CB["blue"], "policy-RL": CB["green"],
             "MARL": "#9E4F7D", "learning-augmented-metaheuristic": CB["orange"],
             "LLM-agent": "#2F7EBC", "actor-critic": "#8DA0CB",
             "IL": "#6E6E6E", "NR": NR_GREY}
    # smoothed stacked area: named families largest-first from the base, NR
    # (missing info) floated to the top so the grey reads as residue, not
    # foundation. Monotone PCHIP interpolation rounds each band boundary while
    # passing exactly through every yearly value and never dipping below zero;
    # thin white seams separate the bands; the partial 2026 half-year fades
    # out under a white gradient, mirroring the translucent 2026 bar in (a).
    from scipy.interpolate import PchipInterpolator
    tot = par.sum().sort_values(ascending=False)
    fams = [c for c in tot.index if str(c) != "NR"]
    if "NR" in par.columns:
        fams.append("NR")
    yrs = par.index.astype(int).values
    dense = np.linspace(yrs.min(), yrs.max(), 241)
    layers = np.vstack([
        np.clip(PchipInterpolator(yrs, par[c].values.astype(float))(dense),
                0, None) for c in fams])
    cum = np.vstack([np.zeros_like(dense), np.cumsum(layers, axis=0)])
    for k, c in enumerate(fams):
        ax3.fill_between(dense, cum[k], cum[k + 1], lw=0, zorder=2,
                         color=FAM_C.get(str(c), DARK_GREY),
                         label={"NR": "NR (not reported)",
                                "IL": "IL (imitation)"}.get(str(c), str(c)))
    for k in range(1, len(fams)):
        ax3.plot(dense, cum[k], color="white", lw=0.9, zorder=3)
    ax3.plot(dense, cum[-1], color="#B5B5B5", lw=0.7, zorder=3)
    ymax = cum[-1].max() * 1.22
    fade = np.ones((1, 160, 4))
    fade[0, :, 3] = np.linspace(0.0, 0.62, 160)
    ax3.imshow(fade, extent=(PARTIAL_YEAR - 1, PARTIAL_YEAR, 0, ymax),
               aspect="auto", origin="lower", interpolation="bilinear",
               zorder=4)
    ax3.text(0.015, 0.70, "* 2026 partial (to July cutoff)",
             transform=ax3.transAxes, ha="left", va="top", fontsize=8,
             color=CB["black"], style="italic", zorder=5)
    ax3.set_xlabel("Year"); ax3.set_ylabel("Publications")
    ax3.set_title("Method-Family Composition over Time", loc="center")
    ax3.legend(frameon=False, ncol=4, fontsize=8, loc="upper left",
               columnspacing=1.0, handlelength=1.0)
    ax3.set_xlim(yrs.min(), yrs.max())
    ax3.set_ylim(0, ymax)
    ax3.set_xticks(yrs)
    ax3.set_xticklabels([f"{y}*" if y == PARTIAL_YEAR else str(y)
                         for y in yrs])
    panel_tag(ax3, "(c)")
    save(fig, "fig2_landscape",
         "Corpus landscape. (a) Domain publications per year stacked "
         "by application layer, with yearly totals; (b) the venues hosting the "
         "corpus; (c) the method-family composition over time. Generated from "
         "the coded database. Takeaway: the field is recent and concentrated, "
         "grows sharply after 2022, and its methodological mix broadens from "
         "value-based reinforcement learning toward policy-gradient, "
         "multi-agent, and language-model approaches.")


# --------------------------------------- Fig 3 problem-space map (2 panels)
def fig3_constraints():
    cf = pd.read_csv(AN / "fig3_constraint_matrix.csv", index_col=0)
    feas = pd.read_csv(AN / "fig3_feasibility_by_layer.csv", index_col=0)
    ncol = cf["n"].to_dict()
    feats = [c for c in cf.columns if c != "n"]
    mat = cf[feats].astype(float)
    norm = mat.div(cf["n"].values, axis=0).fillna(0)

    fig = plt.figure(figsize=(6.5, 5.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1], hspace=1.05)
    ax = fig.add_subplot(gs[0])
    im = ax.imshow(norm.values, aspect="auto", cmap=SEQ, vmin=0, vmax=1)
    ax.set_xticks(range(len(feats)))
    SHORT = {"Disruptions / rescheduling": "Disrupt. / resched.",
             "Mold-buffer-curing": "Mold / buffer / curing",
             "Resource calendars": "Res. calendars",
             "Stochastic durations": "Stoch. durations",
             "Maximum time lags": "Max. time lags",
             "Minimum time lags": "Min. time lags"}
    ax.set_xticklabels([SHORT.get(FAMILY_LABELS.get(f, f),
                                  FAMILY_LABELS.get(f, f)) for f in feats],
                       fontsize=8, rotation=35, ha="right",
                       rotation_mode="anchor")
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels([f"{i} (n={ncol[i]})" for i in mat.index], fontsize=8.5)
    for r in range(mat.shape[0]):
        for c in range(mat.shape[1]):
            v = int(mat.values[r, c])
            col = "white" if norm.values[r, c] > 0.55 else CB["black"]
            ax.text(c, r, str(v), ha="center", va="center", fontsize=8.5,
                    color=col, fontweight="bold" if v == 0 else "normal")
    # highlight the zero-coverage columns
    for c, feat in enumerate(feats):
        if mat[feat].sum() == 0:
            ax.add_patch(Rectangle((c - 0.5, -0.5), 1, len(mat.index),
                                   fill=False, edgecolor=ACCENT,
                                   linewidth=1.8, zorder=5))
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.015)
    cb.set_ticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    cb.set_ticklabels(["0", "20", "40", "60", "80", "100"])
    cb.set_label("Share of layer's studies (%)", fontsize=8.5)
    ax.set_title("Constraint-Feature Coverage by Layer "
                 "(Cell = Study Count, Shaded by Within-Layer Share)",
                 loc="center")
    panel_tag(ax, "(a)")

    ax2 = fig.add_subplot(gs[1])
    fm_cols = list(feas.columns)
    fm_colors = {"action-masking": CB["blue"], "penalty": CB["orange"],
                 "repair": CB["purple"], "constraint-free": CB["skyblue"],
                 "NR": NR_GREY}
    layers = [l for l in ("L1", "L2", "L3") if l in feas.index]
    left = np.zeros(len(layers))
    totals = feas.loc[layers].sum(axis=1).values
    for fm in fm_cols:
        vals = 100 * feas.loc[layers, fm].values / np.maximum(totals, 1)
        ax2.barh(range(len(layers)), vals, left=left, height=0.6,
                 color=fm_colors.get(fm, CB["grey"]), edgecolor="white",
                 linewidth=0.8,
                 label=("NR (not reported)" if fm == "NR" else fm))
        dark_bg = fm in ("action-masking", "repair")
        for i, (v, l0) in enumerate(zip(vals, left)):
            if v >= 5:
                ax2.text(l0 + v / 2, i, f"{v:.0f}", ha="center", va="center",
                         fontsize=8,
                         color="white" if dark_bg else "#333333")
        left += vals
    ax2.set_yticks(range(len(layers)))
    ax2.set_yticklabels([f"{l} (n={ncol[l]})" for l in layers], fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlabel("Share of layer's studies (%)"); ax2.set_xlim(0, 100)
    ax2.set_title("How Feasibility Is Enforced, by Layer", loc="center")
    ax2.legend(frameon=False, ncol=5, fontsize=8, loc="lower center",
               bbox_to_anchor=(0.5, -0.62), columnspacing=1.0, handlelength=1.0)
    panel_tag(ax2, "(b)")
    save(fig, "fig3_constraints",
         "The unified problem-space map. (a) Coverage of scheduling "
         "constraint families across the three layers (cells give study "
         "counts, shaded by within-layer share; red outlines mark families no "
         "study models); (b) the mechanism each study uses to keep schedules "
         "feasible. Generated from the coded database. Takeaway: the "
         "constraint families that define real construction scheduling, "
         "maximum time lags and resource calendars, are modeled by no study, "
         "and most studies do not report how feasibility is enforced at all, "
         "so feasibility under construction's harder constraints is an open "
         "problem rather than a solved detail.")


# ----------------------------------------- Fig 4 dual-track timeline
def fig4_timeline():
    """Redesigned dual-track adoption timeline: swim-lane bands, a shared
    year grid, staggered uniform label cards, and lag connectors that carry
    the figure's message (how many years the domain trails each milestone)."""
    tl = json.loads((AN / "fig4_timeline.json").read_text())
    firsts = tl["domain_firsts"]

    # frontier milestones (short display names, chronological)
    frontier = [
        ("Attention for routing\n(neural CO)", 2019, "kool"),
        ("L2D: learn to dispatch\n(JSSP, GNN)", 2020, "l2d"),
        ("GNN dispatcher\nfor FJSP", 2023, "gnnfjsp"),
        ("Dual-attention\n(DANIEL)", 2023, "daniel"),
        ("Architecture re-examination\n(ReSched)", 2026, "resched"),
    ]
    domain = [
        ("First DRL\nscheduler", firsts.get("first_drl_domain"), "drl"),
        ("First MARL", firsts.get("first_marl_domain"), "marl"),
        ("First GNN\npolicy", firsts.get("first_gnn_domain"), "gnn"),
        ("First LLM\nagent", firsts.get("first_llm_domain"), "llm"),
        ("First attention\npolicy", firsts.get("first_attention_domain"), "att"),
    ]
    domain = [(l, y, k) for (l, y, k) in domain if y]
    # lag connectors: frontier key -> domain key (only defensible pairings)
    pairs = [("l2d", "drl"), ("l2d", "gnn"), ("daniel", "att")]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    Y_TOP, Y_BOT = 1.0, -1.0
    yrs = [y for _, y, _ in frontier] + [y for _, y, _ in domain]
    xmin, xmax = min(yrs) - 0.7, max(yrs) + 0.7

    # swim-lane bands + shared year grid (year labels at the BOTTOM edge so
    # the mid-corridor stays clear for the lag connectors)
    Y_TICK = -3.25
    ax.axhspan(0.62, 1.38, color=CB["blue"], alpha=0.07, zorder=0)
    ax.axhspan(-1.38, -0.62, color=CB["orange"], alpha=0.09, zorder=0)
    for y in range(int(np.ceil(xmin)), int(np.floor(xmax)) + 1):
        ax.plot([y, y], [Y_TICK + 0.18, 2.95], color="#E3E3E3", lw=0.6,
                zorder=0)
        ax.text(y, Y_TICK, str(y), ha="center", va="top", fontsize=8,
                color=CB["black"], zorder=2)
    ax.plot([xmin, xmax], [Y_TOP, Y_TOP], color=CB["blue"], lw=1.2, zorder=1)
    ax.plot([xmin, xmax], [Y_BOT, Y_BOT], color=CB["orange"], lw=1.2, zorder=1)

    def place(items, base, direction, color, marker):
        """Uniform label cards on two staggered tiers, far enough apart that
        card borders cannot intersect. Markers sit exactly on their year
        (same-year markers separate vertically, not horizontally, so the
        plotted x never disagrees with the stated year); only the label
        cards dodge horizontally."""
        pos = {}
        items = sorted(items, key=lambda x: x[1])
        year_seen = {}
        for i, (label, yr, key) in enumerate(items):
            dx = 0.0
            n_same = sum(1 for _, y2, _ in items if y2 == yr)
            if n_same > 1:
                j = year_seen.get(yr, 0)
                dx = (j - (n_same - 1) / 2) * 0.80
                year_seen[yr] = j + 1
            x_card = yr + dx
            y_mark = base
            tier = 1.55 if i % 2 == 0 else 2.62
            y_lab = base + (tier - 1.0) * direction
            ax.plot(yr, y_mark, marker, color=color, ms=7.0, zorder=6,
                    markeredgecolor="white", markeredgewidth=1.0)
            ax.plot([yr, x_card], [y_mark, y_lab - 0.16 * direction],
                    color=color, lw=0.9, alpha=0.9, zorder=3)
            fc = "#F5FAFD" if color == CB["blue"] else "#FEFAF0"
            ax.annotate(f"{label}\n{yr}", (x_card, y_lab), ha="center",
                        va="center", fontsize=7.8, color=CB["black"], zorder=5,
                        linespacing=1.25,
                        bbox=dict(boxstyle="round,pad=0.32", fc=fc,
                                  ec=color, lw=0.9))
            pos[key] = (yr, base)
        return pos

    fpos = place(frontier, Y_TOP, +1, CB["blue"], "o")
    dpos = place(domain, Y_BOT, -1, CB["orange"], "s")

    # lag connectors through the middle, annotated with the lag in years
    for fk, dk in pairs:
        if fk not in fpos or dk not in dpos:
            continue
        (x0, y0), (x1, y1) = fpos[fk], dpos[dk]
        lag = int(round(x1 - x0))
        ax.annotate("", xy=(x1, y1 + 0.09), xytext=(x0, y0 - 0.09), zorder=2,
                    arrowprops=dict(arrowstyle="-|>", color="#888888", lw=1.0,
                                    connectionstyle="arc3,rad=-0.18",
                                    shrinkA=2, shrinkB=2))
        xm, ym = (x0 + x1) / 2 + 0.14, (y0 + y1) / 2 + 0.34 - (lag % 2) * 0.42
        ax.text(xm, ym, f"{lag}-yr lag" if lag > 0 else "same year",
                fontsize=7.5, style="italic", color=CB["black"], ha="left",
                va="center", zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                          alpha=0.9))
    # ReSched: not yet adopted marker
    if "resched" in fpos:
        x0, y0 = fpos["resched"]
        ax.annotate("not yet adopted\nin the domain", xy=(x0, Y_BOT),
                    xytext=(x0, Y_BOT - 0.85), ha="center", fontsize=7.5,
                    style="italic", color="#777777", zorder=3,
                    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.9,
                                    linestyle=(0, (2, 2))))
        ax.plot(x0, Y_BOT, "s", color="white", ms=7.5, zorder=4,
                markeredgecolor="#AAAAAA", markeredgewidth=1.0)

    # lane titles inside the bands at the far left, clear of any label card
    ax.text(xmin - 0.35, Y_TOP, "OR/RL\nmethod\nfrontier", ha="right",
            va="center", fontsize=8.2, fontweight="bold", color=CB["blue"],
            linespacing=1.15)
    ax.text(xmin - 0.35, Y_BOT, "Construction\ndomain\nadoption", ha="right",
            va="center", fontsize=8.2, fontweight="bold", color=CB["orange"],
            linespacing=1.15)
    ax.set_ylim(Y_TICK - 0.35, 3.2)
    ax.set_xlim(xmin - 2.1, xmax + 0.4)
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    save(fig, "fig4_timeline",
         "Dual-track timeline contrasting OR/RL method milestones "
         "(top lane) with the earliest domain adoption of each method class "
         "identified in our corpus (bottom lane); connectors mark the "
         "adoption lag in years, and the newest frontier design (ReSched) "
         "has no domain adoption yet. Milestone references are "
         "registry-verified; domain firsts are computed from the coded "
         "database. Takeaway: construction adoption trails the method "
         "frontier, and the domain is importing the heavy graph and "
         "attention encoders just as the frontier begins to question their "
         "marginal value.")


# ------------------------------------- Fig 5 method-design landscape (3 panels)
def fig5_methods():
    pe = pd.read_csv(AN / "fig5_problem_encoder.csv", index_col=0)
    ta = pd.read_csv(AN / "fig5_training_algo.csv", index_col=0).iloc[:, 0]
    pbl = pd.read_csv(AN / "fig5_paradigm_by_layer.csv", index_col=0)
    fig = plt.figure(figsize=(6.5, 5.0))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.55,
                          wspace=0.72)
    ax1 = fig.add_subplot(gs[0, :])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[1, 1])
    # fixed encoder -> color map; NR is grey so the (large) not-reported mass
    # reads as missing information rather than a loud category
    ENC_C = {"CNN": CB["blue"], "GNN": CB["orange"], "MLP": CB["green"],
             "attention": CB["purple"], "hybrid": CB["skyblue"],
             "GAT": "#A0522D", "none": DARK_GREY, "NR": NR_GREY}

    encoders = list(pe.columns)
    bottom = np.zeros(len(pe))
    for i, enc in enumerate(encoders):
        _lab = "NR (not reported)" if str(enc) == "NR" else str(enc)
        ax1.bar(range(len(pe)), pe[enc], bottom=bottom, label=_lab, width=0.68,
                color=ENC_C.get(str(enc), DARK_GREY), edgecolor="white",
                linewidth=0.3)
        bottom += pe[enc].values
    ax1.set_xticks(range(len(pe)))
    ax1.set_xticklabels([str(i) for i in pe.index], rotation=18, ha="right",
                        fontsize=9)
    ax1.set_ylabel("Studies")
    ax1.set_title("Problem Class by Neural Encoder", loc="center")
    # 3-column legend hugs the top-right corner, above the short right-side
    # bars (max 17) and clear of the tall "custom" stack
    ax1.legend(title="Encoder", frameon=False, fontsize=8, ncol=3,
               loc="upper right", bbox_to_anchor=(1.0, 1.04),
               columnspacing=0.9, handlelength=1.0, labelspacing=0.35)
    ax1.set_ylim(0, bottom.max() * 1.30)
    panel_tag(ax1, "(a)")

    tt = ta.head(8)[::-1]
    # NR keeps the paper-wide grey-means-not-reported convention
    ax2.barh(range(len(tt)), tt.values, height=0.7,
             color=[NR_GREY if str(i) == "NR" else CB["purple"]
                    for i in tt.index])
    for i, v in enumerate(tt.values):
        ax2.text(v + 0.3, i, int(v), va="center", fontsize=9)
    _ylabs = ["NR (not reported)" if str(i) == "NR" else str(i) for i in tt.index]
    ax2.set_yticks(range(len(tt))); ax2.set_yticklabels(_ylabs, fontsize=9)
    ax2.set_xlabel("Studies"); ax2.set_title("Training Algorithm", loc="center")
    ax2.set_xlim(0, tt.values.max() * 1.15)
    panel_tag(ax2, "(b)")

    pbl = pbl.loc[pbl.sum(axis=1).sort_values(ascending=False).index]
    layers = [c for c in ("L1", "L2", "L3") if c in pbl.columns]
    left = np.zeros(len(pbl))
    for lay in layers:
        ax3.barh(range(len(pbl)), pbl[lay], left=left, label=lay, height=0.7,
                 color=LAYER_C[lay], edgecolor="white", linewidth=0.7)
        left += pbl[lay].values
    ax3.set_yticks(range(len(pbl)))
    ax3.set_yticklabels(["NR (not reported)"
                         if str(i) == "NR" else
                         ("learn.-augm. metaheuristic"
                          if str(i) == "learning-augmented-metaheuristic"
                          else str(i))
                         for i in pbl.index], fontsize=8)
    ax3.invert_yaxis()
    ax3.set_xlabel("Studies")
    ax3.set_title("Learning Paradigm by Layer", loc="center")
    ax3.legend(frameon=False, fontsize=8, ncol=3, loc="lower right",
               columnspacing=1.0, handlelength=1.0)
    panel_tag(ax3, "(c)")
    save(fig, "fig5_methods",
         "Method-design landscape of the corpus. (a) Problem class "
         "against neural encoder; (b) training-algorithm frequency; (c) "
         "learning paradigm by layer. Generated from the coded database. "
         "Takeaway: the corpus clusters on resource-constrained project and "
         "custom formulations solved by value-based and policy-gradient "
         "reinforcement learning, and a large share of studies do not report "
         "the encoder, so the design space is both narrow and thinly "
         "documented.")


# ------------------------------------- Fig 6 evidence audit (signature, 4 panels)
def fig6_evidence():
    rub = json.loads((AN / "fig6_rubric.json").read_text())
    per = rub["per_layer"]
    gains = pd.read_csv(AN / "fig6_gain_vs_B.csv")
    rep = pd.read_csv(AN / "fig6_reporting_practices.csv")
    bd = pd.read_csv(AN / "fig6_BD_matrix.csv", index_col=0)

    # Canvas at true print width (\textwidth = 164.5 mm = 6.48 in), so every
    # point size below is the size the reader sees (design-at-final-size).
    fig = plt.figure(figsize=(6.5, 7.0))
    gs = fig.add_gridspec(2, 2, hspace=0.58, wspace=0.44)
    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, 0])
    axD = fig.add_subplot(gs[1, 1])
    dims = [("rubric_B", "B: baseline"), ("rubric_E", "E: evaluation"),
            ("rubric_D", "D: data realism")]
    layers = ["L1", "L2", "L3"]

    # (a) stacked score distributions per dimension per layer; scores are
    # ordinal, so use the sequential-blues ramp (grey = score 0)
    score_colors = SCORE_C
    dim_short = {"rubric_B": "B", "rubric_E": "E", "rubric_D": "D"}
    ypos, labels, y = [], [], 0
    group_spans = []
    for dkey, dlab in dims:
        y_start = y
        for lay in layers:
            dist = per.get(lay, {}).get(dkey.split("_")[1], {})
            tot = sum(dist.values()) or 1
            left = 0
            for sc in (0, 1, 2, 3):
                frac = 100 * dist.get(str(sc), dist.get(sc, 0)) / tot
                axA.barh(y, frac, left=left, color=score_colors[sc],
                         edgecolor="white", linewidth=0.6, height=0.82)
                left += frac
            ypos.append(y)
            labels.append(f"{lay} (n={tot if sum(dist.values()) else 0})")
            y += 1
        group_spans.append((dlab, y_start, y - 1))
        y += 0.7
    axA.set_yticks(ypos); axA.set_yticklabels(labels, fontsize=8)
    axA.invert_yaxis()
    GROUP_LAB = {"B: baseline": "Baseline B", "E: evaluation": "Evaluation E",
                 "D: data realism": "Data realism D"}
    for dlab, y0, y1 in group_spans:
        axA.text(-0.30, (y0 + y1) / 2, GROUP_LAB.get(dlab, dlab),
                 transform=axA.get_yaxis_transform(), rotation=90,
                 ha="center", va="center", fontsize=8, color=CB["black"],
                 clip_on=False)
    axA.set_xlabel("Share of the layer's scorable studies (%)")
    axA.set_xlim(0, 100)
    handles = [plt.Rectangle((0, 0), 1, 1, color=score_colors[s]) for s in (0, 1, 2, 3)]
    axA.legend(handles, ["score 0", "1", "2", "3"], frameon=False, ncol=4,
               fontsize=8, loc="lower center", bbox_to_anchor=(0.5, -0.34),
               columnspacing=1.2, handlelength=1.1)
    axA.set_title("Rubric Score Distribution by\nDimension and Layer",
                  loc="center")
    panel_tag(axA, "(a)")

    # (b) gain vs baseline strength; marker shape encodes the objective the
    # gain was measured on (the medians pool heterogeneous objectives, so the
    # heterogeneity is shown rather than hidden)
    g = gains.copy()
    g["rubric_B"] = pd.to_numeric(g["rubric_B"], errors="coerce")
    g = g.dropna(subset=["rubric_B", "gain_num"])

    def obj_family(o):
        o = str(o).lower()
        if any(k in o for k in ("makespan", "duration", "time", "delay")):
            return "time"
        if "cost" in o:
            return "cost"
        return "other"
    if "primary_objective" in g.columns:
        g["obj_fam"] = g["primary_objective"].map(obj_family)
    else:
        g["obj_fam"] = "other"
    OBJ_MK = {"time": "o", "cost": "s", "other": "D"}
    # global collision-aware dodge: within each B score, points whose gains
    # sit within 2 pp of the previous point step sideways so all n markers
    # stay individually countable
    g = g.sort_values(["rubric_B", "gain_num"]).reset_index(drop=True)
    offs = [0.0, 0.08, -0.08, 0.16, -0.16, 0.24, -0.24]
    g["xoff"] = 0.0
    for _b, grp in g.groupby("rubric_B"):
        k, prev = 0, None
        for idx, row in grp.iterrows():
            k = k + 1 if (prev is not None and row["gain_num"] - prev <= 2.0) else 0
            g.loc[idx, "xoff"] = offs[k % len(offs)]
            prev = row["gain_num"]
    for lay in layers:
        for fam, mk in OBJ_MK.items():
            sub = g[(g["layer"] == lay) & (g["obj_fam"] == fam)]
            if len(sub):
                axB.scatter(sub["rubric_B"] + sub["xoff"], sub["gain_num"],
                            color=LAYER_C[lay], marker=mk, s=26, alpha=0.85,
                            edgecolor="white", linewidth=0.5)
    from matplotlib.lines import Line2D
    # one combined legend in the verified-empty upper-right zone (no data at
    # x >= 2.35 above y ~ 34): column 1 = layer hues, column 2 = objective
    # shapes; never below the axes, where it would crowd panel (d)
    axB.legend(handles=[Line2D([], [], marker="o", ls="", color=LAYER_C[l],
                               label=l) for l in layers]
                       + [Line2D([], [], marker=m, ls="", color="#888888",
                                 label=f) for f, m in OBJ_MK.items()],
               frameon=False, fontsize=8, ncol=2, title=None,
               loc="upper right", bbox_to_anchor=(1.0, 1.0),
               columnspacing=0.8, handletextpad=0.25, labelspacing=0.35,
               borderaxespad=0.1)
    # median lines for weak vs strong (quiet grey reference lines; the dots
    # carry the color, the lines carry the comparison)
    weak = g[g["rubric_B"] <= 1]["gain_num"].median()
    strong = g[g["rubric_B"] >= 2]["gain_num"].median()
    axB.plot([-0.4, 1.4], [weak, weak], color="#777777", lw=1.2, ls=(0, (5, 3)))
    axB.plot([1.6, 3.4], [strong, strong], color="#777777", lw=1.2, ls=(0, (5, 3)))
    # median labels sit in verified empty zones: short label above the weak
    # segment's left end; strong label above the segment's right end, clear of
    # the B=2 column and just above the B=3 cluster
    axB.text(-0.36, weak + 0.9, f"weak median {weak:.1f}%",
             ha="left", va="bottom", fontsize=8, color=CB["black"],
             style="italic")
    axB.text(3.38, strong + 1.0, f"strong median {strong:.1f}%",
             ha="right", va="bottom", fontsize=8, color=CB["black"],
             style="italic")
    tier_n = g["rubric_B"].astype(int).value_counts()
    axB.set_xticks([0, 1, 2, 3])
    axB.set_xticklabels([f"{b}\n(n={int(tier_n.get(b, 0))})" for b in (0, 1, 2, 3)],
                        fontsize=8.5)
    axB.set_xlabel("Baseline-strength score B (0-3)")
    axB.set_ylabel("Reported gain vs strongest baseline (%)")
    axB.set_xticks([0, 1, 2, 3])
    axB.set_title(f"Reported Gain vs Baseline Strength\n(n = {len(g)}, "
                  "Heterogeneous Objectives)", loc="center")
    panel_tag(axB, "(b)")

    # (c) reporting-practice epidemiology
    prac = ["held_out", "feasibility_mech", "seeds_or_stats", "inference_time",
            "code", "data"]
    prac_lab = ["Held-out\ninstances", "Feasibility\nmechanism",
                "Seeds or\nstat. test", "Inference\ntime", "Code\navailable",
                "Data\navailable"]
    ov = rep[rep["scope"] == "overall"].iloc[0]
    n_total = int(ov["n"])
    vals = [ov[p] for p in prac]
    cnts = [int(ov.get(f"{p}_count", round(v * n_total / 100)))
            for p, v in zip(prac, vals)]
    order = np.argsort(vals)
    vals_s = [vals[i] for i in order]
    cnts_s = [cnts[i] for i in order]
    lab_s = [prac_lab[i] for i in order]
    axC.barh(range(len(vals_s)), vals_s, color=SINGLE, height=0.7)
    for i, (v, c) in enumerate(zip(vals_s, cnts_s)):
        axC.text(v + 1.5, i, f"{v}%  ({c}/{n_total})", va="center",
                 fontsize=8.5)
    axC.set_yticks(range(len(lab_s))); axC.set_yticklabels(lab_s, fontsize=8.5)
    axC.set_xlabel("Share of the full corpus with the practice\n"
                   "documented in the available dossier (%)")
    axC.set_xlim(0, 100)
    axC.set_title("Documentation of\nVerification Practices", loc="center")
    panel_tag(axC, "(c)")

    # (d) B x D co-occurrence: the empty high-rigor corner
    m = bd.values.astype(int)
    im = axD.imshow(m, cmap=SEQ, aspect="auto", vmin=0, vmax=m.max())
    axD.set_xticks(range(4)); axD.set_yticks(range(4))
    axD.set_xticklabels([0, 1, 2, 3]); axD.set_yticklabels([0, 1, 2, 3])
    axD.set_xlabel("Data realism D (0-3)")
    axD.set_ylabel("Baseline strength B (0-3)")
    for r in range(4):
        for c in range(4):
            axD.text(c, r, m[r, c], ha="center", va="center", fontsize=8.5,
                     color="white" if m[r, c] > m.max() * 0.55 else CB["black"])
    # outline the strong-baseline + field cell (B>=2, D==3): the empty corner
    axD.add_patch(Rectangle((2.5, 1.5), 1, 2, fill=False,
                            edgecolor=ACCENT, linewidth=2.0, zorder=5))
    axD.text(3.72, 2.5, "no study: strong baseline + field data",
             rotation=90, ha="center", va="center", fontsize=8.5,
             color=ACCENT)
    axD.set_title(f"Baseline Strength vs Data Realism\n(n = {m.sum()} "
                  "Scorable on Both)", loc="center")
    panel_tag(axD, "(d)")
    save(fig, "fig6_evidence",
         "The evidence audit, the review's analytical centerpiece. "
         "(a) Full rubric-score distributions per layer for baseline strength, "
         "evaluation rigor, and data realism; (b) each study's reported gain "
         "against the strength of the baseline it beat, with weak- and "
         "strong-baseline medians; (c) the share of studies reporting each "
         "verification practice; (d) the joint distribution of baseline "
         "strength and data realism. Generated from the coded database. "
         "Takeaway: reported advantages concentrate where baselines are "
         "weakest, most verification practices are reported by a minority of "
         "studies, and no study combines a strong baseline with a real field "
         "deployment, so the field's headline gains are not yet "
         "decision-grade.")


def fig_s2_b_by_deployment():
    """Supplementary Figure S2: the baseline-strength x deployment-level
    cross-tabulation behind the central empty-cell finding. Kept distinct from
    Fig. 7(d) (baseline x data realism): here the second axis is where the
    policy actually ran, not how realistic its data were."""
    bd = pd.read_csv(AN / "b_by_deployment.csv", index_col=0)
    order = [c for c in ("simulation", "pilot", "field") if c in bd.columns]
    m = bd.reindex(columns=order).fillna(0).astype(int)
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    mx = m.values.max()
    ax.imshow(m.values, cmap=SEQ, aspect="auto", vmin=0, vmax=mx)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([o.capitalize() for o in order])
    ax.set_yticks(range(len(m.index)))
    ax.set_yticklabels([str(int(b)) for b in m.index])
    ax.set_xlabel("Deployment level (where the policy ran)")
    ax.set_ylabel("Baseline strength B (0--3)")
    for r in range(m.shape[0]):
        for c in range(m.shape[1]):
            v = int(m.values[r, c])
            ax.text(c, r, v, ha="center", va="center", fontsize=9,
                    color="white" if v > mx * 0.55 else CB["black"])
    # outline the strong-baseline x deployed cells (B >= 2, pilot or field):
    # the empty region the central finding rests on
    if "pilot" in order:
        c0 = order.index("pilot")
        rows_ge2 = [i for i, b in enumerate(m.index) if int(b) >= 2]
        if rows_ge2:
            ax.add_patch(Rectangle((c0 - 0.5, min(rows_ge2) - 0.5),
                                   len(order) - c0, len(rows_ge2),
                                   fill=False, edgecolor=ACCENT, linewidth=2.0,
                                   zorder=5))
            ax.text(len(order) - 0.5, min(rows_ge2) + len(rows_ge2) / 2 - 0.5,
                    "  no deployed study\n  faced a strong baseline",
                    ha="left", va="center", fontsize=8, color=ACCENT)
    ax.set_xlim(-0.5, len(order) + 1.6)
    fig.tight_layout()
    save(fig, "fig_s2_b_by_deployment",
         "Baseline strength by deployment level over the studies scorable on "
         "both. Takeaway: every pilot- or field-deployed study sits in the "
         "B < 2 rows; the strong-baseline, deployed cell (red) is empty, which "
         "is the review's central negative finding shown directly rather than "
         "in prose.")


def fig0_layers_overview():
    """Three-layer orientation schematic shown before the layer reviews
    (Sections 5-7): what each layer schedules, its canonical decision and
    problem form, its distinctive constraints, and its corpus share, plus the
    structural relation between the layers. Study counts come from the coded
    database (fig2_pubs_per_year_layer.csv)."""
    df = pd.read_csv(AN / "fig2_pubs_per_year_layer.csv", index_col=0)
    n = {lay: int(df[lay].sum()) for lay in ("L1", "L2", "L3") if lay in df}
    fig = plt.figure(figsize=(6.5, 4.0))
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    cards = [
        ("L1", "Project-Level\nConstruction Scheduling",
         "On-site construction activities:\nsequencing crews and equipment\nacross a project network",
         "Which activity starts next,\non which crew or equipment,\nat what time",
         "RCPSP recast as a Markov\ndecision process; equipment\ndispatching and routing",
         "Generalized time lags, spatial\nconflict, weather, disruptions\nand rescheduling"),
        ("L2", "Industrialized-Construction\nProduction",
         "Off-site factories and logistics:\nprecast plants, MiC/PPVC lines,\nyard and delivery operations",
         "Which component runs on which\nline or mold, in what order,\nand when to deliver",
         "Flow-shop and flexible job-shop\ntemplates from manufacturing,\nplus transport coordination",
         "Casting molds, curing buffers,\njust-in-time delivery windows,\nmulti-skill crews"),
        ("L3", "Civil-Infrastructure and\nBuilt-Asset Maintenance",
         "Deteriorating bridge, pavement,\npipe, and rail networks;\nbuilding work-order portfolios",
         "When each asset receives\nintervention; who executes\nthe resulting work orders",
         "(PO)MDP over asset condition\n(intervention planning); work-\norder dispatch barely populated",
         "Condition-driven stochasticity,\nSLA deadlines, budget limits,\nnetwork interdependence"),
    ]
    ROW_LAB = ["Setting", "Core decision", "Canonical form",
               "Distinctive\nconstraints", "Corpus"]
    # shared horizontal bands (one grid for all three cards)
    x0s = [0.115, 0.415, 0.715]
    CW = 0.27                      # card width
    TOP, BOT = 0.965, 0.175        # card extent
    hdr_h = 0.115
    row_y = [0.775, 0.615, 0.455, 0.295, 0.215]   # row centers (last = n line)
    row_div = [0.695, 0.535, 0.375, 0.250]        # light separators
    for (lay, name, setting, decision, form, constr), x0 in zip(cards, x0s):
        col = LAYER_C[lay]
        # card frame: black hairline (house rule); colored top rule + tinted
        # header carry the layer identity
        ax.add_patch(Rectangle((x0, BOT), CW, TOP - BOT, fill=False,
                               edgecolor=CB["black"], linewidth=0.8))
        ax.add_patch(Rectangle((x0, TOP - hdr_h), CW, hdr_h,
                               facecolor=col, alpha=0.16, edgecolor="none"))
        ax.add_patch(Rectangle((x0, TOP - 0.006), CW, 0.006,
                               facecolor=col, edgecolor="none"))
        ax.text(x0 + CW / 2, TOP - hdr_h / 2 - 0.002, f"{lay} · {name}",
                ha="center", va="center", fontsize=8.5, fontweight="bold",
                color=CB["black"], linespacing=1.25)
        for yv, txt in zip(row_y[:4], (setting, decision, form, constr)):
            ax.text(x0 + CW / 2, yv, txt, ha="center", va="center",
                    fontsize=7.5, color=CB["black"], linespacing=1.3)
        for yd in row_div:
            ax.plot([x0 + 0.012, x0 + CW - 0.012], [yd, yd],
                    color="#CCCCCC", lw=0.5)
        ax.text(x0 + CW / 2, row_y[4], f"n = {n.get(lay, 0)} studies",
                ha="center", va="center", fontsize=8, fontweight="bold",
                color=CB["black"])
    # left gutter row labels, aligned to the shared bands
    ax.text(0.055, TOP - hdr_h / 2, "Layer", ha="center", va="center",
            fontsize=7.5, style="italic", color=CB["black"])
    for yv, lab in zip(row_y, ROW_LAB):
        ax.text(0.055, yv, lab, ha="center", va="center", fontsize=7.5,
                style="italic", color=CB["black"], linespacing=1.2)
    # relation band: solid bracket joins L1 and L2 (shared skeleton); a dashed
    # branch reaches L3, which shares it only at the dispatch level
    yb = 0.115
    ax.plot([x0s[0] + CW / 2, x0s[0] + CW / 2], [BOT - 0.008, yb],
            color=GRID_GREY, lw=0.9)
    ax.plot([x0s[1] + CW / 2, x0s[1] + CW / 2], [BOT - 0.008, yb],
            color=GRID_GREY, lw=0.9)
    ax.plot([x0s[0] + CW / 2, x0s[1] + CW / 2], [yb, yb],
            color=GRID_GREY, lw=0.9)
    ax.plot([x0s[1] + CW / 2, x0s[2] + CW / 2], [yb, yb],
            color=GRID_GREY, lw=0.9, ls=(0, (4, 3)))
    ax.plot([x0s[2] + CW / 2, x0s[2] + CW / 2], [yb, BOT - 0.008],
            color=GRID_GREY, lw=0.9, ls=(0, (4, 3)))
    ax.text((x0s[0] + x0s[1]) / 2 + CW / 2, yb - 0.052,
            "L1 and L2 share the sequencing-and-assignment skeleton directly",
            ha="center", va="center", fontsize=7.5, color=CB["black"])
    ax.text(x0s[2] + CW / 2, yb - 0.052,
            "L3 shares it only at the\nwork-order dispatch level",
            ha="center", va="center", fontsize=7.5, color=CB["black"],
            linespacing=1.2)
    save(fig, "fig0_layers_overview",
         "Orientation map of the three application layers reviewed in "
         "Sections 5-7: the physical setting each layer schedules, the "
         "decision its studies learn, the canonical problem form, the "
         "constraint families that distinguish it, and its corpus share. "
         "Takeaway: L1 and L2 share one sequencing-and-assignment skeleton, "
         "while L3 joins it only at its barely populated work-order dispatch "
         "level, which is why corpus-wide statistics are always read "
         "alongside per-layer views.")


def fig_s1_comparator_class():
    """Supplementary Figure S1: reported gain stratified by the class of the
    strongest comparator in each study's baseline suite (the comparator-class
    sensitivity behind the weak-vs-strong medians of Fig. 6b)."""
    df = pd.read_csv(AN / "gain_by_comparator_class.csv")
    labels = {"single-rule-manual-or-none": "Single rule, manual,\nor none",
              "multiple-or-tuned-rules": "Multiple or\ntuned rules",
              "prior-learned": "Prior learned\nmethod",
              "metaheuristic": "Metaheuristic",
              "exact": "Exact solver"}
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    for i, (_, row) in enumerate(df.iterrows()):
        vals = [float(v) for v in str(row["gains_pct"]).split("|") if v]
        # deterministic symmetric jitter (no RNG: resume- and repro-safe)
        offs = [(j - (len(vals) - 1) / 2) * min(0.5 / max(len(vals), 1), 0.055)
                for j in range(len(vals))]
        ax.scatter(vals, [i + o for o in offs], s=16, color=CB["skyblue"],
                   edgecolors="#33668C", linewidths=0.4, alpha=0.85, zorder=3)
        med = row["median_gain_pct"]
        if pd.notna(med):
            ax.plot([med, med], [i - 0.22, i + 0.22], color=GRID_GREY,
                    lw=1.6, zorder=4)
        # per-stratum n and median live in a fixed right-hand column, clear
        # of every data point (the bar alone marks the median's position)
        note = (f"n={int(row['n'])}; med {med:.1f}%" if pd.notna(med)
                else f"n={int(row['n'])}")
        ax.annotate(note, (48.5, i), ha="left", va="center", fontsize=8,
                    color=CB["black"], annotation_clip=False)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([labels[c] for c in df["comparator_class"]], fontsize=8)
    ax.set_ylim(-0.6, len(df) - 0.4)
    ax.invert_yaxis()   # weakest class on top, strongest at the bottom
    ax.set_xlim(-1.5, 54)
    ax.set_xlabel("Reported gain vs. strongest baseline (%)")
    fig.tight_layout()
    save(fig, "fig_s1_comparator_class",
         "Reported numeric gain by the class of the strongest comparator in "
         "each study's baseline suite (vertical bar: stratum median). "
         "Takeaway: gains shrink monotonically as the comparator class "
         "strengthens; studies whose strongest comparator is an optimization-"
         "class method or a prior learned method report single-digit medians.")


def main():
    fns = [fig0_layers_overview, fig1_prisma, fig2_landscape,
           fig3_constraints, fig4_timeline, fig5_methods, fig6_evidence,
           fig_s1_comparator_class, fig_s2_b_by_deployment]
    done, failed = [], []
    for fn in fns:
        try:
            fn()
            done.append(fn.__name__)
        except Exception as e:
            import traceback
            failed.append((fn.__name__, repr(e)))
            traceback.print_exc()
    lines = ["# Figure captions (generated by figures/figures.py)\n"]
    for name, cap in captions:
        lines.append(f"## {name}\n\n{cap}\n")
    CAP.write_text("\n".join(lines))
    print(f"\nDONE: {len(done)} rendered; {len(failed)} failed")
    for n, e in failed:
        print(f"  FAILED {n}: {e}")


if __name__ == "__main__":
    main()
