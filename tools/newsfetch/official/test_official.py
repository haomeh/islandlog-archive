"""Offline tests for the official fetcher. Run: python3 -m unittest discover -s tools/newsfetch/official"""

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import crawler as crawler_mod  # noqa: E402
import listing  # noqa: E402
import textutil  # noqa: E402
import fetch_official  # noqa: E402

FIX = HERE / "fixtures"


class DateTests(unittest.TestCase):
    def test_roc_dash(self):
        self.assertEqual(textutil.parse_date("115-10-22"), "2026-10-22")

    def test_roc_slash_and_dot(self):
        self.assertEqual(textutil.parse_date("115/04/24"), "2026-04-24")
        self.assertEqual(textutil.parse_date("115.04.24"), "2026-04-24")

    def test_roc_chinese(self):
        self.assertEqual(textutil.parse_date("115年4月5日"), "2026-04-05")

    def test_iso_and_slash(self):
        self.assertEqual(textutil.parse_date("2026/07/30"), "2026-07-30")
        self.assertEqual(textutil.parse_date("2026-08-03T10:00:00+08:00"), "2026-08-03")

    def test_rfc2822_gmt_to_taipei(self):
        self.assertEqual(textutil.parse_date("Wed, 23 Sep 2026 17:00:00 GMT"), "2026-09-24")

    def test_bad_date(self):
        with self.assertRaises(ValueError):
            textutil.parse_date("hello")


class SnippetTests(unittest.TestCase):
    def test_cut_150(self):
        out = textutil.make_snippet("字" * 400)
        self.assertEqual(len(out), 150)
        self.assertTrue(out.endswith("..."))

    def test_short_kept_and_html_removed(self):
        self.assertEqual(textutil.make_snippet("<p>行政院 通過</p>"), "行政院 通過")

    def test_private_name_replaced(self):
        self.assertIn("[當事人]", textutil.make_snippet("陳男向行政院表示意見"))
        self.assertIn("[當事人]", textutil.make_snippet("王姓民眾提出申請"))

    def test_public_title_kept(self):
        self.assertEqual(textutil.make_snippet("行政院長表示"), "行政院長表示")


class RobotsTests(unittest.TestCase):
    def test_disallow_and_allow(self):
        hr = crawler_mod.HostRobots((FIX / "sample_robots.txt").read_text())
        self.assertFalse(hr.can_fetch("islandlog", "https://x.example/private/a"))
        self.assertTrue(hr.can_fetch("islandlog", "https://x.example/rss/a"))

    def test_missing_robots_allows(self):
        self.assertTrue(crawler_mod.HostRobots(None).can_fetch("islandlog", "https://x.example/a"))

    def test_crawler_blocked_by_robots_makes_no_request(self):
        with tempfile.TemporaryDirectory() as d:
            c = crawler_mod.PoliteCrawler(cache_dir=Path(d))
            c.robots_map["x.example"] = crawler_mod.HostRobots("User-agent: *\nDisallow: /\n")
            self.assertIsNone(c.fetch_raw("https://x.example/a"))
            self.assertEqual(c.host_failures, {})

    def test_user_agent(self):
        self.assertEqual(
            crawler_mod.USER_AGENT,
            "islandlog-newsfetch/0.1 (+https://github.com/haomeh/islandlog-archive)",
        )


class ListingTests(unittest.TestCase):
    def test_rss(self):
        items = listing.parse_rss((FIX / "sample_rss.xml").read_bytes())
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["published_on"], "2026-09-23")
        self.assertEqual(items[0]["url"], "https://gov.example.tw/Page/A/1")

    def test_html_list_roc(self):
        html = (FIX / "sample_judicial_list.html").read_text()
        items = listing.parse_html_list(html, "https://www.judicial.gov.tw/tw/lp-1887-1-1-20.html")
        self.assertEqual([i["published_on"] for i in items], ["2026-10-22", "2026-04-20"])
        self.assertEqual(items[0]["url"], "https://www.judicial.gov.tw/tw/cp-1887-1638020-e3c55-1.html")
        self.assertEqual(items[0]["title"], "憲法法庭受理聲請案")

    def test_html_list_iso_skips_non_dated(self):
        html = (FIX / "sample_list_iso.html").read_text()
        items = listing.parse_html_list(html, "https://city.example.tw/list")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1]["published_on"], "2026-07-30")


class ClassTests(unittest.TestCase):
    def test_default_from_source(self):
        self.assertEqual(
            fetch_official.assign_source_class({"source_class": "official_statement"}, "院會通過預算"),
            "official_statement",
        )

    def test_record_by_title(self):
        for t in ("最高法院民事判決公告", "憲法法庭裁定", "立法院公報第115卷", "市議會會議紀錄"):
            self.assertEqual(
                fetch_official.assign_source_class({"source_class": "official_statement"}, t),
                "official_record",
            )

    def test_record_source(self):
        self.assertEqual(
            fetch_official.assign_source_class({"source_class": "official_record"}, "公告"),
            "official_record",
        )


class RecordTests(unittest.TestCase):
    def test_record_fields(self):
        src = {"id": "ey", "publisher": "行政院", "source_class": "official_statement", "actor_hint": "actor-ey"}
        item = {"url": "u", "title": "行政院通過預算", "published_on": "2026-09-23", "summary": "陳男向行政院表示"}
        rec = fetch_official.build_record(src, item, "2026-10-24T00:00:00Z", ["行政院"])
        self.assertEqual(
            sorted(rec),
            sorted(["url", "title", "publisher", "published_on", "snippet", "fetched_on",
                    "matched_terms", "source_class", "publisher_actor_hint"]),
        )
        self.assertIn("[當事人]", rec["snippet"])
        self.assertLessEqual(len(rec["snippet"]), 150)


if __name__ == "__main__":
    unittest.main()
