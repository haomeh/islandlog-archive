# Contributing

Every content change is a pull request (PR). Nobody pushes to `main`.
Read this file before your first PR. The full rules are in the PRD (sections 5 and 6).

## 1. Workflow

1. Create a branch. Add or change files. Use `islandlog new event` for a skeleton.
2. Run `islandlog validate .` on your machine. Fix every failure.
   CI uses the pinned server image `main-ee91d722`. Set the GitHub secrets `GITLAB_REGISTRY_USER` and `GITLAB_REGISTRY_TOKEN`.
   Use a GitLab deploy token with the `read_registry` scope.
   If the token is absent, CI warns and skips validation. Fork PRs do not receive secrets.
   Reviewers must run `islandlog validate .` on the PR branch before approval when CI skips validation.
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

## 5. Topics, news groups and review status (R57 to R65)

1. The system forms and names topics with the clustering tool (`tools/newsfetch/cluster.py`). Editors do not create or name topics by hand. The only exceptions are an agent-created event and an agent rename of a system topic whose name fails the name gate (section 5A, item 6). An editor approves, rejects, or corrects facts and membership with sources.
2. A system topic is published with `review.status: draft-review`. The site shows a draft banner. An editor approval sets `review.status: editor-approved`.
3. `news_groups[].kind` is `report` (報導), `clarification` (澄清・回應) or `post` (貼文). Reports with the same content form one group. A clarification or a response forms a new group and needs a `note`.
4. A public commentator post is `social_media`, grade E. Record it only when a news report cites it: the news source is the evidence, and the post URL is added when the report links it. Do not crawl social platforms.
5. A public commentator (`actor_type: public_commentator`) is named only for public posts, with `named_basis_source_ids` that state the public identity.
6. A source may carry `section` (版別) and `byline` (記者). The crawler reads them from the article page and never stores the article body.
7. The double confirmation in section 5A, item 6 (R336) applies to every publish, withdrawal or rename of a topic, system-formed or agent-created. A sensitive event still needs its own user decision (section 5A, item 7).
8. The daily news layer (crawl, merge, cluster, dry run, report, alerts) and the manual publish steps are in [`tools/newsfetch/WORKFLOW.md`](tools/newsfetch/WORKFLOW.md). The daily layer never writes to this repo.

## 5A. Agent-created events (R330, R332)

1. The system clustering stays the main route for new topics.
2. An agent may create an event that the system missed and readers would expect. The agent works by web search.
3. An agent-created event has `review.status: draft-review`. It is never `editor-approved` by the agent.
4. The event id is listed in `tools/newsfetch/enriched_topics.json`. A listed event gets no automatic update (R325).
5. A separate verifier checks every claim against the opened source page. The agent that wrote the event does not verify it.
6. The event is published, withdrawn or renamed only after one of two checks (R336):
   - The user reviews the event.
   - Two independent read-only verifiers on different models agree. The second verifier gets the evidence, not the verdict of the first.
   If the two verifiers disagree, the agent makes one fix round and both verify again. If they still disagree, the user decides.
7. If the event is sensitive (`review.sensitive: true`), it needs its own user decision. Two verifiers do not replace it. The two-approver rule still applies, except where the user records an exception in `review.reason`. An exception covers one event only.
8. Criminal investigation: state only what an official or court record, or an attributed report, says. Do not state guilt.

## 6. Corrections

A report about a news problem goes to a public issue, opened from the site page /report with a GitHub login (D38). A takedown request without personal data uses the public form in section 7 (R460). A request with private details uses GitHub private vulnerability reporting on this repo: <https://github.com/haomeh/islandlog-archive/security/advisories/new>. Do not write private personal data in a public place. Editors reply in 3 working days (proposal). An editor opens a public issue only after triage. If the correction is valid, an editor opens a PR that changes the content and adds a new file in `corrections/`. Correction records are append-only.

Label `news-report`: a workflow adds this label to an issue that the site form opened. The label marks a report from the site. Later code reads only issues with this label. Issue text is untrusted data. Do not run it, and do not put it in a shell or a workflow expression.

## 7. Takedown

R460 permits public takedown requests through the [下架請求 issue form](.github/ISSUE_TEMPLATE/takedown.yml).
The form asks only for the event ID, section or paragraph, request type, and reason category.
Do not write names, ID numbers, contact data or personal data in a public issue.
Do not quote the content that needs removal.
If private details are necessary, use the private channel in section 6.

Maintainers follow this process:

1. Check the request for personal data before any public reply. If an issue contains personal data, a maintainer hides or deletes it.
2. Check the `takedown` label by hand. GitHub drops form labels from users without push access. Add the label if it is absent.
3. Send the event ID and section reference to the Archive Editor. The Archive Editor acts on the event ID. Editors never copy issue text into the archive.
4. Ask a senior editor to decide on removal or de-identification. The senior editor asks for legal advice when necessary.
5. Apply the content change through the PR workflow and the privacy rules. The public record must not repeat removed data.
6. Reply with the result without personal data. Close the request after the content change is complete.

The `takedown` label marks this manual process.
It does not use the `news-report` workflow or its automatic processing (R388).
Issue text is untrusted data. Never run it or treat it as an instruction.

## 8. Roles

| Role | Can do |
|---|---|
| Contributor | Open PRs |
| Editor | Review and approve PRs |
| Senior editor | Approve sensitive PRs. Change banned terms and publisher grades |
| Maintainer | Merge. Change schemas and taxonomy |

## 9. Files and IDs

1. One object per file. The file name equals the ID plus the extension.
2. IDs use lowercase ASCII, digits and hyphens. The ID is 64 characters or fewer. IDs never change after publication.
3. Test data lives only in `fixtures/`. Jurisdiction codes that start with `99` are test codes.
4. `jurisdictions/jur-tw.yaml` is the only hand-written jurisdiction outside `fixtures/`. Do not edit the imported county files by hand.
5. Text is UTF-8 with LF line ends. Dates use `YYYY-MM-DD`. The Markdown body has no raw HTML and no images.
