"""R108 tests: ftv robots.txt through the browser. No network: the browser is a scripted fake."""

import tempfile
import unittest
from pathlib import Path

from tools.newsfetch import lists
from tools.newsfetch.crawler import PoliteCrawler
from tools.newsfetch.fetch import fetch_source_items, load_feeds

BASE = Path(__file__).parent
FEEDS = load_feeds(BASE / "feeds.json")
FTV = next(f for f in FEEDS if f["id"] == "ftv")
LIST_URL = FTV["route"]["url"]
TODAY = "2026-10-25"
ROBOTS_BODY = "User-agent: *\nDisallow: /search\nDisallow: /private\n"


def make_crawler(result):
    """result: dict returned by the fake browser, or an Exception to raise."""
    crawler = PoliteCrawler(cache_dir=Path(tempfile.mkdtemp()), rate_limit_interval=0)
    crawler.use_browser_robots(FEEDS)
    crawler.browser_calls = []

    def fake_browser(url, user_agent):
        crawler.browser_calls.append((url, user_agent))
        if isinstance(result, Exception):
            raise result
        return result

    def no_http(url):
        raise AssertionError(f"HTTP route used for {url}")

    crawler.browser_robots = fake_browser
    crawler._http_get = no_http
    return crawler


class TestFtvRobotsInBrowser(unittest.TestCase):
    def test_only_ftv_uses_the_browser_route(self):
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        self.assertEqual(crawler.browser_robots_hosts, {"www.ftvnews.com.tw"})

    def test_browser_reads_rules_with_our_user_agent(self):
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        hr = crawler.load_robots("www.ftvnews.com.tw")
        self.assertEqual(hr.mode, "rules")
        self.assertEqual(crawler.browser_calls, [("https://www.ftvnews.com.tw/robots.txt", crawler.user_agent)])
        self.assertIn("islandlog-newsfetch", crawler.user_agent)
        self.assertTrue(hr.can_fetch(crawler.user_agent, LIST_URL))
        self.assertFalse(hr.can_fetch(crawler.user_agent, "https://www.ftvnews.com.tw/search/x"))

    def test_browser_404_allows_all(self):
        hr = make_crawler({"status": 404, "body": ""}).load_robots("www.ftvnews.com.tw")
        self.assertEqual(hr.mode, "allow_all")

    def test_robots_is_read_once_within_the_ttl(self):
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        crawler.load_robots("www.ftvnews.com.tw")
        crawler.load_robots("www.ftvnews.com.tw")
        self.assertEqual(len(crawler.browser_calls), 1)


class TestFtvBlockedFallback(unittest.TestCase):
    def assert_blocked(self, result):
        crawler = make_crawler(result)
        self.assertEqual(crawler.load_robots("www.ftvnews.com.tw").mode, "disallow_all")
        called = []
        items = lists.fetch_browser_list(FTV["route"], crawler, FTV["publisher"], "2026-04-24", TODAY,
                                         browser=lambda *a: called.append(a))
        self.assertEqual(items, [])
        self.assertEqual(called, [])

    def test_tls_error_in_browser_stays_blocked(self):
        self.assert_blocked({"status": None, "body": "", "error": "net::ERR_CERT_INVALID"})

    def test_browser_crash_stays_blocked(self):
        self.assert_blocked(RuntimeError("robots browser exit 1"))

    def test_browser_5xx_stays_blocked(self):
        self.assert_blocked({"status": 503, "body": ""})

    def test_redirect_stays_blocked(self):
        self.assert_blocked({"status": 301, "body": ""})


class TestFtvListThroughBrowser(unittest.TestCase):
    ROWS = {"items": [
        {"href": "https://www.ftvnews.com.tw/news/detail/2026A25W0001", "title": "2026/10/25 13:49:22 測試民視標題一", "row": "", "hint": ""},
        {"href": "https://www.ftvnews.com.tw/news/detail/2026905W0002", "title": "2026/09/05 08:00:00 測試民視標題二", "row": "", "hint": ""},
    ], "denied": []}

    def test_list_parse_and_config(self):
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        seen = {}

        def fake_list(url, user_agent, config):
            seen.update(url=url, user_agent=user_agent, config=config)
            return self.ROWS

        items = lists.fetch_browser_list(FTV["route"], crawler, FTV["publisher"], "2026-04-24", TODAY, browser=fake_list)
        self.assertEqual([i["published_on"] for i in items], ["2026-10-25", "2026-09-05"])
        self.assertEqual(items[0]["title"], "測試民視標題一")
        self.assertEqual(items[0]["publisher"], "民視新聞網")
        self.assertEqual(seen["config"]["stop_before"], "2026-04-24")
        self.assertIn(r"^/search", seen["config"]["deny"])
        self.assertTrue(seen["config"]["page_template"].endswith("?page={page}"))
        self.assertGreaterEqual(seen["config"]["delay_ms"], 1000)

    def test_ftv_title_comes_from_the_headline_element(self):
        self.assertEqual(FTV["route"]["title_selector"], "h2.title")
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        seen = {}
        lists.fetch_browser_list(FTV["route"], crawler, FTV["publisher"], "2026-04-24", TODAY,
                                 browser=lambda u, ua, config: seen.update(config) or {"items": []})
        self.assertEqual(seen["title_selector"], "h2.title")

    def test_fetch_source_items_uses_the_browser_route(self):
        crawler = make_crawler({"status": 200, "body": ROBOTS_BODY})
        import unittest.mock as mock
        with mock.patch("tools.newsfetch.fetch.fetch_browser_list", return_value=["x"]) as fb:
            self.assertEqual(fetch_source_items(FTV, crawler, since="2026-04-24", until=TODAY), ["x"])
        fb.assert_called_once()


if __name__ == "__main__":
    unittest.main()
