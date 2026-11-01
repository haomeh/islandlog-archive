"""T85 tests (R384). No test or data here holds the name of a minor or of a victim. Names are fake."""

import unittest

from tools.newsfetch import run_report
from tools.newsfetch import topics_full as tf

REMOVED_R384 = ["src-20260806-ettoday-9171cd71", "src-20260806-ettoday-bd4f0e3a", "src-20260912-ltn-7a5c57f9", "src-20260912-ettoday-0768633b",
                "src-20260913-ltn-161b87b1", "src-20260914-ltn-f0972166", "src-20260915-chinatimes-046dc50a", "src-20260925-ettoday-794d5f9d",
                "src-20260926-pts-d2f7eecf"]


class RemovedNineTest(unittest.TestCase):
    """R384.1: nine corpus sources hold the name of the minor of R363.1. They are on the removed list. The report flag reads 父母, 學生, 遺屬."""

    def test_each_of_the_nine_sources_is_on_the_removed_list(self):
        removed = tf.load_removed_sources()
        for sid in REMOVED_R384:
            self.assertIn(sid, removed)
            self.assertIn("R384", removed[sid]["ruling"])
            self.assertTrue(removed[sid]["reason"].strip())

    def test_the_first_two_entries_stay(self):
        removed = tf.load_removed_sources()
        self.assertIn("src-20261023-ltn-ef4f6708", removed)
        self.assertIn("src-20261029-ltn-0db0ff7c", removed)

    def test_the_flag_reads_parents_students_and_the_bereaved(self):
        for title in ("某某某父母盼修法", "某某某同學與學生發聲", "遺屬促請修法 某某某案", "某某某的遺屬出席公聽會"):
            self.assertTrue(run_report.victim_flag(title), title)

    def test_a_plain_policy_title_has_no_flag(self):
        for title in ("政院通過少事法修正草案", "淡江大橋通車典禮"):
            self.assertFalse(run_report.victim_flag(title), title)


if __name__ == "__main__":
    unittest.main()
