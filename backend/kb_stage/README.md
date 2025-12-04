# Credit Copilot Knowledge Base (kb_stage)

This folder contains staged legal content (Markdown + YAML frontmatter) used to enhance AI-generated dispute letters. Files here are curated and then promoted to the production KB (`kb/`) before being ingested into the SQLite FTS5 database.

## Refresh Workflow

1) Fetch latest legal sources into `kb_stage/`

- FCRA + FDCPA statutes (Cornell LII):
  - `python ops/pipelines/fetch_fcra_fdcpa.py --out kb_stage`
  - or the hardened version with retries: `python backend/ops/pipelines/fetch_fcra_fdcpa_hardened.py --out kb_stage`

- CFPB + FTC guidance:
  - `python ops/pipelines/fetch_cfpb_ftc.py --out kb_stage`
  - or the hardened version: `python backend/ops/pipelines/fetch_cfpb_ftc_hardened.py --out kb_stage`

2) Curate staged content (normalize, add anchors, dedupe)

- `python ops/pipelines/curate_stage.py --in kb_stage`

3) Promote curated files to production KB (`kb/`)

- `python ops/pipelines/promote_to_prod.py --from kb_stage --to kb`

4) Ingest the production KB into SQLite for fast search

- Set where to store the KB database:
  - `export KB_DB_PATH=kb.sqlite`
- Ingest (simple ingester):
  - `python backend/ops/pipelines/ingest_staged_to_kb.py`

After ingestion, the backend reads `KB_DB_PATH` and uses FTS5 search to inject relevant legal context and citations during letter generation.

## Makefile shortcuts

If available in your environment:

```
make kb-fetch     # Fetch + curate into kb_stage/
make kb-promote   # Promote to kb/
make kb-ingest    # Ingest production KB
make kb-refresh   # Full refresh (fetch + promote + ingest)
```

## File format

Each Markdown file includes YAML frontmatter like:

```
---
source: FCRA | FDCPA | CFPB | FTC
section: 15 USC 1681i           # optional for statutes
title: Procedure in case of disputed accuracy
version_date: 2025-09-17
tags: [fcra, statute, federal]
anchors: []
meta:
  provenance_url: https://www.law.cornell.edu/uscode/text/15/1681i
  fetched_at: 2025-09-17T18:00:00Z
  content_hash: <sha256>
  license: public_domain
  jurisdiction: federal
---

<Plain text content>
```

Anchors (¶1, ¶a, etc.) are added during curation to enable stable paragraph references.

