"""T34-W2 (R218, R221): a due topic is withdrawn only when its id is in the approval list. The R133 limits still apply."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics_full as tf

YAML = __import__("importlib").util.find_spec("yaml")


@unittest.skipUnless(YAML, "the writer needs PyYAML")
class WithdrawApprovalTest(base.RunHelper, unittest.TestCase):

    def report(self, root):
        return json.loads((root / "report.json").read_text(encoding="utf-8"))

    def test_a_due_topic_with_no_approval_is_blocked_and_stays_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats, text = self.fail_twice(root, approved=set())
            self.assertIn("status: published", text)
            self.assertEqual((stats["withdrawn"], stats["withdraw_blocked"]), (0, 1))
            report = self.report(root)
            self.assertEqual(list(report["withdraw_blocked"]), [self.EVENT_ID])
            self.assertEqual(report["withdraw_blocked_reason"], {self.EVENT_ID: "needs_user_approval"})
            self.assertEqual(self.records(root), [])
            state = json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state[self.EVENT_ID]["fails"], 2)

    def test_a_due_topic_with_its_id_in_the_approval_list_is_withdrawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats, text = self.fail_twice(root, approved={self.EVENT_ID})
            self.assertIn("status: withdrawn", text)
            self.assertEqual((stats["withdrawn"], stats["withdraw_blocked"]), (1, 0))
            self.assertEqual([r["type"] for r in self.records(root)], ["withdrawal"])
            self.assertEqual(self.report(root)["approval_ignored"], [])

    def test_an_approved_id_that_is_not_due_is_ignored_and_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats, text = self.run_in(root, second_news_publisher=False, today="2026-10-25", approved={self.EVENT_ID, "ev-20260101-other"})
            self.assertIn("status: published", text)
            self.assertEqual((stats["withdrawn"], stats["withdraw_blocked"], stats["withdraw_pending"]), (0, 0, 1))
            self.assertEqual(self.report(root)["approval_ignored"], sorted([self.EVENT_ID, "ev-20260101-other"]))

    def test_the_r133_limit_still_blocks_four_approved_due_topics(self):
        due = {f"ev-2026102{i}-topic-0000000{i}": "rejected_name_quality" for i in range(4)}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "events/2026").mkdir(parents=True)
            with mock.patch.object(tf, "apply_hysteresis", return_value=({}, due, [])), mock.patch.object(tf, "withdraw_topic") as w:
                stats, _, _ = tf.run([], [], [], root, root / "report.json", today="2026-10-27", approve_withdraw=set(due))
            w.assert_not_called()
            self.assertEqual((stats["withdrawn"], stats["withdraw_blocked"]), (0, 4))
            self.assertEqual(set(self.report(root)["withdraw_blocked_reason"].values()), {"withdraw_limit"})


class ApprovalFileTest(unittest.TestCase):

    def test_read_approval_file_gives_one_id_per_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approve.txt"
            path.write_text("ev-1\n\n  ev-2  \nev-1\n", encoding="utf-8")
            self.assertEqual(tf.read_approval_file(path), {"ev-1", "ev-2"})

    def test_parse_approve_withdraw_takes_the_file_option(self):
        self.assertEqual(tf.parse_approve_withdraw(["a", "--approve-withdraw", "f.txt", "b"]), (["a", "b"], "f.txt"))
        self.assertEqual(tf.parse_approve_withdraw(["a"]), (["a"], None))
        with self.assertRaises(ValueError):
            tf.parse_approve_withdraw(["--approve-withdraw"])

    def test_main_passes_the_ids_of_the_file_to_run(self):
        seen = {}

        def fake_run(corpus, clusters, seeds, root, report, today=None, approve_withdraw=None):
            seen["ids"] = approve_withdraw
            return {}, [], []

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for name, text in (("c.jsonl", ""), ("k.json", "[]"), ("s.json", "[]"), ("a.txt", "ev-1\n")):
                (tmp / name).write_text(text, encoding="utf-8")
            base_args = ["topics_full", str(tmp / "c.jsonl"), str(tmp / "k.json"), str(tmp / "s.json"), "root", "report.json"]
            with mock.patch.object(tf, "run", fake_run), mock.patch("builtins.print"):
                self.assertEqual(tf.main(base_args), 0)
                self.assertIsNone(seen["ids"])
                self.assertEqual(tf.main(base_args + ["--approve-withdraw", str(tmp / "a.txt")]), 0)
                self.assertEqual(seen["ids"], {"ev-1"})


if __name__ == "__main__":
    unittest.main()
