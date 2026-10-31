import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class RegateSourceDropTest(unittest.TestCase):
    """R329.3, R337: a rejected_source_rule of a re-gate that member drop causes adds no fail count when the sources in the
    event file pass the same rule. A rejected_source_rule without a member drop still adds one."""

    def run_with(self, drop_publisher, publishers=2, off_publisher="中央通訊社", drop_url=None):
        from tools.newsfetch.test_topics_full import RegateTest
        helper = RegateTest()
        real = tp.members

        def members(seed, corpus, df):
            got = real(seed, corpus, df)
            return [m for m in got if m["publisher"] != drop_publisher and m["url"] != drop_url] if drop_publisher or drop_url else got
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, seed, _ = helper.setup(root, publishers=publishers, off_publisher=off_publisher)
            path = root / "events/2026" / f"{helper.ID}.md"
            before = path.read_bytes()
            with mock.patch.object(tp, "members", members):
                stats, _, _ = tf.run(corpus, [], [seed], root, root / "report.json", today="2026-10-25")
            state = json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8"))
            report = json.loads((root / "report.json").read_text(encoding="utf-8"))
            return helper.ID, stats, state, before, path.read_bytes(), report

    def test_member_drop_with_a_file_that_passes_adds_no_fail_count(self):
        pid, stats, state, before, after, report = self.run_with("聯合新聞網")  # the file cites 2 news publishers; the rebuild keeps 1
        self.assertNotIn(pid, state)
        self.assertEqual((stats["regate_failed"], stats["withdraw_pending"]), (0, 0))
        self.assertEqual(after, before)  # the file stays as it is
        self.assertTrue(report["regate"][0]["dropped"])
        self.assertIsNone(report["regate"][0]["gate"])
        self.assertEqual(stats["regate_file_sources_kept"], 1)

    def test_no_member_drop_and_a_file_that_fails_still_adds_a_fail_count(self):
        pid, stats, state, _, _, _ = self.run_with(None, publishers=1, off_publisher="自由時報")  # the file cites 1 news publisher
        self.assertEqual(state[pid]["fails"], 1)
        self.assertEqual(state[pid]["gate"], "rejected_source_rule")

    def test_member_drop_and_a_file_that_fails_still_adds_a_fail_count(self):
        pid, stats, state, _, _, _ = self.run_with(None, publishers=1, off_publisher="自由時報", drop_url="t4")  # the file cites 1 news publisher; the rebuild drops one member
        self.assertEqual(state[pid]["fails"], 1)
        self.assertEqual(state[pid]["gate"], "rejected_source_rule")


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class FileItemsOwnerTest(unittest.TestCase):
    """R344.3, PRD 4.4: file_items maps the publisher of a source file to its owner group, so one owner counts once."""

    def items(self, publishers):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sources/2026").mkdir(parents=True)
            ids = set()
            for i, name in enumerate(publishers):
                sid = f"src-20261001-x-{i:08d}"
                ids.add(sid)
                (root / "sources/2026" / f"{sid}.yaml").write_text(
                    f"id: {sid}\nsource_class: news\ntitle: t{i}\npublisher: {name}\nurl: https://example.org/{i}\n"
                    "published_on: '2026-10-01'\nquote: q\n", encoding="utf-8")
            return tf.file_items(root, ids)

    def test_two_brands_of_one_owner_count_once(self):
        items = self.items(["華視新聞", "公視新聞網"])
        self.assertEqual(len({tf.owner(it) for it in items}), 1)
        self.assertFalse(tf.meets_source_rule(items))

    def test_two_owners_count_twice(self):
        items = self.items(["自由時報", "公視新聞網"])
        self.assertEqual(len({tf.owner(it) for it in items}), 2)
        self.assertTrue(tf.meets_source_rule(items))

    def test_spellings_on_disk_map_to_their_brand_owner(self):
        """T81: two spellings that sources on disk carry map to the brand, so one owner counts once."""
        items = self.items(["Newtalk", "Newtalk新聞"])
        self.assertEqual(len({tf.owner(it) for it in items}), 1)
        self.assertFalse(tf.meets_source_rule(items))
        items = self.items(["華視新聞", "華視新聞（中央社）"])
        self.assertEqual(len({tf.owner(it) for it in items}), 1)
        self.assertFalse(tf.meets_source_rule(items))
        items = self.items(["Newtalk新聞", "華視新聞（中央社）"])
        self.assertEqual(len({tf.owner(it) for it in items}), 2)
        self.assertTrue(tf.meets_source_rule(items))

    def test_an_unknown_publisher_counts_by_its_name(self):
        items = self.items(["某某小報"])
        self.assertEqual(tf.owner(items[0]), "某某小報")


if __name__ == "__main__":
    unittest.main()
