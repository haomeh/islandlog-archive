"""List route tests (T16-C). No network: pages come from saved fixtures and a scripted crawler."""

import datetime
import json
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import lists
from tools.newsfetch.fetch import fetch_source_items, load_feeds
from tools.newsfetch.publishers import PublisherIndex
from tools.newsfetch.test_crawler import ROBOTS_OK, make_crawler

BASE = Path(__file__).parent
FIXTURES = BASE / "fixtures"
FEEDS = {f["id"]: f for f in load_feeds(BASE / "feeds.json")}
TODAY = "2026-10-25"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def parse(feed_id, name, base):
    route = FEEDS[feed_id]["route"]
    return lists.parse_anchor_list(fixture(name), route, base, TODAY, FEEDS[feed_id]["publisher"])


class TestListParsers(unittest.TestCase):
    def test_ettoday_date_before_link_and_canonical_url(self):
        items = parse("ettoday", "list_ettoday.html", "https://www.ettoday.net/news/news-list-2026-06-01-6.htm")
        self.assertEqual([i["published_on"] for i in items], ["2026-06-01", "2026-06-01", "2026-05-31"])
        self.assertEqual(items[2]["url"], "https://www.ettoday.net/news/20260531/1000003.htm")
        self.assertEqual(items[0]["publisher"], "ETtoday新聞雲")

    def test_newtalk_date_from_url_and_title_attribute(self):
        items = parse("newtalk", "list_newtalk.html", "https://newtalk.tw/news/summary/2026-06-01")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["url"], "https://newtalk.tw/news/view/2026-06-01/1000011")
        self.assertEqual(items[0]["title"], "測試新頭殼標題一")
        self.assertEqual(items[0]["published_on"], "2026-06-01")

    def test_pts_reads_heading_links_only_with_date_after_the_link(self):
        items = parse("pts", "list_pts.html", "https://news.pts.org.tw/dailynews?page=2")
        self.assertEqual([i["title"] for i in items], ["測試公視標題一", "測試公視標題二"])
        self.assertEqual([i["published_on"] for i in items], ["2026-10-25", "2026-10-07"])

    def test_ftv_month_letter_and_digit(self):
        route = FEEDS["ftv"]["route"]
        items = lists.parse_anchor_list(fixture("list_ftv.html"), route, "https://www.ftvnews.com.tw/realtime/", TODAY, "民視新聞網")
        self.assertEqual([i["published_on"] for i in items], ["2026-10-25", "2026-09-05"])
        self.assertEqual(items[0]["title"], "測試民視標題一")

    def test_date_without_year_is_never_in_the_future(self):
        route = {"link": "x", "date_regex": r"(?P<m>\d\d)/(?P<d>\d\d)"}
        m = __import__("re").search(route["date_regex"], "12/30")
        self.assertEqual(lists.date_from_match(m, "2026-01-05"), "2025-12-30")

    def test_canonical_url_drops_tracking_fragment_and_slash(self):
        self.assertEqual(
            lists.canonical_url("http://www.chinatimes.com/realtimenews/20260601001-2604/?chdtv&utm_source=x#top"),
            "https://www.chinatimes.com/realtimenews/20260601001-2604",
        )

    def test_snippet_is_at_most_150_characters_and_has_no_body(self):
        item = lists.make_item("https://x/1", "字" * 400, "2026-06-01", "P")
        self.assertLessEqual(len(item["snippet"]), 150)
        self.assertEqual(item["summary"], "")


class TestListFetch(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("tools.newsfetch.crawler.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dated_list_visits_each_day_in_the_window_only(self):
        route = dict(FEEDS["newtalk"]["route"], max_pages=2)
        page = (200, {}, fixture("list_newtalk.html").encode())
        responses = {"https://newtalk.tw/robots.txt": [(404, {}, b"")]}
        for day in ("2026-06-01", "2026-06-02"):
            responses[f"https://newtalk.tw/news/summary/{day}/1"] = [page]
        crawler = make_crawler(responses)
        items = lists.fetch_dated_list(route, crawler, "Newtalk", "2026-06-01", "2026-06-02", TODAY)
        self.assertEqual(len(items), 4)
        urls = [u for u in crawler.calls if "summary" in u]
        self.assertEqual(urls, ["https://newtalk.tw/news/summary/2026-06-01/1",
                                "https://newtalk.tw/news/summary/2026-06-01/2",
                                "https://newtalk.tw/news/summary/2026-06-02/1",
                                "https://newtalk.tw/news/summary/2026-06-02/2"])

    def test_paged_list_stops_when_a_page_is_older_than_since(self):
        route = dict(FEEDS["pts"]["route"], max_pages=50)
        responses = {"https://news.pts.org.tw/robots.txt": [ROBOTS_OK]}
        responses["https://news.pts.org.tw/dailynews?page=1"] = [(200, {}, fixture("list_pts.html").encode())]
        crawler = make_crawler(responses)
        items = lists.fetch_paged_list(route, crawler, "公視新聞網", "2026-11-01", TODAY)
        self.assertEqual(len(items), 2)
        self.assertNotIn("https://news.pts.org.tw/dailynews?page=2", crawler.calls)

    def test_list_fetch_obeys_robots_deny(self):
        route = dict(FEEDS["pts"]["route"])
        responses = {"https://news.pts.org.tw/robots.txt": [(200, {}, b"User-agent: *\nDisallow: /dailynews\n")],
                     "https://news.pts.org.tw/dailynews?page=1": [(200, {}, fixture("list_pts.html").encode())]}
        crawler = make_crawler(responses)
        self.assertEqual(lists.fetch_paged_list(route, crawler, "公視新聞網", "2026-10-01", TODAY), [])
        self.assertNotIn("https://news.pts.org.tw/dailynews?page=1", crawler.calls)

    def test_list_fetch_fails_closed_when_robots_unreadable(self):
        route = dict(FEEDS["pts"]["route"])
        responses = {"https://news.pts.org.tw/robots.txt": [(403, {}, b"")],
                     "https://news.pts.org.tw/dailynews?page=1": [(200, {}, fixture("list_pts.html").encode())]}
        crawler = make_crawler(responses)
        self.assertEqual(lists.fetch_paged_list(route, crawler, "公視新聞網", "2026-10-01", TODAY), [])

    def test_host_stops_after_five_failures(self):
        route = dict(FEEDS["pts"]["route"])
        responses = {"https://news.pts.org.tw/robots.txt": [ROBOTS_OK],
                     "https://news.pts.org.tw/dailynews?page=1": [(503, {}, b"")]}
        crawler = make_crawler(responses)
        for _ in range(5):
            lists.fetch_paged_list(route, crawler, "公視新聞網", "2026-10-01", TODAY)
        self.assertIn("news.pts.org.tw", crawler.stopped_hosts)


class TestBrowserList(unittest.TestCase):
    ROUTE = FEEDS["setn"]["route"]

    def crawler(self, robots):
        return make_crawler({"https://www.setn.com/robots.txt": [robots]})

    def test_relative_dates_from_labels(self):
        calls = []

        def browser(url, ua, config):
            calls.append(config)
            return json.loads(fixture("list_browser_setn.json"))

        now = datetime.datetime(2026, 10, 25, 15, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        with mock.patch("tools.newsfetch.lists.datetime") as dt:
            dt.datetime.now.return_value = now
            dt.timezone = datetime.timezone
            dt.timedelta = datetime.timedelta
            items = lists.fetch_browser_list(self.ROUTE, self.crawler((200, {}, b"User-agent: *\nDisallow: /search/*\n")),
                                             "三立新聞網", "2026-04-24", TODAY, browser=browser)
        self.assertEqual([i["published_on"] for i in items], ["2026-10-25", "2026-10-23", "2026-10-25"])
        self.assertGreaterEqual(calls[0]["delay_ms"], 1000)
        self.assertEqual(calls[0]["stop_before"], "2026-04-24")
        self.assertTrue(any("search" in d for d in calls[0]["deny"]))

    def test_browser_does_not_start_when_robots_denies_the_list(self):
        browser = mock.Mock()
        crawler = self.crawler((200, {}, b"User-agent: *\nDisallow: /viewall\n"))
        self.assertEqual(lists.fetch_browser_list(self.ROUTE, crawler, "三立新聞網", "2026-04-24", TODAY, browser=browser), [])
        browser.assert_not_called()

    def test_browser_does_not_start_when_robots_unreadable(self):
        browser = mock.Mock()
        crawler = self.crawler((500, {}, b""))
        self.assertEqual(lists.fetch_browser_list(self.ROUTE, crawler, "三立新聞網", "2026-04-24", TODAY, browser=browser), [])
        browser.assert_not_called()

    def test_helper_script_aborts_other_sites_and_denied_paths(self):
        script = (BASE / "list_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("hostname.endsWith(site)", script)
        self.assertIn("denyRes.some", script)
        self.assertIn("Math.max(1000", script)


class TestPublishers(unittest.TestCase):
    INDEX = PublisherIndex(list(FEEDS.values()))

    def test_aliases_map_to_one_brand(self):
        for name in ("東森新聞", "EBC東森新聞", "東森新聞雲"):
            self.assertEqual(self.INDEX.brand(name), "東森新聞")

    def test_group_counts_ettoday_and_ebc_as_one(self):
        self.assertEqual(self.INDEX.group("ETtoday新聞雲"), self.INDEX.group("EBC東森新聞"))
        self.assertEqual(self.INDEX.group("公視新聞網"), self.INDEX.group("華視"))
        self.assertNotEqual(self.INDEX.group("TVBS"), self.INDEX.group("Newtalk"))

    def test_every_feed_has_group_with_public_source(self):
        for feed in FEEDS.values():
            self.assertTrue(feed.get("publisher_group"), feed["id"])
            self.assertTrue(feed.get("group_source", "").startswith("https://"), feed["id"])

    def test_blocked_or_latest_only_feeds_carry_a_reason(self):
        for feed in FEEDS.values():
            if feed.get("status") in ("blocked", "latest_only"):
                self.assertTrue(feed.get("blocked_reason"), feed["id"])

    def test_ftv_reads_robots_in_the_browser(self):
        self.assertEqual(FEEDS["ftv"]["type"], "browser_list")
        self.assertEqual(FEEDS["ftv"]["robots_via"], "browser")

    def test_blocked_feed_returns_no_items(self):
        crawler = make_crawler({})
        feed = {"id": "x", "publisher": "X", "type": "blocked", "blocked_reason": "robots"}
        self.assertEqual(fetch_source_items(feed, crawler), [])
        self.assertEqual(crawler.calls, [])


class TestSourceRuleUsesGroups(unittest.TestCase):
    def test_two_brands_of_one_group_are_one_publisher(self):
        from tools.newsfetch.topics_full import meets_news_rule, meets_source_rule

        def item(pub, group=None):
            d = {"publisher": pub, "source_class": "news"}
            if group:
                d["publisher_group"] = group
            return d

        same = [item("ETtoday新聞雲", "東森媒體集團"), item("東森新聞", "東森媒體集團")]
        self.assertFalse(meets_news_rule(same))
        self.assertFalse(meets_source_rule(same))
        other = [item("東森新聞", "東森媒體集團"), item("TVBS", "聯意製作")]
        self.assertTrue(meets_news_rule(other))
        self.assertTrue(meets_news_rule([item("A"), item("B")]))


if __name__ == "__main__":
    unittest.main()
