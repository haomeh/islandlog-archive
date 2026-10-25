import unittest

from tools.newsfetch import article
from tools.newsfetch.crawler import HostRobots, RateLimiter

BODY = "這是新聞內文的第一段，" * 40


class FakeCrawler:
    def __init__(self, robots):
        self.robots = robots
        self.loaded = []

    def load_robots(self, host, scheme="https"):
        self.loaded.append(host)
        return self.robots


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def browser_returning(payload):
    calls = []

    def run(url, user_agent):
        calls.append((url, user_agent))
        return dict(payload)

    run.calls = calls
    return run


LTN_URL = "https://news.ltn.com.tw/news/politics/breakingnews/5586678"


class ArticleStepTest(unittest.TestCase):
    def make(self, robots_text="User-agent: *\nAllow: /\n", payload=None, clock=None):
        robots = HostRobots(content=robots_text) if robots_text is not None else HostRobots(mode="disallow_all")
        payload = payload if payload is not None else {
            "byline": "記者王小明", "section": "政治", "published_at": "2026-09-26T10:21:00+08:00",
            "quote": BODY, "body": BODY, "html": "<p>" + BODY + "</p>"}
        browser = browser_returning(payload)
        clock = clock or FakeClock()
        step = article.ArticleStep(FakeCrawler(robots), browser, RateLimiter(min_interval=1.0), clock=clock)
        return step, browser, clock

    def test_robots_deny_skips_browser(self):
        step, browser, _ = self.make("User-agent: islandlog-newsfetch\nDisallow: /news/\n")
        result = step.extract(LTN_URL)
        self.assertEqual(result["status"], "robots_denied")
        self.assertEqual(browser.calls, [])

    def test_unreadable_robots_fails_closed(self):
        step, browser, _ = self.make(robots_text=None)
        self.assertEqual(step.extract(LTN_URL)["status"], "robots_denied")
        self.assertEqual(browser.calls, [])

    def test_udn_news_path_never_opened(self):
        step, browser, _ = self.make()
        result = step.extract("https://udn.com/news/story/6656/9833831")
        self.assertEqual(result["status"], "host_rule_denied")
        self.assertEqual(browser.calls, [])

    def test_rate_limit_one_per_second_per_host(self):
        step, browser, clock = self.make()
        step.extract(LTN_URL)
        step.extract("https://news.ltn.com.tw/news/life/breakingnews/5586874")
        self.assertEqual(len(browser.calls), 2)
        self.assertTrue(clock.sleeps and clock.sleeps[-1] >= 0.99)

    def test_no_body_in_output(self):
        step, _, _ = self.make()
        result = step.extract(LTN_URL)
        self.assertEqual(set(result), {"url", "status", "byline", "section", "published_at", "quote"})
        for value in result.values():
            self.assertNotIn(BODY, str(value))

    def test_quote_is_150_or_fewer(self):
        step, _, _ = self.make()
        result = step.extract(LTN_URL)
        self.assertLessEqual(len(result["quote"]), 150)
        self.assertTrue(result["quote"])

    def test_user_agent_has_token(self):
        step, browser, _ = self.make()
        step.extract(LTN_URL)
        self.assertIn("islandlog-newsfetch", browser.calls[0][1])

    def test_section_from_url_when_page_has_none(self):
        step, _, _ = self.make(payload={"byline": "", "section": "", "published_at": "", "quote": ""})
        result = step.extract(LTN_URL)
        self.assertEqual(result["section"], "政治")
        self.assertNotIn("byline", result)

    def test_english_section_is_mapped(self):
        step, _, _ = self.make(payload={"byline": "記者王小明", "section": "life", "published_at": "", "quote": "x"})
        self.assertEqual(step.extract(LTN_URL)["section"], "生活")

    def test_byline_cleanup(self):
        self.assertEqual(article.clean_byline("〔記者王小明／台北報導〕"), "記者王小明")
        self.assertEqual(article.clean_byline("記者王小明、李大華／即時報導"), "記者王小明、李大華")
        self.assertEqual(article.clean_byline("〔即時新聞／綜合報導〕"), "即時新聞／綜合報導")
        self.assertEqual(article.clean_byline("x" * 200), "")

    def test_browser_error_is_reported_without_text(self):
        def broken(url, user_agent):
            raise RuntimeError("timeout " + BODY)

        robots = HostRobots(content="User-agent: *\nAllow: /\n")
        step = article.ArticleStep(FakeCrawler(robots), broken, RateLimiter(min_interval=0), clock=FakeClock())
        result = step.extract(LTN_URL)
        self.assertEqual(result["status"], "browser_error")
        self.assertNotIn(BODY, str(result))


if __name__ == "__main__":
    unittest.main()
