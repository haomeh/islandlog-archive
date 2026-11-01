---
schema_version: 1
id: ev-20261014-kuo-kuang-bus-trip-cancellations
kind: historical_event
status: published
title: 國光客運國道客運班次取消與公路局裁罰
summary: 10-14 至 15 日國光客運取消 65 個班次，公路局表示公司未申請減班並將裁罰 [@src-20261015-cts-62929cf9] [@src-20261015-pts-9771ea80]。10-30 報導指公司因再度取消班次，兩週內累計被罰 45 萬元 [@src-20261030-ettoday-9e0788b2] [@src-20261030-udn-13dd015f]。
start_date: '2026-10-14'
start_date_precision: day
gov_levels:
- central
jurisdiction_ids:
- jur-tw
controversy_types:
- governance_procedure
policy_domains:
- transport
- labor
actors:
- actor_id: ac-highway-bureau
  role: decision_maker
- actor_id: ac-kuo-kuang-motor-transport
  role: affected_party
questions:
- id: q-01
  text: 國光客運為何取消班次，公司如何說明與處理？
- id: q-02
  text: 公路局如何裁罰，並對客運業駕駛缺額採取哪些措施？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-kuo-kuang-motor-transport
  stance: other
  summary: 國光客運表示因駕駛不足調整班次，向乘客致歉，啟動緊急調度，以遊覽車支援並提供招募與路線獎金。
  stated_on: '2026-10-15'
  source_ids:
  - src-20261015-cts-62929cf9
  - src-20261015-ltn-1fb08a5f
- id: pos-02
  question_id: q-01
  actor_id: ac-highway-bureau
  stance: other
  summary: 公路局台北區監理所表示，該公司未申請減班，已要求公司儘速改善，並將依公路法與營運規定開單舉發。
  stated_on: '2026-10-15'
  source_ids:
  - src-20261015-cts-62929cf9
  - src-20261015-ltn-1fb08a5f
  - src-20261015-pts-9771ea80
- id: pos-03
  question_id: q-02
  actor_id: ac-highway-bureau
  stance: other
  summary: 公路局副局長表示，駕駛僱用補助延長至明年 2 月，外籍學生駕駛的中文門檻放寬案已送勞動部審議，路線整併與優化正在審議。
  stated_on: '2026-10-30'
  source_ids:
  - src-20261030-cts-d12906bb
- id: pos-04
  question_id: q-02
  actor_id: ac-kuo-kuang-motor-transport
  stance: not_found
- id: pos-05
  question_id: q-01
  actor_id: ac-kuo-kuang-motor-transport
  stance: other
  summary: 華視 10 月 30 日的報導引述國光客運說法，僅稱班次已正常行駛，沒有進一步補充說明。
  stated_on: '2026-10-30'
  source_ids:
  - src-20261030-cts-d12906bb
timeline:
- id: tl-01
  date: '2026-10-14'
  date_precision: day
  title: 國光客運在 4 條國道路線取消班次
  attributed_to: ac-highway-bureau
  lifecycle_stage: emergence
  source_ids:
  - src-20261015-cts-62929cf9
  - src-20261015-pts-9771ea80
- id: tl-02
  date: '2026-10-15'
  date_precision: day
  title: 公路局表示將依公路法裁罰，公司致歉並公布調度措施，宜蘭縣議員要求配套
  lifecycle_stage: institutional_response
  source_ids:
  - src-20261015-cts-62929cf9
  - src-20261015-ltn-1fb08a5f
  - src-20261015-pts-9771ea80
- id: tl-03
  date: '2026-10-29'
  date_precision: day
  title: 國光客運在國道 1820 路線再度取消班次，公路局再罰 9 萬元
  attributed_to: ac-highway-bureau
  lifecycle_stage: decision
  source_ids:
  - src-20261030-ettoday-9e0788b2
  - src-20261030-udn-13dd015f
- id: tl-04
  date: '2026-10-30'
  date_precision: day
  title: 公路局說明駕駛缺額與路線整併審議
  attributed_to: ac-highway-bureau
  lifecycle_stage: implementation
  source_ids:
  - src-20261030-cts-d12906bb
news_groups:
- id: ng-01
  timeline_id: tl-02
  kind: report
  title: 國光客運2天內無預警取消65班 公路局：最高罰9萬
  representative_source_id: src-20261015-pts-9771ea80
  source_ids:
  - src-20261015-cts-62929cf9
  - src-20261015-pts-9771ea80
- id: ng-02
  timeline_id: tl-02
  kind: report
  title: 國光客運2天擅砍65班 謝家倫轟「最高罰9萬不痛不癢」：速提配套
  representative_source_id: src-20261015-ltn-1fb08a5f
  source_ids:
  - src-20261015-ltn-1fb08a5f
- id: ng-03
  timeline_id: tl-03
  kind: report
  title: 國光客運又擅自減班 公路局累計開罰45萬
  representative_source_id: src-20261030-ettoday-9e0788b2
  source_ids:
  - src-20261030-ettoday-9e0788b2
  - src-20261030-udn-13dd015f
- id: ng-04
  timeline_id: tl-04
  kind: report
  title: 國光客運駕駛人力不足屢傳減班 公路局研議路線整併優化
  representative_source_id: src-20261030-cts-d12906bb
  source_ids:
  - src-20261030-cts-d12906bb
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 由 agent 於 2026-11-01 依 R392（T90）以網路搜尋建立，不是系統分群產生；每項主張對照已開啟的來源頁撰寫。本事件是中央層級；起始日是已開啟來源記載的第一個取消日。待兩位獨立驗證者確認（R336）。'
  status: draft-review
---

## 背景

華視轉載的中央社報導，國光客運在 10 月 14 日至 15 日中午取消 65 個班次，其中 14 日 42 班、15 日 23 班，涉及國道 1820、1822、1878 與 1879 路線；公路局台北區監理所確認這些路線有漏班，且公司未申請減班 [@src-20261015-cts-62929cf9]。同一則報導寫，9 月曾有 8 名駕駛突然請假，造成國道 5 號部分路線取消班次 [@src-20261015-cts-62929cf9]。

## 公司的說明

國光客運向乘客致歉，表示已啟動緊急調度與改善措施 [@src-20261015-cts-62929cf9] [@src-20261015-pts-9771ea80]。報導列出的措施包括：宜蘭路線早尖峰班距為 10 至 20 分鐘、預計增加遊覽車後恢復到 8 至 10 分鐘，新竹 1822 路線因乘客少且有競業路線而擬修正時刻表送審，竹東路線檢討遊覽車備援，並提供招募與路線獎金 [@src-20261015-cts-62929cf9]。公司表示因駕駛不足而調整班次 [@src-20261015-ltn-1fb08a5f]。ETtoday 與華視 10 月 30 日的報導引述公司說法，僅稱班次已正常行駛，沒有進一步說明 [@src-20261030-ettoday-9e0788b2] [@src-20261030-cts-d12906bb]。

## 公路局的裁罰與措施

公視新聞網報導，公路局表示公司事前未申請減班，將裁罰，最高可處 9 萬元罰鍰，並要求盡速改善 [@src-20261015-pts-9771ea80]。華視寫的是罰鍰 9,000 元至 9 萬元，依公路法與營運規定開單 [@src-20261015-cts-62929cf9]。自由時報報導，公路局台北區監理所已依公路法開單，並要求公司派遊覽車疏運；該報導中 9 萬元的數字出自宜蘭縣議員的說法，而不是公路局 [@src-20261015-ltn-1fb08a5f]。該議員表示最高罰 9 萬元「不痛不癢」，要求相關單位盡快規劃替代接駁 [@src-20261015-ltn-1fb08a5f]。

聯合新聞網報導，公司在 10 月中旬無預告取消 65 班後被合併裁罰 36 萬元，約兩週後又被罰 9 萬元，兩週內累計 45 萬元；最新一次是 10 月底 1820 路線 4 班上午班次，監理單位以每案最高 9 萬元裁罰 [@src-20261030-udn-13dd015f]。ETtoday 寫的分項不同：36 萬元涵蓋 9 月與 10 月 14 至 15 日的取消，10 月 29 日 1820 與 1820A 路線先取消 8 班、重新調度後取消 4 班，再罰 9 萬元，依公路法按最高額處罰，累計 45 萬元 [@src-20261030-ettoday-9e0788b2]。本頁不判定哪個分項正確。

公路局副局長表示，截至 8 月底國光客運有 397 個駕駛缺額；台北區監理所持續監督，公司可由遊覽車部門調度駕駛；駕駛僱用補助延長到明年 2 月，2019 年以來約 4,700 名駕駛領過補助；放寬外籍學生駕駛中文門檻的建議 9 月送勞動部審議；公路局也請業者提高駕駛薪資；路線整併與優化正在審議，完成後送交通部公告 [@src-20261030-cts-d12906bb]。聯合新聞網報導，公路局表示缺班情形已大幅改善，將持續督導 [@src-20261030-udn-13dd015f]。

## 資料限制

本頁依 2026 年 10 月 15 日與 30 日的 6 篇新聞報導整理，未查得公路局的裁處書與新聞稿原文。報導對裁罰法源與分項金額的寫法不一致，本頁並列。本頁不收錄駕駛與乘客的姓名 [@src-20261030-udn-13dd015f]。
