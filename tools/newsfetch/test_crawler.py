"""Crawler tests. No network: _http_get is replaced by a scripted fake."""

import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from tools.newsfetch.crawler import FileCache, HostRobots, PoliteCrawler


def make_crawler(responses, **kwargs):
    """responses: dict url -> list of (status, headers, body) or Exception."""
    crawler = PoliteCrawler(cache_dir=Path(tempfile.mkdtemp()), rate_limit_interval=0, **kwargs)
    crawler.calls = []
    queues = {u: list(v) for u, v in responses.items()}

    def fake_get(url):
        crawler.calls.append(url)
        q = queues.get(url)
        if not q:
            return 404, {}, b""
        item = q.pop(0) if len(q) > 1 else q[0]
        if isinstance(item, Exception):
            raise item
        return item

    crawler._http_get = fake_get
    return crawler


ROBOTS_OK = (200, {}, b"User-agent: *\nDisallow: /private\n")
PAGE = (200, {}, b"<rss>ok</rss>")


class TestRobotsFailClosed(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("tools.newsfetch.crawler.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_404_and_410_allow(self):
        for code in (404, 410):
            c = make_crawler({"https://a.example/robots.txt": [(code, {}, b"")],
                              "https://a.example/x": [PAGE]})
            self.assertEqual(c.fetch_raw("https://a.example/x"), b"<rss>ok</rss>")

    def test_5xx_disallows_all(self):
        c = make_crawler({"https://a.example/robots.txt": [(503, {}, b"")],
                          "https://a.example/x": [PAGE]})
        self.assertIsNone(c.fetch_raw("https://a.example/x"))
        self.assertNotIn("https://a.example/x", c.calls)

    def test_timeout_disallows_all(self):
        c = make_crawler({"https://a.example/robots.txt": [TimeoutError("t")],
                          "https://a.example/x": [PAGE]})
        self.assertIsNone(c.fetch_raw("https://a.example/x"))
        self.assertNotIn("https://a.example/x", c.calls)

    def test_403_disallows_all(self):
        c = make_crawler({"https://a.example/robots.txt": [(403, {}, b"")],
                          "https://a.example/x": [PAGE]})
        self.assertIsNone(c.fetch_raw("https://a.example/x"))

    def test_disallow_rule_blocks(self):
        c = make_crawler({"https://a.example/robots.txt": [ROBOTS_OK],
                          "https://a.example/private/x": [PAGE]})
        self.assertIsNone(c.fetch_raw("https://a.example/private/x"))

    def test_host_robots_modes(self):
        self.assertFalse(HostRobots(mode="disallow_all").can_fetch("ua", "https://a/x"))
        self.assertTrue(HostRobots(mode="allow_all").can_fetch("ua", "https://a/x"))


class TestRedirects(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("tools.newsfetch.crawler.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_redirect_followed_and_robots_checked_for_target_host(self):
        c = make_crawler({
            "https://a.example/robots.txt": [(404, {}, b"")],
            "https://b.example/robots.txt": [ROBOTS_OK],
            "https://a.example/x": [(301, {"location": "https://b.example/private/y"}, b"")],
            "https://b.example/private/y": [PAGE],
        })
        self.assertIsNone(c.fetch_raw("https://a.example/x"))
        self.assertIn("https://b.example/robots.txt", c.calls)
        self.assertNotIn("https://b.example/private/y", c.calls)

    def test_redirect_to_allowed_target(self):
        c = make_crawler({
            "https://a.example/robots.txt": [(404, {}, b"")],
            "https://b.example/robots.txt": [(404, {}, b"")],
            "https://a.example/x": [(302, {"location": "/z"}, b"")],
            "https://a.example/z": [(301, {"location": "https://b.example/y"}, b"")],
            "https://b.example/y": [PAGE],
        })
        self.assertEqual(c.fetch_raw("https://a.example/x"), b"<rss>ok</rss>")

    def test_more_than_three_hops_stops(self):
        resp = {"https://a.example/robots.txt": [(404, {}, b"")]}
        for i in range(6):
            resp[f"https://a.example/{i}"] = [(302, {"location": f"/{i + 1}"}, b"")]
        resp["https://a.example/6"] = [PAGE]
        c = make_crawler(resp)
        self.assertIsNone(c.fetch_raw("https://a.example/0"))
        self.assertNotIn("https://a.example/4", c.calls)

    def test_rate_limit_waits_per_target_host(self):
        c = make_crawler({
            "https://a.example/robots.txt": [(404, {}, b"")],
            "https://b.example/robots.txt": [(404, {}, b"")],
            "https://a.example/x": [(302, {"location": "https://b.example/y"}, b"")],
            "https://b.example/y": [PAGE],
        })
        hosts = []
        c.rate_limiter.wait = hosts.append
        c.fetch_raw("https://a.example/x")
        self.assertEqual(hosts.count("b.example"), 2)  # robots + page


class TestCache(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("tools.newsfetch.crawler.time.sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_200_is_cached(self):
        c = make_crawler({"https://a.example/robots.txt": [(404, {}, b"")],
                          "https://a.example/x": [(500, {}, b"boom")]})
        self.assertIsNone(c.fetch_raw("https://a.example/x"))
        self.assertIsNone(c.cache.get("https://a.example/x"))
        self.assertIsNone(c.cache.get("https://a.example/robots.txt"))

    def test_error_page_not_cached(self):
        body = b"<html><title>Just a moment...</title>captcha</html>"
        c = make_crawler({"https://a.example/robots.txt": [(404, {}, b"")],
                          "https://a.example/x": [(200, {}, body)]})
        self.assertIsNone(c.fetch_raw("https://a.example/x"))
        self.assertIsNone(c.cache.get("https://a.example/x"))

    def test_good_page_cached_and_reused(self):
        c = make_crawler({"https://a.example/robots.txt": [(404, {}, b"")],
                          "https://a.example/x": [PAGE]})
        c.fetch_raw("https://a.example/x")
        c.fetch_raw("https://a.example/x")
        self.assertEqual(c.calls.count("https://a.example/x"), 1)

    def test_no_cache_flag(self):
        c = make_crawler({"https://a.example/robots.txt": [(404, {}, b"")],
                          "https://a.example/x": [PAGE]}, use_cache=False)
        c.fetch_raw("https://a.example/x")
        c.fetch_raw("https://a.example/x")
        self.assertEqual(c.calls.count("https://a.example/x"), 2)

    def test_ttl_expiry(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = FileCache(Path(tmp.name))
        cache.set("u", b"data")
        self.assertEqual(cache.get("u", ttl=60), b"data")
        old = time.time() - 3600
        import os
        os.utime(cache._get_path("u"), (old, old))
        self.assertIsNone(cache.get("u", ttl=60))
        self.assertEqual(cache.get("u", ttl=7200), b"data")


if __name__ == "__main__":
    unittest.main()
