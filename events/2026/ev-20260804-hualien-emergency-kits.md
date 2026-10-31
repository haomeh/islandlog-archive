---
schema_version: 1
id: ev-20260804-hualien-emergency-kits
kind: historical_event
status: published
title: 花蓮縣政府採購緊急避難包的發放進度與審計查核意見
summary: 2026-08-04，媒體報導審計室查核發現，花蓮縣 2026 年 3 月仍有 2 萬多組緊急避難包未發放 [@src-20260804-cts-ce4fc896]。消防局於 8 月表示剩餘約 9,800 組，可領至 9 月 30 日 [@src-20260804-ltn-ee471cab]。
start_date: '2026-08-04'
start_date_precision: day
gov_levels:
- county_city
jurisdiction_ids:
- jur-10015000
controversy_types:
- budget
policy_domains:
- interior
actors:
- actor_id: ac-hualien-county-government
  role: decision_maker
questions:
- id: q-01
  text: 花蓮縣政府採購的緊急避難包發放進度如何，審計查核與縣府各說了什麼？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-hualien-county-government
  stance: other
  summary: 花蓮縣消防局表示，採購量依戶籍數估算，實際有戶籍在花蓮但不在當地居住的情形；8 月時剩餘約 9,800 組，9 月 30 日前可至各消防分隊領取，未來將在首波發放後再評估是否續購。
  stated_on: '2026-08-04'
  source_ids:
  - src-20260804-ltn-ee471cab
  - src-20260804-cts-ce4fc896
  - src-20260805-cts-650964c2
timeline:
- id: tl-01
  date: '2026-08-04'
  date_precision: day
  title: 媒體報導審計室查核意見，花蓮縣消防局說明剩餘數量與領取期限
  source_ids:
  - src-20260804-cts-ce4fc896
  - src-20260804-ltn-ee471cab
- id: tl-02
  date: '2026-08-05'
  date_precision: day
  title: 縣議員要求縣府說明，消防局補充無法發放的原因
  source_ids:
  - src-20260805-cts-650964c2
  - src-20260805-ltn-f7fa68eb
news_groups:
- id: ng-01
  timeline_id: tl-01
  kind: report
  title: 花蓮採購避難包未發完 審計室要求縣府改善
  representative_source_id: src-20260804-cts-ce4fc896
  source_ids:
  - src-20260804-cts-ce4fc896
- id: ng-02
  timeline_id: tl-01
  kind: clarification
  title: 超額採購浪費公帑？花蓮避難包「2萬組堆倉庫」 消防局回應了
  representative_source_id: src-20260804-ltn-ee471cab
  source_ids:
  - src-20260804-ltn-ee471cab
  note: 報導中載有花蓮縣消防局對審計查核意見的回應
- id: ng-03
  timeline_id: tl-02
  kind: report
  title: 花蓮近萬個避難包堆倉庫逾1年 議員批浪費公帑
  representative_source_id: src-20260805-cts-650964c2
  source_ids:
  - src-20260805-cts-650964c2
  - src-20260805-ltn-f7fa68eb
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 系統原依爬取資料自動形成；2026-10-31 由 agent 依 R344 補入華視來源、改寫標題與內文。2026-10-31 的 T81b 修正議員說法的來源標記與採購年份。待兩位獨立驗證者確認（R336）。'
  status: draft-review
---

## 背景

中央社與自由時報報導，花蓮縣消防局採購緊急避難包與救護包：中央社寫 2024 年追加預算，自由時報寫「去年」採購，兩者的年份不同；自由時報另寫 2025 年 6 月起以每戶一組的方式發放 [@src-20260804-cts-ce4fc896] [@src-20260805-ltn-f7fa68eb]。報導的採購數量與金額不一致：華視轉載的中央社報導寫採購經費 6,500 萬元，並在同一則報導內有 11 萬組與 13 萬組兩種數字 [@src-20260804-cts-ce4fc896]；華視另一則報導寫 13.5 萬組、6,500 萬元 [@src-20260805-cts-650964c2]；自由時報寫總量約 13.5 萬組、合計花費約 345 萬元 [@src-20260804-ltn-ee471cab] [@src-20260805-ltn-f7fa68eb]。本頁不判定哪個數字正確。

## 審計查核意見

報導指出，審計室查核花蓮縣政府 2025 年度總決算，2026 年 3 月時仍有 2 萬多組未發放 [@src-20260804-cts-ce4fc896] [@src-20260805-ltn-f7fa68eb]。審計室指出的問題包括：救護包內的酒精、優碘棉片、傷口敷料等有使用期限；發放方式不一致且缺乏事後稽核機制；廠商未依契約到發放處或倉庫巡檢 [@src-20260804-cts-ce4fc896] [@src-20260804-ltn-ee471cab]。自由時報另報導，審計單位認為需求評估不夠周延，首批尚未發完就追加採購；審計室要求縣府改善 [@src-20260804-ltn-ee471cab] [@src-20260804-cts-ce4fc896]。

## 花蓮縣消防局的說明

花蓮縣消防局表示，採購量依戶籍數估算，但有戶籍在花蓮、人不在當地的情形，因此未領取；8 月時剩餘約 9,800 組，民眾可在 9 月 30 日前到各消防分隊領取 [@src-20260804-ltn-ee471cab] [@src-20260805-ltn-f7fa68eb]。消防局表示，合約要求廠商一年內巡檢並更換過期品項，廠商已在 4 月與 5 月到各鄉鎮巡檢 [@src-20260804-ltn-ee471cab] [@src-20260804-cts-ce4fc896]。

消防局災害管理科代理科長陳力平表示，約一至兩成無法發放，期限後剩餘避難包將用於防災宣導或捐贈弱勢團體 [@src-20260805-cts-650964c2]。消防局並表示，未來將改採動態採購 [@src-20260804-ltn-ee471cab]。

## 縣議員的意見

無黨籍縣議員魏嘉賢表示，2011 年縣府也曾全縣採購避難包，成效不明；他認為避難包宜由家庭自行準備，縣府應優先改善避難收容環境與物資調度 [@src-20260804-cts-ce4fc896]。華視另一則報導寫，他要求縣府主動說明為何有避難包沒有發放出去 [@src-20260805-cts-650964c2]；自由時報寫，他質疑採購數量為什麼和實際需求產生巨大落差 [@src-20260805-ltn-f7fa68eb]。無黨籍縣議員楊華美表示，藥品是否過期必須向民眾說明 [@src-20260805-cts-650964c2]。

## 資料限制

本頁依 2026 年 8 月 4 至 5 日的 2 家媒體報導整理，未查得審計室報告原文與縣府的正式公文。2 萬多組是 3 月查核的數字，約 9,800 組是消防局 8 月的說法，兩者時間不同 [@src-20260805-ltn-f7fa68eb]。
