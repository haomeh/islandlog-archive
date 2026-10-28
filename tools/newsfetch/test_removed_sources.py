import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf
from tools.newsfetch.test_topics_full import item

LIST = Path(__file__).with_name("removed_sources.json")
FIRST_ID = "src-20261023-ltn-ef4f6708"


def write_list(tmp, entries):
    path = Path(tmp) / "removed.json"
    path.write_text(json.dumps({"sources": entries}), encoding="utf-8")
    return path


class ListFileTest(unittest.TestCase):
    """R256.1: one entry per removed source, with id, ruling and reason."""

    def test_the_list_loads_and_each_entry_is_complete(self):
        entries = tf.load_removed_sources()
        self.assertIn(FIRST_ID, entries)
        for sid, entry in entries.items():
            self.assertEqual(entry["id"], sid)
            self.assertTrue(entry["ruling"].strip(), sid)
            self.assertTrue(entry["reason"].strip(), sid)

    def test_the_first_entry_cites_the_rulings(self):
        entry = tf.load_removed_sources()[FIRST_ID]
        for ruling in ("R217", "R225", "R226", "R256"):
            self.assertIn(ruling, entry["ruling"])

    def test_ids_in_the_file_are_unique(self):
        ids = [e["id"] for e in json.loads(LIST.read_text(encoding="utf-8"))["sources"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_duplicate_id_is_an_error(self):
        entry = {"id": "src-20261001-x-00000000", "ruling": "R1", "reason": "r"}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                tf.load_removed_sources(write_list(tmp, [entry, dict(entry)]))

    def test_an_entry_without_a_reason_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                tf.load_removed_sources(write_list(tmp, [{"id": "src-20261001-x-00000000", "ruling": "R1"}]))


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class DropTest(unittest.TestCase):
    """R256.2: a listed source id never reaches clustering, a source file or a topic link."""

    def inputs(self):
        filler = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        topic = [item("a", "桃園市府會勘南崁溪淤積問題", "2026-10-23"),
                 item("b", "南崁溪淤積問題 桃園市府將會勘", "2026-10-24", "聯合新聞網"),
                 item("d", "桃園市府南崁溪淤積問題 擬編預算清淤", "2026-10-24", "中時新聞網"),
                 item("c", "【錯誤】南崁溪淤積問題謠言", "2026-10-24", "MyGoPen", "fact_check")]
        clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in topic]}]}]
        return filler + topic, clusters, {t["url"]: tp.src_id(t, tp.HOSTS) for t in topic}

    def run_with(self, removed_ids):
        corpus, clusters, ids = self.inputs()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for d in ("actors", "sources/2026", "events/2026"):
            (root / d).mkdir(parents=True)
        entries = [{"id": i, "ruling": "R256", "reason": "test"} for i in removed_ids]
        with mock.patch.object(tf, "REMOVED_SOURCES", write_list(tmp.name, entries)):
            stats, published, _ = tf.run(corpus, clusters, [], root, root / "report.json", today="2026-10-25")
        files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "report.json")
        text = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*") if p.is_file() and p.suffix in (".md", ".yaml"))
        report = json.loads((root / "report.json").read_text(encoding="utf-8"))
        return stats, published, files, text, report, ids

    def test_a_listed_id_gives_no_source_file_and_no_link(self):
        _, _, ids = self.inputs()
        gone = ids["d"]
        stats, published, files, text, _, _ = self.run_with([gone])
        self.assertEqual(len(published), 1)
        self.assertEqual([f for f in files if gone in f], [])
        self.assertNotIn(gone, text)
        self.assertEqual(len([f for f in files if f.startswith("sources/")]), 3)

    def test_an_unlisted_input_gives_the_same_output_as_before(self):
        _, _, ids = self.inputs()
        base = self.run_with([])
        other = self.run_with(["src-20200101-none-00000000"])
        self.assertEqual(base[1], other[1])
        self.assertEqual(base[2], other[2])
        self.assertEqual(base[3], other[3])
        self.assertEqual(len([f for f in base[2] if f.startswith("sources/")]), 4)
        self.assertIn(ids["d"], base[3])

    def test_the_run_report_holds_the_count_of_dropped_inputs(self):
        _, _, ids = self.inputs()
        none = self.run_with([])
        self.assertEqual(none[4]["stats"]["dropped_removed_sources"], 0)
        one = self.run_with([ids["d"]])
        self.assertEqual(one[4]["stats"]["dropped_removed_sources"], 1)
        two = self.run_with([ids["d"], ids["b"]])
        self.assertEqual(two[4]["stats"]["dropped_removed_sources"], 2)


if __name__ == "__main__":
    unittest.main()
