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


if __name__ == "__main__":
    unittest.main()
