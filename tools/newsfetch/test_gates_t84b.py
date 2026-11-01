"""T84b tests (R363). No test or data here holds the name of a minor or of a victim."""

import json
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import run_report
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


if __name__ == "__main__":
    unittest.main()
