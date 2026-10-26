"""T26 gate round (R154 to R157). Each rule has judged fail cases from the T25-P precision round (the titles are the real
headlines of the judged topics), one case from outside the judged list, and pass cases."""

import unittest

from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf


def item(url, title, day="2026-10-21", publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


def items(titles):
    return [item(f"u{i}", t, publisher=f"出版社{i % 2}") for i, t in enumerate(titles)]


class CutEdgeTest(unittest.TestCase):
    """R154: a key that lost its first or last part is a fragment. The gate rejects it and does not grow it."""

    def test_a_digit_before_the_key_cuts_the_name(self):
        judged = {
            "號演習": ["漢光42號演習登場 軍方人士：反封鎖護航是重要科目", "國軍漢光42號演習 澎湖進行補給品運補演練", "漢光42號演習登場！國軍現身富岡漁港"],
            "天免簽": ["泰國正式通過「取消60天免簽」", "泰國取消60天免簽 外交部：非針對單一國家", "泰國內閣批准「取消60天免簽」"],
            "下架標準": ["毒油20%下架標準誰訂的 國民黨籲公開會議紀錄", "藍委緊咬20％下架標準會議紀錄", "藍委質疑20%下架標準 食藥署：已送檢調調查"],
        }
        for key, titles in judged.items():
            self.assertTrue(tf.cut_edge(key, titles), key)

    def test_a_latin_letter_before_the_key_cuts_the_name(self):
        self.assertTrue(tf.cut_edge("肝群聚", ["板橋某診所爆C肝群聚11人確診", "安泰淞鶴診所C肝群聚擴大回溯", "爆C肝群聚診所喊冤"]))
        self.assertTrue(tf.cut_edge("型流感疫苗", ["A型流感疫苗接種率偏低", "A型流感疫苗庫存不足"]))  # outside the judged list

    def test_a_list_comma_before_the_key_cuts_the_name(self):
        self.assertTrue(tf.cut_edge("堰塞湖列法定天然災害", ["行政院會通過修正災防法 海嘯、堰塞湖列法定天然災害", "災防法修法 海嘯、堰塞湖列法定天然災害"]))
        self.assertTrue(tf.cut_edge("核電重啟評估", ["能源轉型、核電重啟評估", "減碳、核電重啟評估啟動"]))  # outside the judged list

    def test_a_digit_after_a_key_without_a_noun_head_cuts_the_name(self):
        self.assertTrue(tf.cut_edge("利率連", ["央行利率連10凍 房市管制微調", "央行理監事會利率連10凍"]))
        self.assertTrue(tf.cut_edge("病例住家僅距", ["彰化登革熱 2病例住家僅距110公尺", "兩病例住家僅距110公尺 疾管署研判群聚"]))
        self.assertTrue(tf.cut_edge("調降稅率至", ["財政部擬調降稅率至15%", "營所稅調降稅率至15% 立委質疑"]))  # outside the judged list

    def test_a_whole_name_is_not_cut(self):
        self.assertFalse(tf.cut_edge("軍購條例", ["軍購條例三讀", "藍白軍購條例爭議", "政院提軍購條例"]))
        self.assertFalse(tf.cut_edge("南海仲裁案", ["南海仲裁案10週年 外交部發聲", "南海仲裁案10週年 國防部說明"]))  # a digit after a noun head stays a whole name
        self.assertFalse(tf.cut_edge("三班護病比", ["三班護病比入法", "「三班護病比」將入法 石崇良說明"]))


class SpokenAfterColonTest(unittest.TestCase):
    """R154: a key that follows a colon is what a speaker said."""

    def test_judged_quotes(self):
        self.assertTrue(tf.spoken_after_colon("不因威脅放棄民主", ["外媒曝「賴清德連任」北京恐更傾向動武 總統府：不因威脅放棄民主", "外媒指賴清德若連任 府：不因威脅放棄民主自由", "賴清德連任北京傾向動武？ 總統府：不因威脅放棄民主自由的堅持"]))
        self.assertTrue(tf.spoken_after_colon("底線一直被踩", ["趙少康問「人設轉變」？ 沈伯洋認了變兇：底線一直被踩", "趙少康尖銳問人設轉變 沈伯洋認在立院比較兇：底線一直被踩"]))

    def test_a_quote_from_outside_the_judged_list(self):
        self.assertTrue(tf.spoken_after_colon("預算夠用", ["縣長：預算夠用", "局長：預算夠用 不需追加"]))

    def test_a_name_after_a_colon_in_a_minority_of_its_uses_is_a_name(self):
        self.assertFalse(tf.spoken_after_colon("追加預算", ["追加預算送立院", "行政院：追加預算將於下週送出", "藍白反對追加預算"]))


class IssueNameTest(unittest.TestCase):
    """R154, R155.3: the name of a new topic ends with an issue noun."""

    def test_a_bare_object_place_organization_or_person_fails(self):
        for name in ("苦茶油", "板橋診所", "松山機場", "統促黨", "淡江大橋", "國家圖書館", "鳳梨酥", "王小明"):  # the last three are outside the judged list; R155.3 replaces the R112.2 exception for a named facility
            self.assertFalse(tf.issue_name(name), name)

    def test_a_verb_phrase_without_a_subject_fails(self):
        for name in ("研擬涉案車輛沒收機制", "要求從嚴政治審查", "協商輕軌經費", "避免被收高額代辦費", "取消區公所補助", "全面提高菸稅"):  # the last two are outside the judged list
            self.assertFalse(tf.issue_name(name), name)

    def test_a_sentence_fails(self):
        for name in ("有問題就下架", "他們不能漲電價"):  # the second is outside the judged list
            self.assertFalse(tf.issue_name(name), name)

    def test_a_cut_word_that_ends_with_the_character_for_law_fails(self):
        for name in ("中國科研船非法", "種說法", "餐廳違法"):  # the last is outside the judged list
            self.assertFalse(tf.issue_name(name), name)

    def test_a_name_with_an_issue_noun_passes(self):
        for name in ("軍購條例", "追加預算", "三班護病比", "天坑案", "行動網路降速演練", "副署無人載具條例", "食安法", "毒油風暴", "漢光演習", "淡江大橋通車"):
            self.assertTrue(tf.issue_name(name), name)

    def test_a_motion_or_a_single_case_is_no_issue_noun(self):
        for name in ("洪健益提案", "王小明個案"):  # the first is a topic of the dry run, the second is outside the judged list
            self.assertFalse(tf.issue_name(name), name)

    def test_the_gate_rejects_a_bare_name_of_a_new_topic_and_keeps_a_recorded_one(self):
        titles = ["連淨苦茶油苯駢芘超標 食藥署抽驗", "苦茶油苯駢芘超標 衛福部說明", "苦茶油案 行政院會說明"]
        members = items(titles)
        corpus = members + [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        df = tp.document_frequency(corpus)
        self.assertEqual(tf.gate_topic("苦茶油", members, members[:1], df, corpus)[0], "rejected_issue_name")
        known = {"name": "苦茶油", "jids": ["jur-tw"], "actors": [], "sensitive": False}
        self.assertEqual(tf.gate_topic("苦茶油", members, members[:1], df, corpus, known=known)[0], "ok")  # R155.4: an old topic keeps the R134 test


class WordBoundaryTest(unittest.TestCase):
    def test_a_letter_continues_the_word_on_the_left(self):
        self.assertFalse(tf.has_word_boundary("劃界談判", ["日菲海域劃界談判登場", "日菲海域劃界談判再啟", "日菲EEZ劃界談判", "日菲海域劃界談判破局"], new=True))  # judged: 日菲海域劃界談判
        self.assertFalse(tf.has_word_boundary("實兵演練", ["海軍HX實兵演練", "陸軍AB實兵演練", "空軍XY實兵演練"], new=True))  # outside the judged list
        self.assertTrue(tf.has_word_boundary("劃界談判", ["日菲劃界談判登場", "菲國劃界談判再啟", "雙方劃界談判破局", "新一輪劃界談判", "外長稱劃界談判", "重啟劃界談判", "海巡劃界談判", "漁民劃界談判"]))


class ForeignBodyTest(unittest.TestCase):
    """R154 (PRD 4.5 item 6): a foreign body or official is no body of Taiwan."""

    def test_the_foreign_office_is_taken_out(self):
        self.assertNotIn("外交部", tf.home_text("美伊傳將在卡達會談 伊朗外交部否認"))
        self.assertNotIn("國防部", tf.home_text("美國防部將孔子學院列國安威脅"))
        self.assertNotIn("央行", tf.home_text("埃及央行總裁籲民眾勿恐慌"))
        self.assertNotIn("議員", tf.home_text("曾訪台南韓議員遭北京封殺"))
        self.assertNotIn("議員", tf.home_text("日本前參議員：中國在玩法律戰"))
        self.assertNotIn("央行", tf.home_text("巴西央行升息一碼"))  # outside the judged list
        self.assertIn("外交部", tf.home_text("外交部：尊重泰方決定"))
        self.assertIn("議員", tf.home_text("北市議員質疑市府預算"))
        self.assertIn("國防部", tf.home_text("國防部說明韓國瑜出訪"))  # 韓國瑜 is a person of Taiwan

    def test_the_united_nations_force_and_a_chinese_warship_are_no_national_army(self):
        self.assertFalse(any(__import__("re").search(p, t) for p, _, _, _ in tp.CENTRAL for t in ("聯合國軍司令部證實發現北韓地雷", "日本抗議中國軍艦實彈射擊")))
        self.assertTrue(any(__import__("re").search(p, "國軍漢光演習") for p, _, _, _ in tp.CENTRAL))

    def test_judged_foreign_topics_are_not_about_taiwan(self):
        cases = {
            "伊朗外交部否認": ["美伊傳將在卡達會談 伊朗外交部否認", "川普稱美伊6/30要在卡達會談 伊朗外交部否認"],
            "埃鎊": ["埃鎊續貶創歷史新低 埃及央行總裁籲勿擔憂", "埃鎊續貶創歷史新低　埃及央行總裁籲民眾勿恐慌"],
            "孔子學院": ["將孔子學院列國安威脅 赫格塞斯：已瓦解每一個組織", "美國防部將「孔子學院」列國安威脅 赫格塞斯：已瓦解80個大學宣傳據點"],
            "停戰協定": ["南韓挖出北韓反步兵地雷 聯合國軍司令部：已違反停戰協定", "南韓指控北韓邊境埋設地雷 違反停戰協定要求致歉"],
            "巴西央行": ["巴西央行升息一碼 財長表示支持", "巴西央行會議紀要出爐 通膨預期上修"],  # outside the judged list
        }
        for name, titles in cases.items():
            self.assertFalse(tf.taiwan_relevant(titles, True), name)
            self.assertTrue(tf.names_foreign(titles, True), name)
            self.assertEqual(tf.detect_gov_actors(titles, ["jur-tw"], True), [], name)

    def test_a_foreign_quake_with_the_taiwan_weather_agency_as_source_is_not_about_taiwan(self):
        titles = ["萬那杜規模7.2強震 氣象署：海嘯警報", "萬那杜強震 氣象署發布海嘯警報", "土耳其規模7.1強震 氣象署監測餘震"]  # outside the judged list: the last
        self.assertFalse(tf.taiwan_relevant(titles, True))

    def test_a_forecast_of_the_weather_agency_is_still_about_taiwan(self):
        self.assertTrue(tf.taiwan_relevant(["氣象署：明起鋒面接近", "氣象署發布大雨特報", "氣象署：周末降雨趨緩"], True))

    def test_a_topic_of_taiwan_that_names_a_foreign_country_passes(self):
        titles = ["外交部：尊重泰方決定 取消60天免簽", "泰國取消60天免簽 外交部協助國人", "外交部提醒赴泰旅客"]
        self.assertTrue(tf.taiwan_relevant(titles, True))
        self.assertIn("ac-ministry-of-foreign-affairs", tf.detect_gov_actors(titles, ["jur-tw"], True))


class SingleAccidentTest(unittest.TestCase):
    """R154 (PRD 4.5 item 2): a topic of one accident is no public matter, unless its titles ask for a rule."""

    def test_judged_accidents(self):
        titles = ["台中國光客運撞到新加坡婦 聽到尖叫已捲入輪下 無呼吸心跳", "新加坡婦遭國光客運輾壓命危 對面國中學生全嚇傻", "台中西區客運撞行人 新加坡婦受困車底救出送醫",
                  "國光客運撞新加坡婦 公路局認定未落實停讓"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "single_accident")
        self.assertEqual(tf.new_topic_reason(items(["巨型看板倒塌砸整排車", "看板倒塌壓毀8車 服務處回應了", "看板倒塌被問賠車 黃馨慧致歉"])), "single_accident")

    def test_an_accident_from_outside_the_judged_list(self):
        self.assertEqual(tf.new_topic_reason(items(["國道追撞5車 2人送醫", "國道5車追撞 警方調查肇事原因", "追撞車禍釀1死 國道警察說明"])), "single_accident")

    def test_a_topic_that_asks_for_a_rule_after_accidents_passes(self):
        titles = ["機車後座兒童車禍死傷 交通部要訂規範", "兒童乘坐機車事故頻傳 交通部研擬安全標準", "車禍死傷近7千件 民團盼修法"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_a_typhoon_is_no_single_accident(self):
        self.assertIsNone(tf.new_topic_reason(items(["颱風來襲 北市府宣布停班停課", "颱風假爭議 市府說明", "颱風假 縣府公告放假"])))


class CriminalCaseTest(unittest.TestCase):
    """R154 (PRD 4.5 item 2): a sentence or an act of one person is a criminal case."""

    def test_judged_cases(self):
        self.assertEqual(tf.exclusion_reason(items(["台南前主委涉貪判2年獲緩刑", "台南前副市長之子吸金1.2億 二審改判2年獲緩刑"]), new=True), "criminal_case")
        self.assertEqual(tf.exclusion_reason(items(["男子持球棒闖台中市府砸電腦 遭警壓制帶回", "男闖中市府球棒狂砸電腦螢幕 遭警壓制帶回"]), new=True), "criminal_case")
        self.assertEqual(tf.exclusion_reason(items(["高雄男大生虐殺倉鼠逾30隻 點火燒", "高雄男大生遭爆虐殺數十隻倉鼠 市府出手了"]), new=True), "criminal_case")

    def test_a_case_from_outside_the_judged_list(self):
        self.assertEqual(tf.exclusion_reason(items(["男子縱火燒機車 警方逮人", "縱火案嫌犯到案 檢方偵辦"]), new=True), "criminal_case")

    def test_an_old_topic_does_not_read_the_new_words(self):  # R162 (N1): the new words are for a new topic only
        titles = items(["男子縱火燒機車 警方逮人", "縱火案嫌犯到案 檢方偵辦"])
        self.assertEqual(tf.exclusion_reason(titles, new=True), "criminal_case")
        self.assertEqual(tf.exclusion_reason(items(["男子縱火燒機車 警方處理", "縱火機車 消防局說明"])), None)

    def test_a_policy_titles_are_no_criminal_case(self):
        self.assertIsNone(tf.exclusion_reason(items(["毒駕加嚴 立院三讀道交條例", "毒駕吊銷駕照 交通部說明"]), new=True))


class CandidateTalkTest(unittest.TestCase):
    """R154 (PRD 4.5 item 5): a topic that judges candidates is no topic."""

    def setUp(self):
        tf.set_candidates({"沈伯洋", "蔣萬安", "陳時中", "王大明", "李小華"})

    def tearDown(self):
        tf.set_candidates(())

    def test_judged_attacks_between_two_candidates(self):
        for titles in (["陳時中酸蔣萬安往臉上貼金 北市府：4年前的選舉該放下了", "輝達落腳台北當政績？ 陳時中嗆蔣萬安：往臉上貼金", "陳時中嗆用輝達往臉上貼金 蔣萬安反擊"],
                       ["沈伯洋酸蔣萬安食安開關在花蓮 北市府：沈監督過幾次？", "蔣萬安跑花蓮談倒閣 沈伯洋疑：食安開關在花蓮？"]):
            self.assertEqual(tf.new_topic_reason(items(titles)), "candidate_attack")

    def test_judged_campaign_acts(self):
        self.assertEqual(tf.new_topic_reason(items(["確定了！蔣萬安將出席電視辯論會", "蔣萬安、沈伯洋電視辯論會拍板", "北市長選戰將辦電視辯論會"])), "candidate_attack")
        self.assertEqual(tf.new_topic_reason(items(["鄭麗文基隆站台 力挺議員宋瑋莉", "鄭麗文助選1天跑10場 首站基隆", "宋瑋莉競選總部成立 鄭麗文相挺"])), "candidate_attack")

    def test_an_attack_from_outside_the_judged_list(self):
        self.assertEqual(tf.new_topic_reason(items(["王大明批李小華抹黑 李小華反擊", "李小華回嗆王大明 雙方槓上"])), "candidate_attack")

    def test_a_city_policy_that_names_one_candidate_passes(self):
        self.assertIsNone(tf.new_topic_reason(items(["蔣萬安：市府編列預算改善行道樹", "北市府說明行道樹預算 蔣萬安表示支持", "蔣萬安視察行道樹工程 市府公布時程"])))

    def test_the_candidates_are_the_public_figures_next_to_a_campaign_word(self):
        corpus = [item(f"c{i}", f"沈伯洋宣布參選台北市長{i}", publisher="p") for i in range(5)] + [item(f"d{i}", f"賴清德連任{i}", publisher="p") for i in range(2)]
        corpus += [item(f"e{i}", f"他們表態參選{i}", publisher="p") for i in range(6)]
        self.assertEqual(tf.candidate_names(corpus), {"沈伯洋"})  # 賴清德 has 2 titles; 他們表 is no public figure


class OfficialHealthTest(unittest.TestCase):
    """R154 (rule 4): the health of a named official is private data."""

    def test_judged_case(self):
        titles = ["謝國樑「染B流2週未癒」住進北榮 院長霸氣回應", "謝國樑染「B型流感」住進北榮 院長證實：一定會康復", "謝國樑染流感轉趨嚴重住進北榮 基隆市議會明起定期會將延會"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "official_health")

    def test_a_case_from_outside_the_judged_list(self):
        self.assertEqual(tf.new_topic_reason(items(["部長住院開刀 請假休養", "衛福部長手術順利 請假休養兩週", "部長出院 回部上班"])), "official_health")

    def test_a_mayor_who_comments_on_sick_pupils_passes(self):
        titles = ["民族國小9生腸胃不適 蔣萬安：初步判斷腸胃炎", "民族國小午餐吐瀉 蔣萬安：不排除諾羅病毒 市府調查", "民族國小吐瀉 北市府檢驗午餐"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))


class PrivateMatterTest(unittest.TestCase):
    """R154 (PRD 4.5 item 1): a topic where no title names a public body or a public act is a private matter."""

    def test_judged_cases(self):
        self.assertEqual(tf.new_topic_reason(items(["楊懷民看鍘美藝術節爆紅 幽默喊去鍘趙建銘就好", "趙建銘否認曾兄弟鬩牆 網友串聯鍘美藝術節", "鍘美藝術節公開招募志工 強調不造謠不網路霸凌",
                                                    "台南鍘美藝術節暖身場今晚開鑼", "鍘美藝術節包公斬駙馬鹽水武廟開演"])), "private_matter")
        self.assertEqual(tf.new_topic_reason(items(["南韓挖出北韓反步兵地雷 聯合國軍司令部：已違反停戰協定", "南韓指控北韓邊境埋設地雷 違反停戰協定要求致歉"])), "private_matter")

    def test_a_case_from_outside_the_judged_list(self):
        self.assertEqual(tf.new_topic_reason(items(["某網紅婚宴排場曝光 親友出席名單", "網紅婚宴蛋糕塔登場 網友驚呼"])), "private_matter")

    def test_a_law_a_budget_or_a_public_service_passes(self):
        self.assertIsNone(tf.new_topic_reason(items(["軍購條例三讀 藍白通過", "朝野協商軍購條例", "軍購條例送院會"])))
        self.assertIsNone(tf.new_topic_reason(items(["捷運三鶯線通車 民眾搭乘", "三鶯線通車首日人潮", "捷運三鶯線試乘"])))


class DuplicateIssueTest(unittest.TestCase):
    """R154: two new topics on one issue give one topic."""

    def profile(self, key, titles, day="2026-10-10"):
        return tf.issue_profile(key, [item(f"{key}{i}", t, day) for i, t in enumerate(titles)])

    DF = {}

    def test_one_key_holds_the_other(self):  # judged: 兄弟姊妹 and 兄弟姊妹特留分
        a = self.profile("兄弟姊妹", ["刪除兄弟姊妹特留分 法務部研議", "兄弟姊妹繼承 民法修正"], "2026-04-10")
        b = self.profile("兄弟姊妹特留分", ["兄弟姊妹特留分廢除 立委連署", "兄弟姊妹特留分 法務部說明"], "2026-05-26")
        self.assertTrue(tf.same_issue(a, b, self.DF))

    def test_the_same_key_twice(self):  # judged: 老福法 under two windows; outside: 颱風假
        a = self.profile("老福法", ["老福法修法 社會救助", "老福法三讀"], "2026-10-20")
        b = self.profile("老福法", ["老福法再修 社福團體", "老福法爭議"], "2026-10-22")
        self.assertTrue(tf.same_issue(a, b, self.DF))

    def test_a_shared_rare_term(self):  # judged: 台南鐵路地下化 twice, 玄濟宮 under two names
        a = self.profile("濟顛禪師", ["台東玄濟宮濟顛禪師神像 引爆爭議", "台東玄濟宮濟顛禪師 信徒說明"])
        b = self.profile("尬電師父", ["台東玄濟宮尬電師父 網友瘋傳", "台東玄濟宮尬電師父 宮方回應"])
        df = {"台東玄濟宮": 10}
        self.assertTrue(tf.same_issue(a, b, df))

    def test_a_term_that_many_stories_share_is_no_link(self):
        a = self.profile("空污法", ["藍白立委提空污法修正 逕付二讀", "空污法 藍白立委推動"])
        b = self.profile("民族團結法", ["藍白立委擋民族團結法 逕付二讀", "民族團結法 藍白立委表態"])
        df = {"藍白立委": 300, "逕付二讀": 340}  # four characters only, and common in the corpus
        self.assertFalse(tf.same_issue(a, b, df))

    def test_two_topics_far_apart_in_time_are_two_issues(self):
        a = self.profile("老福法", ["老福法修法 社會救助", "老福法三讀"], "2026-04-01")
        b = self.profile("老福法", ["老福法再修 社福團體", "老福法爭議"], "2026-10-22")
        self.assertFalse(tf.same_issue(a, b, self.DF))


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class OldTopicTest(unittest.TestCase):
    """R155.4: an old topic keeps the R134 name test. A rebuilt candidate that breaks a rule of a new topic does not fail it."""

    EVENT_ID = "ev-20261023-topic-c8f31c28"  # the id of the key 南崁溪, a bare river name

    def run_in(self, root, today):
        import json
        from pathlib import Path
        filler = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        topic = [item("a", "桃園市府會勘南崁溪淤積問題", "2026-10-23"),
                 item("b", "南崁溪石礫堆積 桃園市府將會勘", "2026-10-24", "聯合新聞網"),
                 item("c", "【錯誤】南崁溪淤積謠言", "2026-10-24", "MyGoPen", "fact_check")]
        clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in topic]}]}]
        ids = [tp.src_id(t, tp.HOSTS) for t in topic]
        event = Path(root) / "events/2026" / f"{self.EVENT_ID}.md"
        if not event.exists():
            event.parent.mkdir(parents=True)
            (Path(root) / "sources/2026").mkdir(parents=True)
            (Path(root) / "actors").mkdir()
            event.write_text(f"---\nid: {self.EVENT_ID}\nstatus: published\ntitle: 桃園市南崁溪淤積問題\ntimeline:\n- date: '2026-10-23'\n"
                             f"  source_ids: [{ids[0]}]\n- date: '2026-10-24'\n  source_ids: [{ids[1]}, {ids[2]}]\n"
                             "review:\n  sensitive: false\n  reason: 'draft-review: 系統依爬取資料自動形成與命名，編輯尚未審閱。'\n"
                             "  status: draft-review\n---\n\n報導。\n", encoding="utf-8")
        stats, _, _ = tf.run(filler + topic, clusters, [], root, Path(root) / "report.json", today=today)
        state = Path(root) / "tools/newsfetch/topic_state.json"
        return stats, (json.loads(state.read_text(encoding="utf-8")) if state.exists() else {})

    def test_a_bare_candidate_name_is_rejected_and_the_old_topic_gets_no_fail_count(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            for today in ("2026-10-25", "2026-10-26"):
                stats, state = self.run_in(root, today)
                self.assertEqual(stats["rejected_issue_name"], 1)
                self.assertEqual(stats["published"], 0)
                self.assertEqual(stats["regate_checked"], 1)  # the old topic goes to the re-gate with its recorded name
                self.assertEqual(stats["regate_failed"], 0)
                self.assertNotIn(self.EVENT_ID, state)
                self.assertEqual(stats["withdrawn"], 0)


class SloganNameTest(unittest.TestCase):
    """R162: a name copied from a quote or a slogan in a source title is no issue name. Judged (T26-P): 白海豚不放假, 零軍購."""

    SLOGAN_TITLES = ["區桂芝主張零軍購 綠委轟內賊：法律應找適當方式重懲背叛國家者", "北一女師喊「零軍購」：承認是中國人就有和平 中國網友也怒了",
                     "北一女去年才公告禁令！區桂芝又上中媒主張零軍購 校方暫無回應", "區桂芝喊零軍購「承認是中國人就和平」他轟：比第五縱隊有過之無不及！應重懲！",
                     "北一女教師區桂芝接受中共官媒訪問倡「零軍購」 陸委會：應妥處配合統戰行為"]

    def test_judged_slogan_after_a_slogan_verb_or_inside_quotes(self):
        self.assertTrue(tf.copied_quote("零軍購", self.SLOGAN_TITLES))
        self.assertFalse(tf.new_name_ok("零軍購", self.SLOGAN_TITLES))

    def test_judged_clause_with_a_negated_verb(self):
        self.assertFalse(tf.issue_name("白海豚不放假"))

    def test_a_slogan_from_outside_the_judged_list(self):
        self.assertTrue(tf.copied_quote("免費早餐", ["議員倡免費早餐", "主張免費早餐 市府回應", "「免費早餐」爭議"]))
        self.assertFalse(tf.issue_name("市府不給補助"))
        self.assertFalse(tf.issue_name("學校不發獎金條例"))

    def test_a_name_that_one_title_quotes_is_a_name(self):
        self.assertFalse(tf.copied_quote("軍購條例", ["軍購條例三讀", "藍白軍購條例爭議", "主張軍購條例", "政院提軍購條例"]))
        self.assertFalse(tf.copied_quote("零關稅", ["美方談零關稅", "零關稅談判登場", "政院說明零關稅"]))
        self.assertTrue(tf.issue_name("房屋不動產稅"))  # 不動產 is a noun, not a negated verb


class NounStackNameTest(unittest.TestCase):
    """R162: an object and a weather or disaster noun with no relation between them say nothing. Judged (T26-P): 高雄市月子中心颱風."""

    def test_judged_stack(self):
        self.assertFalse(tf.issue_name("高雄市月子中心颱風"))
        self.assertFalse(tf.issue_name("月子中心颱風"))

    def test_stacks_from_outside_the_judged_list(self):
        for name in ("台北市安養院火災", "新北市幼兒園地震", "彰化縣工廠停電"):
            self.assertFalse(tf.issue_name(name), name)

    def test_a_place_and_a_disaster_or_a_rule_for_the_object_passes(self):
        for name in ("薔琵颱風", "台南地震", "月子中心管理辦法", "幼兒園安全事件"):
            self.assertTrue(tf.issue_name(name), name)


class GenericActNameTest(unittest.TestCase):
    """R162, R161.1: a generic act noun needs a law or an issue before it. A bare event name fails. Judged (T26-P): 修法會議, 數位人權大會."""

    def test_judged_names(self):
        self.assertFalse(tf.issue_name("修法會議"))
        self.assertFalse(tf.issue_name("數位人權大會"))

    def test_names_from_outside_the_judged_list(self):
        for name in ("政府修法", "部長說明", "朝野協商", "亞太經濟峰會", "國際花卉展覽"):
            self.assertFalse(tf.issue_name(name), name)

    def test_a_law_or_an_issue_before_the_act_passes(self):
        for name in ("食安法修法會議", "軍購條例協商", "老福法修法", "司法改革大會"):
            self.assertTrue(tf.issue_name(name), name)
        self.assertEqual(tf.strip_generic_act("食安法修法會議"), "食安法")
        self.assertEqual(tf.strip_generic_act("修法會議"), "")


class VerbLeadNameTest(unittest.TestCase):
    """R162: a name that starts with a tax or price verb has no subject. Judged (T26-P): 課重稅."""

    def test_judged_name(self):
        self.assertFalse(tf.issue_name("課重稅"))

    def test_names_from_outside_the_judged_list(self):
        for name in ("砍預算", "擋軍購條例", "開徵碳費", "加徵關稅"):
            self.assertFalse(tf.issue_name(name), name)

    def test_a_name_with_a_subject_passes(self):
        for name in ("川普晶片關稅", "碳費新制", "晶片課稅爭議"):
            self.assertTrue(tf.issue_name(name), name)


class ThemeWordTest(unittest.TestCase):
    """R162: a keyword bundle. The key is a theme word that is in use in nearly every month of the corpus with no burst.
    Judged (T26-P): 政治獻金案, 26 titles of many cases. Only one bundle fail is in the judged list."""

    def months(self, uses):
        from collections import Counter
        return {f"2026-{m:02d}": Counter({"鍵": n}) for m, n in enumerate(uses, 4)}

    def test_judged_theme_word(self):
        self.assertTrue(tf.theme_word("鍵", self.months([4, 7, 3, 16, 6, 28, 9])))  # the use counts of 政治獻金 in 2026-04 to 2026-10

    def test_a_theme_word_from_outside_the_judged_list(self):
        self.assertTrue(tf.theme_word("鍵", self.months([5, 6, 5, 7, 5, 8, 6])))

    def test_an_issue_with_a_burst_is_no_theme_word(self):
        self.assertFalse(tf.theme_word("鍵", self.months([0, 7, 79, 3, 0, 0, 0])))  # 三班護病比
        self.assertFalse(tf.theme_word("鍵", self.months([0, 1, 12, 40, 1, 2, 0])))  # 民族團結法
        self.assertFalse(tf.theme_word("鍵", self.months([0, 7, 3, 1, 10, 32, 16])))  # 追加預算: 5 months with 2 uses or more
        self.assertFalse(tf.theme_word("鍵", self.months([0, 0, 0, 0, 0, 0, 0])))

    def test_the_gate_rejects_a_theme_word_of_a_new_topic_and_keeps_an_old_topic(self):
        titles = ["政治獻金案二審首庭 柯文哲否認", "政治獻金案二審 檢方說明", "政治獻金案 法務部說明"]
        members = items(titles)
        corpus = members + [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        df = tp.document_frequency(corpus)
        mf = tf.MonthFrequency(corpus)
        for m in range(4, 11):
            mf.months[f"2026-{m:02d}"].update({"政治獻金案": 5 if m != 9 else 6})
        self.assertEqual(tf.gate_topic("政治獻金案", members, members[:1], df, corpus, mf=mf)[0], "rejected_keyword_bundle")
        known = {"name": "政治獻金案", "jids": ["jur-tw"], "actors": ["ac-executive-yuan"], "sensitive": False}
        self.assertEqual(tf.gate_topic("政治獻金案", members, members[:1], df, corpus, known=known, mf=mf)[0], "ok")


class NewTopicScopeTest(unittest.TestCase):
    """R162 (N1, R155.4): the new CRIME words, the foreign list, home_text and the letter boundary are for a new topic only."""

    def test_an_old_topic_reads_the_old_lists(self):
        titles = ["伊朗外交部否認 美伊會談", "伊朗外交部：尊重各方"]
        self.assertTrue(tf.taiwan_relevant(titles))  # the old rule counts 外交部 as a body of Taiwan
        self.assertFalse(tf.taiwan_relevant(titles, True))
        self.assertFalse(tf.names_foreign(["埃及央行升息", "埃及央行總裁說明"]))  # 埃及 is not in the old list
        self.assertTrue(tf.names_foreign(["埃及央行升息", "埃及央行總裁說明"], True))
        self.assertEqual(tf.detect_gov_actors(titles, ["jur-tw"], True), [])
        self.assertIn("ac-ministry-of-foreign-affairs", tf.detect_gov_actors(titles, ["jur-tw"]))
        self.assertTrue(tf.names_government("伊朗外交部否認"))
        self.assertFalse(tf.names_government("伊朗外交部否認", True))
        letters = ["日菲海域劃界談判登場", "日菲海域劃界談判再啟", "日菲EEZ劃界談判", "日菲海域劃界談判破局"]
        self.assertTrue(tf.has_word_boundary("實兵演練", ["海軍HX實兵演練", "陸軍AB實兵演練", "空軍XY實兵演練"]))
        self.assertFalse(tf.has_word_boundary("實兵演練", ["海軍HX實兵演練", "陸軍AB實兵演練", "空軍XY實兵演練"], new=True))
        self.assertFalse(tf.has_word_boundary("劃界談判", letters, new=True))


class DoNotPassTheWordForMethodTest(unittest.TestCase):
    """R162 (N2): 做法 and 作法 are no issue head."""

    def test_the_word_for_method_is_no_head(self):
        for name in ("政府新做法", "學校做法", "地方新作法", "市府新作法"):
            self.assertFalse(tf.issue_name(name), name)

    def test_a_law_still_is_a_head(self):
        for name in ("食安法", "勞基法", "電業法"):
            self.assertTrue(tf.issue_name(name), name)


class DuplicateAcrossTopicsTest(unittest.TestCase):
    """R162, R161.2: the duplicate rule works across 3 topics or more and against old topics."""

    def profile(self, key, titles, day):
        return tf.issue_profile(key, [item(f"{key}{i}", t, day) for i, t in enumerate(titles)])

    def test_judged_two_names_of_one_vote_one_day_apart(self):  # T26-P: 立院三讀免健保費 and 長者有條件免健保費
        a = self.profile("立院三讀免健保費", ["400億大紅包！立院三讀免健保費 時力批劫貧濟富", "立院三讀免健保費 時代力量：連財源都沒有交代"], "2026-10-16")
        b = self.profile("長者有條件免健保費", ["長者有條件免健保費三讀 石崇良憂：絕非健康平權", "長者有條件免健保費三讀 陳昭姿：減輕子女投保負擔", "長者有條件免健保費　陳時中籲修回重啟社會討論"], "2026-10-17")
        self.assertTrue(tf.same_issue(a, b, {"免健保費": 51}))

    def test_a_four_character_term_that_is_common_is_no_link(self):
        a = self.profile("軍購條例", ["藍白立委提軍購條例修正", "軍購條例 藍白立委表態"], "2026-10-16")
        b = self.profile("空污法", ["藍白立委提空污法修正", "空污法 藍白立委表態"], "2026-10-17")
        self.assertFalse(tf.same_issue(a, b, {"藍白立委": 300}))

    def test_a_four_character_term_outside_the_keys_is_no_link(self):  # T26 dry run: 藍白立委 joined 空污法 and 三班護病比; 支持軍購 joined 軍購條例 and 軍購特別預算
        a = self.profile("三班護病比", ["藍白立委推三班護病比入法", "三班護病比 藍白立委表態"], "2026-05-05")
        b = self.profile("空污法", ["藍白立委提空污法修正", "空污法 藍白立委表態"], "2026-05-06")
        self.assertFalse(tf.same_issue(a, b, {"藍白立委": 14}))

    def test_a_four_character_term_does_not_link_topics_a_month_apart(self):
        a = self.profile("立院三讀免健保費", ["立院三讀免健保費 時力批", "立院三讀免健保費 財源"], "2026-09-01")
        b = self.profile("長者有條件免健保費", ["長者免健保費 石崇良", "長者免健保費 陳時中"], "2026-10-17")
        self.assertFalse(tf.same_issue(a, b, {"免健保費": 51}))

    def test_an_old_topic_with_the_same_key(self):  # T26-P: 老福法 (new) and the old 老福法
        old = self.profile("老福法", ["藍白惹議！《老福法》修法恐影響弱勢長者醫療補助", "衛福部狂轟老福法修法 吳宗憲：每一點都站不住"], "2026-10-22")
        new = self.profile("老福法", ["《老福法》強行修正三讀 卓榮泰嗆韓國瑜", "藍白修《老福法》 卓榮泰批韓國瑜"], "2026-10-16")
        issues = [old]
        self.assertTrue(tf.is_duplicate_issue(new, issues, {}))

    def test_a_third_topic_that_links_to_a_skipped_duplicate_only(self):
        a = self.profile("兄弟姊妹特留分", ["兄弟姊妹特留分廢除 立委連署", "兄弟姊妹特留分 法務部說明"], "2026-05-01")
        b = self.profile("兄弟姊妹", ["兄弟姊妹繼承 民法修正", "刪除兄弟姊妹特留分 法務部研議"], "2026-05-20")
        c = self.profile("兄弟姊妹繼承", ["兄弟姊妹繼承新制 草案", "兄弟姊妹繼承 院會通過"], "2026-06-25")
        df = {}
        self.assertFalse(tf.same_issue(a, c, df))  # 55 days apart is inside the gap, but the key of c holds the key of b only
        issues = [a]
        self.assertTrue(tf.is_duplicate_issue(b, issues, df))
        self.assertFalse(tf.is_duplicate_issue(c, issues, df))  # c links to b only, and the run has not added b yet
        issues.append(b)  # the run adds the profile of a skipped duplicate
        self.assertTrue(tf.is_duplicate_issue(c, issues, df))  # it links to b, which was skipped

    def test_a_topic_on_another_issue_is_not_a_duplicate(self):
        a = self.profile("兄弟姊妹特留分", ["兄弟姊妹特留分廢除 立委連署", "兄弟姊妹特留分 法務部說明"], "2026-05-01")
        b = self.profile("颱風假", ["高雄颱風假 市府宣布", "颱風假 台中市府"], "2026-05-02")
        issues = [a]
        self.assertFalse(tf.is_duplicate_issue(b, issues, {}))


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class DuplicateOfOldTopicRunTest(unittest.TestCase):
    """R162, R161.2: a new topic on the issue of an old system topic is not published."""

    OLD_ID = "ev-20261022-topic-0ld00001".replace("0ld", "a1d")

    def test_a_new_topic_with_the_key_of_an_old_topic_is_skipped(self):
        import tempfile
        from pathlib import Path
        filler = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        old = [item("o1", "衛福部批老福法修法 立院應補正", "2026-11-25"), item("o2", "政院喊話老福法修法 三思而後行", "2026-11-25", "聯合新聞網")]  # after the window of the candidate
        new = [item("n1", "老福法修正三讀 行政院院長卓榮泰回應", "2026-10-16"), item("n2", "藍白修老福法 行政院批立法院程序", "2026-10-16", "聯合新聞網"),
               item("n3", "老福法爭議 衛福部部長石崇良說明", "2026-10-17", "ETtoday新聞雲")]
        with tempfile.TemporaryDirectory() as root:
            ids = [tp.src_id(t, tp.HOSTS) for t in old]
            (Path(root) / "events/2026").mkdir(parents=True)
            (Path(root) / "sources/2026").mkdir(parents=True)
            (Path(root) / "actors").mkdir()
            for t, i in zip(old, ids):
                (Path(root) / "sources/2026" / f"{i}.yaml").write_text(
                    f'id: {i}\nurl: "{t["url"]}"\ntitle: "{t["title"]}"\npublished_on: "{t["published_on"]}"\npublisher: "{t["publisher"]}"\nsource_class: news\n', encoding="utf-8")
            (Path(root) / "events/2026" / f"{self.OLD_ID}.md").write_text(
                f"---\nid: {self.OLD_ID}\nstatus: published\ntitle: 老福法\njurisdiction_ids: [jur-tw]\ntimeline:\n- date: '2026-11-25'\n  source_ids: [{ids[0]}, {ids[1]}]\n"
                "review:\n  sensitive: false\n  reason: 'draft-review: 系統依爬取資料自動形成與命名，編輯尚未審閱。'\n  status: draft-review\n---\n\n報導。\n", encoding="utf-8")
            clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in new]}]}]
            stats, published, _ = tf.run(filler + old + new, clusters, [], root, Path(root) / "report.json", today="2026-10-26")
            self.assertEqual(stats["skipped_duplicate_issue"], 1)
            self.assertEqual(stats["published"], 0)


if __name__ == "__main__":
    unittest.main()
