---
schema_version: 1
id: ev-20250304-fanli-river-dredging
aliases: []
kind: controversy
status: published
title: 範例溪疏濬工程爭議（虛構範例）
summary: >-
  範例縣政府於 2025 年 3 月公告範例溪疏濬計畫。
  地方漁會與環保團體對生態影響提出異議 [@src-20250312-fanli-news-a]。
start_date: 2025-03-04
start_date_precision: day
gov_levels: [county_city, township]
jurisdiction_ids: [jur-99000000, jur-99000010]
controversy_types: [environment, public_works]
policy_domains: [environment, economy_energy]
actors:
  - actor_id: ac-fanli-county-government
    role: decision_maker
  - actor_id: ac-fanli-fishermen-association
    role: opponent
  - actor_id: ac-fanli-river-alliance
    role: opponent
  - actor_id: ac-fanli-county-council
    role: reviewer
questions:
  - id: q-01
    text: 範例溪是否應在 2025 年汛期前施作疏濬？
  - id: q-02
    text: 疏濬計畫是否應先做環境影響評估？
positions:
  - id: pos-01
    question_id: q-01
    actor_id: ac-fanli-county-government
    stance: support
    summary: 縣政府表示，疏濬可降低汛期的淹水風險。
    stated_on: 2025-03-04
    source_ids: [src-20250304-fanli-county-press]
  - id: pos-02
    question_id: q-01
    actor_id: ac-fanli-fishermen-association
    stance: oppose
    summary: 漁會表示，汛期前施工會影響河口的魚苗。
    stated_on: 2025-03-12
    source_ids: [src-20250312-fanli-news-a]
  - id: pos-03
    question_id: q-02
    actor_id: ac-fanli-river-alliance
    stance: support
    summary: 環保團體表示，工程規模達到環評門檻，應先做環評。
    stated_on: 2025-03-15
    source_ids: [src-20250315-fanli-alliance-statement]
  - id: pos-04
    question_id: q-01
    actor_id: ac-fanli-river-alliance
    stance: not_found
  - id: pos-05
    question_id: q-02
    actor_id: ac-fanli-county-government
    stance: not_found
  - id: pos-06
    question_id: q-02
    actor_id: ac-fanli-fishermen-association
    stance: not_found
timeline:
  - id: tl-01
    date: 2025-03-04
    date_precision: day
    title: 將於汛期前施作範例溪疏濬
    attributed_to: ac-fanli-county-government
    lifecycle_stage: emergence
    source_ids: [src-20250304-fanli-county-press]
  - id: tl-02
    date: 2025-03-20
    date_precision: day
    title: 縣議員於定期會質詢疏濬計畫
    lifecycle_stage: escalation
    source_ids: [src-20250320-fanli-council-minutes]
  - id: tl-03
    date: 2025-04-10
    date_precision: day
    title: 縣議會通過疏濬工程預算
    lifecycle_stage: decision
    decision_id: dc-20250410-fanli-dredging-approval
    source_ids: [src-20250410-fanli-council-minutes]
decision_ids: [dc-20250410-fanli-dredging-approval]
relations:
  - type: same_issue_other_jurisdiction
    target_id: ev-20230615-example-estuary-dredging
    note: 另一縣市的同類河口疏濬爭議（虛構）
external_refs: []
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: ""
---

## 背景

範例縣政府於 2025 年 3 月 4 日發布新聞稿，表示將在汛期前完成範例溪疏濬 [@src-20250304-fanli-county-press]。

## 經過

範例漁會於 3 月 12 日表示，施工期與魚苗季重疊 [@src-20250312-fanli-news-a]。
範例溪流聯盟於 3 月 15 日發表聲明，主張計畫應先做環境影響評估 [@src-20250315-fanli-alliance-statement]。

縣議會於 4 月 10 日通過疏濬工程預算 [@src-20250410-fanli-council-minutes]。
