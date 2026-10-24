"""Tests for LTN pagination, incremental output and default output names."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import fetch


def ltn_page(ids):
    divs = "".join(
        f'<div class="cont"><a href="https://news.ltn.com.tw/n/{i}" class="tit">立法院 {i}</a>'
        f'<span class="time">2026/05/01</span><p>x</p></div>'
        for i in ids
    )
    return f"<html><body>{divs}</body></html>".encode("utf-8")


class PagedCrawler:
    def __init__(self, pages):
        self.pages = pages  # page number -> list of ids
        self.urls = []

    def fetch_raw(self, url, check_robots=True):
        self.urls.append(url)
        page = int(url.rsplit("page=", 1)[1])
        ids = self.pages.get(page)
        return ltn_page(ids) if ids else None


CFG = {"id": "ltn", "publisher": "自由時報", "type": "ltn_search",
       "url": "https://search.ltn.com.tw/list", "search_terms": ["立法院"]}


class TestLtnPagination(unittest.TestCase):
    def test_follows_pages_until_empty(self):
        c = PagedCrawler({1: [1, 2], 2: [3, 4], 3: [5]})
        items = fetch.fetch_source_items(CFG, c, since="2026-05-01", until="2026-05-01")
        self.assertEqual(len(items), 5)
        self.assertEqual(len(c.urls), 4)  # page 4 is empty

    def test_cap_at_ten_pages_and_logs(self):
        c = PagedCrawler({p: [p * 10 + 1, p * 10 + 2] for p in range(1, 30)})
        with mock.patch.object(fetch, "LTN_MAX_PAGES", 10), \
                self.assertLogs("newsfetch", level="WARNING") as logs:
            items = fetch.fetch_source_items(CFG, c, since="2026-05-01", until="2026-05-01")
        self.assertEqual(len(c.urls), 10)
        self.assertEqual(len(items), 20)
        self.assertTrue(any("page cap" in m for m in logs.output))


class TestOutputFiles(unittest.TestCase):
    def run_main(self, argv, items):
        with mock.patch.object(fetch, "fetch_source_items", return_value=items), \
             mock.patch("sys.argv", ["fetch.py"] + argv):
            fetch.main()

    def item(self, i):
        return {"url": f"https://x/{i}", "title": "立法院通過預算", "published_on": "2026-05-01",
                "snippet": "s", "summary": ""}

    def test_source_run_uses_own_file_and_refuses_full_file(self):
        tmp = Path(tempfile.mkdtemp())
        feeds = tmp / "feeds.json"
        feeds.write_text(json.dumps([{"id": "pts", "publisher": "公視", "type": "rss", "url": "u"}]))
        with mock.patch.object(fetch, "DEFAULT_OUT_PATH", tmp / "out" / "news.jsonl"):
            self.run_main(["--source", "pts", "--feeds", str(feeds), "--cache-dir", str(tmp / "c"),
                           "--since", "2026-05-01", "--until", "2026-05-02"], [self.item(1), self.item(2)])
            self.assertFalse((tmp / "out" / "news.jsonl").exists())
            lines = (tmp / "out" / "news-pts.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            with self.assertRaises(SystemExit):
                self.run_main(["--source", "pts", "--feeds", str(feeds), "--cache-dir", str(tmp / "c"),
                               "--out", str(tmp / "out" / "news.jsonl")], [])

    def test_records_are_flushed_per_item(self):
        tmp = Path(tempfile.mkdtemp())
        feeds = tmp / "feeds.json"
        feeds.write_text(json.dumps([{"id": "pts", "publisher": "公視", "type": "rss", "url": "u"}]))
        out = tmp / "o.jsonl"
        seen_sizes = []
        orig_should_keep = fetch.NewsFilter.should_keep

        def spy(self_, title, summary=""):
            seen_sizes.append(out.stat().st_size if out.exists() else -1)
            return orig_should_keep(self_, title, summary)

        with mock.patch.object(fetch.NewsFilter, "should_keep", spy):
            self.run_main(["--feeds", str(feeds), "--cache-dir", str(tmp / "c"), "--out", str(out),
                           "--since", "2026-05-01", "--until", "2026-05-02"], [self.item(1), self.item(2)])
        self.assertEqual(seen_sizes[0], 0)
        self.assertGreater(seen_sizes[1], 0)  # first record already on disk before second item


if __name__ == "__main__":
    unittest.main()
