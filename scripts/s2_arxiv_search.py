#!/usr/bin/env python
"""Secondary retrieval: Semantic Scholar bulk search + arXiv API.

Same discipline as openalex_search.py: cache every response, log every query
verbatim with counts, append candidates to per-source JSONL ledgers.
S2 etiquette: unauthenticated shared pool, ~1 req/s with backoff on 429.
arXiv etiquette: 3 s between requests.
"""
import hashlib
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "search_log.md"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PaperR-review-retrieval (mailto:ziheng.zhang@singaporetech.edu.sg)"})

S2_CACHE = ROOT / "cache" / "s2"
S2_CACHE.mkdir(parents=True, exist_ok=True)
AX_CACHE = ROOT / "cache" / "arxiv"
AX_CACHE.mkdir(parents=True, exist_ok=True)
S2_OUT = ROOT / "candidates_s2.jsonl"
AX_OUT = ROOT / "candidates_arxiv.jsonl"

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
S2_FIELDS = ("title,year,abstract,venue,publicationVenue,externalIds,"
             "citationCount,authors,publicationTypes,publicationDate")

M_S2 = ('("reinforcement learning" | "graph neural network" | "graph attention" | '
        '"neural combinatorial optimization" | "learned dispatching" | '
        '"policy gradient" | "Q-learning" | "deep Q" | "actor-critic" | '
        '"imitation learning" | "learning-based" | "large language model")')
S_S2 = ('(scheduling | dispatching | sequencing | "resource-constrained" | '
        '"work order" | "job shop" | flowshop | "flow shop" | RCPSP)')

S2_QUERIES = [
    ("S2-L1", "L1", f'{M_S2} + {S_S2} + construction + (project | site | crane | earthmoving | contractor)'),
    ("S2-L2", "L2", f'{M_S2} + {S_S2} + (prefabricated | prefabrication | "modular construction" | '
                    '"off-site construction" | precast | "modular integrated construction" | PPVC)'),
    ("S2-L3", "L3", f'{M_S2} + {S_S2} + ("facility management" | "facilities management" | '
                    '"building maintenance" | "maintenance work order" | CMMS | '
                    '"technician scheduling" | "maintenance scheduling" | "maintenance planning") + '
                    '(building | facility | infrastructure | bridge | campus)'),
]

AX_QUERIES = [
    ("AX-domain", "DOMAIN",
     'abs:"reinforcement learning" AND (abs:scheduling OR abs:dispatching OR abs:sequencing) '
     'AND (abs:construction OR abs:prefabricated OR abs:precast OR abs:"modular construction" '
     'OR abs:"building maintenance" OR abs:"facility management" OR abs:"work order")'),
    ("AX-methods", "METHODS",
     '(abs:"job shop" OR abs:RCPSP OR abs:"project scheduling") AND '
     '(abs:"reinforcement learning" OR abs:"graph neural network")'),
]


def s2_get(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    f = S2_CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(8):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code == 200:
                f.write_text(r.text)
                time.sleep(1.1)
                return r.json()
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"S2 HTTP {r.status_code}: {url[:200]}")
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"S2 failed after retries: {url[:200]}")


def run_s2(qid, tag, query, results):
    params = {"query": query, "fields": S2_FIELDS, "year": "2015-"}
    token, total, fetched = None, None, 0
    for _ in range(12):
        p = dict(params)
        if token:
            p["token"] = token
        url = S2_BASE + "?" + urllib.parse.urlencode(p)
        data = s2_get(url)
        if total is None:
            total = data.get("total")
        for w in data.get("data") or []:
            ext = w.get("externalIds") or {}
            rec = {
                "s2_id": w.get("paperId"),
                "doi": (ext.get("DOI") or "").lower() or None,
                "arxiv_id": ext.get("ArXiv"),
                "title": w.get("title"),
                "year": w.get("year"),
                "date": w.get("publicationDate"),
                "venue": w.get("venue") or (w.get("publicationVenue") or {}).get("name"),
                "authors": [a.get("name") for a in (w.get("authors") or [])][:20],
                "cited_by_count": w.get("citationCount"),
                "abstract": w.get("abstract"),
                "queries": [qid],
                "layer_hint": tag,
                "source_api": "s2",
            }
            k = rec["s2_id"]
            if k in results:
                if qid not in results[k]["queries"]:
                    results[k]["queries"].append(qid)
            else:
                results[k] = rec
            fetched += 1
        token = data.get("token")
        if not token:
            break
    return total, fetched


def ax_get(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    f = AX_CACHE / f"{key}.xml"
    if f.exists():
        return f.read_text()
    for attempt in range(5):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code == 200:
                f.write_text(r.text)
                time.sleep(3.1)
                return r.text
            time.sleep(5 * (attempt + 1))
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"arXiv failed: {url[:200]}")


NS = {"a": "http://www.w3.org/2005/Atom", "o": "http://a9.com/-/spec/opensearch/1.1/"}


def run_arxiv(qid, tag, query, results):
    total, fetched = None, 0
    for start in range(0, 900, 300):
        params = {"search_query": query, "start": start, "max_results": 300,
                  "sortBy": "submittedDate", "sortOrder": "descending"}
        url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        xml = ax_get(url)
        root = ET.fromstring(xml)
        if total is None:
            total = int(root.findtext("o:totalResults", "0", NS))
        entries = root.findall("a:entry", NS)
        for e in entries:
            aid = e.findtext("a:id", "", NS).rsplit("/abs/", 1)[-1]
            year = int(e.findtext("a:published", "0000", NS)[:4])
            if year < 2015:
                continue
            rec = {
                "arxiv_id": aid,
                "doi": (e.findtext("{http://arxiv.org/schemas/atom}doi", "", NS) or None),
                "title": " ".join((e.findtext("a:title", "", NS) or "").split()),
                "year": year,
                "date": e.findtext("a:published", "", NS)[:10],
                "venue": "arXiv",
                "authors": [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)][:20],
                "abstract": " ".join((e.findtext("a:summary", "", NS) or "").split()),
                "queries": [qid],
                "layer_hint": tag,
                "is_preprint": 1,
                "source_api": "arxiv",
            }
            k = rec["arxiv_id"]
            if k in results:
                if qid not in results[k]["queries"]:
                    results[k]["queries"].append(qid)
            else:
                results[k] = rec
            fetched += 1
        if len(entries) < 300:
            break
    return total, fetched


def main():
    lines = [f"\n## Semantic Scholar bulk search (executed {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n",
             "Endpoint: /graph/v1/paper/search/bulk, year=2015-.\n"]
    s2_results = {}
    for qid, tag, q in S2_QUERIES:
        total, fetched = run_s2(qid, tag, q, s2_results)
        line = f"- **{qid}**: `{q}` -> {total} hits, {fetched} fetched"
        lines.append(line)
        print(line[:150], flush=True)
    with S2_OUT.open("w") as fh:
        for rec in s2_results.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lines.append(f"\n**S2 union: {len(s2_results)} unique works** -> `candidates_s2.jsonl`\n")

    lines.append(f"\n## arXiv API search (executed {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n")
    ax_results = {}
    for qid, tag, q in AX_QUERIES:
        total, fetched = run_arxiv(qid, tag, q, ax_results)
        line = f"- **{qid}**: `{q}` -> {total} hits, {fetched} fetched (cap 900, 2015+)"
        lines.append(line)
        print(line[:150], flush=True)
    with AX_OUT.open("w") as fh:
        for rec in ax_results.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lines.append(f"\n**arXiv union: {len(ax_results)} unique works** -> `candidates_arxiv.jsonl`\n")

    with LOG.open("a") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"DONE: S2={len(s2_results)}, arXiv={len(ax_results)}")


if __name__ == "__main__":
    main()
