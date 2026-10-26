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
        self.assertFalse(tf.has_word_boundary("劃界談判", ["日菲海域劃界談判登場", "日菲海域劃界談判再啟", "日菲EEZ劃界談判", "日菲海域劃界談判破局"]))  # judged: 日菲海域劃界談判
        self.assertFalse(tf.has_word_boundary("實兵演練", ["海軍HX實兵演練", "陸軍AB實兵演練", "空軍XY實兵演練"]))  # outside the judged list
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
            self.assertFalse(tf.taiwan_relevant(titles), name)
            self.assertTrue(tf.names_foreign(titles), name)
            self.assertEqual(tf.detect_gov_actors(titles, ["jur-tw"]), [], name)

    def test_a_foreign_quake_with_the_taiwan_weather_agency_as_source_is_not_about_taiwan(self):
        titles = ["萬那杜規模7.2強震 氣象署：海嘯警報", "萬那杜強震 氣象署發布海嘯警報", "土耳其規模7.1強震 氣象署監測餘震"]  # outside the judged list: the last
        self.assertFalse(tf.taiwan_relevant(titles))

    def test_a_forecast_of_the_weather_agency_is_still_about_taiwan(self):
        self.assertTrue(tf.taiwan_relevant(["氣象署：明起鋒面接近", "氣象署發布大雨特報", "氣象署：周末降雨趨緩"]))

    def test_a_topic_of_taiwan_that_names_a_foreign_country_passes(self):
        titles = ["外交部：尊重泰方決定 取消60天免簽", "泰國取消60天免簽 外交部協助國人", "外交部提醒赴泰旅客"]
        self.assertTrue(tf.taiwan_relevant(titles))
        self.assertIn("ac-ministry-of-foreign-affairs", tf.detect_gov_actors(titles, ["jur-tw"]))


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
        self.assertEqual(tf.exclusion_reason(items(["台南前主委涉貪判2年獲緩刑", "台南前副市長之子吸金1.2億 二審改判2年獲緩刑"])), "criminal_case")
        self.assertEqual(tf.exclusion_reason(items(["男子持球棒闖台中市府砸電腦 遭警壓制帶回", "男闖中市府球棒狂砸電腦螢幕 遭警壓制帶回"])), "criminal_case")
        self.assertEqual(tf.exclusion_reason(items(["高雄男大生虐殺倉鼠逾30隻 點火燒", "高雄男大生遭爆虐殺數十隻倉鼠 市府出手了"])), "criminal_case")

    def test_a_case_from_outside_the_judged_list(self):
        self.assertEqual(tf.exclusion_reason(items(["男子縱火燒機車 警方逮人", "縱火案嫌犯到案 檢方偵辦"])), "criminal_case")

    def test_a_policy_titles_are_no_criminal_case(self):
        self.assertIsNone(tf.exclusion_reason(items(["毒駕加嚴 立院三讀道交條例", "毒駕吊銷駕照 交通部說明"])))


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
        df = {"藍白立委": 14, "逕付二讀": 34}  # four characters only: under DUPLICATE_TERM_LEN
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


if __name__ == "__main__":
    unittest.main()
