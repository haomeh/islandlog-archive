---
schema_version: 1
id: ev-20260821-tainan-annan-waste-fire
kind: historical_event
status: published
title: 臺南市安南區空地廢棄物火災爆炸與市府善後
summary: 2026-08-22 凌晨，臺南市安南區海佃路二段空地堆置的廢棄物起火爆炸。市府新聞稿表示 14 人受傷、延燒 11 戶 [@src-20260821-tainan-944e33e5]，並公布安置與補助措施 [@src-20260825-tainan-06433aac]。
start_date: '2026-08-22'
start_date_precision: day
gov_levels:
- special_municipality
- central
jurisdiction_ids:
- jur-67000000
- jur-tw
controversy_types:
- environment
- public_safety
policy_domains:
- environment
actors:
- actor_id: ac-tainan-city-government
  role: decision_maker
- actor_id: ac-office-of-the-president
  role: other
questions:
- id: q-01
  text: 安南區火災爆炸造成哪些損害，臺南市政府與總統府如何說明並處理善後？
positions:
- id: pos-01
  question_id: q-01
  actor_id: ac-tainan-city-government
  stance: other
  summary: 臺南市政府表示，首要工作是安置居民與恢復生活，並將追查廢棄物來源與責任；市府先發給受災戶緊急處理費，並將委託律師公會協助受災戶代位求償。
  stated_on: '2026-08-22'
  source_ids:
  - src-20260822-tainan-a288d359
  - src-20260823-cts-269ad251
  - src-20260825-tainan-06433aac
- id: pos-02
  question_id: q-01
  actor_id: ac-office-of-the-president
  stance: other
  summary: 總統府發言人表示，總統賴清德致電臺南市長黃偉哲，指示相關部會協助地方救災、傷者照護、居民安置與後續復原，並要求盡快查明起火與爆炸的原因及責任。
  stated_on: '2026-08-22'
  source_ids:
  - src-20260822-cts-af6bc559
timeline:
- id: tl-01
  date: '2026-08-22'
  date_precision: day
  title: 安南區海佃路二段空地廢棄物起火並發生爆炸，市府成立指揮中心
  attributed_to: ac-tainan-city-government
  source_ids:
  - src-20260821-tainan-944e33e5
  - src-20260822-cts-febd119f
  - src-20260822-newtalk-062094bb
  - src-20260822-ltn-f847a18f
  - src-20260822-ltn-4fb29eb4
- id: tl-02
  date: '2026-08-22'
  date_precision: day
  title: 市府召開記者會，總統府表示總統指示協助救災與復原
  attributed_to: ac-tainan-city-government
  source_ids:
  - src-20260822-tainan-a288d359
  - src-20260822-cts-af6bc559
  - src-20260822-chinatimes-f4d8449c
  - src-20260822-ltn-49410b12
- id: tl-03
  date: '2026-08-23'
  date_precision: day
  title: 社會局社工訪視受災戶，市府說明緊急處理費與代位求償安排
  attributed_to: ac-tainan-city-government
  source_ids:
  - src-20260823-tainan-e79ad873
  - src-20260823-cts-7962f028
  - src-20260823-cts-269ad251
- id: tl-04
  date: '2026-08-25'
  date_precision: day
  title: 副市長慰問嚴重受災戶，市府公布補助標準並延長申請期限
  attributed_to: ac-tainan-city-government
  source_ids:
  - src-20260825-tainan-06433aac
- id: tl-05
  date: '2026-09-16'
  date_precision: day
  title: 市府公布車損慰助金
  attributed_to: ac-tainan-city-government
  source_ids:
  - src-20260916-tainan-4b6f54d6
news_groups:
- id: ng-01
  timeline_id: tl-01
  kind: report
  title: 台南安南區空地廢棄物起火爆炸多人受傷 市府將查證處理
  representative_source_id: src-20260822-cts-febd119f
  source_ids:
  - src-20260822-cts-febd119f
  - src-20260822-newtalk-062094bb
  - src-20260822-ltn-f847a18f
  - src-20260822-ltn-4fb29eb4
- id: ng-02
  timeline_id: tl-02
  kind: report
  title: 台南安南大爆炸68戶遭殃！11戶嚴重受損 市府將協助受災民眾求償
  representative_source_id: src-20260822-chinatimes-f4d8449c
  source_ids:
  - src-20260822-chinatimes-f4d8449c
  - src-20260822-ltn-49410b12
- id: ng-03
  timeline_id: tl-02
  kind: report
  title: 台南安南起火爆炸 總統致電黃偉哲全力救災復原
  representative_source_id: src-20260822-cts-af6bc559
  source_ids:
  - src-20260822-cts-af6bc559
- id: ng-04
  timeline_id: tl-03
  kind: report
  title: 台南安南區爆炸案 市府擬助提集體訴訟代位求償
  representative_source_id: src-20260823-cts-269ad251
  source_ids:
  - src-20260823-cts-269ad251
  - src-20260823-cts-7962f028
privacy:
  contains_private_persons: false
  basis_source_ids: []
review:
  sensitive: false
  reason: 'draft-review: 系統原依爬取資料自動形成；2026-10-31 由 agent 依 R344 補入其他媒體與市府來源、改寫標題與內文，刑事偵辦不在本頁範圍。待兩位獨立驗證者確認（R336）。'
  status: draft-review
---

## 背景

臺南市政府新聞稿表示，2026 年 8 月 22 日凌晨 1 時許，安南區海佃路二段空地堆置的廢棄物起火，消防局 1 時 12 分接獲通報，5 時 20 分撲滅；14 人受傷，其中 3 人為消防人員，火勢延燒周邊 11 戶透天民宅，另有消防車、救護車與 13 輛民眾車輛受損 [@src-20260821-tainan-944e33e5]。

各報導的數字不同。Newtalk 刊出的報導寫 13 人送醫、延燒 8 戶、波及 20 輛車 [@src-20260822-newtalk-062094bb]；華視轉載的中央社報導寫 3 名警消與 11 名民眾受傷、波及 57 戶 [@src-20260822-cts-febd119f]；中時新聞網寫波及 68 戶，其中 11 戶嚴重受損 [@src-20260822-chinatimes-f4d8449c]；中央社 8 月 23 日的報導寫 11 戶嚴重延燒、102 戶受波及 [@src-20260823-cts-7962f028]；安南區長在自由時報的報導中估計約 40 戶受影響 [@src-20260822-ltn-49410b12]。本頁不判定哪個數字正確。

## 火場與起火物

消防局表示，現場有廢油桶、金屬鋁與金屬鎂；因有禁水性物質，先採周界防禦保護鄰近住宅，加上突降大雨，在物資抵達前即發生爆炸 [@src-20260822-tainan-a288d359]。自由時報報導，指揮官判定起火物為禁水性物質，不直接用水柱噴向火源，等待期間先出現小規模爆炸，接著發生大規模爆炸 [@src-20260822-ltn-4fb29eb4]。

環保局表示，會同環境部化學署技術小組監測，氣體偵測器數值正常；煙霧濃厚時氨氣檢知管曾測得 20 ppm，並呼籲安南區與永康區下風處民眾緊閉門窗、減少外出 [@src-20260821-tainan-944e33e5] [@src-20260822-tainan-a288d359]。起火原因與廢棄物來源仍在調查中 [@src-20260822-tainan-a288d359]。

## 臺南市政府的處置與說明

市府表示，已成立指揮中心，在普法道濟寺安置民眾並發放餐食，逐戶調查屋損並建立名冊；後續將依火調報告與跡證查處違規堆置 [@src-20260821-tainan-944e33e5]。市長黃偉哲表示，首要工作是協助居民安置與恢復生活，並將追查廢棄物來源與責任 [@src-20260822-tainan-a288d359]。

社會局表示，受災 11 戶每戶先領 2 萬元緊急處理費，並啟動「一戶一社工」；工務局將安排土木技師鑑定房屋結構，作為修繕與求償依據 [@src-20260822-tainan-a288d359]。8 月 23 日，社會局近 20 位社工冒雨訪視受災戶與臨時收容處所 [@src-20260823-tainan-e79ad873]。

中央社報導，副市長趙卿惠表示，市府將委託律師公會辦理集體訴訟，代受災民眾代位求償；黃偉哲決定由市府先提供經費處理受損房屋，之後再向違法廠商求償 [@src-20260823-cts-269ad251]。黃偉哲並表示，刑事部分由檢警偵辦，該空地曾由地主、區公所與里辦公處簽訂三方契約，初步看區公所為認養單位，但詳細責任須待司法認定，市府將加強各區公所對認養空地的管理 [@src-20260823-cts-7962f028]。

8 月 25 日，副市長趙卿惠慰問嚴重受災戶。市府新聞稿載明補助標準：受損嚴重的住戶每戶 12 萬元；海佃路二段 288 巷、342 巷受損住戶每受損樓層 1 萬元；其他受波及住戶每受損樓層 2,000 元；申請期限延長至 9 月 30 日 [@src-20260825-tainan-06433aac]。9 月 16 日，市府公布車損慰助金，汽車每輛最高 15,000 元，機車每輛最高 2,000 元，受理至 10 月 15 日 [@src-20260916-tainan-4b6f54d6]。

## 總統府的說明

總統府發言人郭雅慧表示，總統賴清德第一時間致電黃偉哲表達關心，並指示相關部會協助地方救災、傷者照護、居民安置與後續復原，要求相關單位盡快查明起火與爆炸的原因及責任 [@src-20260822-cts-af6bc559]。

## 資料限制

本頁記錄火災爆炸、受災情形與市府善後，不記錄刑事偵辦與人員到案的情形 [@src-20260823-cts-7962f028]。本頁依 2026 年 8 月 22 日至 9 月 16 日的市府新聞稿與 4 家媒體報導整理，未查得消防局的火調報告 [@src-20260822-tainan-a288d359]。
