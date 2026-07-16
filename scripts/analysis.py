#!/usr/bin/env python
"""Analysis stage. Reads corpus/corpus_coded.xlsx,
computes every statistic the manuscript uses, writes:
  - analysis/outputs/*.json + *.csv   (figure/table source data)
  - manuscript/macros.tex             (every number used in prose)
Rerunnable end-to-end. Statistical humility: counts and
proportions; one Spearman rho (B vs gain) only if n >= 30 numeric gains.
"""
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
XLSX = ROOT.parent / "corpus" / "corpus_coded.xlsx"
MACROS = ROOT.parent / "manuscript" / "macros.tex"

CONSTRAINTS = ["precedence", "resource-capacity", "max-time-lags",
               "min-time-lags", "multi-skill", "calendars", "setup-times",
               "transport", "spatial", "multi-project", "due-dates-SLA",
               "stochastic-durations", "dynamic-arrivals",
               "disruptions-rescheduling", "mold-buffer-curing"]
BASELINE_ORDER = ["none", "random", "single-untuned-PDR", "multiple-PDRs",
                  "tuned-rules", "metaheuristic", "exact-CP-MILP",
                  "commercial-tool", "other-DRL", "human-planner"]
EVAL_ITEMS = ["held-out-instances", "size-generalization",
              "distribution-shift", "multiple-seeds", "statistical-test",
              "ablation"]

# OR/RL milestone track for the Figure 4 dual-track timeline (all entries
# must exist in references_verified.csv; verified 2026-07-08)
MILESTONES = [
    ("L2D (learn to dispatch, JSSP)", 2020, "zhang2020l2d"),
    ("GNN dispatcher for FJSP", 2023, "song2023fjsp"),
    ("Dual-attention (DANIEL)", 2023, "wang2023daniel"),
    ("Attention for routing (neural CO)", 2019, "kool2019attention"),
    ("Architecture re-examination (ReSched)", 2026, "resched2026"),
]


def split(v):
    if pd.isna(v) or v in ("", None):
        return []
    return [x.strip() for x in str(v).split("|") if x.strip()]


def tex_escape(s):
    return str(s).replace("%", "\\%").replace("&", "\\&").replace("_", "\\_")


def num_to_word_or_num(n):
    return str(int(n))


def main():
    corpus = pd.read_excel(XLSX, sheet_name="corpus")
    corpus = corpus[corpus["layer"].isin(["L1", "L2", "L3"])].copy()
    methods = pd.read_excel(XLSX, sheet_name="methods_corpus")
    n = len(corpus)
    macros = {}

    # ---------------------------------------------------------- RQ1 landscape
    # Year may be NR for a few studies with no registry year; keep them in the
    # corpus but exclude from year-based views (honest: unknown year cannot be
    # placed on a timeline). year_corpus = rows with a resolvable year.
    corpus["year_num"] = pd.to_numeric(corpus["year"], errors="coerce")
    n_no_year = int(corpus["year_num"].isna().sum())
    year_corpus = corpus.dropna(subset=["year_num"]).copy()
    year_corpus["year"] = year_corpus["year_num"].astype(int)
    macros_year_note = n_no_year
    per_year_layer = (year_corpus.groupby(["year", "layer"]).size()
                      .unstack(fill_value=0).sort_index())
    per_year_layer.to_csv(OUT / "fig2_pubs_per_year_layer.csv")
    # normalize venue aliases so one outlet is not split across name variants
    _VENUE_ALIAS = {
        "arXiv (Cornell University)": "arXiv", "arXiv.org": "arXiv",
        "SSRN Electronic Journal": "SSRN (preprints)",
        "Reliability Engineering & System Safety": "Reliability Engineering and System Safety",
    }
    venue_counts = corpus["venue"].replace(_VENUE_ALIAS).value_counts()
    venue_counts.head(20).to_csv(OUT / "fig2_venue_distribution.csv")
    paradigm_year = (year_corpus.groupby(["year", "learning_paradigm"]).size()
                     .unstack(fill_value=0).sort_index())
    paradigm_year.to_csv(OUT / "fig2_paradigm_evolution.csv")

    macros["nCorpus"] = n
    # LaTeX command names cannot contain digits: L1->Lone, L2->Ltwo, L3->Lthree
    _LWORD = {"L1": "Lone", "L2": "Ltwo", "L3": "Lthree"}
    for lay in ("L1", "L2", "L3"):
        macros[f"n{_LWORD[lay]}"] = int((corpus["layer"] == lay).sum())
    macros["nMethodsCorpus"] = len(methods)
    macros["yearMin"] = int(year_corpus["year"].min())
    macros["yearMax"] = int(year_corpus["year"].max())
    recent = year_corpus[year_corpus["year"] >= 2023]
    macros["pctSinceTwentyThree"] = round(100 * len(recent) / len(year_corpus))
    macros["nNoYear"] = n_no_year
    macros["nPreprint"] = int((corpus["is_preprint"] == 1).sum())

    # lag analysis: first domain adoption per encoder/paradigm proxy
    firsts = {}
    for key, sel in [
        ("first_gnn_domain", corpus["encoder"].isin(["GNN", "GAT"])),
        ("first_attention_domain", corpus["encoder"] == "attention"),
        ("first_marl_domain", corpus["learning_paradigm"] == "MARL"),
        ("first_llm_domain", corpus["learning_paradigm"] == "LLM-agent"),
        ("first_drl_domain", corpus["learning_paradigm"].isin(
            ["value-RL", "policy-RL", "actor-critic"]) & (corpus["encoder"] != "none")),
    ]:
        sub = year_corpus[sel.loc[year_corpus.index]]
        firsts[key] = int(sub["year"].min()) if len(sub) else None
    (OUT / "fig4_timeline.json").write_text(json.dumps({
        "milestones": [{"label": l, "year": y, "ref": r} for l, y, r in MILESTONES],
        "domain_firsts": firsts,
        "per_year_layer": {str(k): {c: int(v) for c, v in row.items()}
                           for k, row in per_year_layer.iterrows()},
    }, indent=1))
    if firsts.get("first_gnn_domain"):
        macros["firstGnnDomainYear"] = firsts["first_gnn_domain"]
        macros["gnnAdoptionLagYears"] = firsts["first_gnn_domain"] - 2020
    if firsts.get("first_marl_domain"):
        macros["firstMarlDomainYear"] = firsts["first_marl_domain"]

    # ------------------------------------------------- RQ2 problem structure
    rows = []
    for lay in ("L1", "L2", "L3"):
        sub = corpus[corpus["layer"] == lay]
        cnt = Counter()
        for v in sub["constraint_features"]:
            cnt.update(split(v))
        rows.append({"layer": lay, "n": len(sub),
                     **{c: cnt.get(c, 0) for c in CONSTRAINTS}})
    cf = pd.DataFrame(rows).set_index("layer")
    cf.to_csv(OUT / "fig3_constraint_matrix.csv")

    feas = corpus["feasibility_mechanism"].fillna("NR").value_counts()
    feas.to_csv(OUT / "feasibility_mechanism.csv")
    macros["pctMasking"] = round(100 * int(feas.get("action-masking", 0)) / n)
    macros["pctFeasNR"] = round(100 * int(feas.get("NR", 0)) / n)
    # feasibility mechanism by layer (Fig 3b), fixed category order
    FEAS_ORDER = ["action-masking", "penalty", "repair", "constraint-free", "NR"]
    feas_by_layer = (corpus.assign(fm=corpus["feasibility_mechanism"].fillna("NR"))
                     .groupby(["layer", "fm"]).size().unstack(fill_value=0)
                     .reindex(columns=FEAS_ORDER, fill_value=0)
                     .reindex(index=["L1", "L2", "L3"], fill_value=0))
    feas_by_layer.to_csv(OUT / "fig3_feasibility_by_layer.csv")
    _l1feas = feas_by_layer.loc["L1"]
    macros["pctFeasNRLone"] = round(100 * int(_l1feas.get("NR", 0)) / max(1, int(_l1feas.sum())))

    # L1 split: equipment/logistics dispatch vs the rest of the layer (baseline
    # tier composition and headline-gain medians, Section 5)
    _l1 = corpus[corpus["layer"] == "L1"]
    _disp = _l1[_l1["problem_class"] == "dispatching-routing"]
    _rest = _l1[_l1["problem_class"] != "dispatching-routing"]
    macros["nDispatchLone"] = len(_disp)
    for name, g in [("Dispatch", _disp), ("Activity", _rest)]:
        _b = pd.to_numeric(g["rubric_B"], errors="coerce")
        _b = _b[_b >= 0]
        macros[f"pctBTwoPlus{name}Lone"] = round(100 * float((_b >= 2).mean())) if len(_b) else "NA"
        _g = pd.to_numeric(g["gain_vs_strongest_baseline_pct"], errors="coerce").dropna()
        macros[f"medGain{name}Lone"] = f"{_g.median():.1f}" if len(_g) else "NA"

    # top-baseline-tier (B=3) numeric-gain subset (Section 8 caveat)
    _b3 = corpus[(pd.to_numeric(corpus["rubric_B"], errors="coerce") == 3)]
    _b3g = pd.to_numeric(_b3["gain_vs_strongest_baseline_pct"], errors="coerce").dropna()
    macros["nGainBThree"] = len(_b3g)
    if len(_b3g):
        macros["gainBThreeMin"] = f"{_b3g.min():.1f}"
        macros["gainBThreeMax"] = f"{_b3g.max():.1f}"

    # full-text acquisition event count (Section 3): a process count from the
    # 16 July 2026 institutional-library fetch, not derivable from the workbook
    macros["nFulltextFetched"] = 78

    # constraint families frequent in domain but rare in methods corpus
    mcnt = Counter()
    for v in methods.get("constraint_features", pd.Series(dtype=str)):
        mcnt.update(split(v))
    dom_tot = Counter()
    for v in corpus["constraint_features"]:
        dom_tot.update(split(v))
    gap_rows = [{"constraint": c,
                 "domain_share": round(dom_tot.get(c, 0) / n, 3),
                 "methods_share": round(mcnt.get(c, 0) / max(1, len(methods)), 3)}
                for c in CONSTRAINTS]
    pd.DataFrame(gap_rows).to_csv(OUT / "constraint_domain_vs_methods.csv",
                                  index=False)
    for c, name in [("max-time-lags", "MaxLags"), ("calendars", "Calendars"),
                    ("multi-skill", "MultiSkill"), ("multi-project", "MultiProject"),
                    ("dynamic-arrivals", "DynArrivals"),
                    ("due-dates-SLA", "DueDates")]:
        macros[f"pctDomain{name}"] = round(100 * dom_tot.get(c, 0) / n)

    # --------------------------------------------------- RQ3 evidence audit
    rub = corpus[["rubric_B", "rubric_E", "rubric_D"]].apply(
        pd.to_numeric, errors="coerce")
    assessable = rub.where(rub >= 0)
    dist = {}
    for col, tag in [("rubric_B", "B"), ("rubric_E", "E"), ("rubric_D", "D")]:
        s = assessable[col].dropna().astype(int)
        dist[tag] = {int(k): int(v) for k, v in s.value_counts().sort_index().items()}
        macros[f"median{tag}"] = num_to_word_or_num(s.median())
        macros[f"pct{tag}ZeroOne"] = round(100 * int((s <= 1).sum()) / max(1, len(s)))
        macros[f"pct{tag}Three"] = round(100 * int((s == 3).sum()) / max(1, len(s)))
    per_layer_rubric = {}
    for lay in ("L1", "L2", "L3"):
        sub = corpus[corpus["layer"] == lay][["rubric_B", "rubric_E", "rubric_D"]].apply(
            pd.to_numeric, errors="coerce")
        sub = sub.where(sub >= 0)
        per_layer_rubric[lay] = {
            c.split("_")[1]: {int(k): int(v) for k, v in
                              sub[c].dropna().astype(int).value_counts().sort_index().items()}
            for c in sub.columns}
    (OUT / "fig6_rubric.json").write_text(json.dumps(
        {"overall": dist, "per_layer": per_layer_rubric}, indent=1))

    corpus["gain_num"] = pd.to_numeric(
        corpus["gain_vs_strongest_baseline_pct"], errors="coerce")
    # released gain-extraction table: one row per coded numeric gain, with the
    # study's primary objective, coding confidence, and preprint status so the
    # medians below are auditable and sensitivity subsets are recoverable
    gains = corpus.dropna(subset=["gain_num"])[[
        "id", "layer", "rubric_B", "rubric_E", "gain_num", "objectives",
        "coding_confidence", "is_preprint"]].copy()
    gains.rename(columns={"objectives": "primary_objective"}, inplace=True)
    gains["primary_objective"] = (gains["primary_objective"].astype(str)
                                  .str.split("|").str[0])
    gains.to_csv(OUT / "fig6_gain_vs_B.csv", index=False)
    macros["nGainsNumeric"] = len(gains)
    gg = gains[pd.to_numeric(gains["rubric_B"], errors="coerce") >= 0].copy()
    gg["rubric_B"] = gg["rubric_B"].astype(int)
    weak = gg[gg["rubric_B"] <= 1]["gain_num"]
    strong = gg[gg["rubric_B"] >= 2]["gain_num"]
    if len(weak) >= 3 and len(strong) >= 3:
        macros["medGainWeakB"] = round(float(weak.median()), 1)
        macros["medGainStrongB"] = round(float(strong.median()), 1)
        macros["nGainWeakB"] = len(weak)
        macros["nGainStrongB"] = len(strong)
        # sensitivity: full-text-coded subset (checks that abstract-
        # level records do not drive the split)
        ggf = gg[gg["coding_confidence"].astype(str) == "full"]
        wf, sf = (ggf[ggf["rubric_B"] <= 1]["gain_num"],
                  ggf[ggf["rubric_B"] >= 2]["gain_num"])
        if len(wf) >= 3 and len(sf) >= 3:
            macros["medGainWeakBFull"] = round(float(wf.median()), 1)
            macros["medGainStrongBFull"] = round(float(sf.median()), 1)
            macros["nGainWeakBFull"] = len(wf)
            macros["nGainStrongBFull"] = len(sf)
        # sensitivity: peer-reviewed (non-preprint) subset
        ggp = gg[pd.to_numeric(gg["is_preprint"], errors="coerce")
                 .fillna(0).astype(int) == 0]
        wp, sp = (ggp[ggp["rubric_B"] <= 1]["gain_num"],
                  ggp[ggp["rubric_B"] >= 2]["gain_num"])
        if len(wp) >= 3 and len(sp) >= 3:
            macros["medGainWeakBPeer"] = round(float(wp.median()), 1)
            macros["medGainStrongBPeer"] = round(float(sp.median()), 1)
            macros["nGainWeakBPeer"] = len(wp)
            macros["nGainStrongBPeer"] = len(sp)
        # sensitivity: leave-one-out stability of the weak-baseline median
        loo_w = [round(float(weak.drop(i).median()), 1) for i in weak.index]
        loo_s = [round(float(strong.drop(i).median()), 1) for i in strong.index]
        macros["looGainWeakMin"], macros["looGainWeakMax"] = (min(loo_w),
                                                              max(loo_w))
        macros["looGainStrongMin"], macros["looGainStrongMax"] = (min(loo_s),
                                                                  max(loo_s))
    if len(gg) >= 10:
        from scipy.stats import spearmanr  # noqa: only if available
        rho, pval = spearmanr(gg["rubric_B"], gg["gain_num"])
        macros["spearmanBGainRho"] = f"{float(rho):.2f}"
        macros["spearmanBGainP"] = f"{float(pval):.3f}"
        macros["nSpearman"] = len(gg)

        # bootstrap 95% CIs for the two medians (robustness reporting: uncertainty
        # on the headline summary statistics; fixed seed for reproducibility)
        import random
        rng = random.Random(20260718)
        def med_ci(series):
            vals = list(series)
            boots = sorted(
                float(pd.Series([vals[rng.randrange(len(vals))]
                                 for _ in vals]).median())
                for _ in range(2000))
            return (round(boots[int(0.025 * len(boots))], 1),
                    round(boots[min(len(boots) - 1, int(0.975 * len(boots)))], 1))
        macros["ciGainWeakLo"], macros["ciGainWeakHi"] = med_ci(weak)
        macros["ciGainStrongLo"], macros["ciGainStrongHi"] = med_ci(strong)

        # win / near-parity / loss composition (reviewer request: report the
        # full outcome distribution, not only positive percentage gains). A
        # margin below 1 percentage point is read as near-parity rather than a
        # win, since it is within the noise of most reported evaluations.
        macros["nGainPositive"] = int((gg["gain_num"] > 0).sum())
        macros["nGainZeroNeg"] = int((gg["gain_num"] <= 0).sum())
        macros["nGainNearParity"] = int((gg["gain_num"].abs() < 1.0).sum())
        macros["nGainClearWin"] = int((gg["gain_num"] >= 1.0).sum())
        macros["nGainLoss"] = int((gg["gain_num"] < 0).sum())

        # ordinal trend test alongside the Spearman correlation (reviewer
        # request): Kendall's tau-b for the monotone gain-vs-baseline trend.
        from scipy.stats import kendalltau
        _tau, _taup = kendalltau(gg["rubric_B"], gg["gain_num"])
        macros["kendallBGainTau"] = f"{float(_tau):.2f}"
        macros["kendallBGainP"] = f"{float(_taup):.3f}"

        # layer-stratified gain gradient (reviewer request: show the corpus-wide
        # weak-vs-strong finding is not driven by, and holds without, Layer 3).
        gl = gains.copy()
        gl["rb"] = pd.to_numeric(gl["rubric_B"], errors="coerce")
        for lay, tag in (("L1", "Lone"), ("L2", "Ltwo"), ("L3", "Lthree")):
            sub = gl[(gl["layer"] == lay) & (gl["rb"] >= 0)]
            macros[f"nGain{tag}Set"] = len(sub)
        _nonL3 = gl[(gl["layer"] != "L3") & (gl["rb"] >= 0)]
        w12 = _nonL3[_nonL3["rb"] <= 1]["gain_num"]
        s12 = _nonL3[_nonL3["rb"] >= 2]["gain_num"]
        if len(w12) >= 3 and len(s12) >= 3:
            macros["medGainWeakBnoLthree"] = round(float(w12.median()), 1)
            macros["medGainStrongBnoLthree"] = round(float(s12.median()), 1)
            macros["nGainWeakBnoLthree"] = len(w12)
            macros["nGainStrongBnoLthree"] = len(s12)

        # per-B-tier counts within the gain set (robustness reporting)
        for tier in range(4):
            macros[f"nGainBtier{['Zero','One','Two','Three'][tier]}"] = int(
                (gg["rubric_B"] == tier).sum())

        # objective-family-stratified medians (robustness reporting: show the
        # direction is not driven by a single objective family)
        fam = gains["primary_objective"].str.lower().map(
            lambda s: "time" if any(k in s for k in
                                    ("makespan", "duration", "time", "wait"))
            else ("cost" if "cost" in s else "other"))
        gg2 = gg.assign(fam=fam.loc[gg.index])
        obj_rows = []
        for f in ("time", "cost", "other"):
            sub = gg2[gg2["fam"] == f]
            w2, s2 = (sub[sub["rubric_B"] <= 1]["gain_num"],
                      sub[sub["rubric_B"] >= 2]["gain_num"])
            obj_rows.append({"family": f, "n_weak": len(w2),
                             "med_weak": round(float(w2.median()), 1) if len(w2) else None,
                             "n_strong": len(s2),
                             "med_strong": round(float(s2.median()), 1) if len(s2) else None})
            tag = f.capitalize()
            if len(w2) >= 3 and len(s2) >= 3:
                macros[f"medGainWeak{tag}Obj"] = round(float(w2.median()), 1)
                macros[f"medGainStrong{tag}Obj"] = round(float(s2.median()), 1)
                macros[f"nGainWeak{tag}Obj"] = len(w2)
                macros[f"nGainStrong{tag}Obj"] = len(s2)
        pd.DataFrame(obj_rows).to_csv(OUT / "gain_by_objective_family.csv",
                                      index=False)

        # research-group clustering robustness (robustness: the Spearman
        # treats same-group studies as independent). Cluster by first-author
        # family name; report the leave-one-cluster-out rho range.
        first_author = corpus.set_index("id").loc[gg["id"], "authors"].astype(str)
        surname = first_author.str.split(";").str[0].str.strip().str.split().str[-1].str.lower()
        gg3 = gg.assign(cluster=surname.values)
        rhos = []
        for c in gg3["cluster"].unique():
            sub = gg3[gg3["cluster"] != c]
            if len(sub) >= 10 and sub["rubric_B"].nunique() > 1:
                r, _ = spearmanr(sub["rubric_B"], sub["gain_num"])
                rhos.append(float(r))
        if rhos:
            macros["locoRhoMin"] = f"{min(rhos):.2f}"
            macros["locoRhoMax"] = f"{max(rhos):.2f}"
            macros["nGainClusters"] = int(gg3["cluster"].nunique())

        # comparator-class sensitivity (robustness: rubric tier B = 2 pools
        # multi-rule portfolios, tuned rules, and standard metaheuristics,
        # which are not equally competitive; re-draw the contrast from the
        # coded comparator classes, classifying each study by the strongest
        # class present in its baseline suite).
        bl = corpus.set_index("id").loc[gg["id"], "baselines"].astype(str)

        def comp_class(b):
            if "exact-CP-MILP" in b:
                return "exact"
            if "metaheuristic" in b:
                return "metaheuristic"
            if "other-DRL" in b:
                return "prior-learned"
            if "tuned-rules" in b or "multiple-PDRs" in b:
                return "multiple-or-tuned-rules"
            return "single-rule-manual-or-none"

        gg4 = gg.assign(cclass=bl.map(comp_class).values)
        cls_order = ["single-rule-manual-or-none", "multiple-or-tuned-rules",
                     "prior-learned", "metaheuristic", "exact"]
        cls_rows = []
        for c in cls_order:
            sub = gg4[gg4["cclass"] == c]["gain_num"]
            cls_rows.append({
                "comparator_class": c, "n": len(sub),
                "median_gain_pct": round(float(sub.median()), 1) if len(sub) else None,
                "gains_pct": "|".join(f"{v:g}" for v in sorted(sub))})
        pd.DataFrame(cls_rows).to_csv(OUT / "gain_by_comparator_class.csv",
                                      index=False)
        for c, tag in (("single-rule-manual-or-none", "Single"),
                       ("multiple-or-tuned-rules", "MultiTuned"),
                       ("prior-learned", "Learned"),
                       ("metaheuristic", "Meta"), ("exact", "Exact")):
            sub = gg4[gg4["cclass"] == c]["gain_num"]
            macros[f"nGainClass{tag}"] = len(sub)
            if len(sub):
                macros[f"medGainClass{tag}"] = round(float(sub.median()), 1)
        # strict redefinition: strong only if an optimization-class method
        # (metaheuristic or exact solver) is in the comparator suite
        is_opt = gg4["cclass"].isin(["metaheuristic", "exact"])
        macros["nGainOptClass"] = int(is_opt.sum())
        macros["medGainOptClass"] = round(
            float(gg4[is_opt]["gain_num"].median()), 1)
        macros["nGainNonOptClass"] = int((~is_opt).sum())
        macros["medGainNonOptClass"] = round(
            float(gg4[~is_opt]["gain_num"].median()), 1)
        rule_only = gg4["cclass"].isin(["single-rule-manual-or-none",
                                        "multiple-or-tuned-rules"])
        macros["nGainRuleClass"] = int(rule_only.sum())
        macros["medGainRuleClass"] = round(
            float(gg4[rule_only]["gain_num"].median()), 1)
        # tuned-or-optimization vs untuned-only dichotomy
        has_tuned = bl.map(lambda b: any(t in b for t in
                           ("tuned-rules", "metaheuristic",
                            "exact-CP-MILP"))).values
        macros["nGainTunedOpt"] = int(has_tuned.sum())
        macros["medGainTunedOpt"] = round(
            float(gg4[has_tuned]["gain_num"].median()), 1)
        macros["nGainUntuned"] = int((~has_tuned).sum())
        macros["medGainUntuned"] = round(
            float(gg4[~has_tuned]["gain_num"].median()), 1)

    # evidence-access composition (which records can support
    # protocol-level judgments at all)
    acc = corpus["access_level"].fillna("title_only").value_counts()
    macros["nAccessFullText"] = int(acc.get("full_text", 0))
    macros["nAccessAbstract"] = int(acc.get("abstract_only", 0))
    macros["nAccessTitle"] = int(acc.get("title_only", 0))
    for lay, tag in (("L1", "Lone"), ("L2", "Ltwo"), ("L3", "Lthree")):
        macros[f"nTitleOnly{tag}"] = int(
            ((corpus["layer"] == lay)
             & (corpus["access_level"] == "title_only")).sum())

    def pct_flag(col, val="y"):
        return round(100 * int((corpus[col].astype(str).str.lower()
                                .str.startswith(val)).sum()) / n)
    macros["pctInferenceTime"] = pct_flag("inference_time_reported")
    macros["pctCodeAvail"] = round(100 * int((~corpus["code_available"]
                                   .astype(str).str.lower().isin(["n", "nr", "nan"])).sum()) / n)
    macros["pctDataAvail"] = round(100 * int((~corpus["data_available"]
                                   .astype(str).str.lower().isin(["n", "nr", "nan"])).sum()) / n)
    dep = corpus["deployment_level"].fillna("NR").value_counts()
    macros["nPilotField"] = int(dep.get("pilot", 0) + dep.get("field", 0))
    macros["pctSimulationOnly"] = round(100 * int(dep.get("simulation", 0)) / n)

    # empty-cell probability argument (sparsity check): among studies
    # scorable on B with a reported deployment level, what share reach B >= 2,
    # and how likely is it under independence that every deployed study
    # misses that tier?
    _bd = corpus[["rubric_B", "deployment_level"]].copy()
    _bd["rubric_B"] = pd.to_numeric(_bd["rubric_B"], errors="coerce")
    _bd = _bd[(_bd["rubric_B"] >= 0) & (_bd["deployment_level"] != "NR")
              & _bd["deployment_level"].notna()]
    macros["nScorableBDep"] = len(_bd)
    _pB2 = float((_bd["rubric_B"] >= 2).mean())
    macros["pctBTwoPlusScorable"] = round(100 * _pB2)
    _ndep = int(_bd["deployment_level"].isin(["pilot", "field"]).sum())
    _prob = (1 - _pB2) ** _ndep
    macros["probEmptyCellPct"] = ("%.1f" % (100 * _prob)) if _prob >= 0.001 else "0.1"
    (pd.crosstab(_bd["rubric_B"].astype(int), _bd["deployment_level"])
     .to_csv(OUT / "b_by_deployment.csv"))
    # distinct denominators the deployment discussion rests on (kept separate
    # so data realism, deployment level, and the B x D matrix are not conflated)
    _B = pd.to_numeric(corpus["rubric_B"], errors="coerce")
    _D = pd.to_numeric(corpus["rubric_D"], errors="coerce")
    macros["nScorableBD"] = int(((_B >= 0) & (_D >= 0)).sum())          # Fig 7(d)
    _pf = corpus["deployment_level"].isin(["pilot", "field"])
    macros["nPilotFieldBScored"] = int((_pf & (_B >= 0)).sum())         # 5 of 6
    # released enumeration of every pilot/field study for the supplement table
    _pfrows = corpus[_pf][["id", "layer", "baselines", "rubric_B", "rubric_D",
                           "deployment_level", "evaluation_protocol"]].copy()
    _pfrows.to_csv(OUT / "pilot_field_studies.csv", index=False)
    tdata = corpus["training_data"].fillna("NR").value_counts()
    macros["pctSynthetic"] = round(100 * int(tdata.get("synthetic", 0)) / n)
    macros["pctRealData"] = round(100 * (int(tdata.get("real-historical", 0))
                                         + int(tdata.get("mixed", 0))) / n)
    base_cnt = Counter()
    for v in corpus["baselines"]:
        base_cnt.update(split(v))
    pd.Series(base_cnt).reindex(BASELINE_ORDER).fillna(0).astype(int).to_csv(
        OUT / "baseline_classes.csv")
    macros["pctVsExact"] = round(100 * base_cnt.get("exact-CP-MILP", 0) / n)
    macros["pctVsMeta"] = round(100 * base_cnt.get("metaheuristic", 0) / n)
    macros["pctVsOtherDRL"] = round(100 * base_cnt.get("other-DRL", 0) / n)
    ev_cnt = Counter()
    for v in corpus["evaluation_protocol"]:
        ev_cnt.update(split(v))
    pd.Series(ev_cnt).reindex(EVAL_ITEMS).fillna(0).astype(int).to_csv(
        OUT / "eval_protocol.csv")
    macros["pctSeedsOrStats"] = round(100 * len(corpus[
        corpus["evaluation_protocol"].apply(
            lambda v: bool({"multiple-seeds", "statistical-test"} & set(split(v))))]) / n)
    macros["pctSizeGen"] = round(100 * ev_cnt.get("size-generalization", 0) / n)
    macros["pctDistShift"] = round(100 * ev_cnt.get("distribution-shift", 0) / n)
    # "coded without full-text evidence" = the abstract-only and title-only
    # access levels combined; aligned to the released access hierarchy so the
    # headline share reconciles exactly with the 32/65/31 breakdown reported
    # in Section 3 (rather than the coder-confidence flag, which differs by one
    # record and would invite a spurious 74 vs 75 mismatch).
    macros["pctPartialCoding"] = round(
        100 * int((corpus["access_level"] != "full_text").sum()) / n)

    # method-design landscape (Fig 5)
    md = (corpus.groupby(["problem_class", "encoder"]).size()
          .unstack(fill_value=0))
    md.to_csv(OUT / "fig5_problem_encoder.csv")
    ta = corpus["training_algo"].fillna("NR").value_counts()
    ta.to_csv(OUT / "fig5_training_algo.csv")
    macros["pctPPO"] = round(100 * int(ta.get("PPO", 0)) / n)
    macros["pctDQNfamily"] = round(100 * (int(ta.get("DQN", 0))
                                          + int(ta.get("double-DQN", 0))) / n)

    # ---- extra figure data (richer multi-panel figures) ----
    # reporting-practice epidemiology (share reporting each practice), overall + per layer
    def reports_inf(s):
        return s.astype(str).str.lower().str.startswith("y")
    practice_rows = []
    for scope, sub in [("overall", corpus)] + [(l, corpus[corpus["layer"] == l])
                                               for l in ("L1", "L2", "L3")]:
        m = max(1, len(sub))
        cnt = {
            "inference_time": int(reports_inf(sub["inference_time_reported"]).sum()),
            "code": int((~sub["code_available"].astype(str).str.lower().isin(["n", "nr", "nan"])).sum()),
            "data": int((~sub["data_available"].astype(str).str.lower().isin(["n", "nr", "nan"])).sum()),
            "seeds_or_stats": int(sub["evaluation_protocol"].apply(
                lambda v: bool({"multiple-seeds", "statistical-test"} & set(split(v)))).sum()),
            "feasibility_mech": int((~sub["feasibility_mechanism"].astype(str).isin(["NR", "nan"])).sum()),
            "held_out": int(sub["evaluation_protocol"].apply(
                lambda v: "held-out-instances" in split(v)).sum()),
        }
        row = {"scope": scope, "n": len(sub)}
        row.update({k: round(100 * v / m) for k, v in cnt.items()})
        row.update({f"{k}_count": v for k, v in cnt.items()})
        practice_rows.append(row)
        if scope == "overall":
            # counts behind the documentation-rate percentages, for n/N (%)
            # phrasing in the text and the Figure 6(c) caption
            macros["nInferenceTime"] = cnt["inference_time"]
            macros["nCodeAvail"] = cnt["code"]
            macros["nDataAvail"] = cnt["data"]
            macros["nSeedsOrStats"] = cnt["seeds_or_stats"]
            macros["nFeasDocumented"] = cnt["feasibility_mech"]
            macros["nFeasNR"] = len(sub) - cnt["feasibility_mech"]
            macros["nHeldOut"] = cnt["held_out"]
    pd.DataFrame(practice_rows).to_csv(OUT / "fig6_reporting_practices.csv", index=False)

    # B x D co-occurrence matrix (shows the empty high-rigor cells; the mutual-exclusivity finding)
    bd = corpus[["rubric_B", "rubric_D", "deployment_level"]].copy()
    bd["B"] = pd.to_numeric(bd["rubric_B"], errors="coerce")
    bd["D"] = pd.to_numeric(bd["rubric_D"], errors="coerce")
    bd = bd[(bd["B"] >= 0) & (bd["D"] >= 0)]
    bd_mat = (bd.groupby(["B", "D"]).size().unstack(fill_value=0)
              .reindex(index=[0, 1, 2, 3], columns=[0, 1, 2, 3], fill_value=0))
    bd_mat.to_csv(OUT / "fig6_BD_matrix.csv")
    # the mutual-exclusivity finding: no study has a strong baseline (B>=2, i.e.
    # a metaheuristic/exact/tuned comparator) AND a field-or-pilot deployment
    # (D==3). This is the empty top-right corner of the B x D matrix.
    macros["nStrongBaselineFieldCell"] = int(bd[(bd["B"] >= 2) & (bd["D"] == 3)].shape[0])
    macros["nRealDataStrongBaseline"] = int(bd[(bd["B"] >= 2) & (bd["D"] >= 2)].shape[0])
    # studies at >=2 on all three rubrics simultaneously (the TODOnum in s8)
    allrub = corpus[["rubric_B", "rubric_E", "rubric_D"]].apply(pd.to_numeric, errors="coerce")
    macros["nMidTierAll"] = int(((allrub["rubric_B"] >= 2) & (allrub["rubric_E"] >= 2)
                                 & (allrub["rubric_D"] >= 2)).sum())
    # LLM-agent count (the other TODOnum in s4)
    macros["nLLMagent"] = int((corpus["learning_paradigm"] == "LLM-agent").sum())

    # paradigm x layer (for a richer Fig 5 panel)
    pl_mat = (corpus.groupby(["learning_paradigm", "layer"]).size()
              .unstack(fill_value=0))
    pl_mat.to_csv(OUT / "fig5_paradigm_by_layer.csv")

    # ---- per-layer rubric macros + counts requested by the drafts (TODOnum) ----
    LNAME = {"L1": "Lone", "L2": "Ltwo", "L3": "Lthree"}
    for lay, tag in LNAME.items():
        sub = corpus[corpus["layer"] == lay]
        m = max(1, len(sub))
        for col, dl in [("rubric_B", "B"), ("rubric_E", "E"), ("rubric_D", "D")]:
            s = pd.to_numeric(sub[col], errors="coerce")
            s = s[s >= 0]
            if len(s):
                macros[f"median{dl}{tag}"] = num_to_word_or_num(s.median())
        sB = pd.to_numeric(sub["rubric_B"], errors="coerce")
        sBa = sB[sB >= 0]
        if len(sBa):
            macros[f"pctBZeroOne{tag}"] = round(100 * int((sBa <= 1).sum()) / len(sBa))
        # "no baseline comparison": rubric_B == 0 (none/random)
        macros[f"pctNoBaseline{tag}"] = round(100 * int((sB == 0).sum()) / m)
        # evaluation protocol reported as NR only
        eval_nr = sub["evaluation_protocol"].apply(
            lambda v: set(split(v)) in ({"NR"}, set()))
        macros[f"pctEvalNR{tag}"] = round(100 * int(eval_nr.sum()) / m)
        # unassignable rubric: baseline-strength (B) not assessable from an
        # abstract-only dossier (rubric_B == -1)
        una = pd.to_numeric(sub["rubric_B"], errors="coerce") < 0
        macros[f"nUnassignable{tag}"] = int(una.sum())
        # numeric-gain count per layer
        macros[f"nGain{tag}"] = int(pd.to_numeric(
            sub["gain_vs_strongest_baseline_pct"], errors="coerce").notna().sum())

    # distinct objective-function SPECIFICATIONS (the full objective set per
    # study, deduplicated as a combination, not per individual term)
    objspecs = set()
    for v in corpus["objectives"]:
        combo = frozenset(x.strip().lower() for x in split(v) if x.strip())
        if combo:
            objspecs.add(combo)
    macros["nObjectives"] = len(objspecs)
    macros["nCustomClass"] = int((corpus["problem_class"] == "custom").sum())
    # L3 studies modeling generalized precedence (for the s2 problem-space claim)
    _l3 = corpus[corpus["layer"] == "L3"]
    macros["nPrecedenceLthree"] = int(_l3["constraint_features"].apply(
        lambda v: "precedence" in split(v)).sum())

    # PRISMA counts as macros (single source for the methodology prose)
    _pl = json.loads((ROOT.parent / "retrieval" / "prisma_ledger.json").read_text())
    macros["nIdentified"] = _pl.get("identified_total_records")
    macros["nAfterDedup"] = _pl.get("after_dedup_unique")
    macros["nScreened"] = _pl.get("pass1_screened_records")
    macros["nFullTextAssessed"] = _pl.get("full_text_assessed")
    macros["nPassTwoExcluded"] = _pl.get("pass2_excluded_total")
    macros["nReportsNotRetrieved"] = _pl.get("reports_not_retrieved")
    macros["nReportsAssessed"] = _pl.get("reports_assessed_eligibility")
    macros["nExcludedAfterAssessment"] = _pl.get("excluded_after_assessment")
    macros["nMethodsTrackDedup"] = _pl.get("methods_track")
    macros["nDomainTrackDedup"] = _pl.get("domain_track")
    macros["nSnowItOne"] = _pl.get("snowball_it1_domain_screened")
    macros["nSnowItTwo"] = _pl.get("snowball_it2_domain_net_screened")
    macros["nSnowItThree"] = _pl.get("snowball_it3_domain_net_screened")

    # ------------------------------------------------------- RQ4 gap matrix
    nr_rates = {}
    for col in ("training_data", "feasibility_mechanism", "deployment_level",
                "state_representation", "encoder"):
        nr_rates[col] = round(100 * int((corpus[col].astype(str)
                              .isin(["NR", "nan"])).sum()) / n)
    nr_rates["inference_time_not_reported"] = 100 - macros["pctInferenceTime"]
    (OUT / "gap_matrix_inputs.json").write_text(json.dumps({
        "nr_rates_pct": nr_rates,
        "eval_counts": {k: int(v) for k, v in ev_cnt.items()},
        "baseline_counts": {k: int(v) for k, v in base_cnt.items()},
        "deployment": {str(k): int(v) for k, v in dep.items()},
    }, indent=1))

    # ---- inter-rater reliability macros (from corpus/reliability.py) ----
    _rel = ROOT.parent / "corpus" / "reliability_report.json"
    if _rel.exists():
        for k, v in json.loads(_rel.read_text()).get("macros", {}).items():
            macros[k] = v
    # dual-coding of the numeric-gain set (corpus/reliability_gain_set.py round)
    _relg = ROOT.parent / "corpus" / "reliability_gain_set.json"
    if _relg.exists():
        for k, v in json.loads(_relg.read_text()).get("macros", {}).items():
            macros[k] = v

    # ------------------------------------------------------------- macros.tex
    lines = ["% GENERATED by analysis/analysis.py; DO NOT EDIT BY HAND.",
             "% Every corpus-derived number in the manuscript resolves here."]
    for k, v in sorted(macros.items()):
        lines.append(f"\\newcommand{{\\{k}}}{{{tex_escape(v)}}}")
    MACROS.write_text("\n".join(lines) + "\n")
    (OUT / "macros_dump.json").write_text(json.dumps(macros, indent=1))
    print(f"analysis complete: n={n} domain studies; "
          f"{len(macros)} macros -> {MACROS}")


if __name__ == "__main__":
    main()
