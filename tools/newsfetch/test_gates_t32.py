"""T32 gate round (R194 to R199, R196 items 1 to 8). Each item has one case from the T31-P fail list (the titles are the real headlines
of the judged topics), one case from outside every judged list, and pass cases."""

import unittest

from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf


def item(url, title, day="2026-10-21", publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


def items(titles, day="2026-10-21"):
    return [item(f"u{i}", t, day, publisher=f"出版社{i % 2}") for i, t in enumerate(titles)]


class ActVerbLeadTest(unittest.TestCase):
    """R196.1: a name whose first word is a verb or an act verb has no subject."""

    def test_judged_names(self):  # 免健保費, 提追加預算, 聲請釋憲, 刪商圈補助預算
        for name in ("免健保費", "提追加預算", "聲請釋憲", "刪商圈補助預算"):
            self.assertTrue(tf.act_verb_lead(name), name)

    def test_names_from_outside_the_judged_list(self):
        for name in ("減徵房屋稅", "追加防疫經費", "修停車管理辦法", "補發春節津貼"):
            self.assertTrue(tf.act_verb_lead(name), name)

    def test_a_name_with_a_subject_or_a_noun_head_passes(self):
        for name in ("國防部提追加預算", "高雄市追加預算", "立法院修憲", "軍購條例", "三班護病比", "炸藥採購案"):
            self.assertFalse(tf.act_verb_lead(name), name)

    def test_the_gate_rejects_it_for_a_new_name_only(self):
        titles = ["長者免健保費 立院三讀 衛福部說明", "免健保費爭議 行政院說明", "免健保費入法 立委推動"]
        members = items(titles)
        corpus = members + [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        df = tp.document_frequency(corpus)
        self.assertEqual(tf.gate_topic("免健保費", members, members[:1], df, corpus)[0], "rejected_issue_name")
        self.assertEqual(tf.gate_topic("免健保費", members, members[:1], df, corpus, rebuilds_old=True)[0], "rejected_issue_name")  # a rebuild gets a new name from its key
        known = {"name": "長者有條件免健保費", "jids": ["jur-tw"], "actors": [], "sensitive": False}
        self.assertEqual(tf.gate_topic("免健保費", members, members[:1], df, corpus, known=known)[0], "ok")  # R155.4: an old topic keeps its recorded name


class TitleTermTest(unittest.TestCase):
    """R196.2: a name that sits inside a quote, or after a colon or 稱, in 2 or more titles is words of a speaker."""

    def test_judged_slogan_and_remark(self):
        slogan = ["政院又不副署 韓國瑜說重話：執政權大不過憲法", "韓國瑜嗆政院執政權大不過憲法 綠黨團回擊：國會多數也大不過憲法",
                  "韓國瑜對政院撂重話 莊瑞雄：國會席次再多 一樣大不過憲法", "韓國瑜批執政權大不過憲法 政院：不副署就是捍衛憲政",
                  "1分鐘看政治》韓痛批卓「執政權再大 大不過憲法」 陳幸妤揭前夫心結", "卓不副署法案》韓：執政權大不過憲法 政院強調有責任護憲",
                  "韓國瑜批「執政權再大、都大不過憲法」 卓榮泰反問：您主導的立法院有恪遵憲法？", "韓批卓 執政權再大 大不過憲法",
                  "韓國瑜喊「執政權大不過憲法」 卓揆：盼共同面對憲法", "韓國瑜批「執政權大不過憲法」》卓榮泰：立院有遵憲嗎 國民黨嗆卓法律系白念"]
        self.assertTrue(tf.title_term("大不過憲法", slogan))
        remark = ["卓揆稱立院刪預算「只能致電地方」民眾黨團列出經費批AI內閣變悲哀", "豪雨灌南部釀災情 卓榮泰：立院刪預算這幾天只能先電話聯繫地方",
                  "雨炸南台！卓揆稱「立院刪預算這幾天只能致電地方」 藍委曝1事狠酸"]
        self.assertTrue(tf.title_term("立院刪預算", remark))

    def test_a_remark_from_outside_the_judged_list(self):
        self.assertTrue(tf.title_term("財源無虞", ["財長稱財源無虞 國庫尚有餘額", "部長：財源無虞 不需加稅", "財政部稱「財源無虞」 在野黨質疑"]))

    def test_an_issue_that_one_title_quotes_passes(self):
        titles = ["無人機條例三讀 藍白推動", "藍白提無人機條例 政院版", "卓榮泰：無人機條例需修正", "無人機條例協商破局", "無人機條例 國防部說明"]
        self.assertFalse(tf.title_term("無人機條例", titles))

    def test_the_gate_rejects_it_for_a_new_topic_only(self):
        titles = ["財長稱財源爭議已解 財政部說明", "部長：財源爭議不影響發放 行政院說明", "財政部稱「財源爭議」 立委質疑"]
        members = items(titles)
        corpus = members + [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        df = tp.document_frequency(corpus)
        self.assertEqual(tf.gate_topic("財源爭議", members, members[:1], df, corpus)[0], "rejected_issue_name")
        self.assertEqual(tf.gate_topic("財源爭議", members, members[:1], df, corpus, rebuilds_old=True)[0], "rejected_issue_name")
        known = {"name": "財源爭議", "jids": ["jur-tw"], "actors": [], "sensitive": False}
        self.assertEqual(tf.gate_topic("財源爭議", members, members[:1], df, corpus, known=known)[0], "ok")


class BareEntityTest(unittest.TestCase):
    """R196.3: a bare organization, fund or company name, and <entity>案 with no issue noun, name no issue."""

    def test_judged_names(self):  # 國安基金, 兆基案
        for name in ("國安基金", "兆基案"):
            self.assertTrue(tf.bare_entity(name), name)

    def test_names_from_outside_the_judged_list(self):
        for name in ("勞退基金", "遠雄公司", "東元案", "新光集團"):
            self.assertTrue(tf.bare_entity(name), name)

    def test_a_name_with_an_issue_noun_passes(self):
        for name in ("炸藥採購案", "總統彈劾案", "南海仲裁案", "勞退基金改革", "國安基金進場", "中選會人事案", "公視預算", "食安法"):
            self.assertFalse(tf.bare_entity(name), name)


class GovernmentScopeTest(unittest.TestCase):
    """R196.6: a title that names another government level than the topic fails (b) for that title. R196.4: two big groups
    of two levels make a mixed cluster."""

    CENTRAL_TITLES = ["外交部今年媒宣費 藍委又要砍逾億", "外交部媒宣費藍委刪1億保留協商 徐巧芯同意不凍結護照預算", "藍提案砍外交部「媒宣費」1億 馬文君：保留送協商",
                      "吳思瑤控刪外交部1億媒宣費 徐巧芯打臉要求公開道歉", "翁曉玲刪光文化部媒宣費 王婉諭：不能為政黨惡鬥癱瘓行政機關",
                      "立院審查文化部預算 媒宣費最終凍結800萬元", "陸委會媒宣費恐遭全砍！梁文傑嗆「剩一張嘴也要戰鬥」翁曉玲：替國家節省公帑",
                      "翁曉玲刪陸委會媒宣費更嗆梁文傑 他噴：按妳標準藍「這縣市」可比照辦理...."]

    def test_a_city_title_in_a_national_topic_fails(self):  # judged: 媒宣費
        titles = self.CENTRAL_TITLES + ["林亮君仿翁曉玲質疑市府媒宣費成效 蔣萬安：預算一定花在刀口上", "舉翁曉玲大刪媒宣費 綠議員喊砍市府媒宣費、轟花錢為盧秀燕擦脂抹粉"]
        off, mixed = tf.scope_levels(titles, True)
        self.assertEqual(sorted(off), [8, 9])
        self.assertFalse(mixed)

    def test_a_city_title_from_outside_the_judged_list(self):
        titles = ["教育部公布營養午餐新制 學校配合", "教育部說明營養午餐補助 立委關切", "營養午餐新制 教育部：下學期上路", "教育部宣布營養午餐加碼", "台中市府營養午餐自辦 市議員質詢"]
        off, mixed = tf.scope_levels(titles, True)
        self.assertEqual(off, [4])
        self.assertFalse(mixed)

    def test_a_central_title_in_a_local_topic_fails(self):
        titles = ["高雄市府推公車免費 交通局說明", "高雄市公車免費 市議員質詢", "高雄市府公車免費上路 局長說明", "交通部審議公車補助 立委質詢"]
        off, mixed = tf.scope_levels(titles, False)
        self.assertEqual(off, [3])
        self.assertFalse(mixed)

    def test_two_big_groups_of_two_levels_are_a_mixed_cluster(self):  # judged: 提追加預算
        titles = ["向議會提追加預算 陳其邁：聚焦4大市民優先策略", "聚焦四大市民優先策略 高市府提追加預算14.23億元", "李文忠：有迫切的商購委製 失職的國防部應提追加預算",
                  "國防預算被打6折 汪浩籲政院「即刻反擊」：再提修法、提追加預算", "國防特別條例被砍部分提追加預算？莊瑞雄嘆總預算都還沒審"]
        self.assertTrue(tf.scope_levels(titles, True)[1])

    def test_a_mixed_cluster_from_outside_the_judged_list(self):
        titles = ["經濟部公布電動車補助 業者表示", "經濟部電動車補助 立委關切", "新竹市府電動車補助 市議會質詢", "新竹市電動車補助 市府說明", "電動車補助新制 各界看法"]
        self.assertTrue(tf.scope_levels(titles, True)[1])


class PlaceScopeTest(unittest.TestCase):
    """R196.5: a place stays in the topic only when every title names it."""

    def test_judged_topic(self):  # 澎湖縣國旅補助優惠
        titles = ["平日國旅補助優惠 澎湖首波額度使用破8成達標", "國旅補助優惠集中在平日 上班族嘆「還要請特休」：寧願出國"]
        self.assertEqual(tf.place_scope(titles, ["jur-10016000"]), ["jur-tw"])

    def test_a_topic_from_outside_the_judged_list(self):
        titles = ["嘉義縣祭典補助新制 縣府公告", "祭典補助新制 農業部說明"]
        self.assertEqual(tf.place_scope(titles, ["jur-10010000"]), ["jur-tw"])

    def test_every_title_names_the_place(self):
        titles = ["嘉義縣祭典補助新制 縣府公告", "嘉義縣祭典補助新制 議員質詢"]
        self.assertEqual(tf.place_scope(titles, ["jur-10010000"]), ["jur-10010000"])
        self.assertEqual(tf.place_scope(titles, ["jur-tw"]), ["jur-tw"])


class DuplicateActorActTest(unittest.TestCase):
    """R196.7: two topics with the same date window, the same actor and the same act are one topic."""

    def profile(self, key, titles, day="2026-09-29"):
        return tf.issue_profile(key, [item(f"{key}{i}", t, day) for i, t in enumerate(titles)])

    def test_judged_pair(self):  # 監察院人事同意權案 and 監委人事案
        a = self.profile("監察院人事同意權案", ["監察院人事同意權案 27位被提名人全遭立院否決", "監察院人事同意權案 立法院投票全遭藍白封殺", "監察院人事同意權案 民進黨團一致性投同意票"])
        b = self.profile("監委人事案", ["監委人事案全遭封殺 監院：衝擊人民權益保障", "監委人事案全遭封殺 總統府：深表遺憾", "監委人事案遭封殺 藍：總統府勿把責任推給國會"])
        self.assertTrue(tf.same_issue(a, b, {}))

    def test_a_pair_from_outside_the_judged_list(self):
        a = self.profile("國防部軍官人事案", ["國防部軍官人事案 立院質詢", "國防部軍官人事案 部長說明", "國防部軍官人事案 在野黨批評"])
        b = self.profile("國防部人事案", ["國防部人事案爭議 立委關切", "國防部人事案 國防部回應", "國防部人事案 朝野協商"])
        self.assertTrue(tf.same_issue(a, b, {}))

    def test_the_same_actor_with_another_act_is_another_topic(self):
        a = self.profile("監察院人事同意權案", ["監察院人事同意權案 立法院投票", "監察院人事同意權案 全遭封殺", "監察院人事同意權案 總統府回應"])
        b = self.profile("監察院彈劾案", ["監察院彈劾案 監委提案", "監察院彈劾案 審查會議", "監察院彈劾案 被彈劾人說明"])
        self.assertFalse(tf.same_issue(a, b, {}))

    def test_the_same_act_with_another_actor_is_another_topic(self):
        a = self.profile("國防部軍官人事案", ["國防部軍官人事案 立院質詢", "國防部軍官人事案 部長說明", "國防部軍官人事案 在野黨批評"])
        b = self.profile("教育部教師人事爭議", ["教育部教師人事爭議 校長遴選", "教育部教師人事爭議 教師團體", "教育部教師人事爭議 主秘離職"])
        self.assertFalse(tf.same_issue(a, b, {}))

    def test_two_windows_far_apart_are_two_topics(self):
        a = self.profile("國防部軍官人事案", ["國防部軍官人事案 立院質詢", "國防部軍官人事案 部長說明", "國防部軍官人事案 在野黨批評"], "2026-05-01")
        b = self.profile("國防部人事案", ["國防部人事案爭議 立委關切", "國防部人事案 國防部回應", "國防部人事案 朝野協商"], "2026-09-20")
        self.assertFalse(tf.same_issue(a, b, {}))


class GenericClauseTest(unittest.TestCase):
    """R196.8: a clause with a subject, a verb and a generic object (預算, 法案) and no named item names no issue."""

    def test_judged_name(self):  # 立院刪預算
        self.assertTrue(tf.generic_clause("立院刪預算"))

    def test_names_from_outside_the_judged_list(self):
        for name in ("國防部砍經費", "政院退法案", "市府凍預算"):
            self.assertTrue(tf.generic_clause(name), name)

    def test_a_named_item_or_no_verb_passes(self):
        for name in ("立院刪公視預算", "國防特別條例", "公視預算", "政院退回數位發展法案", "追加預算"):
            self.assertFalse(tf.generic_clause(name), name)


if __name__ == "__main__":
    unittest.main()
