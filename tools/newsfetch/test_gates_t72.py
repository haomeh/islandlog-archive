import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import topics_full as tf


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class FragmentCandidateTest(unittest.TestCase):
    """R329.1: a candidate that holds a fragment of an old topic and fails rejected_name_quality or rejected_foreign gives the old
    topic no fail count. The re-gate of the old topic decides (R202, R205). Other reject reasons fail the old topic as before."""

    def run_with(self, outcome, enriched=None):
        from tools.newsfetch.test_topics_full import RegateTest
        helper = RegateTest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, seed, _ = helper.setup(root, publishers=1)  # the re-gate of the old topic fails by itself, so a fail count is visible
            fragment = [it["url"] for it in corpus if it["url"] in {"t0", "t1", "t2"}]  # half of the 6 sources of the old topic
            clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": fragment}]}]
            real = tf.gate_topic
            calls = []

            def fake(*args, **kwargs):
                calls.append(args[0])
                return (outcome, None) if len(calls) == 1 else real(*args, **kwargs)  # the re-gate uses the real gate
            path = root / "events/2026" / f"{helper.ID}.md"
            before = path.read_bytes()
            patches = [mock.patch.object(tf, "gate_topic", fake)]
            if enriched:
                patches.append(mock.patch.object(tf.tp, "load_enriched_topics", lambda: enriched))
            for p in patches:
                p.start()
            try:
                stats, _, _ = tf.run(corpus, clusters, [], root, root / "report.json", today="2026-10-25")
            finally:
                for p in patches:
                    p.stop()
            state = json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8"))
            return helper.ID, stats, state, before, path.read_bytes(), len(calls)

    def test_name_quality_fragment_leaves_the_fail_count_to_the_regate(self):
        pid, stats, state, _, _, calls = self.run_with("rejected_name_quality")
        self.assertEqual(stats["rejected_name_quality"], 1)
        self.assertEqual(stats["regate_checked"], 1)  # the old topic goes through its re-gate
        self.assertEqual(state[pid]["fails"], 1)  # one fail count from the re-gate (publishers=1)
        self.assertEqual(stats["regate_failed"], 1)

    def test_foreign_fragment_leaves_the_fail_count_to_the_regate(self):
        pid, stats, state, _, _, _ = self.run_with("rejected_foreign")
        self.assertEqual(stats["regate_checked"], 1)
        self.assertEqual(state[pid]["fails"], 1)
        self.assertNotEqual(state[pid]["gate"], "rejected_foreign")

    def test_the_fragment_does_not_name_the_gate_of_the_old_topic(self):
        pid, stats, state, _, _, _ = self.run_with("rejected_name_quality")
        self.assertNotEqual(state[pid]["gate"], "rejected_name_quality")

    def test_another_reject_reason_still_fails_the_old_topic(self):
        pid, stats, state, _, _, _ = self.run_with("rejected_sensitive")
        self.assertEqual(state[pid]["gate"], "rejected_sensitive")
        self.assertEqual(stats["regate_checked"], 0)  # the topic has its result from the candidate

    def test_a_listed_enriched_event_stays_byte_equal(self):
        enriched = {"ev-20261023-topic-aaaaaaaa"}
        pid, stats, state, before, after, _ = self.run_with("rejected_name_quality", enriched=enriched)
        self.assertEqual(before, after)
        self.assertNotIn(pid, state)


if __name__ == "__main__":
    unittest.main()
