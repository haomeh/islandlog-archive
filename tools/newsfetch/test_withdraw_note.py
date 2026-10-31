"""T75 (R104, R105, R335): a withdrawal record can carry a reason note. Without a note the record text stays as it was."""

import tempfile
import unittest
from pathlib import Path

from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics_full as tf

YAML = __import__("importlib").util.find_spec("yaml")


@unittest.skipUnless(YAML, "the writer needs PyYAML")
class WithdrawNoteTest(base.RunHelper, unittest.TestCase):

    def withdraw(self, note):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fail_twice(root, approved=set())  # the topic stays published
            tf.withdraw_topic(root, self.EVENT_ID, "rejected_name_quality", today="2026-10-31", note=note)
            return self.records(root)

    def test_the_note_is_part_of_the_summary(self):
        records = self.withdraw("名稱只是地名。")
        self.assertEqual(records[-1]["type"], "withdrawal")
        self.assertTrue(records[-1]["summary"].endswith("名稱只是地名。"))
        self.assertEqual(records[-1]["gate"], "rejected_name_quality")

    def test_without_a_note_the_summary_is_as_before(self):
        records = self.withdraw(None)
        self.assertEqual(records[-1]["summary"], "系統撤回事件：未通過 rejected_name_quality（R82）。")


if __name__ == "__main__":
    unittest.main()
