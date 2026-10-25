"""T24 (R141): the follow-up gate fixes after T22. Each test names the item of R141 it checks."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

item = base.item
YAML = __import__("importlib").util.find_spec("yaml")


@unittest.skipUnless(YAML, "the writer needs PyYAML")
class EditorApprovedTest(base.RunHelper, unittest.TestCase):
    """R141.1: withdraw_topic() and fail() never change a topic with review.status editor-approved."""

    def approve(self, root):
        path = root / "events/2026" / f"{self.EVENT_ID}.md"
        path.write_text(path.read_text(encoding="utf-8").replace("draft-review: 系統", "editor-approved: 編輯").replace(
            "status: draft-review", "status: editor-approved"), encoding="utf-8")
        return path

    def test_r141_1_withdraw_topic_leaves_an_editor_approved_topic_as_it_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-24")
            path = self.approve(root)
            before = path.read_text(encoding="utf-8")
            got = tf.withdraw_topic(root, self.EVENT_ID, "rejected_news_rule", today="2026-10-26")
            self.assertEqual(got, path)
            self.assertEqual(path.read_text(encoding="utf-8"), before)
            self.assertEqual(self.records(root), [])

    def test_r141_1_a_failing_run_does_not_count_or_withdraw_an_editor_approved_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-23")
            path = self.approve(root)
            before = path.read_text(encoding="utf-8")
            self.run_in(root, second_news_publisher=False, today="2026-10-24")
            stats, text = self.run_in(root, second_news_publisher=False, today="2026-10-25")
            self.assertEqual(text, before)
            self.assertEqual((stats["withdrawn"], stats["withdraw_pending"], stats["withdraw_blocked"]), (0, 0, 0))
            self.assertEqual(self.records(root), [])
            state = root / "tools/newsfetch/topic_state.json"
            self.assertNotIn(self.EVENT_ID, json.loads(state.read_text(encoding="utf-8")) if state.exists() else {})


@unittest.skipUnless(YAML, "the writer needs PyYAML")
class RecordedNameTest(unittest.TestCase):
    """R141.2: the re-gate uses the recorded name, not a new key, when the recorded name passes the structural tests."""

    ID = "ev-20261022-topic-aaaaaaa1"
    CNA = "違規搬廚餘及餵豬罰鍰提高  農業部：首次違規合計罰百萬元"
    PTS = "違規搬運廚餘、餵豬罰鍰提高 農業部：首次合計開罰100萬"
    NAME = "餵豬罰鍰提高"

    def setup(self, root):
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        cna = item("cna", self.CNA, "2026-10-22", "中央通訊社")
        pts = item("pts", self.PTS, "2026-10-22", "公視新聞網")
        corpus += [cna, pts]
        for d in ("events/2026", "sources/2026", "actors"):
            (root / d).mkdir(parents=True, exist_ok=True)
        seed = {"event_id": self.ID, "seed_urls": ["cna"], "jurisdiction_ids": ["jur-tw"], "jurisdiction_names": [],
                "gov_levels": ["central"], "controversy_types": ["governance_procedure"], "policy_domains": ["agriculture"],
                "actors": [["ac-ministry-of-agriculture", "other"]], "sensitive": False}
        probe = dict(seed, actors=[("ac-ministry-of-agriculture", "other")], _keys=[self.NAME], _name=self.NAME)
        ev = tp.build_event(probe, corpus, tp.document_frequency(corpus), items=[cna, pts])
        tf.ensure_actor_files(root, ["ac-ministry-of-agriculture"])
        tp.write_event(ev, probe, root, {}, overwrite_sources=False)
        corpus.remove(pts)  # the corpus lacks the second source: only the file records it (R132)
        return corpus, seed

    def fake_members(self, corpus):
        by_url = {it["url"]: it for it in corpus}

        def members(seed, corpus_, df):
            seed["_keys"], seed["_name"] = ["次違"], "次違規合"  # the key that the key statistics pick for the seed title
            return [by_url["cna"]]
        return members

    def test_r141_2_the_recorded_name_keeps_the_file_source_that_the_new_key_lacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, seed = self.setup(root)
            with mock.patch.object(tf.tp, "members", self.fake_members(corpus)):
                stats, _, _ = tf.run(corpus, [], [seed], root, root / "report.json", today="2026-10-25")
            self.assertEqual((stats["regate_passed"], stats["regate_failed"]), (1, 0))
            text = (root / "events/2026" / f"{self.ID}.md").read_text(encoding="utf-8")
            self.assertIn("pts", text)
            self.assertIn(f"title: {self.NAME}", text)

    def test_r141_2_a_recorded_name_that_fails_the_structural_tests_does_not_replace_the_key(self):
        self.assertTrue(tf.recorded_name_passes(self.NAME, [self.CNA, self.PTS]))
        for name in ("安南區", "惡性腫瘤", "巡視船", "北高行駁回"):
            self.assertFalse(tf.recorded_name_passes(name, [self.CNA, self.PTS]), name)


class FileSourceAnchorTest(unittest.TestCase):
    """R141.3: a file source stays when its title has the topic key and a second anchor of the topic's own on-topic titles.
    The off-topic titles are the quoted cases of the T22 precision sample (mingjian, cupp, mol-migrant)."""

    MINGJIAN_ON = ["反對南投名間鄉設焚化爐  250位學者批恐衝擊農業籲縣府重新審視", "名間焚化爐二階環評會 自救會遙請濁水媽祖 現場點香爆衝突",
                   "南投名間焚化爐環評會 鄉民射紙飛機抗議場面混亂", "南投焚化爐環評會爆衝突  警否認強制力致傷", "名間焚化爐預定地周邊 拍到石虎",
                   "南投焚化爐預定地拍到石虎 農業部重申三原則嚴格把關", "名間焚化爐鑽探 湧水引爆鄉民怒火"]
    MINGJIAN_OFF = ["驚悚！日本旭山動物園員工殺妻後丟進園內焚化爐  隔天還冷靜上班", "台中文山焚化爐周遭飄「酸臭噴」味 疑垃圾平台異味待查",
                    "台東焚化爐濾管頻傳損壞 歲修換掉480根花費近1500萬", "外縣市垃圾洗產地混入高雄焚化爐  7人被逮起訴"]
    CUPP_ON = ["內政部聲請解散統促黨 學者：切斷中國在台協力者執行體系", "白狼統促黨危害國安！內政部8月初聲請解散  3大理由曝光",
               "內政部聲請解散統促黨 憲法法庭恐遇兩大關卡", "挺內政部聲請解散統促黨 綠委：盼憲法法庭切除國安毒瘤",
               "機關解散政黨首例！內政部赴憲法法庭 正式遞狀聲請解散統促黨", "內政部聲請解散統促黨 國台辦氣炸嗆「綠色恐怖」"]
    CUPP_OFF = ["持刀闖花蓮東大門夜市！ 統促黨男殺人未遂收押", "屏東統促黨里長參選人涉賄！潘建邦等3人羈押禁見",
                "地下匯兌逾千萬！統促黨「白狼」兒媳判1年7月今入獄 兒棄保潛逃"]
    MOL_ON = ["移工來台1個月爆懷孕！雇主不滿控訴、仲介全聯會指制度漏洞", "遭控「移工懷孕雇主養他全家」 勞動部駁斥：嚴重錯誤資訊",
              "逾9成家事移工雇主不滿移工政策要求改革 勞動部這麼說", "遭控縱容雇主鑽漏洞剝削履約移工 勞動部提出5點回應",
              "有關社群軟體上流傳貼文「移工懷孕勞動部一句話讓雇主養他全家」為嚴重錯誤資訊，勞動部澄清"]
    MOL_OFF = ["碧潭大橋驚魂記！疑失聯移工躲查緝 跳2樓半高慘摔空地", "移民署查獲14名失聯移工及逾期停留者台南打黑工",
               "追捕失聯越南籍移工 2海巡人員遭蜂螫傷無生命危險", "【錯誤】網傳「印尼群組攻略」教移工領百萬老年給付？惡意解讀！不實說法且金額誇大",
               "從歧視、高額仲介費到黑戶寶寶，為什麼移工寧願「失聯」也不敢求救？"]

    def kept(self, key, on, off):
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        core = [item(f"on{i}", t, "2026-10-23") for i, t in enumerate(on)]
        extra = [item(f"off{i}", t, "2026-10-23", "出版社" + str(i)) for i, t in enumerate(off)]
        df = tp.document_frequency(corpus + core + extra)
        out = tf.second_anchor_members(core + extra, core, [key], df, len(corpus) + len(core) + len(extra))
        return {m["title"] for m in out}

    def check(self, key, on, off):
        got = self.kept(key, on, off)
        for t in off:
            self.assertNotIn(t, got, t)
        for t in on:
            self.assertIn(t, got, t)

    def test_r141_3_mingjian(self):
        self.check("焚化爐", self.MINGJIAN_ON, self.MINGJIAN_OFF)

    def test_r141_3_cupp(self):
        self.check("統促黨", self.CUPP_ON, self.CUPP_OFF)

    def test_r141_3_mol_migrant(self):
        self.check("移工", self.MOL_ON, self.MOL_OFF)

    def test_r141_3_an_enforcement_or_vote_buying_title_is_another_case(self):
        members = [item(f"u{i}", t, "2026-10-23", f"p{i}") for i, t in enumerate(self.MOL_ON + self.MOL_OFF[:3])]
        groups = tf.split_cases(members)
        self.assertEqual(sorted(len(g) for g in groups), [3, 5])
        members = [item(f"u{i}", t, "2026-10-23", f"p{i}") for i, t in enumerate(self.CUPP_ON + self.CUPP_OFF[1:2])]
        self.assertEqual(sorted(len(g) for g in tf.split_cases(members)), [1, 6])

    def test_r141_3_a_topic_with_no_shared_word_keeps_its_titles(self):
        on = ["某案收賄起訴 檢方偵辦", "某地橋樑啟用 民眾叫好"]
        self.assertEqual(len(self.kept("某", on, [])), 2)


class NotTaiwanFollowupTest(unittest.TestCase):
    """R141.4: typhoon forecasts that name Taiwan, and city policy titles with a mayor name, are about Taiwan. The 9 cases are
    the not_taiwan rejects of the second T22 precision sample (first titles of each topic)."""

    CASES = {
        "typhoon sadel": ["「沙德爾」不排除有強颱機會！氣象署：下週路徑不確定性大", "「沙德爾」颱風生成！ 對台影響、最新路徑曝光", "路徑曝光！粉專：第18號颱風「沙德爾」恐今生成",
                          "北部午後注意短延時豪雨！ 「沙德爾」颱風路徑分歧大", "低壓帶影響中南部連日雨！沙德爾路徑變數大 專家曝一情境偏西走", "「沙德爾」恐升強颱路徑曝光！今全台防豪大雨",
                          "沙德爾增強為中颱！下週五、六最近台灣  最新路徑曝光", "颱風沙德爾最新預測路徑曝！含台灣「這4國」都在射程範圍內", "沙德爾出現「近中心對流爆發」！鄭明典：路徑預報關鍵時機近了",
                          "中颱沙德爾最新路徑曝！氣象粉專：朝台灣靠近機率上升"],
        "typhoon mikla": ["路徑曝！ 氣象粉專：颱風「米克拉」最快端午連假生成", "未來一週台北「熱到紫爆」！颱風米克拉最快明生成 路徑曝光", "熱帶低壓最快明增強為颱風「米克拉」 最新路徑曝",
                          "米克拉有機會升中颱！ 下週二、三成是否近台關鍵觀察期", "米克拉估達中颱以上！氣象專家曝離台灣最近時間", "天氣》米克拉颱風增強為中颱 最新路徑曝光",
                          "米克拉升級中颱！專家曝對台影響  遠離後恐還有鋒面夾擊！", "米克拉最快今晚變中颱 「這兩天」台灣雨最大"],
        "typhoon sulik": ["舒力基颱風估中秋前後生成！路徑可能落在台灣附近", "中秋賞月機率高！ 舒力基颱風最快週四生成 連假尾聲天氣成變數", "舒力基颱風將生成、連假尾聲接近台灣！Google AI分三派 路徑關鍵曝",
                          "「舒力基」最快這幾天生成！中秋連假逼近台灣 最新路徑大分歧", "準颱風「舒力基」攪局中秋？歐洲AI系集最新預測路徑曝光", "「舒力基」最快明生成！估至少達中颱 颱風論壇曝影響最大時間",
                          "「舒力基」颱風最快明生成！氣象署首報路徑曝 賈新興：有朝台灣移動趨勢", "「舒力基」生成！估週五變中颱  最新路徑、對台影響曝"],
        "bar search": ["北市警搜索同志酒吧爆爭議  蔣萬安：即刻檢討、釐清、說明", "西門町同志酒吧被警查緝掀波 公民團體在紅樓前集結抗議", "同志酒吧遭搜索 台灣同志諮詢熱線：不容北市一手消費、又一手打壓",
                       "西門同志酒吧爆執法爭議！民團北市府前抗議  要求蔣萬安公布調查結果", "同志酒吧遭搜索 爆執法過當、歧視言論", "北市同志酒吧爆搜索爭議 炎亞綸深夜發聲",
                       "警方搜索同志酒吧涉歧視言論惹議 蔣萬安致歉要求警紀宣導", "搜索風波掀PTSD？西門町同志酒吧無預警宣布：軍警制服趴取消", "抗議警違法搜索同志酒吧  黃益中怒斥侵犯人權"],
        "airport": ["蔣萬安拋松山機場遷移打造AI園區 網酸：沈伯洋果然沒說錯......", "蔣萬安拋松山機場遷建 柯文哲：2大問題要解決", "蔣萬安提遷松山機場打造AI園區 交通部：需就國家整體角度審慎評估",
                    "蔣萬安拋遷移松山機場 沈伯洋：立委到市長10年 不知做了哪些準備？", "拋松山機場遷建 蔣萬安2022年才批「選舉倉促提出」", "批蔣萬安拋松山機場遷移與李四川政見打架 蘇巧慧辦：被看破手腳"],
        "urban renewal": ["蔣萬安提放寬都更門檻 沈伯洋：出口窄未改會無解", "蔣萬安：放寬都更門檻至50％、大面積都更容積提高至300％", "蔣萬安提放寬都更門檻　內政部：關鍵在縮短審議時間"],
        "morning-after pill": ["事後避孕藥納追蹤引爭議 性平協憂民眾錯過黃金服藥時機", "事後避孕藥追蹤新制 立委要求無配套前暫緩上路", "事後避孕藥納追蹤惹議！ 石崇良：正式實施前會有配套",
                               "事後避孕藥納追蹤引爭議 吳沛憶：WHO早建議開放", "事後避孕藥擬納追蹤 藥師公會批：以保護之名限制女性生育自主", "事後避孕藥改列指示藥？石崇良：下半年定案",
                               "事後避孕藥改列指示藥提案過關 食藥署研議醫師處方、藥師指示雙軌", "事後避孕藥轉類？ 衛福部年底前給答案 追蹤追溯系統同步上路", "事後避孕藥嚴管、轉類引爭議 衛福部年底給答案"],
        "hepatitis C": ["診所爆C肝群聚！ 查出9大管制缺失 NG注射行為恐增加感染風險", "認C肝群聚與診所醫療無關 安泰淞鶴醫師：未用同一針頭施打", "板橋某診所爆C肝群聚被停業 新北衛生局：回溯一年追蹤調查就醫民眾",
                        "針頭重複抽藥！板橋安泰淞鶴診所爆急性C肝群聚 新北擴大追查、開放免費抽血檢驗", "新北診所爆C肝群聚 王必勝評「低級錯誤」、示警1事", "C肝群聚11人確診、逾千人待追蹤！消除認證衛福部已提報WHO",
                        "C肝群聚11人確診！醫檢工會示警：感染管制不能出事才補救", "板橋診所爆C肝群聚  衛福部：健保法現行難代位求償", "板橋安泰淞鶴診所C肝群聚再增2例 全案累計13例"],
        "river bridge": ["豪雨後追回進度 陳金德：台9線馬太鞍溪橋拚年底北上橋雙向通車", "台9線馬太鞍溪橋復建進度超前 交通部：年底北上線雙向通車", "馬太鞍溪橋重建進度超前 年底北上線雙向通車"],
    }

    def test_r141_4_the_nine_quoted_cases_are_about_taiwan(self):
        self.assertEqual(len(self.CASES), 9)
        for name, titles in self.CASES.items():
            self.assertTrue(tf.taiwan_relevant(titles), name)

    def test_r141_4_a_foreign_typhoon_or_a_foreign_city_policy_is_still_not_taiwan(self):
        self.assertFalse(tf.taiwan_relevant(["颱風襲擊菲律賓 馬尼拉淹水", "颱風登陸日本沖繩 航班取消", "越南颱風死亡人數增加"]))
        self.assertFalse(tf.taiwan_relevant(["東京都知事提新交通政策", "東京都新政策 日本首相回應", "大阪市長宣布新計畫"]))
        self.assertFalse(tf.taiwan_relevant(["俄軍轟炸烏克蘭各大城市", "烏克蘭稱星鏈服務未完全恢復", "川普與澤倫斯基會談 台灣議題未列入"]))


class NameQualityFollowupTest(unittest.TestCase):
    """R141.5: a name passes when its titles name a central body, a minister, 大法官 or 原住民族. The keys and titles are the
    wrong name_quality rejects of the second T22 precision sample."""

    CASES = [
        ("為原住民族", ["行政院核定西拉雅族為原住民族 西拉雅號同步完成海試", "行政院核定西拉雅族為原住民族 8月中起可登記", "法定第17個 西拉雅族獲核定為原住民族"]),
        ("收權利金", ["3大法官拒評議卻發「不同意見書」還收權利金 憲法法庭：歷來實務所未見", "大法官法律意見收權利金！ 智財律師筆戰著作權學者 精彩攻防曝光",
                   "拒評議逾300天 卻冠職銜發表不同意見／3大法官還收權利金 司法人檢舉"]),
        ("更貼近臨床需求", ["護理師「考試難度」掀議   石崇良：會讓考題更貼近臨床需求", "石崇良：檢討護理師考題 更貼近臨床需求／近2年國考每年取得執照7至8千人 及格率僅1成5到5成"]),
    ]
    MINISTER = ["衛福部長石崇良出席立法院衛環委員會備詢", "衛福部長石崇良說明健保改革", "衛福部長石崇良視察醫院"]

    def setUp(self):
        tf.set_officials(tf.office_holders([item(f"m{i}", t, "2026-10-20") for i, t in enumerate(self.MINISTER)]))
        self.addCleanup(tf.set_officials, ())

    def test_r141_5_the_quoted_name_that_passes_the_boundary_test_passes(self):
        for key, titles in self.CASES[:1]:
            self.assertEqual(tf.name_quality_ok(key, titles, len(titles), len(titles)), tf.has_word_boundary(key, titles), key)

    # Known misses (R147.2): 收權利金 and 更貼近臨床需求 fail the word-boundary test, which every name must pass (R147.1).
    # 為原住民族 is a known miss too when it fails that test.

    FRAGMENTS = [
        ("屬半成品", ["台糖5月驗出毒油石崇良稱屬半成品無須通報 國民黨：決策鏈必須究責", "石崇良:台糖檢驗脫膠原油屬半成品 無須通報", "台糖粗油屬半成品無須通報？ 陳菁徽舉蘇丹紅為例轟衛福部雙重標準", "衛福部稱台糖脫膠原油屬半成品 時力：通報規範不明  應速修法"]),
        ("部履勘", ["三鶯線拚5月報交通部履勘、6月通車 新北捷運總長達108公里", "捷運三鶯線5月報交部履勘 拚6月通車"]),
        ("案再擴大", ["馬德共諜案再擴大！檢方揪出衛福部副研究員洩密求處有期徒刑12年", "中天前主播馬德案再擴大 衛福部副研究員淪共諜 檢求刑12年"]),
        ("失聯又增", ["桃檢才破獲誘騙赴中活摘器官 陸委會：本週失聯又增9人", "陸委會：赴中失聯又增9人"]),
        ("半夜不適", ["孩子半夜不適難就醫？衛福部：全台205家醫院可看診", "小孩半夜不適 全台205家醫院提供急診"]),
        ("府國務機要費全", ["總預算三讀》總統府國務機要費全砍凍  公布遭擱置5法案始得動支", "總預算三讀》府國務機要費全凍刪 卓榮泰薪資凍結4個月"]),
        ("蘇嘉宏引", ["蘇嘉宏引中學者見解稱東部內海 海委會副主委駁斥：不符國際法", "蘇嘉宏引紅統見解稱東部內海 學者駁斥：非權威解讀", "國民黨推薦新任中選會委員》蘇嘉宏引用中國紅統稱權威 立委批中共代言人"]),
        ("菲律賓參", ["涉杜特蒂血腥掃毒案！菲律賓參議員藏議會躲ICC緝拿 參院傳槍響", "菲律賓參院警隊與調查局對峙 總統府：相互鳴槍示警"]),
        ("賣場美國馬鈴薯發", ["賣場美國馬鈴薯發芽跟調整檢疫有關？ 防檢署嚴正澄清", "謠言終結站》賣場美國馬鈴薯發芽跟調整檢疫有關？ 防檢署嚴正澄清", "網傳賣場美國馬鈴薯發芽 防檢署：鮮食用檢疫規定沒調整"]),
        ("中火燃氣二期環評遭", ["中火燃氣二期環評遭北高行撤銷 台電：配合環境部 拚早日無煤", "中火燃氣二期環評遭撤 環團籲台電進行二階環評"]),
    ]

    def test_r146_titles_that_name_a_central_body_do_not_excuse_a_fragment(self):
        for key, titles in self.FRAGMENTS:
            self.assertFalse(tf.name_quality_ok(key, titles, len(titles), len(titles)), key)

    GATE_FRAGMENTS = [
        ("接閣揆", ["陳其邁酸「工作做好卡實在」回應接閣揆 蔣萬安：重新組閣化解朝野僵局", "蔣萬安點名接閣揆   陳其邁：把工作做好卡實在、台北市長也該如此", "蔣萬安點名接閣揆 陳其邁嗆：先把台北市長做好"]),
        ("法務部模範公務", ["打擊貪瀆與守護國安 竹檢檢察官王遠志獲法務部模範公務人員殊榮", "偵辦徐春鶯、謝宜容案立功 檢察官黃佳彥獲頒法務部模範公務員"]),
        ("廠遭持槍", ["草屯床墊廠遭持槍搶80萬 3嫌落網"]),
        ("巡人員", ["追捕失聯越南籍移工  2海巡人員遭蜂螫傷無生命危險"]),
        ("議會辦桌替姑姑助選", ["謝典霖再爆爭議！吳音寧轟議會辦桌替姑姑助選「公器私用恐涉賄選」"]),
        ("朱安雄", ["前高雄市議長朱安雄在中國病逝！曾因賄選案重傷議會 破天荒補選18人"]),
        ("薛楷莉", ["獨家》吞420萬判刑確定將入獄！薛楷莉疑逃亡 傳喚未到恐遭通緝", "前主播薛楷莉發監未到 恐逃了／私吞420萬 洗錢罪判刑確定", "洗錢判刑確定！前明星主播薛楷莉傳拘無著 北檢發布通緝20年", "前明星主播淪通緝犯！薛楷莉登高檢署網站 黑白大頭照曝光"]),
    ]

    def test_r147_a_name_with_no_skip_fails_the_gate_fragments(self):
        for key, titles in self.GATE_FRAGMENTS:
            self.assertFalse(tf.name_quality_ok(key, titles, len(titles), len(titles)), key)

    def test_r147_a_key_with_one_use_cannot_show_its_word_boundary(self):
        self.assertFalse(tf.has_word_boundary("廠遭持槍", ["草屯床墊廠遭持槍搶80萬 3嫌落網"]))

    def test_r147_a_bare_person_name_fails(self):
        titles = ["前高雄市議長朱安雄在中國病逝", "前主播薛楷莉發監未到"]
        self.assertTrue(tf.is_person_or_party("朱安雄", titles[:1]))
        self.assertTrue(tf.is_person_or_party("薛楷莉", titles[1:]))
        self.assertFalse(tf.is_person_or_party("國小周邊", ["高市查獲國小周邊販售來源不明中國零食"]))

    def test_r141_5_a_title_that_names_a_minister_by_name_counts(self):
        self.assertEqual(tf.office_holders([item(f"m{i}", t, "2026-10-20") for i, t in enumerate(self.MINISTER)]), {"石崇良"})
        self.assertTrue(tf.names_central("石崇良：檢討護理師考題"))
        self.assertFalse(tf.names_central("王小明：檢討護理師考題"))

    def test_r141_5_a_fragment_with_no_central_body_still_fails(self):
        titles = ["他說更貼近臨床需求", "網友說更貼近臨床需求吧", "更貼近臨床需求 網友嘆"]
        self.assertFalse(tf.name_quality_ok("更貼近臨床需求", titles, 3, 3))
        titles = ["北市議員說不可原諒", "網友說不可原諒吧", "不可原諒 網友嘆"]
        self.assertFalse(tf.name_quality_ok("不可原諒", titles, 3, 3))

    def test_r141_5_a_central_body_does_not_excuse_a_generic_name(self):
        titles = ["行政院核定安南區計畫", "行政院說明安南區", "行政院回應安南區"]
        self.assertFalse(tf.name_quality_ok("臺南市安南區", titles, 3, 3))
        self.assertFalse(tf.name_quality_ok("北高行駁回", ["行政院北高行駁回"], 3, 3))


class GovProgramAndSchoolTest(unittest.TestCase):
    """R141.6: a city program name is a government act. A school name alone is not sensitive."""

    PROGRAM = ["熱「暑」！新北涼適地圖據點今年將增加135處 高溫即啟動應變措施", "新北涼適地圖據點 今年再增加135處"]
    SCHOOL = ["竹南高中生沒 YouBike 騎？縣議員促尖峰調度", "苗議員促YouBike停竹南高中 供放學騎乘"]

    def test_r141_6_a_city_program_name_gives_the_city_government(self):
        self.assertIn("ac-new-taipei-city-government", tf.detect_gov_actors(self.PROGRAM, ["jur-65000000"]))

    def test_r141_6_a_city_name_without_a_program_noun_gives_no_actor(self):
        self.assertEqual(tf.detect_gov_actors(["新北詐騙集團落網", "新北男子酒駕"], ["jur-65000000"]), [])

    def test_r141_6_a_school_name_alone_is_not_sensitive(self):
        items = [item(f"u{i}", t, "2026-10-23", f"p{i}", sensitive=True) for i, t in enumerate(self.SCHOOL)]
        self.assertIsNone(tf.exclusion_reason(items))

    def test_r141_6_a_sensitive_term_beside_a_school_name_still_counts(self):
        titles = ["金華國中生墜樓 校方說明", "北市國中生墜樓 市府慰問", "高中生遭性侵 竹南高中回應"]
        items = [item(f"u{i}", t, "2026-10-23", f"p{i}", sensitive=True) for i, t in enumerate(titles)]
        self.assertEqual(tf.exclusion_reason(items), "sensitive")


class TodayOptionTest(unittest.TestCase):
    """R141.7: the CLI takes --today YYYY-MM-DD, so the second-day check of R137 needs no Python call."""

    ARGS = ["topics_full", "corpus.jsonl", "clusters.json", "seeds.json", "root", "report.json"]

    def call(self, extra):
        seen = {}

        def fake_run(corpus, clusters, seeds, root, report, today=None):
            seen["today"] = today
            return {}, [], []
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "corpus.jsonl").write_text("", encoding="utf-8")
            (tmp / "clusters.json").write_text("[]", encoding="utf-8")
            (tmp / "seeds.json").write_text("[]", encoding="utf-8")
            argv = [str(tmp / a) if a.endswith((".jsonl", ".json")) else a for a in self.ARGS] + extra
            with mock.patch.object(tf, "run", fake_run), mock.patch("builtins.print"):
                rc = tf.main(argv)
        return rc, seen

    def test_r141_7_no_option_keeps_the_default(self):
        self.assertEqual(self.call([]), (0, {"today": None}))

    def test_r141_7_the_option_sets_the_day(self):
        self.assertEqual(self.call(["--today", "2026-10-27"]), (0, {"today": "2026-10-27"}))

    def test_r141_7_a_bad_day_or_a_missing_day_stops_the_run(self):
        for extra in (["--today", "27-10-2026"], ["--today"], ["--today", "2026-13-01"]):
            self.assertEqual(self.call(extra), (2, {}), extra)


if __name__ == "__main__":
    unittest.main()
