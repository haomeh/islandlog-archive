"""T79: merge_corpus keeps every old row byte-equal and writes through a temp file (R346)."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import merge_corpus


def row(url, publisher="自由時報", day="2026-10-30", **extra):
    return dict({"url": url, "title": "標題 " + url[-3:], "publisher": publisher, "published_on": day}, **extra)


def write_rows(path, rows, raw=None):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(raw.get(r["url"], json.dumps(r, ensure_ascii=False)) + "\n" if raw else json.dumps(r, ensure_ascii=False) + "\n")


class MergeCorpusTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        self.corpus = self.tmp / "corpus.jsonl"

    def test_old_rows_stay_byte_equal(self):
        # An odd spacing and key order in an old row must survive: the tool never re-encodes old rows.
        odd = '{"published_on": "2026-10-01",  "url": "https://a.example/1", "publisher": "甲", "title": "舊"}'
        old = [json.loads(odd), row("https://a.example/2", "乙", "2026-10-02")]
        write_rows(self.corpus, old, raw={"https://a.example/1": odd})
        before = self.corpus.read_bytes()
        new = self.tmp / "news-x.jsonl"
        write_rows(new, [row("https://a.example/3", "丙"), row("https://a.example/1", "甲", title="換")])
        res = merge_corpus.merge(self.corpus, [new], self.tmp / "next.jsonl")
        out = (self.tmp / "next.jsonl").read_bytes()
        self.assertTrue(out.startswith(before))
        self.assertEqual(res["rows_old"], 2)
        self.assertEqual(res["rows_new"], 1)
        self.assertEqual(self.corpus.read_bytes(), before)

    def test_one_row_per_canonical_url_and_report(self):
        write_rows(self.corpus, [row("https://a.example/1")])
        n1, n2 = self.tmp / "news-a.jsonl", self.tmp / "news-b.jsonl"
        write_rows(n1, [row("https://a.example/9?utm_source=x#top", "甲"), row("https://a.example/1/", "甲")])
        write_rows(n2, [row("https://a.example/9", "甲"), row("https://b.example/5", "乙")])
        out = self.tmp / "next.jsonl"
        res = merge_corpus.merge(self.corpus, [n1, n2], out)
        urls = [json.loads(l)["url"] for l in out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(res["rows_new"], 2)
        self.assertEqual(res["new_by_outlet"], {"甲": 1, "乙": 1})
        self.assertEqual(res["crawled_by_outlet"], {"甲": 3, "乙": 1})
        self.assertEqual(res["sha256"], hashlib.sha256(out.read_bytes()).hexdigest())

    def test_in_place_uses_temp_file_and_atomic_rename(self):
        write_rows(self.corpus, [row("https://a.example/1")])
        new = self.tmp / "news-a.jsonl"
        write_rows(new, [row("https://a.example/2")])
        calls = []
        real = merge_corpus.os.replace
        with mock.patch.object(merge_corpus.os, "replace", side_effect=lambda a, b: (calls.append((str(a), str(b))), real(a, b))[1]):
            merge_corpus.merge(self.corpus, [new], self.corpus)
        self.assertEqual(len(calls), 1)
        self.assertNotEqual(calls[0][0], calls[0][1])
        self.assertEqual(calls[0][1], str(self.corpus))
        self.assertEqual(len(self.corpus.read_text(encoding="utf-8").splitlines()), 2)

    def test_bad_new_row_leaves_corpus_unchanged(self):
        write_rows(self.corpus, [row("https://a.example/1")])
        before = self.corpus.read_bytes()
        bad = self.tmp / "news-bad.jsonl"
        bad.write_text('{"url": "https://a.example/2"\n', encoding="utf-8")
        with self.assertRaises(merge_corpus.MergeError):
            merge_corpus.merge(self.corpus, [bad], self.corpus)
        self.assertEqual(self.corpus.read_bytes(), before)
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name.endswith(".tmp")], [])

    def test_failed_check_keeps_old_file(self):
        write_rows(self.corpus, [row("https://a.example/1")])
        before = self.corpus.read_bytes()
        new = self.tmp / "news-a.jsonl"
        write_rows(new, [row("https://a.example/2")])
        with mock.patch.object(merge_corpus, "_check", side_effect=merge_corpus.MergeError("check failed")):
            with self.assertRaises(merge_corpus.MergeError):
                merge_corpus.merge(self.corpus, [new], self.corpus)
        self.assertEqual(self.corpus.read_bytes(), before)

    def test_missing_corpus_is_an_error(self):
        with self.assertRaises(merge_corpus.MergeError):
            merge_corpus.merge(self.tmp / "none.jsonl", [], self.tmp / "out.jsonl")

    def test_row_without_url_or_publisher_is_an_error(self):
        write_rows(self.corpus, [row("https://a.example/1")])
        bad = self.tmp / "news-bad.jsonl"
        bad.write_text(json.dumps({"title": "x"}) + "\n", encoding="utf-8")
        with self.assertRaises(merge_corpus.MergeError):
            merge_corpus.merge(self.corpus, [bad], self.tmp / "out.jsonl")


if __name__ == "__main__":
    unittest.main()
