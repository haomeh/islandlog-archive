"""T84b tests (R363). No test or data here holds the name of a minor or of a victim."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import run_report
from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

LIST = Path(__file__).with_name("removed_sources.json")


class RemovedSourceVictimTest(unittest.TestCase):
    """R363.1: the juvenile-bill source that names a victim is removed; the report flags titles that may name a minor or a victim."""

    def test_the_juvenile_bill_source_is_on_the_removed_list(self):
        entry = tf.load_removed_sources()["src-20261029-ltn-0db0ff7c"]
        self.assertIn("R363", entry["ruling"])
        self.assertTrue(entry["reason"].strip())

    def test_the_removed_list_reason_holds_no_person_name(self):
        entry = tf.load_removed_sources()["src-20261029-ltn-0db0ff7c"]
        self.assertNotRegex(entry["reason"], r"[一-鿿]{3}父")

    def test_the_first_entry_stays(self):
        self.assertIn("src-20261023-ltn-ef4f6708", tf.load_removed_sources())

    def test_a_flag_for_a_name_with_a_parent_or_a_family_word(self):
        for title in ("政院通過少事法修正草案 某某某父親：肯定改革", "某某某母親盼立院召開公聽會", "少年事件處理法 受害學生家屬發聲", "國中生遭霸凌 校方道歉"):
            self.assertTrue(run_report.victim_flag(title), title)

    def test_no_flag_for_a_plain_policy_title(self):
        for title in ("政院通過少事法修正草案", "教育部公布學校衛生法修正", "淡江大橋通車典禮"):
            self.assertFalse(run_report.victim_flag(title), title)

    def test_the_member_flag_names_the_victim_check_first(self):
        self.assertEqual(run_report.member_flag("少事法", "少事法 某某某父親籲公聽會"), "minor_or_victim")

    def test_new_topic_rows_list_the_flagged_titles(self):
        before = {"events": {}, "sources": {}}
        after = {"events": {"ev-1": {"title": "少事法", "members": ["s1", "s2"]}},
                 "sources": {"s1": {"title": "少事法 某某某父親籲公聽會", "date": "2026-10-29", "class": "news", "publisher": "甲"},
                             "s2": {"title": "少事法修正草案三讀", "date": "2026-10-30", "class": "news", "publisher": "乙"}}}
        row = run_report.new_rows(before, after)[0]
        self.assertIn("某某某父親籲公聽會", row["flagged_titles"])
        self.assertNotIn("三讀", row["flagged_titles"])
        self.assertIn("flagged_titles", run_report.NEW_COLUMNS)


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class HeldSensitiveTest(base.RunHelper, unittest.TestCase):
    """R363.2: a run does not change an event with review.sensitive true. The file stays byte-equal and the report lists it."""

    def make_sensitive(self, root):
        path = root / "events/2026" / f"{self.EVENT_ID}.md"
        path.write_text(path.read_text(encoding="utf-8").replace("sensitive: false", "sensitive: true"), encoding="utf-8")
        return path

    def report(self, root):
        return json.loads((root / "report.json").read_text(encoding="utf-8"))

    def test_a_run_that_would_rewrite_a_sensitive_event_keeps_the_file_byte_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            path = self.make_sensitive(root)
            before = path.read_bytes()
            stats, _ = self.run_in(root, second_news_publisher=True, today="2026-10-26")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(stats["held_sensitive"], 1)

    def test_the_report_lists_the_held_event_and_its_candidate_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            self.make_sensitive(root)
            self.run_in(root, second_news_publisher=True, today="2026-10-26")
            held = self.report(root)["held_sensitive"]
            self.assertEqual([h["id"] for h in held], [self.EVENT_ID])
            self.assertGreaterEqual(len(held[0]["candidates"]), 2)
            self.assertTrue(all(c["id"].startswith("src-") and c["title"] for c in held[0]["candidates"]))

    def test_a_sensitive_event_that_fails_a_gate_is_not_withdrawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=False, today="2026-10-25")
            path = self.make_sensitive(root)
            before = path.read_bytes()
            stats, _ = self.run_in(root, second_news_publisher=False, today="2026-10-26", approved={self.EVENT_ID})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(stats["withdrawn"], 0)
            self.assertEqual(self.records(root), [])

    def test_a_sensitive_event_flag_is_not_refreshed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            path = self.make_sensitive(root)
            before = path.read_bytes()
            tf.set_held(root)
            self.assertEqual(tf.refresh_sensitive(root), [])
            self.assertEqual(path.read_bytes(), before)
            tf.set_held(None)

    def test_an_event_that_is_not_sensitive_is_rewritten_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            path = root / "events/2026" / f"{self.EVENT_ID}.md"
            before = path.read_bytes()
            stats, _ = self.run_in(root, second_news_publisher=True, today="2026-10-26")
            self.assertNotEqual(path.read_bytes(), before)
            self.assertEqual(stats["held_sensitive"], 0)

    def test_the_tsv_lists_the_event_and_its_candidates(self):
        report = {"held_sensitive": [{"id": "ev-1", "title": "甲", "gate": None, "in_file": 2,
                                      "candidates": [{"id": "src-1", "title": "標題一", "in_file": True}, {"id": "src-2", "title": "標題二", "in_file": False}]}]}
        rows = run_report.held_rows(report)
        self.assertEqual([r["candidate_id"] for r in rows], ["src-1", "src-2"])
        self.assertEqual([r["in_file"] for r in rows], ["yes", "no"])
        self.assertEqual(run_report.HELD_COLUMNS[:2], ["id", "title"])


class ForeignMarkerTest(unittest.TestCase):
    """R363.3 (G2): the Taiwan link of a generic body (外交部, 憲法法庭) fails by a foreign marker, not by a missing act word."""

    FOREIGN = ["波蘭憲法法庭裁定總統令違憲", "匈牙利憲法法庭裁定總統令違憲", "中國外交部約見日本公使"]
    TAIWAN = ["教育部 唾液篩檢", "外交部 自動通關", "交通部 機車後座兒童", "國防部 體位區分標準", "內政部 特搜隊成軍"]

    def test_a_foreign_title_with_an_act_word_is_not_about_taiwan(self):
        for title in self.FOREIGN:
            self.assertFalse(tf.taiwan_relevant([title], new=True), title)
            self.assertFalse(tf.taiwan_relevant([title, title.replace("裁定", "宣布")], new=True), title)

    def test_a_taiwan_ministry_with_no_act_word_keeps_the_link(self):
        for title in self.TAIWAN:
            self.assertTrue(tf.taiwan_relevant([title], new=True), title)

    def test_the_test_holds_for_a_country_that_no_list_names(self):
        for place in ("立陶宛", "哈薩克", "秘魯", "捷克", "賴比瑞亞", "塔吉克"):
            self.assertFalse(tf.taiwan_relevant([f"{place}憲法法庭裁定總統令違憲"], new=True), place)

    def test_a_place_word_directly_before_a_generic_body_is_a_marker(self):
        self.assertTrue(tf.foreign_marked("立陶宛外交部召見大使"))
        self.assertTrue(tf.foreign_marked("匈牙利憲法法庭裁定"))
        self.assertFalse(tf.foreign_marked("教育部 唾液篩檢"))

    def test_a_verb_or_a_word_before_a_body_is_no_marker(self):
        for title in ("立委要求教育部說明", "函請外交部協助國人", "送達內政部文件", "民團籲交通部改善", "福利部門與國防部協商"):
            self.assertFalse(tf.foreign_marked(title), title)

    def test_a_taiwan_marker_before_a_body_keeps_the_link(self):
        self.assertTrue(tf.taiwan_relevant(["我國外交部抗議", "中華民國外交部聲明"], new=True))

    def test_an_old_topic_keeps_the_old_reading(self):
        self.assertTrue(tf.taiwan_relevant(["波蘭憲法法庭裁定總統令違憲"], new=False))


class CampaignClassTest(unittest.TestCase):
    """R363.4 (G3): the member rule for campaign titles reads four classes: 助講, 競辦, 候選人表態, 陣營交鋒 (PRD 4.5 item 5)."""

    CAMPAIGN = ["黃國昌竹南助講轟綠抹黑造謠 為長者健保補助向賴清德、卓榮泰下戰帖",
                "黃國昌問沈伯洋「取消北市長者健保補助？」 柯文哲點名9綠營候選人表態",
                "長者健保補助修法議題 竹市白、綠陣營隔空交鋒",
                "長者健保費補助爭議 台灣前進陣線全台串連宣講",
                "長者健保補助掀攻防 李四川競辦追問蘇巧慧：卓榮泰不副署妳支持嗎？"]
    POLICY = ["長者健保費補助 柯文哲：醫療平權 台灣民眾黨說到做到！", "藍批長者健保補助雙標 綠黨團：弱勢保障不能修到漏接", "民眾黨：中央補助長者健保費 健保收入一塊都不會少",
              "藍議員問長者健保費中央買單？周春米：立法院要「精傱」一點啦", "蘇巧慧談長者健保補助：若是全國一致福利當然接受",
              "《少康戰情室專訪》蘇巧慧：長者健保費補助 全國應一致", "衛福部說明長者健保費補助新制", "行政院長卓榮泰：長者健保費補助將修法", "兩部會協商長者健保費 交鋒焦點在財源"]

    def test_each_of_the_five_titles_is_candidate_talk(self):
        for title in self.CAMPAIGN:
            self.assertTrue(tf.candidate_talk(title), title)

    def test_a_policy_title_or_an_official_statement_stays(self):
        for title in self.POLICY:
            self.assertFalse(tf.candidate_talk(title), title)

    def test_one_title_for_each_class(self):
        self.assertTrue(tf.candidate_talk("議員為候選人助講 批新制"))
        self.assertTrue(tf.candidate_talk("市府新制 某黨競辦回應"))
        self.assertTrue(tf.candidate_talk("市府新制 候選人表態支持"))
        self.assertTrue(tf.candidate_talk("市府新制 藍綠陣營交鋒"))

    def test_the_member_filter_drops_the_five_titles_and_keeps_the_policy_titles(self):
        from tools.newsfetch.test_topics_full import item
        members = [item(f"c{i}", t, "2026-10-24", f"報{i}") for i, t in enumerate(self.CAMPAIGN)] + [item(f"p{i}", t, "2026-10-24", f"報{i}") for i, t in enumerate(self.POLICY)]
        kept = [m["title"] for m in tf.drop_candidate_talk(members)]
        self.assertEqual(kept, self.POLICY)


class CriminalCaseTest(unittest.TestCase):
    """R363.5 (G5): a criminal case of a person (判刑, 入獄) is another case than the issue of the topic. A court ruling on a public act stays."""

    def members(self, titles):
        from tools.newsfetch.test_topics_full import item
        return [item(f"m{i}", t, "2026-10-24", f"報{i}") for i, t in enumerate(titles)]

    def test_a_sentence_or_a_prison_title_is_a_case_title(self):
        for title in ("地下匯兌逾千萬！統促黨「白狼」兒媳判1年7月今入獄 兒棄保潛逃", "統促黨幹部入獄服刑", "統促黨幹部判刑確定", "統促黨成員判2年 緩刑"):
            self.assertTrue(tf.CASE_TITLE.search(title), title)

    def test_a_court_ruling_on_a_public_act_is_no_case_title(self):
        for title in ("憲法法庭判決 死刑規定違憲", "行政法院判決 市府裁罰撤銷", "法院裁定 公所補助款應撥付", "最高行政法院判決 環評審查無效"):
            self.assertFalse(tf.CASE_TITLE.search(title), title)

    def test_the_case_title_leaves_as_its_own_list(self):
        titles = ["統促黨解散案 內政部聲請憲法法庭", "統促黨解散案 憲法法庭開庭", "地下匯兌 統促黨幹部之媳判1年7月今入獄"]
        lists = tf.split_cases(self.members(titles))
        self.assertEqual(sorted(len(g) for g in lists), [1, 2])

    def test_the_ruling_on_a_public_act_stays_in_the_topic(self):
        titles = ["統促黨解散案 內政部聲請憲法法庭", "統促黨解散案 憲法法庭判決出爐", "統促黨解散案 憲法法庭裁定"]
        self.assertEqual(len(tf.split_cases(self.members(titles))), 1)


def _group(urls_titles, kind="report"):
    items = [{"url": u, "title": t, "published_on": "2026-05-05", "publisher": f"報{i}", "source_class": "news", "fetched_on": "2026-05-05T12:00:00Z"}
             for i, (u, t) in enumerate(urls_titles)]
    return {"kind": kind, "items": items, "urls": [i["url"] for i in items]}


class DisplayCapTest(unittest.TestCase):
    """R363.6 (G4): the display cap keeps first the groups with a title that holds the event key, then the bigger groups. It counts what it cuts."""

    def build(self, groups, key="淡江大橋"):
        seed = {"event_id": "ev-20260504-x", "seed_urls": [], "_keys": [key], "_name": key, "jurisdiction_names": [], "jurisdiction_ids": ["jur-tw"],
                "gov_levels": [], "controversy_types": [], "policy_domains": [], "actors": []}
        items = [i for g in groups for i in g["items"]]
        with mock.patch.object(tp, "group_items", lambda its: groups), mock.patch.object(tp, "MAX_GROUPS", 2):
            return tp.build_event(seed, items, {}, items=items)

    def test_a_group_with_the_key_ranks_before_a_bigger_group_without_it(self):
        big = _group([("https://x.example/a1", "小虎鯨擱淺 海巡搶救"), ("https://x.example/a2", "小虎鯨擱淺 動保搶救"), ("https://x.example/a3", "鯨豚擱淺 安置")])
        key1 = _group([("https://x.example/k1", "淡江大橋通車 典禮")])
        key2 = _group([("https://x.example/k2", "淡江大橋機車道 設計")])
        ev = self.build([big, key1, key2])
        self.assertEqual(sorted(ev["used"]), ["https://x.example/k1", "https://x.example/k2"])

    def test_among_groups_with_the_key_the_bigger_group_ranks_first(self):
        small = _group([("https://x.example/s1", "淡江大橋 小事")])
        big = _group([("https://x.example/b1", "淡江大橋 大事一"), ("https://x.example/b2", "淡江大橋 大事二")])
        mid = _group([("https://x.example/m1", "淡江大橋 中事一"), ("https://x.example/m2", "淡江大橋 中事二")])
        ev = self.build([small, big, mid])
        self.assertEqual(sorted(ev["used"]), ["https://x.example/b1", "https://x.example/b2", "https://x.example/m1", "https://x.example/m2"])

    def test_the_event_counts_the_items_that_the_cap_cuts(self):
        a = _group([("https://x.example/a1", "淡江大橋 甲")])
        b = _group([("https://x.example/b1", "淡江大橋 乙")])
        c = _group([("https://x.example/c1", "淡江大橋 丙")])
        ev = self.build([a, b, c])
        self.assertEqual((len(ev["used"]), ev["capped"]), (2, 1))


class OneStoryBranchTest(unittest.TestCase):
    """R363.6 (G4): the key names one story (淡江大橋 + 通車). A title with the key but with no anchor and no companion word is another story (a whale, a model, a lecture)."""

    def corpus(self):
        core = [f"淡江大橋通車第{n}報 新北市府未受邀祈福典禮 公路局回應" for n in range(24)]
        off = ["淡江大橋下4小虎鯨擱淺 海巡動保搶救安置", "不只淡江大橋 札哈哈蒂古根漢美術館留模型", "鋼結構建材可回收 中龍鋼鐵邀淡江大橋團隊研討"]
        filler = [f"無關新聞{n}號 氣象消息" for n in range(60)] + [f"淡江大橋周邊商圈第{n}號 美食消息" for n in range(100)]  # the key has other uses: the key alone names no issue
        rows = []
        for i, t in enumerate(core + off + filler):
            rows.append({"url": f"https://x.example/{i}", "title": t, "published_on": "2026-05-05", "publisher": f"報{i % 7}", "source_class": "news",
                         "fetched_on": "2026-05-05T12:00:00Z"})
        return rows, core, off

    def test_the_off_story_titles_leave_and_the_story_stays(self):
        rows, core, off = self.corpus()
        df = tp.document_frequency(rows)
        cands = [r for r in rows if "淡江大橋" in r["title"] and "商圈" not in r["title"]]
        kept = {c["title"] for c in tp.anchored(cands, core[:3], ["淡江大橋"], df, len(rows))}
        for t in off:
            self.assertNotIn(t, kept, t)
        self.assertTrue(set(core) <= kept)


if __name__ == "__main__":
    unittest.main()
