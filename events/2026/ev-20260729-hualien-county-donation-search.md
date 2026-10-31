---
schema_version: 1
id: ev-20260729-hualien-county-donation-search
kind: controversy
status: published
title: 花蓮縣府社會處遭搜索與震災善款調查
summary: 報導指，花蓮地檢署於 2026-07-29 搜索花蓮縣府社會處，調查 2018 年震災善款的帳目與運用 [@src-20260730-pts-hualien-search-bail]。縣府表示偵辦時機引發疑慮；檢方表示沒有政治考量 [@src-20260730-ettoday-hualien-prosecutor-reply]。案件在偵辦中。
start_date: '2026-07-29'
start_date_precision: day
gov_levels:
- county_city
jurisdiction_ids:
- jur-10015000
controversy_types:
- misconduct
policy_domains:
- health_welfare
- justice
actors:
- actor_id: ac-hualien-district-prosecutors-office
  role: reviewer
- actor_id: ac-hualien-county-government
  role: affected_party
- actor_id: ac-control-yuan
  role: reviewer
questions:
- id: q-01
  text: 檢方搜索的時機與動機是否涉及政治考量？
- id: q-02
  text: 2018 年感恩餐會與寄送感謝函的採購程序和預算流用，是否符合規定？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-hualien-county-government
  stance: other
  summary: 花蓮縣府表示，選舉將近之際大規模偵辦多年前的案件，恐引發外界對辦案時機的質疑，並請檢方客觀公正、偵查不公開。
  stated_on: '2026-07-29'
  source_ids:
  - src-20260730-ltn-hualien-county-timing
  - src-20260730-ettoday-hualien-prosecutor-reply
- id: pos-02
  question_id: q-01
  actor_id: ac-hualien-district-prosecutors-office
  stance: other
  summary: 花蓮地檢署主任檢察官表示，依目前蒐證結果，證據已達搜索及偵辦程度，沒有任何政治考量；案情細節因偵查不公開不予說明。
  stated_on: '2026-07-30'
  source_ids:
  - src-20260730-ettoday-hualien-prosecutor-reply
  - src-20260730-udn-hualien-prosecutor-targets
- id: pos-03
  question_id: q-02
  actor_id: ac-control-yuan
  stance: other
  summary: 監察院糾正案文指出，花蓮縣政府 2018 年感恩餐會與寄送感謝函的採購程序，以及預算流用，違反採購法與預算法等規定。
  stated_on: '2020-03-17'
  source_ids:
  - src-20200317-cy-hualien-correction
- id: pos-04
  question_id: q-02
  actor_id: ac-hualien-county-government
  stance: not_found
- id: pos-05
  question_id: q-02
  actor_id: ac-hualien-district-prosecutors-office
  stance: not_found
timeline:
- id: tl-01
  date: '2020-03-17'
  date_precision: day
  title: 監察院就感恩餐會與相關採購提出糾正案
  attributed_to: ac-control-yuan
  lifecycle_stage: decision
  source_ids:
  - src-20200317-cy-hualien-correction
  - src-20250723-newtalk-hualien-correction-date
- id: tl-02
  date: '2026-07-29'
  date_precision: day
  title: 花蓮地檢署搜索花蓮縣府社會處
  attributed_to: ac-hualien-district-prosecutors-office
  lifecycle_stage: institutional_response
  source_ids:
  - src-20260729-ettoday-hualien-search
  - src-20260730-pts-hualien-search-bail
- id: tl-03
  date: '2026-07-29'
  date_precision: day
  title: 花蓮縣府就偵辦時機發表聲明
  attributed_to: ac-hualien-county-government
  source_ids:
  - src-20260730-ltn-hualien-county-timing
  - src-20260730-ettoday-hualien-prosecutor-reply
- id: tl-04
  date: '2026-07-30'
  date_precision: day
  title: 社會處長以 40 萬元交保
  source_ids:
  - src-20260730-pts-hualien-search-bail
  - src-20260730-udn-hualien-prosecutor-targets
- id: tl-05
  date: '2026-07-30'
  date_precision: day
  title: 花蓮地檢署表示沒有政治考量
  attributed_to: ac-hualien-district-prosecutors-office
  source_ids:
  - src-20260730-ettoday-hualien-prosecutor-reply
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: true
  reason: 'draft-review: 由 agent 以網路搜尋建立（R330），不是系統分群形成；編輯尚未審閱。使用者於 2026-10-31 核准發佈，這是對兩位核准者規則的一次記錄在案的例外（R332），不是通則。本案仍在偵辦中，沒有起訴，也沒有判決。'
  status: draft-review
---

## 背景

監察院的糾正案文指出，花蓮縣政府於 2018 年 4 月 30 日辦理震災感恩餐會，與原規劃的 90 桌 900 人不同，改為宴請約 3,000 人；案文並指出該府採購被質疑規避政府採購法，且動支第二預備金並流用身心障礙福利業務預算 580 萬餘元 [@src-20200317-cy-hualien-correction]。Newtalk 報導，這項糾正案於 2020 年 3 月 17 日提出 [@src-20250723-newtalk-hualien-correction-date]。

## 搜索與調查

ETtoday 報導，花蓮地檢署於 2026 年 7 月 29 日持搜索票搜索花蓮縣府社會處，並向財政處、民政處調閱公文；調查標的是 2018 年花蓮地震後的善款流向 [@src-20260729-ettoday-hualien-search]。公視新聞網報導，社會處長被帶回調查站後移送複訊，並於 7 月 30 日以 40 萬元交保，限制出海與住居 [@src-20260730-pts-hualien-search-bail]；聯合新聞網報導，限制範圍為住居、出境及出海 [@src-20260730-udn-hualien-prosecutor-targets]。公視新聞網另報導，本案源於一件關於 0206 地震善款的檢舉，檢方依貪污罪嫌辦理 [@src-20260730-pts-hualien-search-bail]。聯合新聞網報導，主任檢察官表示偵辦對象包含現任社會處長、當年相關承辦人員、科員及部分廠商，共 6 人被帶回詢問；報導引述消息人士稱，檢方追查的金流達上千萬元 [@src-20260730-udn-hualien-prosecutor-targets]。本案仍在偵辦中，沒有判決。

## 各方立場

花蓮縣府表示，案件歷經多年，曾有多次調查，經辦人員也有更動；縣府表示配合調查，並指選前大規模偵辦久遠案件恐引發外界對時機的質疑 [@src-20260730-ltn-hualien-county-timing] [@src-20260730-ettoday-hualien-prosecutor-reply]。

花蓮地檢署主任檢察官表示，檢方依蒐證結果認定證據已達搜索程度，沒有政治考量；因偵查不公開，不說明涉嫌罪名細節 [@src-20260730-ettoday-hualien-prosecutor-reply]。

自由時報報導，一名民進黨籍花蓮市民代表在臉書表示尊重司法，並要求當年的主事者出面說明；一名縣議員表示縣府多次把問題推給善款管理委員會 [@src-20260730-ltn-hualien-green-camp]。該報導並引述縣議員的說法：縣府在調查後第一時間以臉書發文，指此案是政治辦案；此臉書發文不是對上述兩人說法的回應。

## 資料限制

各報對善款總額的數字不同，本頁不採用任何總額。檢方尚未公開起訴內容 [@src-20260730-udn-hualien-prosecutor-targets]。
