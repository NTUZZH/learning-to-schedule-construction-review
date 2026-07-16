#!/usr/bin/env python
"""Primary retrieval: OpenAlex boolean title-abstract searches.

Every executed query is logged
verbatim with result counts to retrieval/search_log.md; every API response
is cached to retrieval/cache/openalex/. Candidates append to
retrieval/candidates_openalex.jsonl (one JSON object per work, tagged with
the query ids that retrieved it).
"""
import hashlib
import json
import time
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache" / "openalex"
CACHE.mkdir(parents=True, exist_ok=True)
OUT_JSONL = ROOT / "candidates_openalex.jsonl"
LOG = ROOT / "search_log.md"
MAILTO = "ziheng.zhang@singaporetech.edu.sg"
BASE = "https://api.openalex.org/works"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"PaperR-review-retrieval (mailto:{MAILTO})"})

# ---------------------------------------------------------------- query plan
M_CORE = ('"reinforcement learning" OR "graph neural network" OR '
          '"graph attention" OR "neural combinatorial optimization" OR '
          '"learn to dispatch" OR "learned dispatching" OR "policy gradient" '
          'OR "Q-learning" OR "deep Q" OR "actor-critic" OR "imitation learning"')
M_SOFT = '"learning-based" OR "large language model" OR "machine learning"'
S_BLOCK = ('scheduling OR schedule OR dispatching OR sequencing OR '
           '"resource allocation" OR "resource-constrained" OR "work order" OR '
           '"job shop" OR flowshop OR "flow shop" OR RCPSP')
S_TIGHT = ('scheduling OR dispatching OR sequencing OR "resource-constrained" '
           'OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP')
D_L1 = ('construction AND (project OR site OR crane OR earthmoving OR '
        '"lift planning" OR contractor OR "site logistics")')
D_L2 = ('prefabricated OR prefabrication OR "modular construction" OR '
        '"off-site construction" OR "offsite construction" OR precast OR '
        '"modular integrated construction" OR PPVC OR "volumetric construction"')
D_L3 = ('"facility management" OR "facilities management" OR '
        '"building maintenance" OR "maintenance work order" OR '
        '"work order scheduling" OR CMMS OR "technician scheduling" OR '
        '"technician routing" OR "maintenance scheduling" OR '
        '"maintenance planning"')
D_L3_GUARD = 'building OR facility OR facilities OR infrastructure OR bridge OR campus'
M_METHODS = ('"job shop" OR "flexible job shop" OR RCPSP OR '
             '"project scheduling" OR "resource-constrained project"')

QUERIES = [
    # (qid, layer-tag, boolean search string, filters dict, max_pages)
    ("Q1-L1-core", "L1", f"({M_CORE}) AND ({S_BLOCK}) AND ({D_L1})", {}, 15),
    ("Q2-L2-core", "L2", f"({M_CORE}) AND ({S_BLOCK}) AND ({D_L2})", {}, 15),
    ("Q3-L3-core", "L3", f"({M_CORE}) AND ({S_TIGHT}) AND ({D_L3}) AND ({D_L3_GUARD})", {}, 15),
    ("Q4-L1-soft", "L1", f"({M_SOFT}) AND ({S_TIGHT}) AND ({D_L1})", {}, 15),
    ("Q5-L2-soft", "L2", f"({M_SOFT}) AND ({S_TIGHT}) AND ({D_L2})", {}, 15),
    ("Q6-L3-soft", "L3", f"({M_SOFT}) AND ({S_TIGHT}) AND ({D_L3}) AND ({D_L3_GUARD})", {}, 15),
    # methods-corpus track: no domain block, top-cited slice only (cap per 5.4)
    ("Q7-methods", "METHODS", f"({M_CORE}) AND ({M_METHODS})",
     {"sort": "cited_by_count:desc"}, 3),
]

VENUE_SWEEPS = [
    # (qid, issn, extra domain guard or None)
    ("V1-AutCon", "0926-5805", None),
    ("V2-AEI", "1474-0346", None),
    ("V3-JCEM", "0733-9364", None),
    ("V4-JME", "0742-597X", None),
    ("V5-JCCE", "0887-3801", None),
    ("V6-ECAM", "0969-9988", None),
    ("V7-CAIE", "0360-8352", D_L2),
    ("V8-ITcon", "1874-4753", None),
]
V_METHOD = ('"reinforcement learning" OR "graph neural network" OR '
            '"deep learning" OR "learning-based" OR "Q-learning" OR '
            '"multi-agent" OR "imitation learning" OR "large language model"')
V_SCHED = ('scheduling OR dispatching OR sequencing OR "work order" OR '
           '"resource allocation" OR "resource-constrained"')


def cache_get(url):
    """GET with on-disk cache, retries, and polite pacing."""
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(5):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code == 200:
                f.write_text(r.text)
                time.sleep(0.15)
                return r.json()
            if r.status_code in (429, 500, 502, 503):
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {r.status_code}: {url[:200]}")
        except requests.RequestException as e:
            time.sleep(3 * (attempt + 1))
            err = e
    raise RuntimeError(f"failed after retries: {url[:200]}")


def abstract_from_inv(inv):
    if not inv:
        return None
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos)) if pos else None


def norm_work(w, qid):
    loc = w.get("primary_location") or {}
    src = loc.get("source") or {}
    return {
        "openalex_id": w["id"].rsplit("/", 1)[-1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": w.get("title"),
        "year": w.get("publication_year"),
        "date": w.get("publication_date"),
        "venue": src.get("display_name"),
        "venue_issn": src.get("issn_l"),
        "venue_type": src.get("type"),
        "work_type": w.get("type"),
        "is_retracted": w.get("is_retracted", False),
        "authors": [a.get("author", {}).get("display_name")
                    for a in (w.get("authorships") or [])][:20],
        "cited_by_count": w.get("cited_by_count"),
        "abstract": abstract_from_inv(w.get("abstract_inverted_index")),
        "queries": [qid],
        "source_api": "openalex",
    }


def run_query(qid, tag, search, extra, max_pages, results):
    filt = f"title_and_abstract.search:{search},from_publication_date:2015-01-01"
    params = {"filter": filt, "per-page": 200, "mailto": MAILTO}
    params.update(extra)
    cursor = "*"
    total = None
    fetched = 0
    for page in range(max_pages):
        params["cursor"] = cursor
        url = BASE + "?" + urllib.parse.urlencode(params)
        data = cache_get(url)
        if total is None:
            total = data["meta"]["count"]
        for w in data.get("results", []):
            if w.get("language") not in (None, "en"):
                continue
            rec = norm_work(w, qid)
            rec["layer_hint"] = tag
            key = rec["openalex_id"]
            if key in results:
                if qid not in results[key]["queries"]:
                    results[key]["queries"].append(qid)
            else:
                results[key] = rec
            fetched += 1
        cursor = data["meta"].get("next_cursor")
        if not cursor or not data.get("results"):
            break
    return total, fetched


def main():
    results = {}
    log_lines = ["\n## OpenAlex primary search (executed "
                 f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n",
                 "Filter template: `title_and_abstract.search:<QUERY>,"
                 "from_publication_date:2015-01-01`; per-page=200; "
                 "cursor paging; English or unknown language only.\n"]
    for qid, tag, search, extra, mp in QUERIES:
        total, fetched = run_query(qid, tag, search, extra, mp, results)
        line = (f"- **{qid}** (layer {tag}): `{search}` -> {total} hits, "
                f"{fetched} fetched (cap {mp} pages)")
        log_lines.append(line)
        print(line[:160], flush=True)

    log_lines.append("\n### Venue hand-search sweeps (2020-2026, method+scheduling terms)\n")
    for qid, issn, guard in VENUE_SWEEPS:
        search = f"({V_METHOD}) AND ({V_SCHED})"
        if guard:
            search += f" AND ({guard})"
        filt = (f"title_and_abstract.search:{search},"
                f"primary_location.source.issn:{issn},"
                f"from_publication_date:2020-01-01")
        params = {"filter": filt, "per-page": 200, "mailto": MAILTO, "cursor": "*"}
        total, fetched, cursor = None, 0, "*"
        for _ in range(5):
            params["cursor"] = cursor
            url = BASE + "?" + urllib.parse.urlencode(params)
            data = cache_get(url)
            if total is None:
                total = data["meta"]["count"]
            for w in data.get("results", []):
                if w.get("language") not in (None, "en"):
                    continue
                rec = norm_work(w, qid)
                rec["layer_hint"] = "VENUE"
                key = rec["openalex_id"]
                if key in results:
                    if qid not in results[key]["queries"]:
                        results[key]["queries"].append(qid)
                else:
                    results[key] = rec
                fetched += 1
            cursor = data["meta"].get("next_cursor")
            if not cursor or not data.get("results"):
                break
        line = f"- **{qid}** (ISSN {issn}): {total} hits, {fetched} fetched"
        log_lines.append(line)
        print(line, flush=True)

    with OUT_JSONL.open("w") as fh:
        for rec in results.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log_lines.append(f"\n**OpenAlex union: {len(results)} unique works** "
                     f"-> `candidates_openalex.jsonl`\n")
    with LOG.open("a") as fh:
        fh.write("\n".join(log_lines) + "\n")
    print(f"DONE: {len(results)} unique works")


if __name__ == "__main__":
    main()
