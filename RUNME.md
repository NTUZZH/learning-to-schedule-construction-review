# Reproducing the analysis outputs and figures

The scripts in `scripts/` are the exact programs that derived `results/`
and the manuscript figures and tables from the coded database. They use a
project-relative layout, so arrange the tree once and run from the
repository root:

```bash
pip install -r requirements.txt
mkdir -p corpus analysis
cp data/corpus_coded.xlsx corpus/
cp scripts/analysis.py analysis/
python analysis/analysis.py     # -> analysis/outputs/*.csv|json (compare with results/)
                                #    and manuscript/macros.tex (every corpus-derived
                                #    number used in the paper)
python scripts/figures.py       # -> scripts/*.pdf|png (Figures 1-7 and S1)
python scripts/tables.py        # -> manuscript/tables/*.tex (Tables 1-3 and S1-S3)
```

Offline reproducibility: `analysis.py`, `figures.py`, and `tables.py` run
entirely from `data/corpus_coded.xlsx`; regenerated files in
`analysis/outputs/` should match `results/` byte-for-byte up to floating-point
formatting. The bootstrap and resampling seeds are fixed in the scripts.

Reference scripts (need live web APIs, so they re-execute the logged search
protocol rather than reproduce it offline): `openalex_search.py`,
`s2_arxiv_search.py`, `snowball.py`, `merge_dedupe.py`. The verbatim query
strings and harvest dates they log are in `data/search_log.md`.
`reliability.py` implements the ordinal Krippendorff alpha and bootstrap
intervals reported in `data/reliability_report.json`.
