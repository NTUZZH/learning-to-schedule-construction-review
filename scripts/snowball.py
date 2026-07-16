#!/usr/bin/env python
"""Snowballing via Semantic Scholar Graph API.

Iteration seeds come from --seeds argument:
  it1  = verified prior reviews + domain seeds (references_verified.csv)
  it2+ = all Pass-2 included domain studies (corpus file)
Backward (references) + forward (citations) of every seed, cached, polite.
Candidates are kept when they pass a generous keyword pre-net (they still go
through the normal Pass-1 screening rules afterwards); everything is logged.
"""
import argparse
import csv
import hashlib
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache" / "s2_snowball"
CACHE.mkdir(parents=True, exist_ok=True)
LOG = ROOT / "search_log.md"
S = requests.Session()
S.headers.update({"User-Agent": "PaperR-snowball (mailto:ziheng.zhang@singaporetech.edu.sg)"})
FIELDS = ("title,year,abstract,venue,externalIds,citationCount,authors,"
          "publicationDate")

LEARN = re.compile(r"reinforcement learning|deep q|q.learning|policy gradient|"
                   r"actor.critic|graph neural|graph attention|imitation learning|"
                   r"neural combinatorial|learning.based|learned dispatch|"
                   r"multi.agent|large language model|deep learning", re.I)
DOMAIN = re.compile(r"construction|prefabricat|precast|modular|off.?site|"
                    r"crane|earthmov|building|facilit|maintenance|work.order|"
                    r"technician|cmms|infrastructure|bridge|pipeline|campus|"
                    r"asset management|rcpsp|project schedul", re.I)
SCHED = re.compile(r"schedul|dispatch|sequenc|assignment|allocation|job.shop|"
                   r"flow.?shop|work.order|planning", re.I)


def s2get(url):
    key = hashlib.sha256(url.encode()).hexdigest()[:24]
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(8):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200:
                f.write_text(r.text)
                time.sleep(1.2)
                return r.json()
            if r.status_code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    return None


def harvest(pid, direction):
    """direction: 'references' or 'citations'."""
    out, offset = [], 0
    while True:
        url = (f"https://api.semanticscholar.org/graph/v1/paper/{pid}/"
               f"{direction}?fields={FIELDS}&limit=500&offset={offset}")
        data = s2get(url)
        if not data:
            break
        items = data.get("data") or []
        for it in items:
            w = it.get("citedPaper") or it.get("citingPaper") or {}
            if w.get("paperId"):
                out.append(w)
        if data.get("next") is None or not items:
            break
        offset = data["next"]
        if offset >= 3000:
            break
    return out


def keep(w):
    text = " ".join(filter(None, [w.get("title"), w.get("abstract") or ""]))
    if not text:
        return False
    year = w.get("year") or 0
    if year and year < 2010:
        return False
    return bool(SCHED.search(text) and (LEARN.search(text) or DOMAIN.search(text)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iteration", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    seeds = []
    if args.iteration == "it1":
        for row in csv.DictReader((ROOT.parent / "corpus" / "references_verified.csv").open()):
            if row["status"] != "verified":
                continue
            if row["doi"]:
                seeds.append(("DOI:" + row["doi"], row["ref_id"]))
            elif row["arxiv_id"]:
                seeds.append(("ARXIV:" + row["arxiv_id"], row["ref_id"]))
    else:
        seed_file = ROOT / f"snowball_seeds_{args.iteration}.json"
        for pid, rid in json.loads(seed_file.read_text()):
            seeds.append((pid, rid))

    found, per_seed = {}, []
    for pid, rid in seeds:
        refs = harvest(pid, "references")
        cits = harvest(pid, "citations")
        kept = 0
        for w in refs + cits:
            if not keep(w):
                continue
            k = w["paperId"]
            kept += 1
            if k not in found:
                ext = w.get("externalIds") or {}
                found[k] = {
                    "s2_id": k,
                    "doi": (ext.get("DOI") or "").lower() or None,
                    "arxiv_id": ext.get("ArXiv"),
                    "title": w.get("title"), "year": w.get("year"),
                    "date": w.get("publicationDate"),
                    "venue": w.get("venue"),
                    "authors": [a.get("name") for a in (w.get("authors") or [])][:20],
                    "cited_by_count": w.get("citationCount"),
                    "abstract": w.get("abstract"),
                    "queries": [f"SB-{args.iteration}:{rid}"],
                    "layer_hint": "SNOWBALL", "source_api": "s2",
                }
            else:
                tag = f"SB-{args.iteration}:{rid}"
                if tag not in found[k]["queries"]:
                    found[k]["queries"].append(tag)
        per_seed.append((rid, len(refs), len(cits), kept))
        print(f"{rid:28s} refs={len(refs):4d} cits={len(cits):4d} kept={kept:4d}", flush=True)

    with (ROOT / args.out).open("w") as fh:
        for rec in found.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with LOG.open("a") as fh:
        fh.write(f"\n## Snowballing {args.iteration} (executed "
                 f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())})\n\n")
        fh.write("Backward+forward via S2 /references and /citations, "
                 "keyword pre-net (SCHED AND (LEARN OR DOMAIN)), year>=2010.\n\n")
        for rid, nr, nc, nk in per_seed:
            fh.write(f"- {rid}: {nr} refs, {nc} cits, {nk} kept\n")
        fh.write(f"\n**{args.iteration} union: {len(found)} unique pre-net "
                 f"candidates** -> `{args.out}`\n")
    print(f"DONE: {len(found)} unique -> {args.out}")


if __name__ == "__main__":
    main()
