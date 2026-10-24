---
schema_version: 1
id: ev-20230615-example-estuary-dredging
aliases: []
kind: controversy
status: published
title: 範例河口疏濬工程爭議（虛構範例）
summary: >-
  另一個範例縣於 2023 年 6 月討論範例河口疏濬計畫，各方對施工時程意見不同 [@src-20230615-example-estuary-record]。
start_date: 2023-06-15
start_date_precision: day
gov_levels: [county_city]
jurisdiction_ids: [jur-99010000]
controversy_types: [environment, public_works]
policy_domains: [environment]
actors:
  - actor_id: ac-example-county-government
    role: decision_maker
  - actor_id: ac-example-county-council
    role: reviewer
questions:
  - id: q-01
    text: 範例河口是否應在 2023 年內施作疏濬？
positions:
  - id: pos-01
    question_id: q-01
    actor_id: ac-example-county-government
    stance: support
    summary: 縣政府表示，疏濬可改善河口排水。
    stated_on: 2023-06-15
    source_ids: [src-20230615-example-estuary-record]
  - id: pos-02
    question_id: q-01
    actor_id: ac-example-county-council
    stance: conditional
    summary: 議會表示，疏濬時程應配合河口的魚苗季。
    stated_on: 2023-06-15
    source_ids: [src-20230615-example-estuary-record]
timeline:
  - id: tl-01
    date: 2023-06-15
    date_precision: day
    title: 討論範例河口疏濬計畫
    lifecycle_stage: institutional_response
    source_ids: [src-20230615-example-estuary-record]
decision_ids: []
relations: []
external_refs: []
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: ""
---

## 背景

另一個範例縣於 2023 年 6 月 15 日召開會議，討論範例河口疏濬計畫 [@src-20230615-example-estuary-record]。

## 經過

會議紀錄記載，縣政府與議會對施工時程提出不同意見 [@src-20230615-example-estuary-record]。
