"""T70 (R179, R324.4): every HTTP route request keeps at least 1.1 s per host. No network, no real sleep."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import crawler as crawler_mod
from tools.newsfetch import netguard

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "official"))
import crawler as official_mod  # noqa: E402

HOSTS = ["news.ltn.com.tw", "feeds.ettoday.net", "feed.newtalk.tw"]


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def run_gap(mod, hosts, rounds=3):
    """Fetch several URLs per host with default settings. Return the request times per host."""
    clock = FakeClock()
    sent = {}
    crawler = mod.PoliteCrawler(cache_dir=Path(tempfile.mkdtemp()), use_cache=False)

    def fake_get(url):
        host = crawler.get_host(url)
        sent.setdefault(host, []).append(clock.now)
        clock.now += 0.05  # a request takes time
        if url.endswith("/robots.txt"):
            return 200, {}, b"User-agent: *\nAllow: /\n"
        return 200, {}, b"<html></html>"

    crawler._http_get = fake_get
    with mock.patch.object(mod.time, "time", clock.time), mock.patch.object(mod.time, "sleep", clock.sleep):
        for i in range(rounds):
            for host in hosts:
                crawler.fetch_raw(f"https://{host}/list/{i}")
    return sent


class HostGapTest(unittest.TestCase):
    def assert_gaps(self, sent):
        self.assertTrue(sent)
        for host, times in sent.items():
            self.assertGreater(len(times), 1, host)
            for a, b in zip(times, times[1:]):
                self.assertGreaterEqual(b - a, 1.1 - 1e-9, f"{host} gap {b - a:.3f}")

    def test_constant_is_1_1(self):
        self.assertEqual(netguard.MIN_HOST_GAP, 1.1)

    def test_default_limiters_use_constant(self):
        self.assertEqual(crawler_mod.RateLimiter().min_interval, 1.1)
        self.assertEqual(official_mod.RateLimiter().min_interval, 1.1)

    def test_news_crawler_gap(self):
        self.assert_gaps(run_gap(crawler_mod, HOSTS))

    def test_official_crawler_gap(self):
        self.assert_gaps(run_gap(official_mod, ["www.mol.gov.tw", "www.moj.gov.tw"]))

    def test_article_step_default_gap(self):
        from tools.newsfetch import article
        step = article.ArticleStep(object())
        self.assertGreaterEqual(step.min_interval, 1.1)


if __name__ == "__main__":
    unittest.main()
