"""T84 (R359): gate fixes after the T83 run. Each test names the item of R359 it checks.
The titles are the member titles of the old topics in the T83 run (cut to 60 characters)."""

import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

item = base.item


class SecondAnchorMemberTest(unittest.TestCase):
    """R359.1 (G8): one anchor word, or a body that is held by a minority of the on-topic titles, must not remove on-topic members.
    China's 外交部 is not the 外交部 of Taiwan."""

    DELIVERY = [
        '外送專法子法拍板！平台業者表態：全力配合、儘速研析新制',
        '勞動部發布外送專法三子法 企業須在7/21前改正所有外送員契約',
        '外送專法7月21日上路 3子法明確4大保障',
        '外送專法21日上路！DEAT提3大建議、專家示警5大衝擊',
        '外送專法將上路 工會批媒合費違法是課金上班',
        'DEAT盼滾動檢討外送專法 專家：研議向外送員收媒合費',
        '業者估外送專法上路成本恐增3成 平台是否漲價待評估',
        '《外送專法》21日上路 Uber Eats公布外送員4大保障措施',
        '外送專法7/21上路 Uber Eats推即時提領報酬',
        '外送專法7／21上路 傳平台預告「運費必調」 估大漲3成',
        '外送專法7／21上路 平台預告「運費必漲」最高5成',
        '外送專法將上路 民眾黨團5訴求要求保障外送員',
        '外送專法明上路配套未齊 民眾黨轟陳世凱「別只會騎車作秀」',
        '《外送專法》明上路 四大部會完成相關7項配套法規同步施行',
        '外送專法上路！公平會警告外送平台\u3000聯合漲價違者可重罰5千萬',
        '外送專法今上路 經部公布外送合作契約範本',
        '外送專法上路！平台疊單意願低 消費者等餐恐更久',
        '外送專法今上路！ 勞動部曝「以四方關係衡平為核心」：將建立溝通機制',
        '外送專法今上路 Grab接球18大工會聲明 承諾保障外送員收入、尊重多平台接單',
        '外送專法今上路！Uber Eats率先調漲2費用 foodpanda最新回應曝',
        '外送專法上路！律師點出隱憂 恐4類人都輸「只有立委贏了」',
        '外送專法上路「三輸」？黃世聰轟藍白政治操作：苦的還是外送員',
        '外送專法上路「薪」酸 南部外送員：單量變少',
        '外送專法上路2週 Uber Eats：低報酬者收入增逾18%',
        '外送專法上路兩週 Uber Eats：外送夥伴報酬提升、整體訂單量穩定',
        '外送專法上路首批報酬明細曝光 工會痛批Uber Eats：不要把外送員當傻子',
        '外送專法上路2周 Uber Eats：外送員報酬提升18.2％ 訂單量持穩',
        'UberEats挨告！外送專法上路 聯盟、工會控：短付報酬涉詐欺',
        '法律觀點－外送專法新上路 誰受益，誰買單？',
        '外送專法上路成本增！foodpanda商家續約方案掀討論 官方回應了',
        '外送專法上路變貴又變慢？胡采蘋等餐逾1小時怒：每叫一次都在懲罰自己',
        '外送專法上路！Uber Eats數據揭：平台成本增4成、消費者等餐多7分',
    ]

    SEA = [
        '南海仲裁案10週年 外交部重申4原則籲維護和平',
        '南海仲裁案裁決10週年 14國聯合聲明中國不接受',
        '南海仲裁案10周年 外交部重申我國「四點原則」、反對單邊擴張主義',
        '南海仲裁案10週年 外交部重申4原則：台灣應納入多邊爭端解決機制',
        '中國外交部約見日本公使 抗議南海仲裁案等議題',
        '南海仲裁案裁決10週年 14國聲明肯定裁決拘束力',
        '南海仲裁案10週年 陳清龍：政府該「強硬起來」表達主權',
        '南海仲裁案10周年 陳以信籲賴清德親登太平島',
        '南海仲裁案10週年 作證美學者竟在菲律賓家中遭搶劫槍殺',
    ]

    MEDIA_FEE = [
        '藍提案砍外交部「媒宣費」1億 馬文君：保留送協商',
        '外交部媒宣費藍委刪1億保留協商 徐巧芯同意不凍結護照預算',
        '外交部今年媒宣費 藍委又要砍逾億',
        '遭控刪外交部1.04億媒宣費 徐巧芯批造謠抹黑要求道歉 吳思瑤急更正',
        '外交部媒宣費 藍委提案刪1億 保留協商',
        '吳思瑤控刪外交部1億媒宣費 徐巧芯打臉要求公開道歉',
        '獨家》翁曉玲對文化部下狠手 4738萬元媒宣費全砍光',
        '尊重翁曉玲刪光文化部媒宣費 蔡春綢：公帑不能發包給顏色親近側翼',
        '翁曉玲刪光文化部媒宣費 王婉諭：不能為政黨惡鬥癱瘓行政機關',
        '遭指砍文化部媒宣費 翁曉玲：浮編亂編就該刪',
        '才大刪外交部》翁曉玲再下重手 要砍光文化部媒宣費',
        '下重手砍光文化部媒宣費 翁曉玲嗆：我太佛心！否則會刪更多',
        '提案砍光文化部4738萬媒宣費 翁曉玲自稱「佛心」',
        '翁曉玲砍文化部媒宣費 嗆「我太佛心」否則刪更多！王定宇轟：台灣哪裡對不起妳？',
        '文化部媒宣費柯志恩「凍結300萬」取得共識  遭羅廷瑋駁：須尊重翁曉玲',
        '立院審查文化部預算 媒宣費最終凍結800萬元',
        '翁曉玲提全刪文化部媒宣費！ 「教委會」吵翻.最終凍結800萬',
        '點名7女綠委轟「跳樑小丑」 翁曉玲嗆再刪光文化部媒宣費',
        '文化部編列4738萬元媒宣費惹議 立法院決議凍結800萬元',
        '批砍文化部媒宣費閹割台灣文化力 吳思瑤嗆她：還要繼續作亂嗎',
        '翁曉玲砍媒宣費遭轟「文化殺手」 綠委爆4部會提案全複製貼上',
        '鐵了心砍光文化部4738萬媒宣費！ 翁曉玲嗆綠營：將再提案全刪',
        '不滿翁曉玲要砍光文化部4738萬媒宣費 吳沛憶轟：政治凌駕文化的傲慢',
        '翁曉玲刪光文化部及13部會媒宣費 律師：已違憲、檢調應查是否受中國指示',
        '翁曉玲狂刪13部會媒宣費 黃暐瀚：刪光不叫監督！藍營執政14縣市是否也全砍？',
        '批藍營「刪光預算不叫監督」 黃暐瀚：執政縣市媒宣費也全砍光？',
        '翁曉玲砍多部會媒宣費 民進黨：這不算監督而是傲慢',
        '陳秀寳憂在野黨擬提案刪媒宣費 李遠盼溝通',
        '總預算啟動朝野協商 藍黨團：媒宣費、首長特別費嚴格刪減或凍結',
        '陸委會媒宣費恐遭全砍！梁文傑嗆「剩一張嘴也要戰鬥」翁曉玲：替國家節省公帑',
        '翁曉玲發文嗆媒宣費全刪！梁文傑親自轉發回「這句」嗆爆',
        '翁曉玲刪陸委會媒宣費更嗆梁文傑 他噴：按妳標準藍「這縣市」可比照辦理....',
        '文化部媒宣費全刪 李遠：假日繼續宣傳政策',
        '公視預算刪2185萬 文化部媒宣費全砍',
        '媒宣費刪減89% 陸委會：年度僅有144萬元可用',
        '陸委會媒宣費到年底只剩15萬 梁文傑嘆：比縣市中小局處都少',
    ]

    SINKHOLE = [
        '巴威颱風攪局 竹北「豐采520」天坑案宣判延期至下週一',
        '竹北天坑案一審宣判 楊文科獲判無罪',
        '天坑案楊文科一審無罪 竹檢：收到判決後評估上訴',
        '竹北天坑案一審獲判無罪 楊文科喊「真相終於水落石出」：沒有喜悅只有欣慰',
        '竹北天坑案被控涉貪 楊文科一審無罪',
        '竹北天坑案一審無罪 楊文科：鐵腕把關不退讓 清白經得起檢驗',
        '天坑案宣判楊文科無罪  歐陽霆：切割下屬卸責「有什麼好欣慰」',
        '天坑案宣判 民進黨竹縣長參選人、竹北市長鄭朝方這麼回應',
        '竹北天坑案》楊文科獲判無罪 曾聖凱：市民更在意城市是否安全',
        '不服天坑案一審判決 豐邑建設：將依法提起上訴',
        '竹北天坑案一審出爐 楊文科脫罪、兩公務員涉不法利益有罪',
        '快訊／新竹縣長楊文科捲竹北天坑案 一審宣判無罪',
        '新竹天坑案宣判前一天…「豐邑文心匯」出事！高空招牌驚見明火',
        '竹北天坑案涉圖利獲判無罪 楊文科：事實不會被抹黑掩蓋',
        '天坑案楊文科一審無罪！竹北市長參選人邱臣遠：安全底線不能退讓',
        '竹北天坑案楊文科一審無罪 王婉諭支持檢方上訴 促楊專心縣政',
        '天坑案 楊文科獲判無罪》藍營：遲來的正義 綠議員：責推下屬',
        '竹北天坑案判決掀議！專家揭建商「8次違規」仍一路闖關 他直呼：主管能都不知情？',
        '天坑案才判完！楊文科率高官請假跑造勢 她怒轟：基層公務員情何以堪？',
        '竹北天坑案爆「藏寶圖」藏賄款  監院彈劾前竹縣工務處長江良淵',
        '竹北天坑案楊文科一審無罪 新竹地檢提上訴',
        '獨家》竹北天坑案楊文科涉貪一審無罪  竹檢不服判決提上訴',
        '竹北天坑案楊文科涉貪一審宣判無罪竹檢提上訴 竹縣府回應了',
        '竹北豐采520天坑案「楊文科無罪」 檢察官不服提上訴',
        '快訊／竹北天坑案楊文科一審無罪！ 竹檢不服上訴',
    ]

    def kept(self, key, titles, other_uses=0):
        """`other_uses`: the titles outside the topic that hold the key. Every other word is common in the real corpus (df 1000), as in the T83 run,
        where only the body names were second anchors."""
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(60)]
        core = [item(f"m{i}", t, "2026-10-23", "出版社" + str(i % 5)) for i, t in enumerate(titles)]
        df = {g: 1000 for g in tp.document_frequency(corpus + core)}
        df[key] = len(core) + other_uses
        out = tf.second_anchor_members(core, core, [key], df, len(corpus) + len(core))
        return {m["title"] for m in out}

    def test_r359_1_a_single_body_anchor_keeps_the_on_topic_members_of_the_delivery_law(self):
        got = self.kept("外送專法", self.DELIVERY, other_uses=19)  # 29 of 51 uses in the T83 corpus
        self.assertEqual(got, set(self.DELIVERY))

    def test_r359_1_a_generic_key_still_needs_the_anchor(self):
        got = self.kept("外送專法", self.DELIVERY, other_uses=600)  # the same titles under a key that most other news holds
        self.assertLess(len(got), len(self.DELIVERY))
        self.assertTrue(all("勞動部" in t for t in got))

    def test_r359_1_the_opposition_side_of_the_media_fee_topic_stays(self):
        got = self.kept("媒宣費", self.MEDIA_FEE, other_uses=27)
        for t in self.MEDIA_FEE:
            if "翁曉玲" in t or "黃暐瀚" in t or "陳秀寳" in t or "協商" in t:
                self.assertIn(t, got, t)

    def test_r359_1_the_developer_side_of_the_sinkhole_case_stays(self):
        got = self.kept("天坑案", self.SINKHOLE, other_uses=8)
        for t in self.SINKHOLE:
            if "竹北" in t:
                self.assertIn(t, got, t)

    def test_r359_1_the_arbitration_topic_keeps_the_14_nation_statement_and_drops_the_foreign_office(self):
        got = self.kept("南海仲裁案", self.SEA, other_uses=3)
        for t in self.SEA:
            if "14國" in t or "陳清龍" in t:
                self.assertIn(t, got, t)
        self.assertNotIn("中國外交部約見日本公使 抗議南海仲裁案等議題", got)  # 中國外交部 is not a body of Taiwan

    def test_r359_1_a_foreign_office_is_no_anchor(self):
        got = self.kept("南海仲裁案", self.SEA, other_uses=3)
        self.assertTrue(any("外交部重申" in t for t in got))
        self.assertFalse(any(t.startswith("中國外交部") for t in got))

    def test_r359_1_a_robbery_title_is_another_case(self):
        members = [item(f"m{i}", t, "2026-10-23", "出版社" + str(i)) for i, t in enumerate(self.SEA)]
        lists = tf.split_cases(members)
        robbery = "南海仲裁案10週年 作證美學者竟在菲律賓家中遭搶劫槍殺"
        self.assertEqual(len(lists), 2)
        self.assertEqual([m["title"] for lst in lists for m in lst if m["title"] == robbery], [robbery])
        self.assertNotIn(robbery, {m["title"] for m in max(lists, key=len)})


class ForeignEventTest(unittest.TestCase):
    """R359.2 (G1): a foreign court is not a Taiwan body. A body that foreign states share (憲法法庭, 外交部) counts as a Taiwan link in a new topic only with a
    public act. The test holds for every country, not for a list of countries. The name 波蘭憲法法 is a cut of 憲法法庭 and 憲法法院."""

    POLAND = ["波蘭憲法法庭院長遭停職警方進駐！總統斥「政變」", "波蘭憲法法院動盪蔓延 駐中大使率先請辭引發跟進潮", "波蘭憲法法庭爆發對峙危機 總統緊急中斷訪非行程返國協商",
              "波蘭憲法法庭院長遭停職引爆司法危機 總統中斷訪塞內加爾急返國", "波蘭憲法法庭院長遭停職引爆危機 警方戒備總統急返國",
              "波蘭憲法法院爆奪權爭議 總統急返國召開危機對談", "波蘭憲法法院動盪蔓延  駐中大使請辭引發跟進潮"]
    TAIWAN_COURT = ["憲法法庭裁定死刑違憲 法務部回應", "憲法法庭公告言詞辯論日期", "大法官審查國民法官法 憲法法庭判決出爐"]
    TAIWAN_FOREIGN_MINISTRY = ["外交部公告旅遊警示升級", "外交部決定增派人員 協助國人撤離"]

    def test_r359_2_a_foreign_court_with_no_act_is_not_about_taiwan(self):
        self.assertFalse(tf.taiwan_relevant(self.POLAND, new=True))

    def test_r359_2_the_test_holds_for_another_country(self):
        titles = [t.replace("波蘭", "匈牙利") for t in self.POLAND]
        self.assertFalse(tf.taiwan_relevant(titles, new=True))

    def test_r359_2_a_taiwan_court_with_an_act_is_about_taiwan(self):
        self.assertTrue(tf.taiwan_relevant(self.TAIWAN_COURT, new=True))
        self.assertTrue(tf.taiwan_relevant(self.TAIWAN_FOREIGN_MINISTRY, new=True))

    def test_r359_2_a_body_that_only_Taiwan_has_still_counts(self):
        self.assertTrue(tf.taiwan_relevant(["行政院會議討論", "政院回應此事"], new=True))

    def test_r359_2_an_old_topic_keeps_the_old_reading(self):
        self.assertTrue(tf.taiwan_relevant(self.POLAND, new=False))  # R155.4: the rule of a new topic does not change an old topic

    def test_r359_2_the_cut_name_of_a_foreign_court_fails_the_name_test(self):
        self.assertFalse(tf.has_word_boundary("波蘭憲法法", self.POLAND, new=True))

    def test_r359_2_a_law_name_keeps_the_name_test(self):
        titles = ["外送專法7月21日上路 3子法明確4大保障", "外送專法21日上路！DEAT提3大建議", "外送專法將上路 工會批媒合費違法", "外送專法上路 平台預告運費必調",
                  "外送專法今上路 經部公布外送合作契約範本", "外送專法上路2週 Uber Eats報酬提升"]
        self.assertTrue(tf.has_word_boundary("外送專法", titles, new=True))

    def test_r359_2_the_gate_rejects_the_polish_court_topic_for_a_new_topic_and_for_the_key_of_a_whole_name(self):
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        members = [item(f"m{i}", t, "2026-10-31", "出版社" + str(i)) for i, t in enumerate(self.POLAND)]
        df = tp.document_frequency(corpus + members)
        for key in ("波蘭憲法法", "波蘭憲法法庭"):
            outcome, _ = tf.gate_topic(key, members, members, df, corpus + members)
            self.assertNotEqual(outcome, "ok", key)


class CivilMarchTest(unittest.TestCase):
    """R359.3 (G2): a civil march with traffic control and police is no public act (R229.2c). 警方 alone is no public body or act."""

    MARCH = ["台灣同志遊行本周登場！ 文總換新裝：為自由去愛的靈魂應援", "台灣同志遊行10/31登場 交通管制措施看這裡",
             "台灣同志遊行明登場 蔡英文感性發聲：願每個人都能勇敢安心做自己", "台灣同志遊行31日登場 盼共築多元共好社會、邁向真正傾聽",
             "台灣同志遊行台北登場 主辦單位估17萬人上街「做伙行」", "台灣同志遊行登場 蕭美琴：這條路還需大家繼續並肩前行",
             "北市不當搜索同志酒吧刺激 台灣同志遊行今下午登場估15萬人潮", "台灣同志遊行台北登場 主辦單位估17萬人上街「做伙行」【圖輯】",
             "圖輯／台灣同志遊行上看17萬人上街 同婚靈魂人物現身揮舞彩虹旗", "台灣同志遊行登場 鄭麗文扮「黑魔女」祝福：放下偏見看見愛",
             "台灣同志遊行「聲做伙聽 路做伙行」今登場 下午北市府前廣場出發", "第24屆台灣同志遊行登場 北市動員260名警力維安",
             "第24屆台灣同志遊行登場 卓榮泰、鄭麗君都說話了", "現身台灣同志遊行！沈伯洋發「彩虹洋流」飄帶 民眾開心喊「我的市長」"]  # the 14 titles of the topic in the T83 run

    def test_r359_3_traffic_control_for_a_march_is_no_public_act(self):
        self.assertTrue(tf.no_public_act(self.MARCH))
        self.assertFalse(tf.public_act_title("遊行10/31登場 交通管制措施看這裡"))

    def test_r359_3_the_new_topic_gate_rejects_the_march(self):
        members = [item(f"m{i}", t, "2026-10-31", "出版社" + str(i)) for i, t in enumerate(self.MARCH)]
        self.assertEqual(tf.new_topic_reason(members), "no_public_act")

    def test_r359_3_a_ruling_or_a_permit_makes_a_march_an_issue(self):
        titles = self.MARCH + ["遊行路權爭議 市府核准路線", "遊行團體不服 行政法院裁定准許集會"]
        self.assertFalse(tf.no_public_act(titles))

    def test_r359_3_a_road_closure_order_for_a_disaster_stays_an_act(self):
        self.assertTrue(tf.public_act_title("颱風來襲 公路局公告封閉道路 禁止通行"))

    def test_r359_3_the_police_alone_is_no_public_act_for_the_private_matter_gate(self):
        self.assertIsNone(tf.PUBLIC_ACT.search("警方到場了解"))
        members = [item(f"m{i}", t, "2026-10-31", "出版社" + str(i)) for i, t in enumerate(["警方到場了解網紅聚會糾紛", "警方呼籲民眾勿圍觀", "警方關切聚會爭議"])]
        self.assertEqual(tf.new_topic_reason(members), "private_matter")

    def test_r359_3_a_body_with_an_act_still_passes_the_private_matter_gate(self):
        members = [item(f"m{i}", t, "2026-10-31", "出版社" + str(i)) for i, t in enumerate(["警方開罰違規業者", "警方公告取締時段", "警方稽查夜店"])]
        self.assertIsNone(tf.new_topic_reason(members))


class AccessedOnTest(unittest.TestCase):
    """R359.4 (G3): accessed_on of a new source file is the Taipei date of the corpus row (fetched_on), never a constant. Existing files stay."""

    def doc(self, **extra):
        it = item("https://www.ltn.com.tw/news/politics/breakingnews/5624930", "測試標題", "2026-10-27", "自由時報", fetched_on="2026-10-27T17:46:20Z")
        it.update(extra)
        return tp._source_doc(it, {}, tp.HOSTS)

    def test_r359_4_the_date_comes_from_the_row(self):
        self.assertEqual(self.doc()["accessed_on"], "2026-10-28")  # 17:46 UTC is 01:46 of the next day in Taipei

    def test_r359_4_the_date_is_not_before_the_publication_date(self):
        for fetched in ("2026-10-27T00:00:00Z", "2026-10-31T05:00:00Z", "2026-11-02T20:00:00Z"):
            got = self.doc(fetched_on=fetched)["accessed_on"]
            self.assertGreaterEqual(got, "2026-10-27", fetched)

    def test_r359_4_a_row_without_fetched_on_is_an_error(self):
        it = item("https://www.ltn.com.tw/news/politics/breakingnews/5624931", "測試標題", "2026-10-27", "自由時報")
        del it["fetched_on"]
        with self.assertRaises(ValueError):
            tp._source_doc(it, {}, tp.HOSTS)

    def test_r359_4_no_constant_date_is_left_in_the_source_writer(self):
        text = (Path(tp.__file__)).read_text(encoding="utf-8")
        self.assertFalse('"accessed_on": "20' in text, "a constant accessed_on is left in topics.py")

    def test_r359_4_the_enrich_step_keeps_the_accessed_on_of_an_existing_file(self):
        import json
        import tempfile
        it = item("https://www.ltn.com.tw/news/politics/breakingnews/5624930", "測試標題", "2026-10-27", "自由時報", fetched_on="2026-10-30T01:00:00Z")
        doc = tp._source_doc(it, {}, tp.HOSTS)
        doc["accessed_on"] = "2026-10-25"  # a file from an earlier run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sources/2026").mkdir(parents=True)
            path = root / "sources/2026" / (doc["id"] + ".yaml")
            path.write_text(tp._dump(doc), encoding="utf-8")
            enrich = root / "enrich.jsonl"
            enrich.write_text(json.dumps({"url": it["url"], "status": "ok", "byline": "記者"}, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(tf.enrich_sources(root, [it], enrich), 1)
            text = path.read_text(encoding="utf-8")
        self.assertIn("accessed_on: '2026-10-25'", text)
        self.assertIn("byline", text)


class NationalBillTest(unittest.TestCase):
    """R359.5 (G5): a national bill gets gov level central and jur-tw, also when the titles name the place of the case that led to it.
    Rule read for the sensitive flag: CONTRIBUTING section 4, item 4 and PRD R-03 (CI-15) make a record of a person's criminal past, health, genes
    or sex life sensitive (sensitive_terms.yaml: 前科, 犯罪紀錄, 刑案紀錄 ...). A bill that a case led to is a law topic. The case name (割頸案) is no listed term,
    so the topic is not sensitive. The event file names no minor."""

    BILL = ["新北國中割頸案促「少事法」修法 重大犯罪服刑1/2才能假釋", "新北割頸案促少事法修法 重大犯罪服刑1/2才能假釋", "行政院會通過少事法修正草案 立法院將審議"]
    LOCAL = ["新北市府推出敬老卡新制 長者免費搭公車", "新北市政府公告敬老卡新制加值辦法", "新北敬老卡新制上路 市府加碼補助", "議員質疑敬老卡新制 市府回應", "長者領取敬老卡新制 市府說明", "持卡搭乘 敬老卡新制 市府公告"]

    def gate(self, key, titles):
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        members = [item(f"m{i}", t, "2026-10-29", "出版社" + str(i)) for i, t in enumerate(titles)]
        df = tp.document_frequency(corpus + members)
        return tf.gate_topic(key, members, members[:1], df, corpus + members)

    def test_r359_5_a_national_bill_has_the_national_jurisdiction(self):
        outcome, found = self.gate("少事法", self.BILL)
        self.assertEqual(outcome, "ok")
        self.assertEqual(found["jids"], ["jur-tw"])
        self.assertEqual(found["name_jids"], ["jur-tw"])
        self.assertEqual(tf._levels(found["jids"]), ["central"])
        self.assertNotIn("ac-new-taipei-city-government", found["actors"])

    def test_r359_5_a_local_program_keeps_its_place(self):
        outcome, found = self.gate("敬老卡新制", self.LOCAL)
        self.assertEqual(outcome, "ok")
        self.assertIn("jur-65000000", found["jids"])
        self.assertNotIn("jur-tw", found["jids"])

    def test_r359_5_the_bill_titles_hold_no_sensitive_term(self):
        self.assertFalse(tf.has_sensitive_term(self.BILL))


class CandidateMemberTest(unittest.TestCase):
    """R359.6 (G6): the candidate-attack gate (PRD 4.5 item 5) reads the members that a re-gate adds and the members of a new topic, not only the share of a candidate.
    A member of the file stays: an old topic keeps its sources (R155.4)."""

    ATTACK = "南崁溪淤積 王小明批李大華 桃園市府疏濬進度成戰場"
    PLAIN = "南崁溪淤積 桃園市府公告疏濬進度"

    def setUp(self):
        tf.set_candidates({"王小明", "李大華"})
        self.addCleanup(tf.set_candidates, frozenset())

    def test_r359_6_the_filter_removes_a_candidate_title_that_is_not_in_the_file(self):
        members = [item("a", self.ATTACK, "2026-10-24"), item("b", self.PLAIN, "2026-10-24", "聯合新聞網")]
        kept = tf.drop_candidate_talk(members)
        self.assertEqual([m["title"] for m in kept], [self.PLAIN])

    def test_r359_6_a_title_of_the_file_stays(self):
        members = [item("a", self.ATTACK, "2026-10-24")]
        kept = tf.drop_candidate_talk(members, keep_ids={tp.src_id(members[0], tp.HOSTS)})
        self.assertEqual(len(kept), 1)

    def test_r359_6_a_regate_does_not_add_a_candidate_attack_member(self):
        import tempfile
        rt = base.RegateTest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, seed, _ = rt.setup(root)
            corpus += [item("n1", self.ATTACK, "2026-10-24", "中央通訊社"), item("n2", self.PLAIN, "2026-10-24", "聯合新聞網")]
            with mock.patch.object(tf, "candidate_names", lambda c: {"王小明", "李大華"}):  # the names come from the public figure list in a real run
                stats, _, _ = rt.run_gate(root, corpus, seed)
            text = (root / "events/2026" / f"{rt.ID}.md").read_text(encoding="utf-8")
            self.assertIn(tp.src_id(corpus[-1], tp.HOSTS), text)  # the plain title joins
            self.assertNotIn(tp.src_id(corpus[-2], tp.HOSTS), text)  # the attack title does not
            self.assertEqual(stats["regate_passed"], 1)

    def test_r359_6_a_new_topic_does_not_keep_a_candidate_attack_member(self):
        import tempfile
        helper = base.RunHelper()
        corpus, topic = helper.corpus(second_news_publisher=True)
        attack = item("x", "南崁溪淤積問題 王小明批李大華 桃園市府疏濬成戰場", "2026-10-24", "中央通訊社")
        corpus = corpus + [attack]
        clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in topic + [attack]]}]}]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(tf, "candidate_names", lambda c: {"王小明", "李大華"}):
            root = Path(tmp)
            for d in ("events/2026", "sources/2026", "actors"):
                (root / d).mkdir(parents=True)
            stats, published, _ = tf.run(corpus, clusters, [], root, root / "report.json", today="2026-10-25")
            files = sorted((root / "events/2026").glob("*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
        self.assertEqual(stats["candidate_attack_members_removed"], 1)
        self.assertNotIn(tp.src_id(attack, tp.HOSTS), text)
        self.assertIn(tp.src_id(topic[0], tp.HOSTS), text)


class EnrichNoiseTest(unittest.TestCase):
    """R359.8: the list of enrich candidates (daily.enrich_candidates) holds no market, lottery, quake, digest, live or campaign cluster. The quake and campaign
    rules are the rules of the gates (no_public_act, ELECTION, candidate_talk). The titles are the 20 candidates of the 2026-10-31 daily report."""

    NOISE = {
        "quake": ["宜蘭外海規模4.4地震 最大震度3級"],
        "market": ["快訊／台積電漲40元至2120 台股大漲逾660點重返38K", "三大法人買超台股545.86億元", "新台幣開盤升2.5分 為31.55元",
                   "精測4月和前4月營收創新高 AI晶片測試強勁", "5月電子期漲 金融期跌", "3飆股列「抓去關」新名單！處置到5／13 聯發科、旺宏列注意股"],
        "lottery": ["今彩539第115101期開獎"],
        "digest": ["04/24 各報重點新聞一覽", "超商咖啡「買2送2」助攻考生提神 周末優惠一次看"],
        "live": ["立院LIVE》院會 現場直播中"],
        "campaign": ["新北市長選舉》民調反超李四川0.2個百分點 蘇巧慧有最新回應", "沈伯洋競總成立   蔡其昌要帶東泉雞蛋糕祝賀？"],
    }
    KEEP = ["中共9機艦台海周邊活動 國軍嚴密監控應處", "蘋果供應鏈遭駭！iPhone 18 Pro主機板設計圖、A20 Pro文件外洩", "中油：下週汽柴油價格凍漲 累計吸收124億元",
            "高雄旗山水管橋漏水搶修！停水23小時 影響範圍曝光", "颱風假 台中市停班停課", "立法院三讀通過水土保持法修正草案"]

    def test_r359_8_each_class_of_noise_has_its_label(self):
        for label, titles in self.NOISE.items():
            for t in titles:
                self.assertEqual(tf.enrich_noise(t), label, t)

    def test_r359_8_an_issue_title_is_no_noise(self):
        for t in self.KEEP:
            self.assertIsNone(tf.enrich_noise(t), t)

    def test_r359_8_the_candidate_list_drops_noise_clusters(self):
        import shutil
        import tempfile
        from tools.newsfetch import daily
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "events" / "2026").mkdir(parents=True)
        (tmp / "sources" / "2026").mkdir(parents=True)
        titles = [t for ts in self.NOISE.values() for t in ts] + self.KEEP
        clusters, meta = [], {}
        for i, t in enumerate(titles):
            urls = [f"https://a.example/{i}/1", f"https://a.example/{i}/2"]
            clusters.append({"cluster_id": f"c{i}", "title": t, "news_groups": [{"source_ids": urls}]})
            meta.update({urls[0]: ("甲", "2026-10-30"), urls[1]: ("乙", "2026-10-30")})
        got = daily.enrich_candidates(clusters, meta, tmp, "2026-10-31", recent_days=3, limit=50)
        self.assertEqual(sorted(c["title"] for c in got), sorted(self.KEEP))


class DeployDocsTest(unittest.TestCase):
    """R358, R359.8: the env example and the README of the daily layer name GIT_SSH_COMMAND and GOCACHE (T80: the fetch step failed under the sandbox without the first;
    the validator via go run needs a cache folder that the sandbox can write)."""

    DEPLOY = Path(tp.__file__).parent / "deploy"

    def test_r359_8_the_env_example_sets_the_ssh_command_and_the_go_cache(self):
        text = (self.DEPLOY / "newsfetch.env.example").read_text(encoding="utf-8")
        self.assertIn("GIT_SSH_COMMAND=ssh -F /dev/null -o BatchMode=yes", text)
        self.assertRegex(text, r"(?m)^GOCACHE=/home/USER/islandlog-news/gocache$")

    def test_r359_8_the_readme_tells_why(self):
        text = (self.DEPLOY / "README.md").read_text(encoding="utf-8")
        self.assertIn("GIT_SSH_COMMAND", text)
        self.assertIn("GOCACHE", text)
        self.assertIn("20-systemd-ssh-proxy.conf", text)


class RunReportTest(unittest.TestCase):
    """R359.7 (G4, G7): changed.tsv lists the renames, the removed members with their titles and an off-topic flag for each added member."""

    def tree(self, root, title, members):
        """`members`: list of (date, publisher, title). The event cites each member."""
        (root / "events/2026").mkdir(parents=True, exist_ok=True)
        (root / "sources/2026").mkdir(parents=True, exist_ok=True)
        ids = []
        for i, (day, pub, t) in enumerate(members):
            sid = f"src-{day.replace('-', '')}-x-{i:08d}"
            ids.append(sid)
            (root / "sources/2026" / f"{sid}.yaml").write_text(
                f"schema_version: 1\nid: {sid}\nsource_class: news\ngrade: C\ntitle: {t}\npublisher: {pub}\nurl: https://x.example/{sid}\npublished_on: '{day}'\n", encoding="utf-8")
        (root / "events/2026/ev-20261001-topic-aaaaaaaa.md").write_text(
            f"---\nid: ev-20261001-topic-aaaaaaaa\nstatus: published\ntitle: {title}\n---\n\n" + " ".join(f"[@{i}]" for i in ids) + "\n", encoding="utf-8")

    def rows(self, before, after):
        import tempfile
        from tools.newsfetch import run_report
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.tree(Path(a), *before)
            self.tree(Path(b), *after)
            return run_report.changed_rows(run_report.load_tree(Path(a)), run_report.load_tree(Path(b)))

    def test_r359_7_a_rename_is_listed(self):
        rows = self.rows(("南鶯活動中心", [("2026-10-01", "甲", "南鶯活動中心啟用"), ("2026-10-02", "乙", "南鶯活動中心啟用典禮")]),
                         ("新北南鶯活動中心", [("2026-10-01", "甲", "南鶯活動中心啟用"), ("2026-10-02", "乙", "南鶯活動中心啟用典禮")]))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["title_before"], rows[0]["title_after"], rows[0]["renamed"]), ("南鶯活動中心", "新北南鶯活動中心", "yes"))
        self.assertEqual((rows[0]["members_before"], rows[0]["members_after"]), (2, 2))

    def test_r359_7_removed_members_come_with_their_titles_and_the_date_that_goes_back_is_flagged(self):
        before = ("外送專法", [("2026-07-01", "甲", "外送專法上路"), ("2026-09-04", "乙", "外送專法一個月")])
        after = ("外送專法", [("2026-07-01", "甲", "外送專法上路")])
        row = self.rows(before, after)[0]
        self.assertEqual((row["removed"], row["added"]), (1, 0))
        self.assertIn("外送專法一個月", row["removed_titles"])
        self.assertEqual((row["latest_news_before"], row["latest_news_after"], row["latest_moves_back"]), ("2026-09-04", "2026-07-01", "yes"))

    def test_r359_7_an_added_member_is_checked_for_the_key_a_foreign_body_a_case_and_an_attack(self):
        tf.set_candidates({"王小明", "李大華"})
        self.addCleanup(tf.set_candidates, frozenset())
        base_members = [("2026-10-01", "甲", "移工懷孕爭議"), ("2026-10-02", "乙", "移工懷孕 勞動部說明")]
        added = [("2026-10-03", "丙", "移工 雇主政策調整"), ("2026-10-03", "丁", "中國外交部約見日本公使 抗議移工懷孕"),
                 ("2026-10-04", "戊", "移工懷孕 王小明批李大華"), ("2026-10-04", "己", "移工懷孕 查獲非法雇主"), ("2026-10-04", "庚", "移工懷孕 補助新制")]
        row = self.rows(("移工懷孕", base_members), ("移工懷孕", base_members + added))[0]
        self.assertEqual(row["added"], 5)
        flags = row["added_flags"]
        self.assertIn("no_key:移工 雇主政策調整", flags)
        self.assertIn("foreign_body:中國外交部約見日本公使 抗議移工懷孕", flags)
        self.assertIn("candidate_attack:移工懷孕 王小明批李大華", flags)
        self.assertIn("case:移工懷孕 查獲非法雇主", flags)
        self.assertNotIn("補助新制", flags)

    def test_r359_7_an_event_with_no_change_is_not_listed(self):
        members = [("2026-10-01", "甲", "南鶯活動中心啟用")]
        self.assertEqual(self.rows(("南鶯活動中心", members), ("南鶯活動中心", members)), [])

    def test_r359_7_the_tsv_has_a_header_and_one_line_for_each_row(self):
        import tempfile
        from tools.newsfetch import run_report
        row = {"id": "ev-1", "title_before": "甲", "title_after": "乙", "renamed": "yes", "members_before": 1, "members_after": 2, "added": 1, "removed": 0,
               "latest_news_before": "2026-10-01", "latest_news_after": "2026-10-02", "latest_moves_back": "no", "added_flags": "", "removed_titles": "", "added_titles": "標題"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "changed.tsv"
            run_report.write_tsv(path, run_report.CHANGED_COLUMNS, [row])
            lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0].split("\t"), run_report.CHANGED_COLUMNS)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1].split("\t")[0:4], ["ev-1", "甲", "乙", "yes"])


if __name__ == "__main__":
    unittest.main()
