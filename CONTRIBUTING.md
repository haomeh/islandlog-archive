# Contributing

Every content change is a pull request (PR). Nobody pushes to `main`.
Read this file before your first PR. The full rules are in the PRD (sections 5 and 6).

## 1. Workflow

1. Create a branch. Add or change files. Use `islandlog new event` for a skeleton.
2. Run `islandlog validate .` on your machine. Fix every failure.
3. Open a PR. Pick the template: `event`, `correction` or `takedown`.
4. Fill in `review_sensitive`, `review_reason` and the verification steps.
5. An editor approves. A sensitive PR needs two approvals, one from a senior editor. You cannot approve your own PR.
6. A maintainer merges. The index updates within about 5 minutes.

## 2. Neutral wording

1. Every statement of fact has at least one source marker: `[@src-YYYYMMDD-slug]`.
2. Write a claim as "X said ...". Never write a claim as a fact.
3. Do not use evaluative terms in titles and summaries. The list is `taxonomy/banned_terms.yaml`.
4. Titles of events, decisions and timeline entries have no slogans and no quotes.
5. Record each position with its source. If you find no public position, write `stance: not_found`.
6. Before a final judgment, do not describe a person with a conviction term. Add later acquittals or withdrawals to the same timeline.

## 3. Source grades

| Grade | Sources | Use |
|---|---|---|
| A | Primary official records: gazettes, roll-call votes, judgments, council minutes | Supports a fact alone |
| B | Statement of an actor about itself: press release, party or group statement | Supports "X said ..." only |
| C | News media with a correction policy; fact-check reports | Supports a fact. A disputed fact needs two publishers |
| D | Third-party advocacy or analysis | Attributed opinion only |
| E | Social media, anonymous posts, content farms | Never evidence |

The class-to-grade table is `taxonomy/source_classes.yaml`. A grade B source needs `publisher_actor_id`.
Do not copy news text. Keep the link, title, date, publisher and a quote of 150 characters or fewer.

## 4. Privacy

1. Public figures appear only in their public roles.
2. Do not name a private person unless an official record names them in a public role. Then set `named_basis_source_ids` (grade A only).
3. Do not write ID numbers, phone numbers, emails or home addresses.
4. Content on health, genes, sex life or criminal records (see `taxonomy/sensitive_terms.yaml`) is sensitive. Set `review.sensitive: true`.
5. Events with the type `misconduct` or `election` are always sensitive.

## 5. Corrections

Never post a correction request, a suggestion or a takedown request in a public issue. Send it through the site contact form (M1). Until the form exists, use GitHub private vulnerability reporting on this repo: <https://github.com/haomeh/islandlog-archive/security/advisories/new>. Do not write private personal data in a public place. Editors reply in 3 working days (proposal). An editor opens a public issue only after triage. If the correction is valid, an editor opens a PR that changes the content and adds a new file in `corrections/`. Correction records are append-only.

## 6. Takedown

A data subject can ask for removal or masking. Send the request through the private channel in section 5. A senior editor decides, with legal advice when needed. The public record does not repeat the removed data.

## 7. Roles

| Role | Can do |
|---|---|
| Contributor | Open PRs |
| Editor | Review and approve PRs |
| Senior editor | Approve sensitive PRs. Change banned terms and publisher grades |
| Maintainer | Merge. Change schemas and taxonomy |

## 8. Files and IDs

1. One object per file. The file name equals the ID plus the extension.
2. IDs use lowercase ASCII, digits and hyphens. The ID is 64 characters or fewer. IDs never change after publication.
3. Test data lives only in `fixtures/`. Jurisdiction codes that start with `99` are test codes.
4. `jurisdictions/jur-tw.yaml` is the only hand-written jurisdiction outside `fixtures/`. Do not edit the imported county files by hand.
5. Text is UTF-8 with LF line ends. Dates use `YYYY-MM-DD`. The Markdown body has no raw HTML and no images.
