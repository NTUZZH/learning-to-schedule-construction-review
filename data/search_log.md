# Search Log — literature retrieval for the review

Every executed query is recorded verbatim with
result counts. Sources: OpenAlex (primary), Semantic Scholar (secondary +
snowballing), Crossref (verification), arXiv (preprints), venue hand-search
sweeps via OpenAlex ISSN filters, backward/forward snowballing to saturation.
Time window: 2015-01-01 onward (venue sweeps 2020-01-01 onward per Section 5.1).
All raw API responses cached under `retrieval/cache/`.

Query-plan notes (deviations from Section 5.2 literal text, with reasons):
- `prefabricat*` expanded manually (OpenAlex lacks truncation): prefabricated,
  prefabrication.
- Acronym `MiC` dropped as a standalone term (collides with "MIC"/microphone
  noise); covered by the phrase "modular integrated construction".
- `"deep reinforcement learning"`, `"multi-agent reinforcement learning"`
  subsumed by the phrase `"reinforcement learning"` in OpenAlex phrase search.
- L3 domain block guarded with (building OR facility OR facilities OR
  infrastructure OR bridge OR campus) to suppress manufacturing-plant
  maintenance noise; "asset management" folded into the guarded block.
- METHOD block split into M_CORE (specific method phrases) and M_SOFT
  ("learning-based", "large language model", "machine learning") so the soft
  terms' noise is traceable per query.

## OpenAlex primary search (executed 2026-07-07 18:47 UTC)

Filter template: `title_and_abstract.search:<QUERY>,from_publication_date:2015-01-01`; per-page=200; cursor paging; English or unknown language only.

- **Q1-L1-core** (layer L1): `("reinforcement learning" OR "graph neural network" OR "graph attention" OR "neural combinatorial optimization" OR "learn to dispatch" OR "learned dispatching" OR "policy gradient" OR "Q-learning" OR "deep Q" OR "actor-critic" OR "imitation learning") AND (scheduling OR schedule OR dispatching OR sequencing OR "resource allocation" OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND (construction AND (project OR site OR crane OR earthmoving OR "lift planning" OR contractor OR "site logistics"))` -> 164 hits, 163 fetched (cap 15 pages)
- **Q2-L2-core** (layer L2): `("reinforcement learning" OR "graph neural network" OR "graph attention" OR "neural combinatorial optimization" OR "learn to dispatch" OR "learned dispatching" OR "policy gradient" OR "Q-learning" OR "deep Q" OR "actor-critic" OR "imitation learning") AND (scheduling OR schedule OR dispatching OR sequencing OR "resource allocation" OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND (prefabricated OR prefabrication OR "modular construction" OR "off-site construction" OR "offsite construction" OR precast OR "modular integrated construction" OR PPVC OR "volumetric construction")` -> 40 hits, 40 fetched (cap 15 pages)
- **Q3-L3-core** (layer L3): `("reinforcement learning" OR "graph neural network" OR "graph attention" OR "neural combinatorial optimization" OR "learn to dispatch" OR "learned dispatching" OR "policy gradient" OR "Q-learning" OR "deep Q" OR "actor-critic" OR "imitation learning") AND (scheduling OR dispatching OR sequencing OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND ("facility management" OR "facilities management" OR "building maintenance" OR "maintenance work order" OR "work order scheduling" OR CMMS OR "technician scheduling" OR "technician routing" OR "maintenance scheduling" OR "maintenance planning") AND (building OR facility OR facilities OR infrastructure OR bridge OR campus)` -> 44 hits, 44 fetched (cap 15 pages)
- **Q4-L1-soft** (layer L1): `("learning-based" OR "large language model" OR "machine learning") AND (scheduling OR dispatching OR sequencing OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND (construction AND (project OR site OR crane OR earthmoving OR "lift planning" OR contractor OR "site logistics"))` -> 623 hits, 621 fetched (cap 15 pages)
- **Q5-L2-soft** (layer L2): `("learning-based" OR "large language model" OR "machine learning") AND (scheduling OR dispatching OR sequencing OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND (prefabricated OR prefabrication OR "modular construction" OR "off-site construction" OR "offsite construction" OR precast OR "modular integrated construction" OR PPVC OR "volumetric construction")` -> 41 hits, 41 fetched (cap 15 pages)
- **Q6-L3-soft** (layer L3): `("learning-based" OR "large language model" OR "machine learning") AND (scheduling OR dispatching OR sequencing OR "resource-constrained" OR "work order" OR "job shop" OR flowshop OR "flow shop" OR RCPSP) AND ("facility management" OR "facilities management" OR "building maintenance" OR "maintenance work order" OR "work order scheduling" OR CMMS OR "technician scheduling" OR "technician routing" OR "maintenance scheduling" OR "maintenance planning") AND (building OR facility OR facilities OR infrastructure OR bridge OR campus)` -> 305 hits, 302 fetched (cap 15 pages)
- **Q7-methods** (layer METHODS): `("reinforcement learning" OR "graph neural network" OR "graph attention" OR "neural combinatorial optimization" OR "learn to dispatch" OR "learned dispatching" OR "policy gradient" OR "Q-learning" OR "deep Q" OR "actor-critic" OR "imitation learning") AND ("job shop" OR "flexible job shop" OR RCPSP OR "project scheduling" OR "resource-constrained project")` -> 1115 hits, 598 fetched (cap 3 pages)

### Venue hand-search sweeps (2020-2026, method+scheduling terms)

- **V1-AutCon** (ISSN 0926-5805): 29 hits, 29 fetched
- **V2-AEI** (ISSN 1474-0346): 65 hits, 65 fetched
- **V3-JCEM** (ISSN 0733-9364): 6 hits, 6 fetched
- **V4-JME** (ISSN 0742-597X): 2 hits, 2 fetched
- **V5-JCCE** (ISSN 0887-3801): 2 hits, 2 fetched
- **V6-ECAM** (ISSN 0969-9988): 4 hits, 4 fetched
- **V7-CAIE** (ISSN 0360-8352): 4 hits, 4 fetched
- **V8-ITcon** (ISSN 1874-4753): 3 hits, 3 fetched

**OpenAlex union: 1756 unique works**


## Semantic Scholar bulk search (executed 2026-07-07 18:49 UTC)

Endpoint: /graph/v1/paper/search/bulk, year=2015-.

- **S2-L1**: `("reinforcement learning" | "graph neural network" | "graph attention" | "neural combinatorial optimization" | "learned dispatching" | "policy gradient" | "Q-learning" | "deep Q" | "actor-critic" | "imitation learning" | "learning-based" | "large language model") + (scheduling | dispatching | sequencing | "resource-constrained" | "work order" | "job shop" | flowshop | "flow shop" | RCPSP) + construction + (project | site | crane | earthmoving | contractor)` -> 112 hits, 112 fetched
- **S2-L2**: `("reinforcement learning" | "graph neural network" | "graph attention" | "neural combinatorial optimization" | "learned dispatching" | "policy gradient" | "Q-learning" | "deep Q" | "actor-critic" | "imitation learning" | "learning-based" | "large language model") + (scheduling | dispatching | sequencing | "resource-constrained" | "work order" | "job shop" | flowshop | "flow shop" | RCPSP) + (prefabricated | prefabrication | "modular construction" | "off-site construction" | precast | "modular integrated construction" | PPVC)` -> 23 hits, 23 fetched
- **S2-L3**: `("reinforcement learning" | "graph neural network" | "graph attention" | "neural combinatorial optimization" | "learned dispatching" | "policy gradient" | "Q-learning" | "deep Q" | "actor-critic" | "imitation learning" | "learning-based" | "large language model") + (scheduling | dispatching | sequencing | "resource-constrained" | "work order" | "job shop" | flowshop | "flow shop" | RCPSP) + ("facility management" | "facilities management" | "building maintenance" | "maintenance work order" | CMMS | "technician scheduling" | "maintenance scheduling" | "maintenance planning") + (building | facility | infrastructure | bridge | campus)` -> 43 hits, 43 fetched

**S2 union: 171 unique works**


## arXiv API search (executed 2026-07-07 18:49 UTC)

- **AX-domain**: `abs:"reinforcement learning" AND (abs:scheduling OR abs:dispatching OR abs:sequencing) AND (abs:construction OR abs:prefabricated OR abs:precast OR abs:"modular construction" OR abs:"building maintenance" OR abs:"facility management" OR abs:"work order")` -> 278 hits, 277 fetched (cap 900, 2015+)
- **AX-methods**: `(abs:"job shop" OR abs:RCPSP OR abs:"project scheduling") AND (abs:"reinforcement learning" OR abs:"graph neural network")` -> 66 hits, 66 fetched (cap 900, 2015+)

**arXiv union: 332 unique works**


## Snowballing it1 (executed 2026-07-07 19:11 UTC)

Backward+forward via S2 /references and /citations, keyword pre-net (SCHED AND (LEARN OR DOMAIN)), year>=2010.

- zhang2020l2d: 51 refs, 458 cits, 325 kept
- song2023fjsp: 46 refs, 365 cits, 297 kept
- wang2023daniel: 48 refs, 131 cits, 121 kept
- resched2026: 0 refs, 0 cits, 0 kept
- kool2019attention: 38 refs, 1625 cits, 485 kept
- bengio2021ml4co: 72 refs, 1822 cits, 370 kept
- mazyavkina2021rl4co: 147 refs, 795 cits, 233 kept
- hartmann2010rcpsp: 0 refs, 953 cits, 496 kept
- hartmann2022rcpsp: 229 refs, 253 cits, 299 kept
- peiris2023metaheuristics: 113 refs, 47 cits, 84 kept
- jcem2022rlcem: 0 refs, 34 cits, 10 kept
- autcon2023robotics: 108 refs, 167 cits, 35 kept
- js2025mlschedule: 54 refs, 1 cits, 15 kept
- jms2025drlsurvey: 146 refs, 2 cits, 90 kept
- lv2025jsspreview: 0 refs, 24 cits, 14 kept
- zhang2024resilient: 165 refs, 51 cits, 124 kept
- kayhan2023rlreview: 0 refs, 140 cits, 88 kept
- gnnjssp2024survey: 130 refs, 55 cits, 98 kept
- yao2024validaction: 48 refs, 34 cits, 44 kept
- rcim2023disruption: 0 refs, 46 cits, 33 kept
- autcon2022crane: 0 refs, 43 cits, 13 kept
- zhu2023tase: 0 refs, 57 cits, 20 kept
- asce2024crew: 0 refs, 2 cits, 0 kept
- hyun2021modular: 0 refs, 24 cits, 15 kept
- lee2019moduleGA: 0 refs, 35 cits, 18 kept
- chen2018bimfm: 0 refs, 220 cits, 37 kept
- andriotis2019dcmac: 102 refs, 208 cits, 72 kept
- andriotis2021inspection: 82 refs, 127 cits, 60 kept
- bukhsh2023pipes: 52 refs, 15 cits, 20 kept

**it1 union: 2595 unique pre-net candidates**

## Methods-corpus curation (cap 60)

Selected 60 entries: {'verified': 10, 'screening': 45, 'pool': 5}; pool families {'FJSP': 1, 'dispatch-JSSP': 1, 'RCPSP': 1, 'MARL': 1, 'neuralCO': 1}. Rule: verified seeds + screening methods_canon flags + round-robin top-cited per family.

## Snowballing it2 (executed 2026-07-08 04:18 UTC)

Backward+forward via S2 /references and /citations, keyword pre-net (SCHED AND (LEARN OR DOMAIN)), year>=2010.

- S0259: 0 refs, 77 cits, 22 kept
- C1616: 0 refs, 10 cits, 1 kept
- C0748: 0 refs, 0 cits, 0 kept
- S0178: 26 refs, 2 cits, 17 kept
- C0065: 0 refs, 1 cits, 0 kept
- C1671: 0 refs, 1 cits, 0 kept
- S0260: 0 refs, 61 cits, 14 kept
- S0196: 56 refs, 0 cits, 25 kept
- C0168: 32 refs, 0 cits, 12 kept
- C0032: 0 refs, 0 cits, 0 kept
- C0014: 0 refs, 0 cits, 0 kept
- C1232: 39 refs, 3 cits, 9 kept
- S0242: 55 refs, 0 cits, 9 kept
- C0264: 67 refs, 0 cits, 29 kept
- C0871: 0 refs, 1 cits, 1 kept
- C0464: 0 refs, 0 cits, 0 kept
- C0503: 0 refs, 0 cits, 0 kept
- C0082: 54 refs, 0 cits, 21 kept
- C1145: 0 refs, 0 cits, 0 kept
- C0061: 39 refs, 0 cits, 13 kept
- C0865: 0 refs, 3 cits, 2 kept
- S0087: 48 refs, 22 cits, 9 kept
- C1560: 62 refs, 4 cits, 10 kept
- S0284: 0 refs, 1 cits, 0 kept
- C1047: 48 refs, 34 cits, 44 kept
- C0774: 27 refs, 3 cits, 10 kept
- C0568: 0 refs, 0 cits, 0 kept
- C0352: 14 refs, 0 cits, 0 kept
- S0280: 0 refs, 52 cits, 10 kept
- C1267: 0 refs, 0 cits, 0 kept
- C0713: 2 refs, 0 cits, 0 kept
- C0088: 0 refs, 0 cits, 0 kept
- S0283: 42 refs, 8 cits, 8 kept
- C0659: 0 refs, 0 cits, 0 kept
- C1195: 15 refs, 2 cits, 5 kept
- C1181: 0 refs, 1 cits, 1 kept
- C0283: 0 refs, 0 cits, 0 kept
- C0575: 35 refs, 0 cits, 9 kept
- C0665: 0 refs, 0 cits, 0 kept
- C0408: 0 refs, 3 cits, 1 kept
- C0095: 0 refs, 1 cits, 0 kept
- C0823: 0 refs, 0 cits, 0 kept
- C0946: 35 refs, 2 cits, 4 kept
- C1610: 0 refs, 38 cits, 20 kept
- S0267: 0 refs, 0 cits, 0 kept
- C0018: 18 refs, 0 cits, 4 kept
- S0248: 74 refs, 24 cits, 17 kept
- S0229: 0 refs, 12 cits, 8 kept
- C0461: 0 refs, 2 cits, 1 kept
- C0966: 0 refs, 0 cits, 0 kept
- C1264: 0 refs, 1 cits, 0 kept
- C0813: 0 refs, 0 cits, 0 kept
- C0504: 0 refs, 1 cits, 1 kept
- C0654: 51 refs, 1 cits, 11 kept
- C1316: 0 refs, 0 cits, 0 kept
- C0028: 0 refs, 1 cits, 1 kept
- S0243: 128 refs, 0 cits, 25 kept
- S0270: 0 refs, 2 cits, 0 kept
- C0965: 0 refs, 0 cits, 0 kept
- C0229: 0 refs, 0 cits, 0 kept
- S0272: 0 refs, 19 cits, 3 kept
- C0798: 0 refs, 1 cits, 1 kept
- C0262: 0 refs, 0 cits, 0 kept
- C1660: 0 refs, 48 cits, 29 kept
- C0122: 0 refs, 0 cits, 0 kept
- S0179: 0 refs, 12 cits, 8 kept
- C1703: 87 refs, 48 cits, 47 kept
- C0230: 18 refs, 0 cits, 1 kept
- C0874: 0 refs, 1 cits, 0 kept
- S0194: 50 refs, 0 cits, 12 kept
- C0398: 37 refs, 9 cits, 9 kept
- C0006: 12 refs, 0 cits, 3 kept
- C1508: 0 refs, 49 cits, 10 kept
- C1347: 0 refs, 33 cits, 10 kept
- C1113: 0 refs, 7 cits, 4 kept
- C1280: 0 refs, 19 cits, 7 kept
- C0091: 63 refs, 0 cits, 44 kept
- C1283: 0 refs, 6 cits, 2 kept
- C1336: 0 refs, 65 cits, 35 kept
- C0714: 0 refs, 0 cits, 0 kept
- C0728: 0 refs, 4 cits, 1 kept
- C1704: 0 refs, 48 cits, 11 kept
- C0092: 0 refs, 0 cits, 0 kept
- C0270: 0 refs, 0 cits, 0 kept
- C0998: 0 refs, 2 cits, 2 kept
- C0206: 0 refs, 0 cits, 0 kept
- C1488: 0 refs, 0 cits, 0 kept
- C0215: 71 refs, 4 cits, 17 kept
- C0375: 0 refs, 0 cits, 0 kept
- S0266: 0 refs, 29 cits, 7 kept
- C0076: 0 refs, 0 cits, 0 kept
- C1571: 0 refs, 0 cits, 0 kept
- C0035: 0 refs, 0 cits, 0 kept
- C0882: 0 refs, 0 cits, 0 kept
- C0885: 0 refs, 0 cits, 0 kept
- C1081: 0 refs, 0 cits, 0 kept
- C1321: 0 refs, 0 cits, 0 kept
- C0831: 0 refs, 3 cits, 1 kept
- C0133: 0 refs, 0 cits, 0 kept
- C1753: 0 refs, 1 cits, 1 kept
- C1385: 0 refs, 17 cits, 11 kept
- C1675: 0 refs, 16 cits, 6 kept
- S0228: 17 refs, 1 cits, 4 kept
- C0797: 0 refs, 1 cits, 0 kept
- S0257: 47 refs, 31 cits, 14 kept
- C1655: 0 refs, 0 cits, 0 kept
- C0708: 1 refs, 2 cits, 1 kept
- C0637: 0 refs, 0 cits, 0 kept
- C0300: 15 refs, 0 cits, 4 kept
- S0265: 82 refs, 127 cits, 60 kept
- C0978: 0 refs, 48 cits, 22 kept
- S0258: 60 refs, 58 cits, 30 kept
- C0420: 0 refs, 3 cits, 2 kept
- C0730: 0 refs, 0 cits, 0 kept
- C0521: 30 refs, 4 cits, 6 kept
- C0027: 0 refs, 0 cits, 0 kept
- S0237: 0 refs, 2 cits, 0 kept
- C0912: 1 refs, 1 cits, 1 kept
- C1407: 16 refs, 3 cits, 3 kept
- C0509: 0 refs, 6 cits, 3 kept
- C1277: 0 refs, 0 cits, 0 kept
- C1265: 69 refs, 3 cits, 15 kept
- C0465: 0 refs, 0 cits, 0 kept
- C1338: 43 refs, 17 cits, 44 kept
- C0593: 0 refs, 0 cits, 0 kept
- S0253: 0 refs, 28 cits, 4 kept
- C0802: 0 refs, 5 cits, 2 kept
- C0261: 0 refs, 0 cits, 0 kept
- S0187: 0 refs, 0 cits, 0 kept
- S0254: 70 refs, 17 cits, 19 kept
- S0158: 33 refs, 0 cits, 3 kept
- C0930: 0 refs, 0 cits, 0 kept
- C0204: 0 refs, 0 cits, 0 kept

**it2 union: 663 unique pre-net candidates**

## Snowballing it3 (executed 2026-07-12 16:20 UTC)

Backward+forward via S2 /references and /citations, keyword pre-net (SCHED AND (LEARN OR DOMAIN)), year>=2010.

- T0036: 68 refs, 10 cits, 19 kept
- T0037: 31 refs, 20 cits, 4 kept
- T0025: 58 refs, 99 cits, 31 kept
- T0001: 0 refs, 0 cits, 0 kept
- T0031: 0 refs, 2 cits, 2 kept
- T0055: 0 refs, 0 cits, 0 kept
- T0032: 59 refs, 29 cits, 20 kept

**it3 union: 71 unique pre-net candidates**

## Snowballing iteration 3 (executed 2026-07-13, confirmatory)

Seeds: the 7 iteration-2 inclusions (T0001, T0025, T0031, T0032, T0036, T0037,
T0055), backward and forward via the Semantic Scholar Graph API, same
parameters as iterations 1-2.

- Returned: 71 unique records -> 55 new against all prior pools after
  cross-source deduplication.
- Screening (same two-pass scope test): **2 in-scope studies included**
  (T0056, robot-prefab assembly DRL, IEEE CASE 2021, missed by keyword search
  because neither title nor abstract contains a scheduling term the task
  clause matches; T0057, network-asset intervention-timing imitation, JCEM
  2022). Both fall within already-covered themes. The remaining 53 were out
  of scope (no learned scheduling component, transit operations, perception,
  robotics motion planning, generic LLM/robotics method papers) or fed the
  methods-track pool.
- Yield 2/130 = 1.5% with no new problem class, method family, or layer:
  the pre-specified stopping rule is met; the search stopped here.

## Closed-index coverage check: Scopus and Web of Science

After corpus assembly, the authors cross-validated the search on Scopus and
Web of Science (institutional access). Neither index surfaced an in-scope
study absent from the assembled corpus, so closed-index coverage is checked
rather than assumed.
