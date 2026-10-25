import unittest

from tools.newsfetch import topics


def item(url, title, day, publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


CORPUS = [
    item("https://news.ltn.com.tw/news/politics/breakingnews/1", "仁愛圓環6年對比「綠樹幾乎消失」！杜奕瑾質疑：這麼多棵同時得絕症？", "2026-09-26"),
    item("https://news.ltn.com.tw/news/life/breakingnews/2", "仁愛圓環6年對比「綠樹幾乎消失」？北市公園處回應了", "2026-09-26"),
    item("https://news.ltn.com.tw/news/life/paper/3", "杜奕瑾揭6年對比 仁愛圓環綠樹消失", "2026-09-27"),
    item("https://news.ltn.com.tw/news/life/breakingnews/4", "仁愛圓環樹木 杜奕瑾臉書PO文再質疑", "2026-09-29"),
    item("https://news.ltn.com.tw/news/life/breakingnews/5", "颱風來襲 北市公園處加強巡查", "2026-09-28"),
    item("https://news.ltn.com.tw/news/life/breakingnews/6", "北市公園處說明行道樹修剪原則", "2026-09-28"),
    item("https://news.ltn.com.tw/news/life/breakingnews/7", "北市公園處舉辦花展", "2026-09-20"),
    item("https://news.ltn.com.tw/news/life/breakingnews/8", "仁愛路車禍 機車騎士送醫", "2026-09-26"),
    item("https://www.ey.gov.tw/Page/1", "行政院說明仁愛圓環周邊交通", "2026-09-27", "行政院", "official_statement"),
]
SEED = {"event_id": "ev-20260926-taipei-renai-roundabout-trees", "seed_urls": [CORPUS[0]["url"], CORPUS[1]["url"]],
        "jurisdiction_names": ["臺北市"]}


class TopicTest(unittest.TestCase):
    def setUp(self):
        self.df = topics.document_frequency(CORPUS)

    def test_name_is_the_distinctive_phrase(self):
        key = topics.pick_key([CORPUS[0]["title"], CORPUS[1]["title"]], self.df, len(CORPUS))
        self.assertEqual(key, "仁愛圓環")

    def test_longer_phrase_wins_when_it_covers_the_same_seeds(self):
        corpus = [item(f"u{i}", t, "2026-05-12") for i, t in enumerate(
            ["淡江大橋通車首日", "淡江大橋機車道太窄", "淡江大橋祈福", "長江大橋觀光"])]
        df = topics.document_frequency(corpus)
        self.assertEqual(topics.pick_key([c["title"] for c in corpus[:3]], df, 60000), "淡江大橋")

    def test_generic_phrase_loses_to_specific_phrase(self):
        corpus = [item("a", "恆春中元豎孤棚網傳假徵才 鎮公所急澄清", "2026-07-12"),
                  item("b", "豎孤棚徵才？ 恆春鎮公所澄清是詐騙", "2026-07-13")]
        corpus += [item(f"g{i}", f"第{i}鄉鎮公所辦活動", "2026-07-01") for i in range(80)]
        df = topics.document_frequency(corpus)
        dfw = topics.window_frequency(corpus, topics._day("2026-07-05"), topics._day("2026-08-12"))
        self.assertEqual(topics.pick_key([corpus[0]["title"], corpus[1]["title"]], df, 60000, dfw=dfw), "豎孤棚")

    def test_display_name_takes_a_dominant_noun_form(self):
        titles = ["花蓮萬里溪上游驚現堰塞湖", "花蓮萬里溪堰塞湖蓄水量估達600萬", "萬里溪堰塞湖持續蓄積", "萬里溪堰塞湖黃色警戒"]
        self.assertEqual(topics.display_name("萬里溪", titles), "萬里溪堰塞湖")

    def test_display_name_never_cuts_a_place_on_the_left(self):
        titles = ["南投名間焚化爐環評", "名間焚化爐自救會", "名間焚化爐抗爭", "焚化爐選址爭議"]
        self.assertEqual(topics.display_name("焚化爐", titles), "焚化爐")

    def test_display_name_of_a_short_key_comes_from_the_first_seed(self):
        titles = ["遭控「移工懷孕雇主養他全家」 勞動部駁斥", "失聯移工就地合法引反對", "失聯移工見警駕車逃竄", "疑失聯移工躲查緝"]
        self.assertEqual(topics.display_name("移工", titles), "移工懷孕")

    def test_display_name_keeps_earlier_good_names(self):
        self.assertEqual(topics.display_name("薔琵", ["強颱「薔琵」本週恐生成", "薔琵颱風逼近", "薔琵颱風來襲", "颱風薔琵發威"]), "薔琵颱風")
        self.assertEqual(topics.display_name("和山", ["高雄大樹和山光電場邊坡滑落", "大樹和山案場遭AI造假", "和山光電限期改善"]), "大樹和山")

    def test_title_adds_the_jurisdiction(self):
        self.assertEqual(topics.topic_title("仁愛圓環", ["臺北市"]), "臺北市仁愛圓環")
        self.assertEqual(topics.topic_title("臺北市仁愛圓環", ["臺北市"]), "臺北市仁愛圓環")
        self.assertEqual(topics.topic_title("薔琵颱風", ["高雄市"], national=True), "薔琵颱風")
        self.assertEqual(topics.topic_title("馬鈴薯", ["高雄市"], national=True, generic=True), "高雄市馬鈴薯")

    def test_generic_key_needs_a_place(self):
        corpus = [item("s1", "南投名間焚化爐環評會衝突", "2026-05-01"), item("s2", "南投焚化爐自救會抗爭", "2026-05-02"),
                  item("s3", "名間焚化爐自救會陳情", "2026-05-02"),
                  item("m1", "名間焚化爐環評再開會", "2026-05-03"), item("x1", "台中焚化爐歲修", "2026-05-03")]
        corpus += [item(f"g{i}", f"焚化爐新聞{i}", "2026-01-01") for i in range(30)]
        df = topics.document_frequency(corpus)
        seed = {"event_id": "e", "seed_urls": ["s1", "s2", "s3"], "jurisdiction_names": ["南投縣"], "jurisdiction_ids": ["jur-10008000"]}
        urls = {m["url"] for m in topics.members(seed, corpus, df)}
        self.assertIn("m1", urls)
        self.assertNotIn("x1", urls)  # another county's incinerator

    def test_members_share_the_key_and_window(self):
        members = topics.members(SEED, CORPUS, self.df)
        urls = {m["url"] for m in members}
        self.assertIn(CORPUS[3]["url"], urls)
        self.assertNotIn(CORPUS[7]["url"], urls)  # 仁愛路, not 仁愛圓環
        self.assertNotIn(CORPUS[4]["url"], urls)

    def test_members_need_an_anchor_term(self):
        titles = [
            ("s1", "離譜！台中市府上訴逾期1天遞狀 好市多A肝莓果案200萬免罰", "2026-06-17"),
            ("s2", "行政作業出包好市多閃過200萬罰單 中市衛生局長道歉自請處分", "2026-06-18"),
            ("m1", "中市府「慢1天上訴」好市多閃過200萬罰單 綠轟公信力失守", "2026-06-18"),
            ("m2", "台中食安事件連發 天選之肉、非洲豬瘟、好市多A肝莓果官司被翻出", "2026-07-16"),
            ("x1", "確定了！全台最大間好市多新高雄店7/3開幕", "2026-06-12"),
            ("x2", "台南芒果首銷英國超市 上架日本好市多", "2026-07-08"),
            ("x3", "桃園市蘆竹饋線跳脫釀565戶停電 好市多一度受影響", "2026-07-15"),
        ]
        # No background: 好市多 news is concentrated in the window, so the place filter does not start.
        corpus = [item(u, t, d) for u, t, d in titles]
        df = topics.document_frequency(corpus)
        seed = {"event_id": "e", "seed_urls": ["s1", "s2"], "jurisdiction_names": ["臺中市"], "jurisdiction_ids": ["jur-66000000"]}
        urls = {m["url"] for m in topics.members(seed, corpus, df)}
        self.assertEqual(urls, {"s1", "s2", "m1", "m2"})

    def _members(self, seeds, others, filler=()):
        """Member urls of a topic. `filler` titles are background news that make a word common."""
        corpus = [item(u, t, d) for u, t, d in seeds + others]
        corpus += [item(f"f{i}", t, "2026-03-01") for i, t in enumerate(filler)]
        df = topics.document_frequency(corpus)
        seed = {"event_id": "e", "seed_urls": [u for u, _, _ in seeds], "jurisdiction_names": ["臺中市"],
                "jurisdiction_ids": ["jur-66000000"]}
        return {m["url"] for m in topics.members(seed, corpus, df)}

    COSTCO_SEEDS = [
        ("s1", "離譜！台中市府上訴逾期1天遞狀 好市多A肝莓果案200萬免罰", "2026-06-17"),
        ("s2", "行政作業出包好市多閃過200萬罰單 中市衛生局長道歉自請處分", "2026-06-18"),
        ("s3", "好市多「A肝莓果案」中市府出包變免罰 他嘆：盧媽媽又把責任推給基層", "2026-06-18"),
        ("s4", "中市府「慢1天上訴」好市多閃過200萬罰單 綠轟公信力失守", "2026-06-18"),
    ]
    COSTCO_OTHERS = [
        ("kaohsiung", "高市好市多雞蛋沙拉遭控吃到衛生紙 衛生局二度稽查無異狀", "2026-06-15"),
        ("oil", "中聯致癌油、美國蔬菜及蛋白粉連出包 好市多回應下架", "2026-07-15"),
        ("later", "台中食安事件連發 天選之肉、非洲豬瘟、好市多A肝莓果官司被翻出", "2026-07-16"),
        ("paper", "《逾期一天上訴》好市多重罰遭撤銷 議員批盧市府螺絲鬆", "2026-06-19"),
    ]
    # Common words: 衛生局 and 出包 are in many unrelated items of the corpus.
    COMMON = [f"第{i}區衛生局稽查餐廳" for i in range(60)] + [f"第{i}號工程出包" for i in range(60)]

    def test_a_common_word_does_not_join_another_issue(self):
        urls = self._members(self.COSTCO_SEEDS, self.COSTCO_OTHERS, self.COMMON)
        self.assertNotIn("kaohsiung", urls)  # shares only the common word 衛生局
        self.assertNotIn("oil", urls)        # shares only the common word 出包

    def test_a_rare_word_of_two_core_titles_is_an_anchor(self):
        urls = self._members(self.COSTCO_SEEDS, self.COSTCO_OTHERS, self.COMMON)
        self.assertIn("later", urls)   # A肝莓果 is in no seed title, but in two core titles
        self.assertIn("paper", urls)   # 逾期一天上訴 / 螺絲

    def test_a_title_of_a_sub_issue_in_the_seeds_joins(self):
        seeds = [("a", "統促黨幹部 屏東里長參選人送肉粽遭偵辦", "2026-10-03"),
                 ("b", "持刀闖花蓮東大門夜市！ 統促黨男殺人未遂收押", "2026-10-09"),
                 ("c", "內政部聲請解散統促黨 學者：切斷中國在台協力者執行體系", "2026-07-30")]
        others = [("moi", "141黨員涉殺人未遂、毒品近百案 刑事局：統促黨實為犯罪組織", "2026-07-31"),
                  ("far", "統促黨成立三十週年餐敘", "2026-08-01")]
        urls = self._members(seeds, others)
        self.assertIn("moi", urls)
        self.assertNotIn("far", urls)

    def test_a_common_event_word_does_not_join_another_county(self):
        seeds = [("a", "一觸即發！彰化芳苑火葬場今辦說明會 自救會：選址不當立即撤案", "2026-05-05"),
                 ("b", "彰化生命園區抗議聲中動土！王惠美堅持一定要做：這裡最適合", "2026-07-28"),
                 ("c", "反設芳苑生命園區 數百鄉親抗議", "2026-05-06")]
        others = [("pingtung", "內政部挹注1.47億元 強化東港生命園區聯外交通 屏東公道三新闢工程動土", "2026-07-23")]
        common = [f"第{i}校舍動土典禮" for i in range(60)]
        self.assertNotIn("pingtung", self._members(seeds, others, common))

    def _issue(self, seeds, others, names, ids, filler=200, common=()):
        """Member urls for real titles. `filler` unrelated titles make the corpus big, so a word such as 通車 is rare.
        `common` words are in 60 other titles, so they are not rare."""
        corpus = [item(u, t, d, **x) for u, t, d, *rest in seeds + others for x in [rest[0] if rest else {}]]
        corpus += [item(f"f{i}", f"第{i}號無關新聞 氣象消息", "2026-03-01") for i in range(filler)]
        corpus += [item(f"c{i}", f"第{i}次查獲{w}案", "2026-03-01") for w in common for i in range(60)]
        df = topics.document_frequency(corpus)
        seed = {"event_id": "e", "seed_urls": [u for u, *_ in seeds], "jurisdiction_names": names, "jurisdiction_ids": ids}
        return {m["url"] for m in topics.members(seed, corpus, df)}

    DANJIANG = [
        ("d01", "淡江大橋5/12通車！橋上野餐、音樂會吸引逾15萬人次", "2026-05-03"),
        ("d02", "淡江大橋機車道被嫌太窄 李四川：需要進行工程改善", "2026-05-04"),
        ("d03", "李四川質疑淡江大橋機車道有危險 交通部：符合法規", "2026-05-07"),
        ("d04", "淡江大橋明通車 無人機違規拍攝最高開罰30萬", "2026-05-11"),
        ("d05", "通車在即！淡江大橋遭批護欄不符設計規範、螺帽外露？ 交通部澄清", "2026-05-11"),
        ("d06", "淡江大橋明通車沒邀侯友宜？公路局：簡單祈福未邀首長民代", "2026-05-11"),
        ("d07", "淡江大橋通車祈福未邀新北市府 藍議員江怡臻：令人心寒", "2026-05-11"),
        ("d08", "淡江大橋通車！今天僅橋管中心揭牌 議員里長抗議未獲邀", "2026-05-12"),
        ("d09", "公路局致電不要參加淡江大橋通車 淡水、八里區長：一起祈福是好事", "2026-05-12"),
        ("d10", "淡江大橋通車祈福不揪地方 藍議員：新北負擔79億、交通部有失周延", "2026-05-12"),
        ("d11", "新北「千陽號主燈」慶淡江大橋通車 遭疑非全國首座、台南早就展過", "2026-05-12"),
        ("d12", "新北市府未受邀淡江大橋通車祈福 李四川：橋梁沒分顏色 建設也沒分藍綠", "2026-05-12"),
        ("d13", "淡江大橋通車首日淡水、八里端匝道回堵 鄭宇恩機車實測提建議", "2026-05-12"),
        ("d14", "淡江大橋今正式通車 護欄、螺帽包覆調整改善", "2026-05-12"),
        ("d15", "淡江大橋今通車！中央被指「搶功」未邀新北 卓榮泰：我也沒被邀", "2026-05-12"),
        ("d16", "陳世凱參加淡江大橋通車活動立院備詢請假 藍委：觀感不好", "2026-05-12"),
        ("d17", "淡江大橋今通車 藍營民代批陳世凱為剪綵缺席總質詢", "2026-05-12"),
        ("d18", "淡江大橋昨通車侯友宜稱「有點混亂」 紓解關渡橋車流奏效", "2026-05-13"),
        ("d19", "淡江大橋5/12通車「碰巧」陳世凱生日  公路局急澄清", "2026-05-13"),
        ("d20", "淡江大橋5/12通車遭抹黑「為交長慶生」 公路局狠打臉", "2026-05-13"),
        ("d21", "淡江大橋通車首日 行人大讚友善、機車飆仔被開4張罰單", "2026-05-13"),
        ("d22", "淡江大橋通車第2天！他追撞紅燈車陣 釀首起連環車禍", "2026-05-13"),
    ]
    DANJIANG_LOST = [  # on topic, and no rare word in common with the seeds
        ("opening", "淡江大橋5/12通車 卓揆：打造臺灣最新名片 展現國家實力與文明的新地標", "2026-05-07"),
        ("before", "扯！淡江大橋通車前機車硬闖挨罰扣車 異想天開偷貨車來載", "2026-05-19"),
        ("week", "淡江大橋通車滿1週！ 洪孟楷緊盯淡水端交織回堵、螺絲鬆動問題", "2026-05-20"),
        ("steel", "鋼結構建材90％可回收 中龍鋼鐵邀淡江大橋、綠美圖團隊研討", "2026-04-29"),
        ("typhoon", "輕颱薔蜜恐貼東部外海北上  淡江大橋「封橋」條件曝", "2026-05-27"),
    ]

    DANJIANG_OUTSIDE = [  # other months: the key is also in later news (typhoon closures, accidents), so it is not specific
        ("o01", "淡江大橋機車道救援 擬設活動柵欄", "2026-04-24"),
        ("o02", "淡江大橋超窄機車道引安全憂慮 李四川：新北大橋曾有同樣問題", "2026-04-25"),
        ("o03", "強颱巴威17級強風週末襲台 淡江大橋封橋條件曝光", "2026-07-07"),
        ("o04", "強颱巴威將襲台 公路局：風速10級將封閉淡江大橋", "2026-07-08"),
        ("o05", "淡江大橋今晚11時全面封閉  警方提醒用路人改道", "2026-07-10"),
        ("o06", "騎士淡江大橋自摔  公路局澄清：14分鐘送醫、絕無回堵和二次事故", "2026-07-24"),
        ("o07", "淡江大橋機車道車禍 交通部還原救援過程", "2026-07-25"),
        ("o08", "白海豚颱風週末最接近台灣 交通部：不排除再封淡江大橋", "2026-08-06"),
        ("o09", "淡江大橋看煙火 議員促設景觀平台", "2026-08-19"),
        ("o10", "電輔自行車可騎上淡江大橋了！公路局擬加嚴「風力封橋」規定", "2026-09-14"),
        ("o11", "颱風薔琵影響淡江大橋預警性封閉　擬下午5時解除", "2026-10-24"),
        ("o12", "颱風漸遠離 淡江大橋下午5點後開放通車", "2026-10-24"),
    ]

    def test_a_key_of_one_story_keeps_its_own_titles(self):
        """淡江大橋: 通車 is in most core titles, so every title with the key is on topic."""
        seeds = self.DANJIANG
        urls = self._issue(seeds, self.DANJIANG_LOST + self.DANJIANG_OUTSIDE, ["新北市"], ["jur-65000000"])
        for u, *_ in self.DANJIANG_LOST:
            self.assertIn(u, urls)

    def test_a_title_with_a_companion_word_joins(self):
        """安南區 is a place, so it needs a companion: 爆炸 is in most core titles. The three titles about the
        stationery, the pet fair and the sports center stay out."""
        core = [("a1", "台南安南區爆炸驚魂！ 後備軍人暖心救援", "2026-08-22"),
                ("a2", "現場直擊》安南區大爆炸14人送醫  百公尺內住戶鐵門歪、玻璃碎", "2026-08-22"),
                ("a3", "台南安南區廢棄物火警濃煙竄天 氨氣一度達20ppm", "2026-08-22"),
                ("a4", "台南安南區爆炸40戶受影響 後續賠償待紅黃單鑑定", "2026-08-22"),
                ("a5", "台南安南區火警爆炸案 消防局還原救災過程", "2026-08-22"),
                ("a6", "安南區爆炸驚擾住宅區 議員籲全面清查危險廢棄物場址", "2026-08-22"),
                ("a7", "台南安南區火災大爆炸 當地里長等3嫌收押禁見", "2026-08-24"),
                ("a8", "台南安南區空地火堆大爆炸 15人傷、燒11戶 疑堆置鎂鋁、廢油爆炸 57戶民宅波及受損", "2026-08-23")]
        later = [("w1", "台南安南區空地堆置廢棄物引發火警 市府全力灌救、安置民眾並啟動後續處置", "2026-08-21"),
                 ("w2", "安南區空地竄詭異白火！  消防死守火線防堵火勢", "2026-08-22"),
                 ("w3", "社工與民眾同在 臺南安南區火災爆炸案 社會局社工團隊23日至災區關懷受災戶", "2026-08-23"),
                 ("fire", "台南安南區凌晨火災驚爆！3消防、11民眾受傷 多輛消防車燒毀", "2026-08-22"),
                 ("visit", "安南區火災爆炸事故 趙卿惠副市長慰問嚴重受災戶 市府全力協助家園復原", "2026-08-25"),
                 ("car", "安南區火災爆炸事故 市府提供車損慰助金 以降低民眾財損壓力", "2026-09-16"),
                 ("pet", "安南區萌萌寵物嘉年華登場 黃偉哲籲響應認養代替購買", "2026-09-13"),
                 ("kit", "愛心相挺迎開學 安南區360份文具大禮包助學童安心學習", "2026-09-14"),
                 ("gym", "安南區全民運動館結合在地學校 帶領九份子國小學童體驗植栽落實永續回饋", "2026-09-16"),
                 # other months: 安南區 is a place, so the key is shared with other news
                 ("p1", "北外環2期明年中完工  4期展開協議價購  北區與安南區受益快速路網效應", "2026-04-30"),
                 ("p2", "台南科工區引資290億 將增逾6千個就業機會  周圍安南區首購宅仍3字頭房價", "2026-05-18"),
                 ("p3", "台南安南區夜間火警 2樓竄火舌波及3車", "2026-05-20"),
                 ("p4", "黃偉哲市長爭取9千萬打造安南區兩座地下滯洪池 解鎖安中路水患「最後一塊拼圖」", "2026-05-25"),
                 ("p5", "安南區疑似宰殺犬隻案 動保處：現場犬隻經X光檢查均無骨折 可疑檢體初判非犬隻組織仍送驗確認", "2026-07-08"),
                 ("p6", "巴威颱風逼近 黃偉哲赴安南區視察防颱整備 全面強化防災應變守護市民安全", "2026-07-09"),
                 ("p7", "謝龍介站台力挺李中岑 籲守住安南區唯一藍營席次", "2026-10-04"),
                 ("p8", "怡中市地重劃完工啟用 黃偉哲：完善公共設施、提升安南區發展機能", "2026-10-13")]
        urls = self._issue(core, later, ["臺南市"], ["jur-67000000"], common=("火災", "爆炸", "市府", "事故", "慰問", "民眾"))
        self.assertTrue({"fire", "visit", "car"} <= urls)
        self.assertFalse({"pet", "kit", "gym"} & urls)

    def test_a_response_of_an_official_or_a_fact_check_joins(self):
        """移工: the labor ministry answer and two fact checks join. Arrests of 失聯移工 are other news."""
        seeds = [("s1", "遭控「移工懷孕雇主養他全家」 勞動部駁斥：嚴重錯誤資訊", "2026-10-13"),
                 ("s2", "遭控縱容雇主鑽漏洞剝削履約移工 勞動部提出5點回應", "2026-10-15"),
                 ("s3", "移工政策惹民怨！雇主協會調查94％不滿意 近9成反對失聯移工就地合法", "2026-10-15"),
                 ("s4", "逾9成家事移工雇主不滿移工政策要求改革 勞動部這麼說", "2026-10-15")]
        others = [("mol", "民間團體於今日（15）針對移工雇主權益所召開之記者會，勞動部回應", "2026-10-15",
                   {"source_class": "official_statement", "publisher": "行政院"}),
                  ("fc1", "【誤導】移工來臺費用最高19萬元全由雇主買單？圖卡混淆適用對象與實施時程", "2026-10-15",
                   {"source_class": "fact_check", "publisher": "MyGoPen"}),
                  ("fc2", "【錯誤】網傳「印尼群組攻略」教移工領百萬老年給付？惡意解讀！不實說法且金額誇大", "2026-10-16",
                   {"source_class": "fact_check", "publisher": "MyGoPen"}),
                  ("crime1", "騎註銷車牌機車還闖紅燈 警壓制逮越南失聯移工", "2026-10-21"),
                  ("crime2", "未打方向燈露餡 通緝犯載4失聯移工被警攔查逮捕", "2026-10-09")]
        corpus = [item(u, t, d, **(x[0] if x else {})) for u, t, d, *x in seeds + others]
        corpus += [item(f"c{i}", f"第{i}次查獲{w}案", "2026-03-01") for w in ("失聯", "雇主", "勞動部") for i in range(60)]
        df = topics.document_frequency(corpus)
        cands = [c for c in corpus if "移工" in c["title"]]
        urls = {c["url"] for c in topics.anchored(cands, [t for _, t, _ in seeds], ["移工"], df, len(corpus))}
        self.assertTrue({"mol", "fc1", "fc2"} <= urls)
        self.assertFalse({"crime1", "crime2"} & urls)

    def test_a_long_rare_key_is_its_own_anchor(self):
        """續放颱風假 is one phrase for one event. The Taipei titles with it join the Taichung seeds."""
        seeds = [("s1", "台中人續放颱風假 百貨公司人潮「恢復假日水準」", "2026-10-24"),
                 ("s2", "續放颱風假！台中人開逛百貨\u3000鹿港老街人潮少3成", "2026-10-24")]
        others = [("s3", "台中續放颱風假 各大百貨宣布今正常營業", "2026-10-24"),
                  ("s4", "台中人7點沒等到是否繼續放颱風假 市府：20:00宣布", "2026-10-23"),
                  ("cna", "台北續放颱風假\u3000部分醫院開設特別門診", "2026-10-23"),
                  ("storm", "北市10/24續放颱風假！網友灌爆蔣萬安臉書：我們做你的靠山，不怕什麼流", "2026-10-23"),
                  ("storm2", "薔琵颱風最新動態》明天10/24繼續放颱風假？「10縣市暴風侵襲率衝100%」，最劇烈風雨時段曝", "2026-10-23")]
        corpus = [item(u, t, d) for u, t, d in seeds + others]
        corpus += [item(f"f{i}", f"第{i}號無關新聞 氣象消息", "2026-03-01") for i in range(100)]
        df = topics.document_frequency(corpus)
        cands = [c for c in corpus if "續放颱風假" in c["title"]]
        urls = {c["url"] for c in topics.anchored(cands, [t for _, t, _ in seeds], ["續放颱風假"], df, len(corpus))}
        self.assertTrue({"cna", "storm", "storm2"} <= urls)

    def test_a_long_key_used_in_other_counties_is_not_its_own_anchor(self):
        """全民運動館 is a facility type: 20 uses in the corpus, 7 in the Miaoli window. Tainan and Taitung titles stay out."""
        seeds = [("m1", "World Gym營運苗栗市全民運動館 林月琴質疑成私人健身房 余文忠回應了", "2026-08-26"),
                 ("m2", "苗栗全民運動館委外惹議 林月琴轟「苗栗版馬關條約」余文忠不再回應", "2026-08-27"),
                 ("m3", "質疑1.72億苗栗市全民運動館涉圖利 林月琴：余文忠別再問A答B", "2026-08-28")]
        others = [("m4", "苗栗全民運動館委外 林月琴質疑圖利私人", "2026-08-28"),
                  ("t1", "體育局長視察永康全民運動館 打造健康城市 體育建設再升級", "2026-09-11"),
                  ("t2", "安南區全民運動館結合在地學校 帶領九份子國小學童體驗植栽落實永續回饋", "2026-09-16"),
                  ("t3", "新營全民運動館進度97％ 月底竣工", "2026-09-19"),
                  ("t4", "新營全民運動館進度達75%！市府技監親赴視察 確保115年如期如質完工", "2026-04-24"),
                  ("t5", "安南全民運動館完工倒數 黃偉哲視察強調兼顧全齡運動與文化意象", "2026-04-27"),
                  ("t6", "打造運動新據點 永康、仁德全民運動館招商", "2026-05-22"),
                  ("t7", "臺南四座全民運動館ROT招商成功 打造全齡運動新生活", "2026-07-16"),
                  ("t8", "視察安南全民運動館 落實工程品質力拚市府優質獎及中央金質獎", "2026-08-13"),
                  ("t9", "永康、仁德全民運動館ROT案完成簽約 臺南運動設施再添新據點", "2026-09-28"),
                  ("t10", "永康全民運動館工程查核獲甲等 進度超前 市府持續嚴格把關品質", "2026-10-07"),
                  ("t11", "台南安南區全民運動館招商涉行賄 市府：涉案被告未得標", "2026-10-19"),
                  ("t12", "台東全民運動館開幕！攀岩、街舞、練團室 從青少年到銀髮族都能玩", "2026-10-24")]
        corpus = [item(u, t, d) for u, t, d in seeds + others]
        corpus += [item(f"f{i}", f"第{i}號無關新聞 氣象消息", "2026-03-01") for i in range(100)]
        df = topics.document_frequency(corpus)
        window = [c for c in corpus if "全民運動館" in c["title"] and "2026-08-20" <= c["published_on"] <= "2026-09-20"]
        urls = {c["url"] for c in topics.anchored(window, [t for _, t, _ in seeds], ["全民運動館"], df, len(corpus))}
        self.assertTrue({"m1", "m2", "m3", "m4"} <= urls)
        self.assertFalse({"t1", "t2", "t3"} & urls)

    def test_kinds(self):
        self.assertEqual(topics.kind_of(CORPUS[0]), "report")
        self.assertEqual(topics.kind_of(CORPUS[1]), "clarification")
        self.assertEqual(topics.kind_of(CORPUS[3]), "post")
        self.assertEqual(topics.kind_of(CORPUS[8]), "official")
        self.assertEqual(topics.kind_of(item("u", "標題", "2026-09-26", quote="杜奕瑾在臉書PO出對比圖")), "post")

    def test_same_content_groups_merge_paper_copy(self):
        members = topics.members(SEED, CORPUS, self.df)
        groups = topics.group_items(members)
        news = [g for g in groups if g["kind"] != "official"]
        first = [g for g in news if CORPUS[0]["url"] in g["urls"]][0]
        self.assertEqual(first["kind"], "report")
        self.assertIn(CORPUS[2]["url"], first["urls"])  # the paper copy of item 0
        clar = [g for g in news if g["kind"] == "clarification"]
        self.assertEqual([g["urls"] for g in clar], [[CORPUS[1]["url"]]])

    def test_official_never_in_news_groups(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={"www.ey.gov.tw": ("行政院", "ac-executive-yuan", "ey")})
        group_urls = {u for g in event["news_groups"] for u in g["source_urls"]}
        self.assertNotIn(CORPUS[8]["url"], group_urls)
        self.assertTrue(all(g["kind"] in ("report", "clarification", "post") for g in event["news_groups"]))
        self.assertTrue(all(g.get("note") for g in event["news_groups"] if g["kind"] == "clarification"))

    def test_station_titles_are_neutral_counts(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={})
        for t in event["timeline"]:
            self.assertRegex(t["title"], r"^\d+ 則")
            self.assertNotIn("「", t["title"])

    def test_kind_needs_two_stances(self):
        self.assertEqual(topics.event_kind([{"actor_id": "a", "stance": "not_found"}]), "historical_event")
        self.assertEqual(topics.event_kind([{"actor_id": "a", "stance": "support"}, {"actor_id": "b", "stance": "oppose"}]), "controversy")
        self.assertEqual(topics.event_kind([{"actor_id": "a", "stance": "support"}, {"actor_id": "a", "stance": "oppose"}]), "historical_event")

    def test_benign_phrases_are_not_sensitive(self):
        self.assertFalse(topics.has_sensitive_term(["呼籲市府全面體檢危險廢棄物堆置場"]))
        self.assertFalse(topics.has_sensitive_term(["為解決民眾就醫需求，醫院開設門診"]))
        self.assertTrue(topics.has_sensitive_term(["病患就醫紀錄外洩"]))
        self.assertTrue(topics.has_sensitive_term(["市長公開體檢報告"]))

    @unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
    def test_sensitive_from_source_quotes(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            for d in ("events/2026", "sources/2026", "actors"):
                (Path(root) / d).mkdir(parents=True)
            seed = dict(SEED, gov_levels=["special_municipality"], jurisdiction_ids=["jur-63000000"],
                        controversy_types=["environment"], policy_domains=["environment"], actors=[])
            event = topics.build_event(seed, CORPUS, self.df, actors_by_host={})
            topics.write_event(event, seed, root, {}, actors_by_host={})
            text = (Path(root) / "events/2026" / f"{seed['event_id']}.md").read_text(encoding="utf-8")
            self.assertIn("sensitive: false", text)
            quote = {CORPUS[1]["url"]: {"url": CORPUS[1]["url"], "status": "ok", "quote": "公園處表示將協助民眾就醫"}}
            topics.write_event(event, seed, root, quote, actors_by_host={})
            text = (Path(root) / "events/2026" / f"{seed['event_id']}.md").read_text(encoding="utf-8")
            self.assertIn("sensitive: true", text)

    def test_system_topics_have_no_lifecycle_stage(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={})
        self.assertTrue(all("lifecycle_stage" not in t for t in event["timeline"]))

    def test_review_status_is_draft(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={})
        self.assertEqual(event["review"]["status"], "draft-review")
        self.assertEqual(event["title"], "臺北市仁愛圓環")


if __name__ == "__main__":
    unittest.main()
