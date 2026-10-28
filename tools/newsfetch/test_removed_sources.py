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


def tree(root):
    for d in ("actors", "sources/2026", "events/2026"):
        (Path(root) / d).mkdir(parents=True)
    return Path(root)


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class RegateTest(unittest.TestCase):
    """R261.2a: the re-gate path skips a listed id that is already on disk."""

    def setUp(self):
        self.drop = DropTest()
        corpus, clusters, self.ids = self.drop.inputs()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tree(tmp.name)
        self.listed = self.ids["d"]
        self.corpus = [it for it in corpus if tp.src_id(it, tp.HOSTS) != self.listed]
        with mock.patch.object(tf, "REMOVED_SOURCES", write_list(tmp.name, [])):
            tf.run(corpus, clusters, [], self.root, self.root / "report.json", today="2026-10-25")
        (self.old,) = tf.old_system_topics(self.root)

    def regate(self, listed):
        corpus = self.corpus
        tf.set_officials(tf.office_holders(corpus))
        tf.set_candidates(tf.candidate_names(corpus))
        df = tp.document_frequency(corpus)
        _, doc, text = self.old
        with mock.patch.object(tf, "REMOVED_SOURCES", write_list(self.root, [{"id": i, "ruling": "R256", "reason": "test"} for i in listed])):
            rec = tf.regate_topic(self.root, doc, text, None, corpus, df, {it["url"]: it for it in corpus},
                                  tf.source_urls_by_id(self.root), "2026-10-26")
        return rec, (self.root / "events/2026" / f"{doc['id']}.md").read_text(encoding="utf-8")

    def test_the_old_event_cites_the_listed_id_and_its_file_is_on_disk(self):
        self.assertIn(self.listed, self.old[2])
        self.assertTrue((self.root / "sources/2026" / f"{self.listed}.yaml").exists())

    def test_the_regate_drops_the_citation_of_a_listed_id(self):
        rec, text = self.regate([self.listed])
        self.assertIsNone(rec["gate"])
        self.assertIn(self.listed, rec["removed"])
        self.assertNotIn(self.listed, text)

    def test_the_regate_keeps_an_unlisted_file_source(self):
        rec, text = self.regate([])
        self.assertIsNone(rec["gate"])
        self.assertIn(self.listed, text)

    def test_file_items_skip_a_listed_id(self):
        self.assertEqual(len(tf.file_items(self.root, {self.listed})), 1)
        with mock.patch.object(tf, "REMOVED_SOURCES", write_list(self.root, [{"id": self.listed, "ruling": "R256", "reason": "test"}])):
            self.assertEqual(tf.file_items(self.root, {self.listed}), [])


class OldCliTest(unittest.TestCase):
    """R261.2b: topics.py never writes a source file of a listed id; R261.2c: both paths share one loader."""

    def run_cli(self, listed):
        from tools.newsfetch.test_topics import CORPUS, SEED
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        root = tree(base / "tree")
        (base / "corpus.jsonl").write_text("\n".join(json.dumps(it, ensure_ascii=False) for it in CORPUS), encoding="utf-8")
        seed = dict(SEED, gov_levels=["special_municipality"], jurisdiction_ids=["jur-63000000"],
                    controversy_types=["environment"], policy_domains=["environment"], actors=[])
        (base / "seeds.json").write_text(json.dumps([seed], ensure_ascii=False), encoding="utf-8")
        ids = [tp.src_id(CORPUS[i], tp.HOSTS) for i in listed]
        entries = [{"id": i, "ruling": "R256", "reason": "test"} for i in ids]
        with mock.patch.object(tp, "REMOVED_SOURCES", write_list(base, entries)):
            code = tp.main(["topics", str(base / "corpus.jsonl"), str(base / "seeds.json"), str(root)])
        self.assertEqual(code, 0)
        files = sorted(p.name for p in (root / "sources/2026").iterdir())
        text = "\n".join(p.read_text(encoding="utf-8") for p in (root / "events/2026").iterdir())
        return ids, files, text

    def test_a_listed_id_gives_no_file_and_no_link(self):
        _, base_files, _ = self.run_cli([])
        ids, files, text = self.run_cli([1])
        self.assertIn(f"{ids[0]}.yaml", base_files)
        self.assertNotIn(f"{ids[0]}.yaml", files)
        self.assertNotIn(ids[0], text)
        self.assertEqual(len(files), len(base_files) - 1)

    def test_write_event_refuses_a_listed_id(self):
        from tools.newsfetch.test_topics import CORPUS, SEED
        seed = dict(SEED, gov_levels=["special_municipality"], jurisdiction_ids=["jur-63000000"],
                    controversy_types=["environment"], policy_domains=["environment"], actors=[])
        event = tp.build_event(seed, CORPUS, tp.document_frequency(CORPUS), actors_by_host={})
        sid = tp.src_id(next(iter(event["used"].values())), {})
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(tp, "REMOVED_SOURCES", write_list(tmp, [{"id": sid, "ruling": "R256", "reason": "test"}])):
                with self.assertRaises(ValueError):
                    tp.write_event(event, seed, tree(Path(tmp) / "tree"), {}, actors_by_host={})
                self.assertEqual(list((Path(tmp) / "tree/sources/2026").iterdir()), [])

    def test_both_paths_use_the_same_loader(self):
        self.assertIs(tf.load_removed_sources, tp.load_removed_sources)
        self.assertEqual(tf.REMOVED_SOURCES, tp.REMOVED_SOURCES)


if __name__ == "__main__":
    unittest.main()
