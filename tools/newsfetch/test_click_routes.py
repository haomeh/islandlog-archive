"""T29 tests: browser click routes (R179). No internet: fixtures, a scripted crawler and a local server on 127.0.0.1."""

import datetime
import json
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from tools.newsfetch import lists
from tools.newsfetch.fetch import fetch_source_items, load_feeds
from tools.newsfetch.test_crawler import make_crawler

BASE = Path(__file__).parent
FEEDS = {f["id"]: f for f in load_feeds(BASE / "feeds.json")}
OUTLETS = ["udn", "cts", "chinatimes", "mirror", "pts", "cna", "ebc", "tvbs", "setn", "storm", "ftv"]
TODAY = "2026-10-26"
NOW = datetime.datetime(2026, 10, 26, 15, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
LEAD = "這是測試用的導言段落"


def run_node(script):
    proc = subprocess.run(["node", str(BASE / script)], capture_output=True, text=True, timeout=120, check=True)
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestClickFeeds(unittest.TestCase):
    def test_every_outlet_has_one_click_route(self):
        for outlet in OUTLETS:
            self.assertIn("click_route", FEEDS[outlet], outlet)

    def test_route_keys(self):
        for outlet in OUTLETS:
            route = FEEDS[outlet]["click_route"]
            for key in ("urls", "rows", "link", "title_selector", "date_selector"):
                self.assertTrue(route.get(key), f"{outlet} {key}")
            # The route acts like a reader: click a control or scroll.
            self.assertTrue(any(route.get(k) for k in ("next", "scroll", "scroll_to")), outlet)
            for url in route["urls"]:
                self.assertTrue(url.startswith("https://"), url)
            self.assertLessEqual(route.get("request_cap", 20000), 40000)

    def test_cts_has_13_categories_and_no_breaking(self):
        urls = FEEDS["cts"]["click_route"]["urls"]
        self.assertEqual(len(urls), 13)
        self.assertFalse(any("/breaking/" in u for u in urls))

    def test_no_route_calls_an_api_url_directly(self):
        for outlet in OUTLETS:
            for url in FEEDS[outlet]["click_route"]["urls"]:
                self.assertNotIn("/api/", url, outlet)

    def test_tvbs_names_its_api_host_so_robots_decides(self):
        self.assertEqual(FEEDS["tvbs"]["click_route"]["allow_hosts"], ["api.news.tvbs.app"])


class TestClickParse(unittest.TestCase):
    """One parse per outlet: the row reader reads a fixture page, then the Python step builds items."""

    @classmethod
    def setUpClass(cls):
        cls.rows = run_node("click_parse_check.mjs")

    def items(self, outlet):
        crawler = make_crawler({f"https://{u.split('/')[2]}/robots.txt": [(200, {}, b"User-agent: *\nDisallow: /private/\n")]
                                for u in FEEDS[outlet]["click_route"]["urls"]})
        with mock.patch("tools.newsfetch.lists.datetime") as dt:
            dt.datetime.now.return_value = NOW
            dt.timezone = datetime.timezone
            dt.timedelta = datetime.timedelta
            dt.date = datetime.date
            return lists.fetch_click_list(FEEDS[outlet]["click_route"], crawler, FEEDS[outlet]["publisher"], "2026-04-24", TODAY,
                                          browser=lambda url, ua, config: {"items": self.rows[outlet], "stop": "no_next", "steps": 1},
                                          sleep=lambda s: None)

    def check_outlet(self, outlet, first_date, second_date):
        rows = self.rows[outlet]
        self.assertEqual(len(rows), 2, outlet)
        for row in rows:
            self.assertTrue(row["title"].startswith("測試"), row)
            self.assertNotIn(LEAD, row["title"] + row["date"] + row["row"])
            self.assertLessEqual(len(row["title"]), 200)
        items = self.items(outlet)
        self.assertEqual([i["published_on"] for i in items][:2], [first_date, second_date], outlet)
        for item in items:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertNotIn("from=", item["url"])
            self.assertEqual(item["publisher"], FEEDS[outlet]["publisher"])
            self.assertEqual(item["summary"], "")

    def test_parse_udn(self):
        self.check_outlet("udn", "2026-09-20", "2026-09-20")

    def test_parse_cts(self):
        self.check_outlet("cts", "2026-09-20", "2026-09-20")

    def test_parse_chinatimes(self):
        self.check_outlet("chinatimes", "2026-09-20", "2026-09-20")

    def test_parse_mirror(self):
        self.check_outlet("mirror", "2026-09-20", "2026-09-19")

    def test_parse_pts(self):
        self.check_outlet("pts", "2026-09-20", "2026-09-19")

    def test_parse_cna(self):
        self.check_outlet("cna", "2026-09-20", "2026-09-20")

    def test_parse_ebc(self):
        self.check_outlet("ebc", "2026-09-20", "2026-09-20")

    def test_parse_tvbs_relative_labels(self):
        self.check_outlet("tvbs", "2026-10-26", "2026-10-25")

    def test_parse_setn_relative_labels_and_subdomain(self):
        self.check_outlet("setn", "2026-10-26", "2026-10-24")
        self.assertTrue(any("star.setn.com" in r["href"] for r in self.rows["setn"]))

    def test_parse_storm(self):
        self.check_outlet("storm", "2026-09-20", "2026-09-19")

    def test_parse_ftv(self):
        self.check_outlet("ftv", "2026-09-20", "2026-09-19")

    def test_setn_reads_the_desktop_headline_not_the_mobile_one(self):
        self.assertEqual(self.rows["setn"][0]["title"], "測試三立標題一")

    def test_cts_keeps_publisher_for_wire_rows(self):
        items = self.items("cts")
        self.assertTrue(any("/cna/" in i["url"] for i in items))
        self.assertTrue(all(i["publisher"] == FEEDS["cts"]["publisher"] for i in items))


class TestStopRulesAndRobots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = run_node("click_rules_check.mjs")

    def test_stop_rules(self):
        s = self.out["stops"]
        self.assertEqual(s["go"], "")
        self.assertEqual(s["date"], "date")
        self.assertEqual(s["dateMixed"], "")
        self.assertEqual(s["noRows"], "no_rows")
        self.assertEqual(s["noRowsLimit6"], "")
        self.assertEqual(s["noNext"], "no_next")
        self.assertEqual(s["maxSteps"], "max_steps")
        self.assertEqual(s["disallowed"], "disallowed")
        self.assertEqual(s["disallowedButRows"], "")
        self.assertEqual(s["captcha"], "captcha")
        self.assertEqual(s["cap"], "cap")

    def test_date_labels(self):
        d = self.out["dates"]
        self.assertEqual(d["iso"], "2026-09-05")
        self.assertEqual(d["isoT"], "2026-09-20")
        self.assertEqual(d["hours"], "2026-10-26")
        self.assertEqual(d["days"], "2026-10-24")
        self.assertEqual(d["yesterday"], "2026-10-25")
        self.assertEqual(d["none"], "")

    def test_block_pages(self):
        b = self.out["blocked"]
        self.assertTrue(b["captchaTitle"])
        self.assertTrue(b["cloudflare"])
        self.assertTrue(b["status403"])
        self.assertFalse(b["normal"])

    def test_robots_rules_longest_match_and_named_group(self):
        r = self.out["rules"]
        self.assertFalse(r["namedBlocks"])
        self.assertTrue(r["namedAllowsApi"], "a group that names our token wins over *")
        self.assertFalse(r["namedBlocksJsonEnd"])
        self.assertTrue(r["namedAllowsJsonQuery"])
        self.assertFalse(r["starBlocksApi"])
        self.assertTrue(r["starLongestAllow"])
        self.assertFalse(r["starBlocksSearch"])
        self.assertTrue(r["starAllowsList"])

    def test_every_request_is_checked_per_host_and_fails_closed(self):
        c = self.out["checks"]
        self.assertTrue(c["aList"])
        self.assertFalse(c["aApi"], "a disallowed path is aborted")
        self.assertFalse(c["aApi2"])
        self.assertTrue(c["bAny"], "404 allows")
        for host in ("cAny", "dAny", "eAny"):
            self.assertFalse(c[host], f"{host}: 503, a thrown error and a redirect disallow all")
        self.assertEqual(self.out["reads"], ["a.test", "b.test", "c.test", "d.test", "e.test"], "one robots.txt read per host")
        self.assertEqual(self.out["aborts"]["a.test"], 2)

    def test_helper_checks_robots_before_the_gate_and_before_continue(self):
        script = (BASE / "list_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("from './robots_rules.mjs'", script)
        self.assertLess(script.index("guard.check(target)"), script.index("gate.admit(u.hostname"))
        self.assertLess(script.index("gate.admit(u.hostname"), script.index("route.continue("))
        self.assertIn("ROBOTS-ABORT", script)
        self.assertEqual(script.count("route.continue("), 1)


class TestClickRunner(unittest.TestCase):
    """fetch_click_list: robots on the start url, one browser process per url, reports."""

    ROUTE = {"urls": ["https://x.test/a", "https://x.test/b"], "rows": "li", "link": "x\\.test/n/\\d+", "title_selector": "a",
             "date_selector": "time", "next": "a.next", "max_steps": 5}

    def crawler(self, robots):
        return make_crawler({"https://x.test/robots.txt": [robots]})

    def result(self, n):
        return {"items": [{"href": f"https://x.test/n/{n}", "title": f"測試標題數字{n}", "date": "2026-09-0%d 10:00" % n, "row": "", "hint": ""}],
                "stop": "date", "steps": 3, "oldest": "2026-09-0%d" % n, "robots_aborts": {"x.test": 1}, "min_gap_ms": 1100}

    def test_one_process_per_url_with_a_pause_between_them(self):
        pauses, calls = [], []

        def browser(url, ua, config):
            calls.append((url, config))
            return self.result(len(calls))

        reports = []
        items = lists.fetch_click_list(self.ROUTE, self.crawler((200, {}, b"User-agent: *\nDisallow: /api/\n")), "測試報", "2026-04-24", TODAY,
                                       browser=browser, sleep=pauses.append, reports=reports)
        self.assertEqual([c[0] for c in calls], self.ROUTE["urls"])
        self.assertEqual(pauses, [2.0])
        self.assertEqual(len(items), 2)
        self.assertEqual(calls[0][1]["mode"], "click")
        self.assertEqual(calls[0][1]["stop_before"], "2026-04-24")
        self.assertTrue(any("api" in d for d in calls[0][1]["deny"]))
        self.assertEqual([r["stop"] for r in reports], ["date", "date"])
        self.assertEqual(reports[0]["robots_aborts"], {"x.test": 1})
        self.assertEqual(reports[0]["items"], 1)

    def test_browser_does_not_start_when_robots_denies_the_start_url(self):
        browser = mock.Mock()
        reports = []
        items = lists.fetch_click_list(self.ROUTE, self.crawler((200, {}, b"User-agent: *\nDisallow: /\n")), "測試報", "2026-04-24", TODAY,
                                       browser=browser, sleep=lambda s: None, reports=reports)
        self.assertEqual(items, [])
        browser.assert_not_called()
        self.assertEqual([r["stop"] for r in reports], ["disallowed", "disallowed"])

    def test_browser_does_not_start_when_robots_unreadable(self):
        browser = mock.Mock()
        items = lists.fetch_click_list(self.ROUTE, self.crawler((500, {}, b"")), "測試報", "2026-04-24", TODAY, browser=browser, sleep=lambda s: None)
        self.assertEqual(items, [])
        browser.assert_not_called()

    def test_rows_without_a_date_and_duplicate_urls_are_dropped(self):
        rows = [{"href": "https://x.test/n/1?utm_source=a", "title": "測試標題數字一", "date": "2026-09-01 10:00"},
                {"href": "https://x.test/n/1", "title": "測試標題數字一", "date": "2026-09-01 10:00"},
                {"href": "https://x.test/n/2", "title": "測試標題數字二", "date": "熱門"}]
        route = dict(self.ROUTE, urls=["https://x.test/a"])
        items = lists.fetch_click_list(route, self.crawler((200, {}, b"User-agent: *\n")), "測試報", "2026-04-24", TODAY,
                                       browser=lambda u, a, c: {"items": rows, "stop": "no_next"}, sleep=lambda s: None)
        self.assertEqual([i["url"] for i in items], ["https://x.test/n/1"])

    def test_a_failed_browser_run_keeps_the_rows_saved_on_the_way(self):
        import os
        import subprocess as sp
        tmp = tempfile.mkdtemp()
        seen = {}

        def browser(url, ua, config):
            seen.update(config)
            Path(config["partial"]).write_text(json.dumps({"items": self.result(1)["items"]}), encoding="utf-8")
            raise sp.TimeoutExpired("node", 1)

        reports = []
        route = dict(self.ROUTE, urls=["https://x.test/a"])
        with mock.patch.dict(os.environ, {"NEWSFETCH_CLICK_PARTIAL_DIR": tmp}):
            items = lists.fetch_click_list(route, self.crawler((200, {}, b"User-agent: *\n")), "測試報", "2026-04-24", TODAY, browser=browser,
                                           sleep=lambda s: None, reports=reports)
        self.assertEqual(len(items), 1)
        self.assertEqual(reports[0]["stop"], "error")

    def test_long_routes_set_their_own_time_limit(self):
        for outlet in ("udn", "cts", "chinatimes"):
            self.assertGreaterEqual(FEEDS[outlet]["click_route"]["timeout_s"], 14400)

    def test_click_mode_skips_an_outlet_without_a_click_route(self):
        feed = {"id": "z", "publisher": "測試報", "type": "sitemap", "url": "https://x.test/s.xml"}
        crawler = self.crawler((200, {}, b"User-agent: *\n"))
        self.assertEqual(fetch_source_items(feed, crawler, route_mode="click"), [])
        self.assertEqual(crawler.calls, [])


class Handler(BaseHTTPRequestHandler):
    """A tiny list site on 127.0.0.1: pages with a next link, a page whose button calls a disallowed API, a CAPTCHA page."""

    log = []

    def log_message(self, *args):
        pass

    def page(self, body, title="測試列表"):
        data = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title></head><body>{body}</body></html>".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        Handler.log.append(self.path)
        path, _, query = self.path.partition("?")
        if path == "/robots.txt":
            data = b"User-agent: *\nDisallow: /api/\n"
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path == "/list":
            n = int(query.split("=")[1]) if query else 1
            day = {1: "2026-09-20", 2: "2026-09-15", 3: "2026-09-05", 4: "2026-09-01"}[n]
            rows = "".join(f'<li class="row"><a href="/n/{n}{k}">測試新聞{n}{k}</a><time datetime="{day} 1{k}:00">x</time></li>' for k in (0, 1))
            self.page(f'<ul>{rows}</ul><a class="next" href="/list?page={n + 1}">下一頁</a>')
        elif path == "/more":
            rows = '<li class="row"><a href="/n/90">測試新聞90</a><time datetime="2026-09-20 10:00">x</time></li>'
            script = "document.getElementById('more').onclick=()=>fetch('/api/more').then(r=>r.text())"
            self.page(f'<ul>{rows}</ul><button id="more">更多</button><script>{script}</script>')
        elif path == "/end":
            self.page('<ul><li class="row"><a href="/n/80">測試新聞80</a><time datetime="2026-09-20 10:00">x</time></li></ul>')
        elif path == "/captcha":
            self.page("<p>Verify you are human</p>", title="Please complete the CAPTCHA")
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()


class TestClickEngine(unittest.TestCase):
    """The real list_browser.mjs click mode against the local site. Each request is spaced 1.1 s, so the tests take a few seconds."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def run_route(self, path, **extra):
        log = Path(self.tmp.name) / f"requests-{path.strip('/').replace('?', '_')}.log"
        config = {"mode": "click", "rows": "li.row", "link": "/n/\\d+", "title_selector": "a", "date_selector": "time", "next": "a.next",
                  "max_steps": 10, "delay_ms": 1000, "settle_ms": 500, "wait_ms": 3000, "stop_before": "2026-09-10", "request_log": str(log)}
        config.update(extra)
        proc = subprocess.run(["node", str(BASE / "list_browser.mjs"), f"http://127.0.0.1:{self.port}{path}", "islandlog-newsfetch/0.1 (+test)", json.dumps(config)],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        return json.loads(proc.stdout.strip().splitlines()[-1]), log.read_text(encoding="utf-8") if log.exists() else ""

    def test_next_link_stops_when_rows_are_older_than_the_start_date(self):
        result, log = self.run_route("/list?page=1")
        self.assertEqual(result["stop"], "date")
        self.assertEqual(result["oldest"], "2026-09-05")
        self.assertEqual(len(result["items"]), 6)
        self.assertEqual([i["href"].rsplit("/", 1)[1] for i in result["items"]][:2], ["10", "11"])
        self.assertGreaterEqual(result["min_gap_ms"], 1100)
        self.assertIn("/robots.txt", log)

    def test_a_request_that_robots_disallows_is_aborted_and_stops_the_route(self):
        result, log = self.run_route("/more", next="#more")
        self.assertEqual(result["stop"], "disallowed")
        self.assertEqual(sum(result["robots_aborts"].values()), 1)
        self.assertIn("ROBOTS-ABORT /api/more", log)
        self.assertEqual([p for p in Handler.log if p.startswith("/api/")], [], "the server never saw the disallowed request")

    def test_no_next_control_stops_the_route(self):
        result, _ = self.run_route("/end")
        self.assertEqual(result["stop"], "no_next")
        self.assertEqual(len(result["items"]), 1)

    def test_captcha_page_stops_the_route(self):
        result, _ = self.run_route("/captcha")
        self.assertEqual(result["stop"], "captcha")
        self.assertEqual(result["items"], [])

    def test_request_cap_stops_the_route(self):
        result, _ = self.run_route("/list?page=1", request_cap=3, stop_before="2026-01-01")
        self.assertTrue(result["capped"])
        self.assertEqual(result["stop"], "cap")


if __name__ == "__main__":
    unittest.main()
