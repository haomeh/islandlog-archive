"""T82b: cluster.py reads fewer fields and writes one cluster at a time; the file is the same as the whole-list version gives."""
import json
import os
import tempfile
import unittest

from tools.newsfetch import cluster as cl
from tools.newsfetch import test_perf_equal as tpe


class WriteJsonListTest(unittest.TestCase):
    def test_the_file_equals_json_dumps_of_the_list(self):
        cases = [[], [1], [{"a": "x\ny", "b": [1, {"c": []}], "d": {}}, "中文", None, [], {}], [[[]]], [{"k": "line1\nline2 “q” \\ \"x\""}] * 3]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "o.json")
            for values in cases:
                cl.write_json_list(path, iter(values))
                with open(path, encoding="utf-8") as f:
                    self.assertEqual(f.read(), json.dumps(values, ensure_ascii=False, indent=2) + "\n")


class MainOutputTest(unittest.TestCase):
    def test_main_writes_the_files_that_the_whole_list_version_gives(self):
        rows = tpe.cluster_rows(300, 5)
        rows[3]["snippet"] = "not read"
        rows.append({"url": "https://example.com/bad", "title": "x", "published_on": "not a date"})
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.jsonl")
            with open(src, "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n\n")
            for flag in ([], ["--as-news-groups"]):
                out = os.path.join(d, "o.json")
                cl.main([src, out] + flag)
                clusters = cl.cluster_items([dict(r) for r in rows])
                if flag:
                    clusters, mapping = cl.as_news_groups(clusters, [r for r in rows if cl._valid_day(r)])
                    with open(out + ".sources.json", encoding="utf-8") as f:
                        self.assertEqual(f.read(), json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
                with open(out, encoding="utf-8") as f:
                    self.assertEqual(f.read(), json.dumps(clusters, ensure_ascii=False, indent=2) + "\n")

    def test_read_jsonl_with_keep_holds_only_the_named_fields_that_are_present(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "in.jsonl")
            with open(src, "w", encoding="utf-8") as f:
                f.write('{"url": "u", "title": "t", "snippet": "s", "fetched_on": 1}\n\n[1, 2]\n')
            self.assertEqual(cl.read_jsonl(src, ("url", "title", "topics")), [{"url": "u", "title": "t"}, [1, 2]])
            self.assertEqual(cl.read_jsonl(src)[0]["snippet"], "s")


if __name__ == "__main__":
    unittest.main()
