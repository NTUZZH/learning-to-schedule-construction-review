#!/usr/bin/env python
"""Generate LaTeX tables (Tables 1-6) into
manuscript/tables/*.tex, and keep the source CSVs. Every table is booktabs,
single-column-friendly, and driven by the coded database / analysis outputs
or (Table 1) the verified prior-reviews list. No table carries a claim not
present in its backing data.
"""
import csv
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
AN = ROOT.parent / "analysis" / "outputs"
CORPUS = ROOT.parent / "corpus"
TDIR = ROOT.parent / "manuscript" / "tables"
TDIR.mkdir(parents=True, exist_ok=True)
CSVDIR = ROOT.parent / "manuscript" / "tables" / "csv"
CSVDIR.mkdir(parents=True, exist_ok=True)


def esc(s):
    s = str(s)
    for a, b in [("&", "\\&"), ("%", "\\%"), ("_", "\\_"), ("#", "\\#"),
                 ("$", "\\$")]:
        s = s.replace(a, b)
    # coded text uses ~ / (approx) as "approximately"; a raw ~ is a LaTeX
    # non-breaking space and silently disappears
    s = s.replace("~", "$\\sim$").replace("≈", "$\\approx$")
    # slashed compounds (metaheuristic/hybrid) are unbreakable by default and
    # overflow narrow p-columns; allow a break after the slash
    s = s.replace("/", "/\\allowbreak{}")
    return s


def write_tex(name, body):
    (TDIR / f"{name}.tex").write_text(body)
    print(f"wrote tables/{name}.tex")


# --------------------------------------------------- Table 1: prior reviews
def table1_prior_reviews():
    """Rows are the prior reviews (Section 2.1); columns are coverage axes.
    Driven by a hand-maintained matrix keyed to verified ref_ids; the matrix
    is factual metadata (what each review covers), recorded from each review's
    own scope, and each ref_id must be status=verified."""
    matrix_file = CORPUS / "table1_prior_reviews.csv"
    if not matrix_file.exists():
        # scaffold with the verified prior-review ref_ids; scope cells filled
        # from each review's abstract.
        verified = {r["ref_id"]: r for r in csv.DictReader((CORPUS / "references_verified.csv").open())}
        prior = [rid for rid, r in verified.items() if r["role"] == "prior-review"]
        with matrix_file.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["ref_id", "citation", "domain", "methods_covered",
                        "layers_covered", "critical_evidence_audit", "year"])
            for rid in prior:
                r = verified[rid]
                w.writerow([rid, "", "", "", "", "", r.get("year", "")])
        print(f"  scaffolded {matrix_file.name} ({len(prior)} prior reviews) "
              "-- fill scope cells")
        return
    df = pd.read_csv(matrix_file)
    header = ("\\begin{table*}[t]\n\\centering\n\\caption{Prior reviews related "
              "to learning-based scheduling, positioned against this review. "
              "In the evidence-audit column, a dash denotes no evidence audit; a check denotes one. "
              "L1--L3 are this review's application layers: project "
              "scheduling, industrialized construction, and built-asset "
              "maintenance (defined in Section 1). "
              "Abbreviations: DRL, deep reinforcement learning; GNN, graph neural network; MARL, multi-agent reinforcement learning; IL, imitation learning; LLM, large language model; GA, genetic algorithm; PSO, particle-swarm optimization; SA, simulated annealing; ACO, ant-colony optimization; ML, machine learning; CO, combinatorial optimization; JSSP, job-shop scheduling problem; RL, reinforcement learning. "
              "Compiled from each review's stated scope.}\n"
              "\\label{tab:prior_reviews}\n\\small\n\\renewcommand{\\arraystretch}{1.14}\n"
              "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{3.4cm}"
              ">{\\raggedright\\arraybackslash}p{2.4cm}"
              ">{\\raggedright\\arraybackslash}p{2.6cm}"
              ">{\\raggedright\\arraybackslash}p{2.2cm}c@{}}\n\\toprule\n"
              "Review & Domain & Methods covered & Layers & Evidence audit \\\\\n\\midrule\n")
    rows = []
    for _, r in df.iterrows():
        # cite each prior review by its verified key so the row is traceable
        cite = f"\\citet{{{r['ref_id']}}}" if str(r.get("ref_id", "")).strip() else esc(r["citation"])
        # the caption's convention: dash = no coverage, check = explicit
        audit = "--" if str(r["critical_evidence_audit"]).strip().lower() in (
            "no", "none", "-", "--") else esc(r["critical_evidence_audit"])
        rows.append(" & ".join([cite] + [esc(x) for x in [
            r["domain"], r["methods_covered"],
            r["layers_covered"]]] + [audit]) + " \\\\")
    footer = ("\n\\midrule\n\\textbf{This review} & Construction \\& built "
              "environment & DRL, GNN, MARL, IL, LLM agents & L1--L3 & "
              "\\checkmark \\\\\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")
    write_tex("table1_prior_reviews", header + "\n".join(rows) + footer)


# --------------------------------------- Table 2: constraint families / layer
def table2_constraints():
    f = AN / "fig3_constraint_matrix.csv"
    if not f.exists():
        print("  table2 skipped (no analysis output yet)")
        return
    cf = pd.read_csv(f, index_col=0)
    feats = [c for c in cf.columns if c != "n"]
    header = ("\\begin{table*}[t]\n\\centering\n\\caption{Constraint-family "
              "coverage across the three layers. Cells give the number of "
              "corpus studies whose available text reports modeling each "
              "family; a zero therefore means no assessable study reports "
              "the family, not proven absence (Section~\\ref{sec:method}). Computed from "
              "the coded database.}\n\\label{tab:constraints}\n\\small\n"
              "\\begin{tabular}{@{}l" + "c" * len(cf.index) + "@{}}\n\\toprule\n"
              "Constraint family & " + " & ".join(f"{i} ($n={int(cf.loc[i,'n'])}$)"
                                                   for i in cf.index) + " \\\\\n\\midrule\n")
    from figures import FAMILY_LABELS
    rows = []
    for feat in feats:
        rows.append(esc(FAMILY_LABELS.get(feat, feat)) + " & "
                    + " & ".join(str(int(cf.loc[i, feat]))
                    for i in cf.index) + " \\\\")
    write_tex("table2_constraints", header + "\n".join(rows)
              + "\n\\bottomrule\n\\end{tabular}\n\\end{table*}\n")



def _trunc(s, n):
    """Truncate at a word boundary with an ellipsis (never mid-word)."""
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + " ..."

# --------------------------------- Tables 3-5: per-layer study summaries
def tables_layers():
    """Landscape longtables: the wide page gives the headline column ~11 cm,
    so findings appear in full (no ellipsis) while rows stay to 3-4 lines."""
    xlsx = CORPUS / "corpus_coded.xlsx"
    if not xlsx.exists():
        print("  tables 3-5 skipped (no corpus_coded.xlsx yet)")
        return
    df = pd.read_excel(xlsx, sheet_name="corpus")
    layer_names = {"L1": "project-level construction scheduling",
                   "L2": "industrialized construction",
                   "L3": "civil-infrastructure maintenance planning and built-asset work-order scheduling"}
    for idx, lay in enumerate(["L1", "L2", "L3"], start=3):
        sub = df[df["layer"] == lay].copy()
        if sub.empty:
            continue
        sub["year"] = pd.to_numeric(sub["year"], errors="coerce")
        # comprehensive: ALL studies in the layer, ordered by year then id
        sub = sub.sort_values(["year", "id"], na_position="last")

        def cite(r):
            y = r.get("year")
            ytag = f" ({int(y)})" if pd.notna(y) else ""
            return f"\\citet{{{r['id']}}}{ytag}"
        cap = ("Layer " + lay[-1] + " (" + layer_names[lay] + ") corpus: all "
               + str(len(sub)) + " studies, ordered by year. Rubric columns give "
               "baseline strength (B), evaluation rigor (E), and data realism (D) "
               "on a 0--3 scale; a dash marks a dimension the available text is "
               "insufficient to assess, whereas a 0 is an assessed absence; NR = "
               "not reported in the available text; (+$n$) in the Baseline "
               "column counts further baselines omitted for space. Compiled "
               "from the coded database.")
        P = ">{\\raggedright\\arraybackslash}p"
        colspec = ("@{}" + P + "{2.3cm}" + P + "{1.8cm}" + P + "{2.3cm}"
                   + P + "{2.1cm}ccc " + P + "{11.0cm}@{}")
        head = ("Study & Problem & Method & Baseline & B & E & D & "
                "Headline finding \\\\\n\\midrule\n")
        # No landscape wrapper: the supplement document is itself typeset in
        # landscape (see supplementary.tex), so the page is already wide and
        # its footer prints upright. Wrapping the table in a rotate-the-page
        # environment here would rotate it back to sideways.
        header = ("\\begin{footnotesize}\n"
                  "\\setlength{\\tabcolsep}{4pt}\n"
                  "\\renewcommand{\\arraystretch}{1.14}\n"
                  "\\begin{longtable}{" + colspec + "}\n"
                  "\\caption{" + cap + "}\\label{tab:layer" + lay[-1] + "}\\\\\n"
                  "\\toprule\n" + head + "\\endfirsthead\n"
                  "\\multicolumn{8}{c}{\\tablename\\ \\thetable: continued}\\\\\n"
                  "\\toprule\n" + head + "\\endhead\n"
                  "\\midrule\\multicolumn{8}{r}{continued on next page}\\\\\n\\endfoot\n"
                  "\\bottomrule\n\\endlastfoot\n")

        def rub(v):
            v = str(v).replace(".0", "")
            return "--" if v in ("-1", "nan", "NR", "") else v
        rows = []
        for _, r in sub.iterrows():
            bl = [b for b in str(r.get("baselines", "")).split("|") if b and b != "nan"]
            bl_disp = (", ".join(bl[:2])
                       + (f" (+{len(bl) - 2})" if len(bl) > 2 else "")) if bl else "NR"
            method = str(r.get("learning_paradigm", ""))
            enc = str(r.get("encoder", ""))
            if enc not in ("NR", "nan", "none", ""):
                method += "/" + enc
            rows.append(" & ".join([
                cite(r), esc(r.get("problem_class", "")), esc(method),
                esc(bl_disp),
                rub(r.get("rubric_B")), rub(r.get("rubric_E")), rub(r.get("rubric_D")),
                esc(str(r.get("headline_result", "")).strip())]) + " \\\\")
        write_tex(f"table{idx}_layer{lay[-1]}",
                  header + "\n".join(rows)
                  + "\n\\end{longtable}\n\\end{footnotesize}\n")


# --------------------------------- Table 6: research-agenda matrix
def table6_agenda():
    f = AN / "gap_matrix_inputs.json"
    scaffold = CORPUS / "table6_agenda.csv"
    if not scaffold.exists():
        with scaffold.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["open_problem", "L1", "L2", "L3", "what_evidence_would_settle_it"])
            for prob in ["Open benchmark suite", "Realistic constraint families",
                         "Data and sim-to-real", "Human-in-the-loop / explainability"]:
                w.writerow([prob, "", "", "", ""])
        print(f"  scaffolded {scaffold.name} -- fill (agenda)")
        return
    df = pd.read_csv(scaffold)
    header = ("\\begin{table}[!htb]\n\\centering\n\\caption{Research-agenda "
              "matrix: open problems by layer and the evidence that would "
              "resolve each. A check marks a plank of primary relevance to "
              "the layer (L1, project scheduling; L2, industrialized construction; "
              "L3, infrastructure/built-asset maintenance); $\\sim$ marks partial or secondary "
              "relevance. "
              "Abbreviations: CMMS, computerized maintenance management "
              "system; ERP, enterprise resource planning.}\n"
              "\\label{tab:agenda}\n\\small\n"
              "\\renewcommand{\\arraystretch}{1.3}\n"
              "\\begin{tabular}{@{}>{\\raggedright\\arraybackslash}p{4.2cm}ccc"
              ">{\\raggedright\\arraybackslash}p{6.4cm}@{}}\n\\toprule\n"
              "Open problem & L1 & L2 & L3 & What evidence would settle it \\\\\n\\midrule\n")
    rows = []
    for _, r in df.iterrows():
        rows.append(" & ".join(esc(x) for x in [
            r["open_problem"], r["L1"], r["L2"], r["L3"],
            r["what_evidence_would_settle_it"]]) + " \\\\")
    write_tex("table6_agenda", header + "\n".join(rows)
              + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")


def main():
    table1_prior_reviews()
    table2_constraints()
    tables_layers()
    table6_agenda()
    table_exemplars()
    table_pilot_field()
    print("tables.py done")


def table_pilot_field():
    """Supplementary Table S4: every pilot- or field-deployed study, its
    strongest comparator, and the nature of its operational evaluation. This
    is the study-level backing for the central empty-cell finding (no deployed
    study faced a strong baseline), matched exactly to the wording of that
    claim (deployment level, not data realism)."""
    csv_path = AN / "pilot_field_studies.csv"
    if not csv_path.exists():
        print("  table S4 skipped (no pilot_field_studies.csv)")
        return
    df = pd.read_csv(csv_path)
    CLS_ORDER = ["exact-CP-MILP", "metaheuristic", "other-DRL", "tuned-rules",
                 "multiple-PDRs", "human-planner", "single-untuned-PDR",
                 "random", "other", "none", "NR"]
    CLS_LABEL = {"exact-CP-MILP": "exact solver", "metaheuristic": "metaheuristic",
                 "other-DRL": "prior learned method", "tuned-rules": "tuned rules",
                 "multiple-PDRs": "multiple PDRs", "human-planner": "human planner",
                 "single-untuned-PDR": "single untuned PDR", "random": "random",
                 "other": "other (non-learning system)", "none": "none", "NR": "not reported"}

    def strongest(bl):
        toks = [t.strip() for t in str(bl).split("|") if t and t != "nan"]
        for c in CLS_ORDER:
            if c in toks:
                return CLS_LABEL[c]
        return "not reported"
    # evaluation nature, each phrase traceable to the study's coded headline
    NATURE = {
        "C0065": "autonomous live adjustments, two real modular projects",
        "C0882": "offline evaluation on one real photovoltaic project",
        "C0946": "field test on a real urban-rail project",
        "C1277": "industrial proof of concept, building portfolio",
        "C1321": "field trial on a real residential complex (advisory)",
        "S0228": "field, human-in-the-loop crew allocation on one mid-rise",
    }

    def sc(v):
        v = pd.to_numeric(v, errors="coerce")
        return "--" if pd.isna(v) or v < 0 else str(int(v))
    df = df.sort_values(["deployment_level", "layer", "id"])
    header = ("\\begin{footnotesize}\n\\setlength{\\tabcolsep}{5pt}\n"
              "\\renewcommand{\\arraystretch}{1.25}\n"
              "\\begin{longtable}{@{}llll cc >{\\raggedright\\arraybackslash}p{5.2cm}@{}}\n"
              "\\caption{All pilot- and field-deployed studies in the corpus, "
              "with the strongest comparator each was evaluated against and the "
              "nature of its operational evaluation. Baseline strength (B) and "
              "data realism (D) are on a 0--3 scale; a dash marks a dimension "
              "not assessable from the available text. No deployed study "
              "reaches the strong-baseline tier (B\\,$\\geq$\\,2), the "
              "study-level basis for the empty-cell finding (Figure~S2).}"
              "\\label{tab:pilotfield}\\\\\n\\toprule\n"
              "Study & Layer & Deployment & Strongest comparator & B & D & "
              "Evaluation nature \\\\\n\\midrule\n\\endfirsthead\n"
              "\\toprule\nStudy & Layer & Deployment & Strongest comparator & B "
              "& D & Evaluation nature \\\\\n\\midrule\n\\endhead\n"
              "\\bottomrule\n\\endlastfoot\n")
    rows = []
    for _, r in df.iterrows():
        rows.append(" & ".join([
            "\\citet{%s}" % r["id"], str(r["layer"]),
            str(r["deployment_level"]), esc(strongest(r["baselines"])),
            sc(r["rubric_B"]), sc(r["rubric_D"]),
            esc(NATURE.get(r["id"], "operational evaluation"))]) + " \\\\")
    (TDIR / "table_pilot_field.tex").write_text(
        header + "\n".join(rows) + "\n\\end{longtable}\n\\end{footnotesize}\n")
    print("wrote tables/table_pilot_field.tex (%d rows)" % len(rows))




def table_exemplars():
    """Compact main-text exemplar table (full per-study records are released
    and appear as Supplementary Tables S1-S3): every study at the top tier of
    any rubric dimension, plus every pilot- or field-deployed study."""
    df = pd.read_excel(CORPUS / "corpus_coded.xlsx")
    df = df[df["layer"].isin(["L1", "L2", "L3"])].copy()
    for c in ("rubric_B", "rubric_E", "rubric_D"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    sel = df[(df["rubric_B"] == 3) | (df["rubric_E"] == 3) | (df["rubric_D"] == 3)
             | (df["deployment_level"].isin(["pilot", "field"]))].copy()

    def why(r):
        # plain text (no math): the cell passes through esc(), which would
        # print literal dollar signs
        tags = []
        if r["rubric_B"] == 3: tags.append("B = 3")
        if r["rubric_E"] == 3: tags.append("E = 3")
        if r["rubric_D"] == 3: tags.append("D = 3")
        if r["deployment_level"] in ("pilot", "field"):
            tags.append(str(r["deployment_level"]))
        return "; ".join(tags)

    def score(v):
        return "--" if pd.isna(v) or v < 0 else str(int(v))

    sel["why"] = sel.apply(why, axis=1)
    sel = sel.sort_values(["layer", "id"])
    header = ("\\begin{table}[!htb]\n\\centering\n\\caption{Exemplar studies: "
              "every study that reaches the top tier of a rubric dimension "
              "(baseline strength B, evaluation rigor E, or data realism D, "
              "each 0--3) or reports a pilot or field deployment. A dash marks "
              "a dimension not assessable from the available text. Layers: L1, "
              "project scheduling; L2, industrialized construction; L3, "
              "infrastructure/built-asset maintenance. The full per-study records for all "
              "\\nCorpus\\ studies are given in Supplementary Tables S1--S3 "
              "and in the released database.}\n\\label{tab:exemplars}\n\\small\n"
              "\\renewcommand{\\arraystretch}{1.15}\n"
              "\\begin{tabular}{@{}llp{2.6cm}p{2.9cm}cccp{2.3cm}@{}}\n\\toprule\n"
              "Study & Layer & Problem class & Strongest comparator class & "
              "B & E & D & Why listed \\\\\n\\midrule\n")
    # the strongest comparator CLASS by hierarchy (exact > metaheuristic >
    # prior learned > tuned rules > multiple PDRs > human > single PDR >
    # random/other/none), not merely the first-listed baseline
    CLS_ORDER = ["exact-CP-MILP", "metaheuristic", "other-DRL", "tuned-rules",
                 "multiple-PDRs", "human-planner", "single-untuned-PDR",
                 "random", "other", "none", "NR"]
    CLS_LABEL = {"exact-CP-MILP": "exact solver",
                 "metaheuristic": "metaheuristic",
                 "other-DRL": "prior learned method",
                 "tuned-rules": "tuned rules",
                 "multiple-PDRs": "multiple PDRs",
                 "human-planner": "human planner",
                 "single-untuned-PDR": "single untuned PDR",
                 "random": "random", "other": "other", "none": "none",
                 "NR": "NR"}

    def strongest_class(bl):
        toks = [t.strip() for t in str(bl).split("|") if t and t != "nan"]
        for c in CLS_ORDER:
            if c in toks:
                return CLS_LABEL[c]
        return "--"

    rows = []
    for _, r in sel.iterrows():
        strongest = (strongest_class(r["baselines"])
                     if pd.notna(r["baselines"]) else "--")
        rows.append(" & ".join([
            "\\citet{%s}" % r["id"], str(r["layer"]),
            esc(str(r["problem_class"])), esc(strongest),
            score(r["rubric_B"]), score(r["rubric_E"]), score(r["rubric_D"]),
            esc(r["why"])]) + " \\\\")
    footer = "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    (TDIR / "table_exemplars.tex").write_text(header + "\n".join(rows) + footer)
    print("wrote tables/table_exemplars.tex (%d rows)" % len(rows))


if __name__ == "__main__":
    main()
