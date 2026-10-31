---
schema_version: 1
id: ev-20260715-china-branded-attendance-devices
kind: historical_event
status: published
title: 政府機關差勤生物辨識設備的產地質疑與機關說明
summary: 2026-07-15，立委林俊憲表示，數個機關採購的差勤設備疑似使用中國熵基科技產品 [@src-20260715-chinatimes-c2b689da]。警政署表示已停用 [@src-20260715-cts-500e9759]；海巡署表示設備含中國廠牌 [@src-20260715-cts-28e3841a]；關務署表示責成兩關停用 [@src-20260715-ltn-456351f6]。
start_date: '2026-07-15'
start_date_precision: day
gov_levels:
- central
jurisdiction_ids:
- jur-tw
controversy_types:
- cross_strait_foreign
- information
policy_domains:
- interior
actors:
- actor_id: ac-coast-guard-administration
  role: decision_maker
- actor_id: ac-customs-administration
  role: decision_maker
- actor_id: ac-national-police-agency
  role: decision_maker
questions:
- id: q-01
  text: 政府機關採購的差勤生物辨識設備是否使用中國廠牌產品，各機關如何說明？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-national-police-agency
  stance: other
  summary: 警政署人事室主任劉永福表示，警政署差勤系統為內部網路，沒有連接外部，尚未發現危害資安的情事，已全面停止使用相關設備，並請廠商提出完整產地說明。
  stated_on: '2026-07-15'
  source_ids:
  - src-20260715-cts-500e9759
- id: pos-02
  question_id: q-01
  actor_id: ac-coast-guard-administration
  stance: other
  summary: 海巡署表示，2025 年 12 月清查時發現艦隊分署差勤系統含中國廠牌產品，違反採購須知；得標廠商疑似使用中國貼牌產品。該系統已下架並全部汰換。
  stated_on: '2026-07-15'
  source_ids:
  - src-20260715-cts-28e3841a
  - src-20260715-newtalk-e237c03c
  - src-20260715-oac-5d652ef0
- id: pos-03
  question_id: q-01
  actor_id: ac-customs-administration
  stance: other
  summary: 關務署表示，台北關與高雄關曾向同一廠商採購差勤設備，設備採封閉式主機、不對外連網，因此認為目前沒有個資外洩風險，但為求慎重，責成兩關立即停用。
  stated_on: '2026-07-15'
  source_ids:
  - src-20260715-cts-cb4cc0be
  - src-20260715-ltn-456351f6
timeline:
- id: tl-01
  date: '2026-07-15'
  date_precision: day
  title: 立委林俊憲召開記者會，警政署、海巡署與關務署說明設備處理情形
  source_ids:
  - src-20260715-chinatimes-c2b689da
  - src-20260715-ettoday-a0bbe4fe
  - src-20260715-cts-500e9759
  - src-20260715-cts-28e3841a
  - src-20260715-cts-cb4cc0be
  - src-20260715-newtalk-e237c03c
  - src-20260715-oac-5d652ef0
  - src-20260715-ltn-456351f6
  - src-20260715-ltn-e0af5abc
  - src-20260715-ltn-5b56f220
- id: tl-02
  date: '2026-07-16'
  date_precision: day
  title: 自由時報刊出報導，數發部資安署表示將研議把個人資料的蒐集及利用納入業務範疇
  source_ids:
  - src-20260716-ltn-8bea6fc4
news_groups:
- id: ng-01
  timeline_id: tl-01
  kind: report
  title: 林俊憲質疑警政署等機關採購的差勤設備疑為中國廠牌貼牌
  representative_source_id: src-20260715-chinatimes-c2b689da
  source_ids:
  - src-20260715-chinatimes-c2b689da
  - src-20260715-ettoday-a0bbe4fe
  - src-20260715-cts-500e9759
- id: ng-02
  timeline_id: tl-01
  kind: report
  title: 海巡署艦隊分署說明差勤系統已下架停用並汰換
  representative_source_id: src-20260715-cts-28e3841a
  source_ids:
  - src-20260715-cts-28e3841a
  - src-20260715-newtalk-e237c03c
  - src-20260715-ltn-5b56f220
- id: ng-03
  timeline_id: tl-01
  kind: report
  title: 關務署說明台北關與高雄關停用差勤設備
  representative_source_id: src-20260715-cts-cb4cc0be
  source_ids:
  - src-20260715-cts-cb4cc0be
  - src-20260715-ltn-456351f6
- id: ng-04
  timeline_id: tl-01
  kind: report
  title: 林俊憲揭差勤機竟用「中國貼牌」廠商 警政署：已全面停用
  representative_source_id: src-20260715-ltn-e0af5abc
  source_ids:
  - src-20260715-ltn-e0af5abc
- id: ng-05
  timeline_id: tl-02
  kind: report
  title: 政府人臉指紋差勤設備驚見中國貼牌貨
  representative_source_id: src-20260716-ltn-8bea6fc4
  source_ids:
  - src-20260716-ltn-8bea6fc4
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 系統原依爬取資料自動形成；2026-10-31 由 agent 依 R344 補入其他媒體來源、改寫標題與內文。2026-10-31 依兩份驗證報告補入海巡署自身的說明並修正措辭（T81）。待兩位獨立驗證者確認（R336）。'
  status: draft-review
---

## 背景

立法委員林俊憲於 2026 年 7 月 15 日在立法院召開記者會。他表示，內政部警政署、海巡署、財政部關務署與台灣中油採購的差勤用人臉、指紋辨識設備，疑似使用中國熵基科技的產品；他稱某家台灣廠商疑將該公司的機器貼上自有品牌，10 年內取得 16 件政府標案 [@src-20260715-chinatimes-c2b689da] [@src-20260715-ettoday-a0bbe4fe] [@src-20260715-cts-500e9759]。這是林俊憲的說法，來源報導未載廠商的回應。

林俊憲並表示，他比對設備外觀、產品說明書與國家通訊傳播委員會（NCC）型式認證資料，認為該產品疑似為熵基產品換牌 [@src-20260715-cts-500e9759] [@src-20260715-ettoday-a0bbe4fe]。中央社報導，NCC 認證報告載明的製造商為 ARMATURA TECH CO., Ltd.；林俊憲表示，公開資料顯示該公司是熵基持股 99.98% 的子公司。報導把後一點記為林俊憲的說法，不是 NCC 資料所載 [@src-20260715-cts-500e9759]。

## 各機關的說明

警政署人事室主任劉永福表示，警政署差勤系統為內部網路，沒有連接外部，尚未發現危害資安的情事，已全面停止使用相關設備；警政署並請廠商提出完整產地說明，送資安署確認 [@src-20260715-cts-500e9759]。

海巡署於當日在海洋委員會網站發布說明，表示艦隊分署差勤系統的得標廠商疑似使用中國貼牌產品，該分署已立即下架停用並全部汰換完竣 [@src-20260715-oac-5d652ef0]。中央社與 Newtalk 報導，海巡署表示，該問題是在 2025 年 12 月清查所屬資安設備時主動發現，系統含中國廠牌產品，違反採購須知「不得為中國大陸製產品，應檢附原產地文件」等規定，並於同月下架停用；系統未連結內部網路，差勤紀錄存於系統主機，因此尚無資安外洩疑慮 [@src-20260715-cts-28e3841a] [@src-20260715-newtalk-e237c03c]。

財政部關務署表示，經清查，台北關與高雄關曾向同一廠商採購差勤設備，設備採封閉式主機、不對外連網，因此認為目前沒有個資外洩風險，但為求慎重，已責成兩關立即停用；中央社的報導寫成關務署「將立即全數停用」，自由時報寫成「已責成兩關立即全面停用」；關務署並表示，資訊服務採購契約範本要求廠商不得提供或使用中國大陸廠牌的資通訊產品 [@src-20260715-cts-cb4cc0be] [@src-20260715-ltn-456351f6]。

中時新聞網與 ETtoday 的報導未載警政署、關務署、海巡署或中油的回應 [@src-20260715-chinatimes-c2b689da] [@src-20260715-ettoday-a0bbe4fe]。

## 林俊憲的要求與數發部資安署的說明

林俊憲表示，各機關對生物辨識設備是否屬「敏感性採購」的認定標準不一致，並要求：曾採購相關設備的機關全面清查設備來源並確保資料未外洩；數位發展部資通安全署規定涉及個資蒐集的設備一律列為敏感性採購；行政院公共工程委員會檢討採購制度，對敏感性採購參考最有利標精神 [@src-20260715-cts-500e9759] [@src-20260715-chinatimes-c2b689da]。

數位發展部資安署綜合規劃組長李東宜表示，資安署已訂定敏感性業務範疇，採購範本規定各單位自認屬敏感的資通系統不得採購，資安署將評估是否把處理個人資料的資通系統採購納入該範疇 [@src-20260715-chinatimes-c2b689da]。自由時報 7 月 16 日的報導寫成，李東宜表示未來會研議把個人資料的蒐集及利用納入業務範疇 [@src-20260716-ltn-8bea6fc4]。

## 資料限制

本頁依 2026 年 7 月 15 至 16 日的報導與海洋委員會的說明整理。除海巡署自行說明其設備含中國廠牌產品外，「貼牌」與產地認定來自林俊憲的說法；本頁未查得廠商、熵基科技、警政署或關務署對產地的正式查證結果，本頁不作判定 [@src-20260715-cts-500e9759] [@src-20260715-cts-28e3841a]。

## 2026-07-15　報導

自由時報以「林俊憲揭差勤機竟用「中國貼牌」廠商 警政署：已全面停用」為題報導 [@src-20260715-ltn-e0af5abc]。

自由時報以「林俊憲爆差勤系統使用中國貼牌貨  海巡署：已全部汰換」為題報導 [@src-20260715-ltn-5b56f220]。
