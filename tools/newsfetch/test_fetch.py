"""Unit tests for tools.newsfetch modules.

Tests:
1. Date parsing (ISO 8601, RFC 2822, range filtering).
2. Term filtering (inclusion terms, exclusion of sports/entertainment/crime).
3. Snippet cut (max 150 characters, HTML cleanup).
4. Robots handling (local fixture, user-agent check).
5. Privacy anonymization (replacing private person names with [當事人]).
"""

import os
import unittest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestDateParsing(unittest.TestCase):
    """Test date parsing and date range verification."""

    def test_parse_iso_date_with_offset(self):
        from tools.newsfetch.parser import parse_date

        self.assertEqual(parse_date("2026-10-24T19:05:35+08:00"), "2026-10-24")

    def test_parse_iso_date_without_seconds(self):
        from tools.newsfetch.parser import parse_date

        self.assertEqual(parse_date("2026-10-24T22:27+08:00"), "2026-10-24")

    def test_parse_rfc2822_date(self):
        from tools.newsfetch.parser import parse_date

        self.assertEqual(parse_date("Sat, 24 Oct 2026 09:00:00 +0800"), "2026-10-24")
        self.assertEqual(parse_date("Fri, 23 Oct 2026 23:43:17 +0800"), "2026-10-23")

    def test_parse_rfc2822_gmt_date(self):
        from tools.newsfetch.parser import parse_date

        # 2026-10-23 02:22 GMT is 2026-10-23 in UTC+8
        self.assertEqual(parse_date("Fri, 23 Oct 2026 02:22:05 GMT"), "2026-10-23")

    def test_parse_plain_date(self):
        from tools.newsfetch.parser import parse_date

        self.assertEqual(parse_date("2026-10-24"), "2026-10-24")

    def test_parse_slash_date(self):
        from tools.newsfetch.parser import parse_date

        self.assertEqual(parse_date("2026/04/24"), "2026-04-24")

    def test_date_in_range(self):
        from tools.newsfetch.parser import is_date_in_range

        self.assertTrue(is_date_in_range("2026-10-24", "2026-04-24", "2026-10-24"))
        self.assertTrue(is_date_in_range("2026-04-24", "2026-04-24", "2026-10-24"))
        self.assertTrue(is_date_in_range("2026-07-15", "2026-04-24", "2026-10-24"))
        self.assertFalse(is_date_in_range("2026-04-23", "2026-04-24", "2026-10-24"))
        self.assertFalse(is_date_in_range("2026-10-25", "2026-04-24", "2026-10-24"))


class TestSnippetCut(unittest.TestCase):
    """Test cutting snippets to 150 characters or fewer."""

    def test_short_snippet_preserved(self):
        from tools.newsfetch.parser import make_snippet

        text = "立法院三讀通過法案。"
        self.assertEqual(make_snippet(text), text)

    def test_long_snippet_truncated_to_max_150(self):
        from tools.newsfetch.parser import make_snippet

        long_text = "這是一篇關於立法院重大法案審查的長篇新聞摘要報導。" * 15
        snippet = make_snippet(long_text)
        self.assertLessEqual(len(snippet), 150)
        self.assertTrue(snippet.endswith("..."))

    def test_html_cleaned_from_snippet(self):
        from tools.newsfetch.parser import make_snippet

        html = "<p>行政院今日宣布<b>重大決策</b>，詳見內部報告。</p>"
        snippet = make_snippet(html)
        self.assertEqual(snippet, "行政院今日宣布重大決策，詳見內部報告。")


class TestPrivacyAnonymization(unittest.TestCase):
    """Test replacing private person names with [當事人]."""

    def test_private_person_pattern(self):
        from tools.newsfetch.parser import mask_private_person

        self.assertEqual(
            mask_private_person("陳姓男子涉違法傾倒廢棄物 遭地檢署裁罰起訴"),
            "[當事人]涉違法傾倒廢棄物 遭地檢署裁罰起訴",
        )
        self.assertEqual(
            mask_private_person("林姓婦人騎車違規受罰提起行政訴訟"),
            "[當事人]騎車違規受罰提起行政訴訟",
        )
        self.assertEqual(
            mask_private_person("張男與李女向地檢署自首"),
            "[當事人]與[當事人]向地檢署自首",
        )

    def test_public_figure_not_masked(self):
        from tools.newsfetch.parser import mask_private_person

        titles = [
            "行政院長卓榮泰視察災情",
            "台北市長蔣萬安說明預算編列",
            "立委黃國昌質詢法務部長",
            "總統賴清德主持國安會議",
        ]
        for t in titles:
            self.assertEqual(mask_private_person(t), t)


class TestTermFilter(unittest.TestCase):
    """Test term matching and exclusion logic."""

    def setUp(self):
        from tools.newsfetch.filter import NewsFilter

        terms_data = {
            "include_terms": ["立法院", "行政院", "縣政府", "市政府", "議會", "環評", "判決", "憲法法庭", "公投", "預算", "裁罰", "地檢署"],
            "exclude_categories": {
                "sports": ["職棒", "中職", "MLB", "NBA", "總冠軍賽"],
                "entertainment": ["演唱會", "影帝", "影后", "韓團", "藝人", "緋聞"],
                "crime_victim": ["命案", "遇害", "陳屍", "墜樓", "遭砍"]
            }
        }
        self.filter = NewsFilter(terms_data)

    def test_positive_match(self):
        matched, is_excluded = self.filter.check_match("立法院院會三讀通過環境保護法修正案", "")
        self.assertIn("立法院", matched)
        self.assertFalse(is_excluded)

    def test_multiple_terms_match(self):
        matched, is_excluded = self.filter.check_match("行政院通過明年度總預算案 函送立法院審議", "")
        self.assertIn("行政院", matched)
        self.assertIn("立法院", matched)
        self.assertIn("預算", matched)
        self.assertFalse(is_excluded)

    def test_drop_sports(self):
        matched, is_excluded = self.filter.check_match("職棒總冠軍賽開打 市政府派員維護交通", "")
        self.assertTrue(is_excluded)

    def test_drop_entertainment(self):
        matched, is_excluded = self.filter.check_match("某韓團演唱會門票秒殺 市政府呼籲民眾防詐", "")
        self.assertTrue(is_excluded)

    def test_drop_crime_victim(self):
        matched, is_excluded = self.filter.check_match("台南某民宅命案男子遇害 地檢署展開調查", "")
        self.assertTrue(is_excluded)

    def test_no_match(self):
        matched, is_excluded = self.filter.check_match("今日全台晴到多雲 氣溫略微回升", "")
        self.assertEqual(matched, [])
        self.assertFalse(is_excluded)


class TestRobotsHandling(unittest.TestCase):
    """Test robots.txt compliance using local fixtures (no network)."""

    def test_robots_allowed_and_disallowed(self):
        from tools.newsfetch.crawler import HostRobots

        robots_path = FIXTURES_DIR / "sample_robots.txt"
        with open(robots_path, "r", encoding="utf-8") as f:
            robots_content = f.read()

        hr = HostRobots(robots_content)
        user_agent = "islandlog-newsfetch/0.1 (+https://github.com/haomeh/islandlog-archive)"

        self.assertTrue(hr.can_fetch(user_agent, "https://news.example.com/xml/sitemap.xml"))
        self.assertTrue(hr.can_fetch(user_agent, "https://news.example.com/sitemap.xml"))
        self.assertTrue(hr.can_fetch(user_agent, "https://news.example.com/rss/all.xml"))
        self.assertFalse(hr.can_fetch(user_agent, "https://news.example.com/search?q=test"))
        self.assertFalse(hr.can_fetch(user_agent, "https://news.example.com/admin/settings"))


class TestParsers(unittest.TestCase):
    """Test XML sitemap and RSS parsing without network."""

    def test_parse_news_sitemap(self):
        from tools.newsfetch.parser import parse_news_sitemap_xml

        sitemap_path = FIXTURES_DIR / "sample_news_sitemap.xml"
        with open(sitemap_path, "rb") as f:
            content = f.read()

        items = parse_news_sitemap_xml(content, publisher="測試新聞網")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["url"], "https://news.example.com/article/1001")
        self.assertEqual(items[0]["title"], "立法院院會三讀通過環境保護法修正案")
        self.assertEqual(items[0]["published_on"], "2026-10-24")
        self.assertEqual(items[0]["publisher"], "測試新聞網")

    def test_parse_rss(self):
        from tools.newsfetch.parser import parse_rss_xml

        rss_path = FIXTURES_DIR / "sample_rss.xml"
        with open(rss_path, "rb") as f:
            content = f.read()

        items = parse_rss_xml(content, publisher="測試新聞網")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://news.example.com/rss/2001")
        self.assertEqual(items[0]["published_on"], "2026-10-24")
        self.assertIn("行政院", items[0]["snippet"])

    def test_parse_ltn_search_html(self):
        from tools.newsfetch.parser import parse_ltn_search_html

        fixture_path = FIXTURES_DIR / "sample_ltn_search.html"
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        items = parse_ltn_search_html(content, publisher="自由時報")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://news.ltn.com.tw/news/politics/breakingnews/5415200")
        self.assertEqual(items[0]["title"], "立法院協商法案引發熱烈討論")
        self.assertEqual(items[0]["published_on"], "2026-04-24")
        self.assertEqual(items[0]["publisher"], "自由時報")
        self.assertIn("立法院朝野黨團", items[0]["snippet"])


class TestCLI(unittest.TestCase):
    """Test CLI execution and arguments."""

    def test_generate_weekly_windows(self):
        from tools.newsfetch.fetch import generate_weekly_windows

        windows = generate_weekly_windows("2026-04-24", "2026-05-08")
        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0], ("20260424", "20260430"))
        self.assertEqual(windows[1], ("20260501", "20260507"))
        self.assertEqual(windows[2], ("20260508", "20260508"))

    def test_fetch_source_items_ltn_search(self):
        from tools.newsfetch.fetch import fetch_source_items

        class MockCrawler:
            def fetch_raw(self, url, check_robots=True):
                fixture_path = FIXTURES_DIR / "sample_ltn_search.html"
                with open(fixture_path, "rb") as f:
                    return f.read()

        feed_cfg = {
            "id": "ltn",
            "publisher": "自由時報",
            "type": "ltn_search",
            "url": "https://search.ltn.com.tw/list",
            "search_terms": ["立法院"],
        }
        items = fetch_source_items(
            feed_cfg,
            MockCrawler(),
            since="2026-04-24",
            until="2026-04-30",
        )
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["published_on"], "2026-04-24")

    def test_cli_help(self):
        import subprocess
        import sys

        fetch_script = Path(__file__).parent / "fetch.py"
        res = subprocess.run(
            [sys.executable, str(fetch_script), "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Fetch and filter Taiwan news metadata", res.stdout)
        self.assertIn("--since", res.stdout)
        self.assertIn("--until", res.stdout)
        self.assertIn("--out", res.stdout)


if __name__ == "__main__":
    unittest.main()
