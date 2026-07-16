# Learning to Schedule in Construction — Coded Evidence Base

Data and analysis outputs accompanying the manuscript:

> **Learning to schedule in construction and built-environment operations: A systematic critical review of deep reinforcement learning, graph neural networks, and multi-agent approaches.**
> Ziheng Zhang, Tzu Pei Ku Chia, Wei Zhang.
> Companion data and code repository for a manuscript prepared for submission to *Automation in Construction*.

The review systematically codes the literature on learned (deep reinforcement
learning, graph neural network, multi-agent, imitation, and language-model)
scheduling policies across three application layers: project-level
construction scheduling (L1), industrialized construction (L2), and
built-asset and civil-infrastructure maintenance scheduling (L3). Each study
is scored on three ordinal 0–3 rubrics: baseline strength (B), evaluation
rigor (E), and data realism (D).

## Contents

### `data/`
| File | Description |
|---|---|
| `search_log.md` | Every executed database query verbatim, with API parameters, harvest dates (7-8 July 2026), and per-query result counts. |
| `prisma_ledger.json` | The per-stage retrieval ledger behind the PRISMA figure: identification, deduplication, screening, full-text, and inclusion counts, including the duplicate-report consolidation map. |
| `corpus_coded.xlsx` | The coded study database: 127 included domain studies (85 excluded records, with PRISMA reason codes, on the domain_excluded sheet; the two reports-not-retrieved records are among them) and 60 methods-track studies in a 39-field schema (see the `data_dictionary` sheet), including per-study B/E/D rubric scores and the PRISMA stage counts (`prisma` sheet). |
| `references.csv` | Bibliographic registry of the corpus and all cited works (author, year, title, venue, DOI / arXiv id). |
| `reliability_report.json` | Inter-rater reliability for the dual-coded 20% subsample: ordinal Krippendorff's alpha, exact agreement, and within-one agreement per rubric dimension. |
| `reliability_gain_set.json` | Blind dual-coding agreement for the full numeric-gain set (48 studies, seven fields), with the adjudication summary. |
| `second_coding_gain_set.json` | The second coder's blind codings for the gain set, as collected (pre-adjudication). |
| `screening_audit.json` | Independent audits of the screening pipeline: a blind re-screen of all 83 full-text-stage exclusions then on the ledger (none overturned), an independent dual screening of a 200-record sample of the title/abstract decisions (kappa 0.76-0.83), an earlier 15-record exclusion audit (two reinstatements), a recall audit of the snowballing keyword pre-net, dual coding of the remaining top-tier and deployed studies, the upgrade of one title-only record from its retrieved abstract (layer reassigned L1 to L2), and the reclassification of the two remaining title-only records as PRISMA reports-not-retrieved exclusions. |

### `scripts/`
The programs that derived everything in `results/` from `data/corpus_coded.xlsx`
(analysis, figures, tables, reliability statistics) and the retrieval programs
that executed the logged searches. See `RUNME.md` for the exact reproduction
steps and `requirements.txt` for the environment.

### `results/`
Aggregated results computed from the coded database: the exact inputs behind
every figure in the manuscript. File prefixes are internal identifiers, not
print figure numbers: `fig3_*` -> Figure 1, `fig2_*` -> Figure 3, `fig5_*` ->
Figure 4, `fig4_timeline.json` -> Figure 5, `fig6_*` -> Figure 7 (evidence audit); Figure 2
(the PRISMA flow) is generated from `data/prisma_ledger.json`, and the
three-layer orientation map (Figure 6) draws its per-layer study counts from
`fig2_pubs_per_year_layer.csv`. `pilot_field_studies.csv` enumerates every pilot- or field-deployed study (the study-level basis for the empty-cell finding), and `b_by_deployment.csv` is the baseline-strength by deployment-level cross-tabulation. `gain_by_comparator_class.csv` holds the
comparator-class sensitivity behind Supplementary Figure S1: reported gains
stratified by the strongest comparator class in each study's baseline suite
(single rule/manual/none, multiple or tuned rules, prior learned method,
metaheuristic, exact solver).

## Citation

If you use this database, please cite the manuscript above.

## Contact

Ziheng Zhang — ziheng.zhang@singaporetech.edu.sg
