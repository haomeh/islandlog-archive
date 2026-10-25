---
schema_version: 1
id: ev-20200313-taichung-coal-ordinance-void
kind: controversy
status: published
title: 行政院函告臺中市生煤自治條例部分條文無效
summary: 行政院於 2020 年 3 月 13 日表示，臺中市公私場所管制生煤及禁用石油焦自治條例第 3 條、第 4 條及第 6 條牴觸空氣污染防制法及相關規定，該等條文無效 [@src-20200313-ey-taichung-ordinance]。臺中市政府表示，市府將尋求訴願、行政訴訟或釋憲等救濟 [@src-20200313-pts-taichung-permits]。
start_date: '2020-03-13'
start_date_precision: day
gov_levels:
- central
- special_municipality
jurisdiction_ids:
- jur-tw
- jur-66000000
controversy_types:
- environment
- legislation
policy_domains:
- environment
- economy_energy
actors:
- actor_id: ac-executive-yuan
  role: decision_maker
- actor_id: ac-taichung-city-government
  role: opponent
- actor_id: ac-taichung-city-council
  role: affected_party
questions:
- id: q-01
  text: 臺中市生煤自治條例第 3 條、第 4 條及第 6 條是否牴觸空氣污染防制法？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-executive-yuan
  stance: support
  summary: 行政院表示，該等條文牴觸空氣污染防制法及相關規定，因此無效。
  stated_on: '2020-03-13'
  source_ids:
  - src-20200313-ey-taichung-ordinance
- id: pos-02
  question_id: q-01
  actor_id: ac-taichung-city-government
  stance: other
  summary: 市府表示，條例是市議會依法制定的，市府將尋求訴願、行政訴訟或釋憲等救濟。
  stated_on: '2020-03-13'
  source_ids:
  - src-20200313-pts-taichung-permits
timeline:
- id: tl-01
  date: '2019-12-01'
  date_precision: month
  title: 臺中市政府廢止臺中火力發電廠2部燃煤機組的操作許可證
  description: 公視報導的時間為2019年底。
  attributed_to: ac-taichung-city-government
  lifecycle_stage: implementation
  source_ids:
  - src-20200313-pts-taichung-permits
- id: tl-02
  date: '2020-03-13'
  date_precision: day
  title: 行政院函告該條例第3條、第4條及第6條無效
  attributed_to: ac-executive-yuan
  lifecycle_stage: decision
  decision_id: dc-20200313-ey-taichung-void
  source_ids:
  - src-20200313-ey-taichung-ordinance
- id: tl-03
  date: '2020-03-13'
  date_precision: day
  title: 臺中市政府表示將尋求救濟
  attributed_to: ac-taichung-city-government
  lifecycle_stage: contestation
  source_ids:
  - src-20200313-pts-taichung-permits
decision_ids:
- dc-20200313-ey-taichung-void
relations:
- type: follows
  target_id: ev-20151223-taichung-coal-ordinance-passed
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 由代理人起草，使用者尚未審閱，公開前須審閱。'
  status: draft-review
---

## 背景

公視報導，臺中市政府於 2019 年底依該條例廢止臺中火力發電廠 2 部燃煤機組的操作許可證，環境保護署認定該廢止程序違法 [@src-20200313-pts-taichung-permits]。

## 行政院的說明

行政院的新聞稿載明，第 3 條第 1 項與第 4 條禁止並剝奪人民申請新設固定污染源生煤與石油焦使用許可證的權利，牴觸空氣污染防制法第 28 條第 1 項 [@src-20200313-ey-taichung-ordinance]。

新聞稿載明，第 6 條要求生煤堆置場所以封閉式建築物為限，牴觸施行細則第 4 條第 1 項，該項另允許其他 4 種方式 [@src-20200313-ey-taichung-ordinance]。

## 臺中市政府的說明

公視報導，臺中市政府表示，條例是市議會依法制定的，且在市府依法關閉中火 2 部燃煤機組之後，中央才宣告條例無效 [@src-20200313-pts-taichung-permits]。
