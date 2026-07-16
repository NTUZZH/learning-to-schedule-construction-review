#!/usr/bin/env python
"""Inter-rater reliability for the B/E/D rubric.

Compares the second (independent) coder's scores on a 20% random subsample
against the primary coding, and reports Krippendorff's alpha (ordinal
distance) per rubric dimension plus exact/adjacent agreement. Emits macros
for the methodology section. The -1 "not assessable" code is treated as a
distinct nominal-style value only for the assessability-agreement measure;
alpha is computed on items both coders scored on the 0--3 ordinal scale.
"""
import json
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SECOND = json.loads((Path(__file__).resolve().parent / "reliability_second_coder.json").read_text())["scores"]
XLSX = ROOT / "corpus_coded.xlsx"


def krippendorff_ordinal(pairs):
    """Krippendorff's alpha for two coders, ordinal metric.
    pairs: list of (v1, v2) integer scores (both present)."""
    vals = [v for p in pairs for v in p]
    if not vals:
        return None
    # ordinal metric delta(a,b) = (sum of frequencies strictly between, plus
    # half the endpoints)^2 ; standard Krippendorff ordinal.
    from collections import Counter
    n = len(vals)
    freq = Counter(vals)
    levels = sorted(freq)

    def cumulative(g):
        # number of values <= g
        return sum(freq[l] for l in levels if l <= g)

    def delta2(a, b):
        if a == b:
            return 0.0
        lo, hi = min(a, b), max(a, b)
        s = 0.0
        for g in levels:
            if lo <= g <= hi:
                s += freq[g]
        s = s - (freq[lo] + freq[hi]) / 2.0
        return s * s

    # observed disagreement Do
    Do_num = sum(delta2(a, b) for (a, b) in pairs) * 2  # each unit twice (symmetric)
    n_units = len(pairs)
    Do = Do_num / (2 * n_units) if n_units else 0.0
    # expected disagreement De
    De_num = 0.0
    for a, b in combinations(vals, 2):
        De_num += delta2(a, b)
    De = De_num * 2 / (n * (n - 1)) if n > 1 else 0.0
    if De == 0:
        return 1.0
    return 1 - Do / De


def main():
    prim = pd.read_excel(XLSX, sheet_name="corpus")
    prim = prim[prim["layer"].isin(["L1", "L2", "L3"])].set_index("id")
    macros = {}
    report = {}
    for dim, key in [("rubric_B", "B"), ("rubric_E", "E"), ("rubric_D", "D")]:
        pairs = []
        assess_agree = 0
        n_items = 0
        for s in SECOND:
            cid = s["cand_id"]
            if cid not in prim.index:
                continue
            v1 = pd.to_numeric(prim.loc[cid, dim], errors="coerce")
            v2 = s[dim]
            if pd.isna(v1):
                continue
            v1 = int(v1)
            n_items += 1
            a1 = v1 >= 0
            a2 = v2 >= 0
            if a1 == a2:
                assess_agree += 1
            if a1 and a2:
                pairs.append((v1, v2))
        alpha = krippendorff_ordinal(pairs)
        exact = sum(1 for a, b in pairs if a == b) / len(pairs) if pairs else 0
        adjacent = sum(1 for a, b in pairs if abs(a - b) <= 1) / len(pairs) if pairs else 0
        report[key] = {"n_both_scorable": len(pairs), "alpha_ordinal": alpha,
                       "exact_agreement": exact, "within_one": adjacent,
                       "assessability_agreement": assess_agree / n_items if n_items else 0}
        macros[f"alpha{key}"] = f"{alpha:.2f}" if alpha is not None else "NA"
        macros[f"exactAgree{key}"] = round(100 * exact)
        # nonparametric bootstrap CI over units (fixed seed for reproducibility)
        if pairs:
            import random
            rng = random.Random(20260717)
            boots = []
            for _ in range(2000):
                bs = [pairs[rng.randrange(len(pairs))] for _ in pairs]
                a = krippendorff_ordinal(bs)
                if a is not None:
                    boots.append(a)
            boots.sort()
            lo = boots[int(0.025 * len(boots))]
            hi = boots[min(len(boots) - 1, int(0.975 * len(boots)))]
            report[key]["alpha_ci95"] = [round(lo, 2), round(hi, 2)]
            macros[f"alpha{key}Lo"] = f"{lo:.2f}"
            macros[f"alpha{key}Hi"] = f"{hi:.2f}"
    macros["nReliabilitySample"] = len(SECOND)
    macros["pctReliabilitySample"] = round(100 * len(SECOND) / len(prim))
    # mean alpha across dimensions
    alphas = [report[k]["alpha_ordinal"] for k in report if report[k]["alpha_ordinal"] is not None]
    macros["alphaMean"] = f"{sum(alphas)/len(alphas):.2f}" if alphas else "NA"

    # analysis.py owns macros.tex (single source of truth); it reads these.
    (ROOT / "reliability_report.json").write_text(
        json.dumps({"report": report, "macros": macros}, indent=1))
    print(json.dumps({"report": report, "macros": macros}, indent=1))


if __name__ == "__main__":
    main()
