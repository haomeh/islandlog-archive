# islandlog archive

Content repository of Island Log (islandlog): a neutral, source-backed archive of public controversies and government decisions in Taiwan.
Content is Markdown and YAML files. PostgreSQL in the `server` repo is only a rebuildable query index.

- License: CC BY-SA 4.0 (see `LICENSE`). Government data keeps its attribution (see `ATTRIBUTION.md`).
- Rules for editors and contributors: `CONTRIBUTING.md`.
- Home: <https://github.com/haomeh/islandlog-archive>. Send corrections, suggestions and takedown requests as `CONTRIBUTING.md` section 5 says. Do not use public issues.
- Product requirements: `docs/PRD.md` in the project root (not in this repo; see PRD Q-15).

## Layout

| Path | Content |
|---|---|
| `schemas/` | 10 JSON Schemas (draft 2020-12) |
| `taxonomy/` | 10 taxonomy and term files |
| `events/`, `decisions/`, `actors/`, `sources/`, `corrections/` | Published content (empty in M0) |
| `jurisdictions/` | `jur-tw.yaml` (hand-written) and 22 county files (imported) |
| `geo/` | County boundaries as TopoJSON |
| `fixtures/` | Fictional test data. Indexing skips it by default |

## Validate

```sh
islandlog validate .
```

The command comes from the `server` repo. It checks `archive/` and `fixtures/` together.
Content under `fixtures/` is fictional. Never copy it into `events/`.
