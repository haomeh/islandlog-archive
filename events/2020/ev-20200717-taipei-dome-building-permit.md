---
schema_version: 1
id: ev-20200717-taipei-dome-building-permit
kind: controversy
status: published
title: 臺北市核發臺北大巨蛋新建照並同意復工
summary: 公視報導，臺北市政府於 2020 年 7 月核發臺北大巨蛋新的建造執照，核發前要求完成都市設計審議、環境差異分析審查及防火避難性能評定 [@src-20200717-pts-dome-permit]。臺北市政府於 2020 年 8 月 7 日同意大巨蛋復工 [@src-20200808-pts-dome-resume]。
start_date: '2020-07-17'
start_date_precision: day
gov_levels:
- special_municipality
jurisdiction_ids:
- jur-63000000
controversy_types:
- public_works
- public_safety
policy_domains:
- interior
actors:
- actor_id: ac-taipei-city-government
  role: decision_maker
- actor_id: ac-farglory
  role: proposer
questions:
- id: q-01
  text: 臺北大巨蛋是否應在核發新建照後復工？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-taipei-city-government
  stance: not_found
- id: pos-02
  question_id: q-01
  actor_id: ac-farglory
  stance: not_found
timeline:
- id: tl-01
  date: '2015-05-20'
  date_precision: day
  title: 大巨蛋被勒令停工
  lifecycle_stage: escalation
  source_ids:
  - src-20200808-pts-dome-resume
- id: tl-02
  date: '2020-07-01'
  date_precision: month
  title: 核准第3次變更設計並核發新建照
  description: 公視報導的時間為2020年7月中旬。
  attributed_to: ac-taipei-city-government
  lifecycle_stage: decision
  source_ids:
  - src-20200717-pts-dome-permit
  - src-20200808-pts-dome-resume
- id: tl-03
  date: '2020-08-07'
  date_precision: day
  title: 同意大巨蛋復工
  attributed_to: ac-taipei-city-government
  lifecycle_stage: implementation
  decision_id: dc-20200807-taipei-dome-resume
  source_ids:
  - src-20200808-pts-dome-resume
decision_ids:
- dc-20200807-taipei-dome-resume
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 由代理人起草，使用者尚未審閱，公開前須審閱。'
---

## 新建照

公視報導，臺北市政府在完成都市設計審議、環境差異分析審查及防火避難性能評定後，依法核發新的建造執照給遠雄 [@src-20200717-pts-dome-permit]。

公視報導，副市長表示，這次核准不包括第 97 條防火安全梯規劃，遠雄必須在取得使用執照前辦理變更 [@src-20200717-pts-dome-permit]。

公視報導，臺北市議員仍對公共安全問題存疑 [@src-20200717-pts-dome-permit]。

## 復工

公視報導，大巨蛋於 2015 年 5 月 20 日被勒令停工，臺北市政府表示大巨蛋在三次變更設計後已完成改正程序，同意自 2020 年 8 月 7 日起復工 [@src-20200808-pts-dome-resume]。
