"""T70 (R324.2): an event on tools/newsfetch/enriched_topics.json is never changed by a run."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import test_topics_full as base
from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

YAML = __import__("importlib").util.find_spec("yaml")
LIST = Path(__file__).with_name("enriched_topics.json")


def write_list(tmp, ids):
    path = Path(tmp) / "enriched.json"
    path.write_text(json.dumps({"events": [{"id": i, "ruling": "R324", "reason": "enriched by an editor"} for i in ids]}), encoding="utf-8")
    return path


def listed(path):
    return mock.patch.object(tp, "ENRICHED_TOPICS", path)


class LoaderTest(unittest.TestCase):
    def test_the_list_file_in_this_branch_loads_the_eight_listed_ids(self):
        self.assertEqual(set(tp.load_enriched_topics(LIST)), {
            "ev-20260912-topic-54fa35c7", "ev-20260729-topic-fec46013", "ev-20260625-topic-6ac76a2a",
            "ev-20260708-topic-d8105c51", "ev-20260829-topic-97f2fc8b",
            "ev-20260729-hualien-county-donation-search", "ev-20261028-pakistan-airspace-taiwan-flights",
            "ev-20260424-ccg-kinmen-restricted-waters"})

    def test_a_missing_file_is_an_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tp.load_enriched_topics(Path(tmp) / "none.json"), {})

    def test_a_good_file_loads_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list(tp.load_enriched_topics(write_list(tmp, ["ev-20260912-topic-54fa35c7"]))), ["ev-20260912-topic-54fa35c7"])

    def test_a_bad_file_is_an_error(self):
        bad = ["{not json", "[]", '{"events": {}}', '{"events": [{"id": "ev-1"}]}', '{"events": ["ev-1"]}',
               json.dumps({"events": [{"id": "a", "ruling": "R", "reason": "x"}, {"id": "a", "ruling": "R", "reason": "x"}]})]
        for text in bad:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "enriched.json"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError, msg=text):
                    tp.load_enriched_topics(path)

    def test_run_stops_on_a_bad_file_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            bad = Path(tmp) / "enriched.json"
            bad.write_text("{broken", encoding="utf-8")
            with listed(bad), self.assertRaises(ValueError):
                tf.run([], [], [], root, root / "report.json", today="2026-10-25")
            self.assertEqual(list(root.iterdir()), [])


@unittest.skipUnless(YAML, "the writer needs PyYAML")
class GuardTest(base.RunHelper, unittest.TestCase):
    """Each test runs the same flow twice: with the id on the list (bytes stay) and with an empty list (as before)."""

    def event_path(self, root):
        return root / "events/2026" / f"{self.EVENT_ID}.md"

    def records(self, root):
        return sorted((root / "corrections").glob("*/cr-*.yaml")) if (root / "corrections").exists() else []

    def test_a_candidate_with_the_same_id_does_not_rewrite_a_listed_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            with listed(write_list(tmp, [self.EVENT_ID])):
                self.run_in(root, second_news_publisher=True, today="2026-10-25")
                before = self.event_path(root).read_bytes()
                stats, _, _ = tf.run(*self.args(root), today="2026-10-26")
                self.assertEqual(self.event_path(root).read_bytes(), before)
                self.assertEqual(stats["skipped_enriched"], 1)
                self.assertEqual(stats["published"], 0)

    def args(self, root):
        corpus, topic = self.corpus(True)
        clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in topic]}]}]
        return corpus, clusters, [], root, root / "report.json"

    def test_an_event_that_is_not_listed_is_rewritten_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            with listed(write_list(tmp, ["ev-20260101-topic-00000000"])):
                self.run_in(root, second_news_publisher=True, today="2026-10-25")
                seeded = self.event_path(root).read_bytes()
                stats, _ = self.run_in(root, second_news_publisher=True, today="2026-10-26")
                self.assertEqual(stats["published"], 1)
                self.assertEqual(stats["skipped_enriched"], 0)
                self.assertNotEqual(self.event_path(root).read_bytes(), seeded)

    def test_regate_does_not_rewrite_a_listed_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            helper = RegateHelper()
            corpus, seed, off_id = helper.setup(root)
            path = root / "events/2026" / f"{helper.ID}.md"
            before = path.read_bytes()
            with listed(write_list(tmp, [helper.ID])):
                stats, _, _ = tf.run(corpus, [], [seed], root, root / "report.json", today="2026-10-25")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual((stats["regate_checked"], stats["skipped_enriched"]), (0, 1))
            with listed(write_list(tmp, [])):  # the same flow with an empty list rewrites the file
                stats, _, _ = tf.run(corpus, [], [seed], root, root / "report.json", today="2026-10-25")
            self.assertNotEqual(path.read_bytes(), before)
            self.assertEqual(stats["regate_checked"], 1)

    def test_regate_topic_called_directly_returns_without_a_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            helper = RegateHelper()
            corpus, seed, _ = helper.setup(root)
            path = root / "events/2026" / f"{helper.ID}.md"
            before = path.read_bytes()
            doc, _ = tf._read_event(path)
            with listed(write_list(tmp, [helper.ID])):
                rec = tf.regate_topic(root, doc, path.read_text(encoding="utf-8"), seed, corpus, tp.document_frequency(corpus), {}, {}, "2026-10-25")
            self.assertIsNone(rec["gate"])
            self.assertEqual(path.read_bytes(), before)

    def test_fail_and_withdraw_do_not_touch_a_listed_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            with listed(write_list(tmp, [self.EVENT_ID])):
                self.run_in(root, second_news_publisher=False, today="2026-10-25")
                before = self.event_path(root).read_bytes()
                stats, _ = self.run_in(root, second_news_publisher=False, today="2026-10-26", approved={self.EVENT_ID})
                self.assertEqual(self.event_path(root).read_bytes(), before)
                self.assertEqual((stats["withdrawn"], stats["withdraw_blocked"], stats["withdraw_pending"]), (0, 0, 0))
                self.assertEqual(self.records(root), [])
                self.assertFalse((root / "tools/newsfetch/topic_state.json").exists() and
                                 self.EVENT_ID in json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8")))

    def test_the_same_flow_withdraws_an_event_that_is_not_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            with listed(write_list(tmp, [])):
                stats, text = self.fail_twice(root)
            self.assertEqual(stats["withdrawn"], 1)
            self.assertIn("status: withdrawn", text)

    def test_withdraw_topic_called_directly_leaves_a_listed_file_and_a_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            path = self.event_path(root)
            before = path.read_bytes()
            with listed(write_list(tmp, [self.EVENT_ID])):
                tf.withdraw_topic(root, self.EVENT_ID, "rejected_news_rule", today="2026-10-26")
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(self.records(root), [])
                path.unlink()
                tf.withdraw_topic(root, self.EVENT_ID, "rejected_news_rule", today="2026-10-26")
                self.assertFalse(path.exists())  # no restore from git either

    def test_withdraw_topic_rejects_an_id_that_is_not_an_event_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            for bad in ["EV-20260912-topic-54FA35C7", "ev-2026-x", "", None]:
                with self.assertRaises(ValueError, msg=repr(bad)):
                    tf.withdraw_topic(root, bad, "rejected_news_rule", today="2026-10-26")
            self.assertEqual(list(root.rglob("*.md")), [])

    def test_write_topic_and_write_event_skip_a_listed_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            helper = RegateHelper()
            corpus, seed, _ = helper.setup(root)
            path = root / "events/2026" / f"{helper.ID}.md"
            before = path.read_bytes()
            ev = {"id": helper.ID, "review": {}, "used": {}, "actors": []}
            with listed(write_list(tmp, [helper.ID])):
                self.assertIsNone(tf.write_topic(root, ev, seed, "2026-10-26"))
                tp.write_event(ev, seed, root, {})  # would raise on this thin ev if it ran
                tf._write_event(path, {"id": helper.ID, "x": 1}, "changed\n")
            self.assertEqual(path.read_bytes(), before)


class RegateHelper:
    ID = base.RegateTest.ID
    ON = base.RegateTest.ON
    OFF = base.RegateTest.OFF
    setup = base.RegateTest.setup


if __name__ == "__main__":
    unittest.main()
