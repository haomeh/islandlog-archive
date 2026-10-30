"""T64 tests: host rules (F-01, F-04), body cap (F-03). No network."""

import gzip
import io
import json
import subprocess
import unittest
from pathlib import Path

from unittest import mock

from tools.newsfetch import crawler as crawler_mod
from tools.newsfetch import netguard

BASE = Path(__file__).parent


def node_eval(expr):
    code = f"import * as g from {json.dumps((BASE / 'url_guard.mjs').as_uri())}; console.log(JSON.stringify({expr}))"
    proc = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(proc.stdout)


class UrlGuardMjsTest(unittest.TestCase):
    def test_registrable_domain_keeps_the_full_domain(self):
        self.assertEqual(node_eval("g.registrableDomain('news.ltn.com.tw')"), "ltn.com.tw")
        self.assertEqual(node_eval("g.registrableDomain('www.ftvnews.com.tw')"), "ftvnews.com.tw")
        self.assertEqual(node_eval("g.registrableDomain('udn.com')"), "udn.com")
        self.assertEqual(node_eval("g.registrableDomain('news.pts.org.tw')"), "pts.org.tw")

    def test_same_site_needs_a_dot_boundary(self):
        self.assertTrue(node_eval("g.sameSite('news.ltn.com.tw', 'ltn.com.tw')"))
        self.assertTrue(node_eval("g.sameSite('ltn.com.tw', 'ltn.com.tw')"))
        self.assertFalse(node_eval("g.sameSite('evil.com.tw', 'ltn.com.tw')"))
        self.assertFalse(node_eval("g.sameSite('evilltn.com.tw', 'ltn.com.tw')"))
        self.assertFalse(node_eval("g.sameSite('ltn.com.tw.evil.example', 'ltn.com.tw')"))

    def test_private_host_literals(self):
        for host in ("127.0.0.1", "10.1.2.3", "192.168.0.5", "172.16.0.1", "169.254.169.254", "localhost", "[::1]", "::ffff:127.0.0.1", "fe80::1", "0.0.0.0"):
            self.assertTrue(node_eval(f"g.isPrivateHostLiteral({json.dumps(host)})"), host)
        for host in ("news.ltn.com.tw", "8.8.8.8", "172.32.0.1"):
            self.assertFalse(node_eval(f"g.isPrivateHostLiteral({json.dumps(host)})"), host)

    def test_http_only(self):
        self.assertTrue(node_eval("g.isHttpUrl('https://a.example/x')"))
        self.assertFalse(node_eval("g.isHttpUrl('file:///etc/passwd')"))
        self.assertFalse(node_eval("g.isHttpUrl('ftp://a.example/')"))


class BrowserScriptsUseGuardTest(unittest.TestCase):
    def test_list_browser_has_no_suffix_match_on_two_labels(self):
        text = (BASE / "list_browser.mjs").read_text(encoding="utf-8")
        self.assertNotIn("slice(-2).join('.')", text)
        self.assertNotIn("u.hostname.endsWith(site)", text)
        self.assertIn("sameSite(u.hostname, site)", text)

    def test_article_browser_guards_every_request(self):
        text = (BASE / "article_browser.mjs").read_text(encoding="utf-8")
        self.assertIn("isHttpUrl", text)
        self.assertIn("isPrivateHostLiteral", text)


class NetguardTest(unittest.TestCase):
    def test_read_capped_refuses_a_large_body(self):
        self.assertEqual(netguard.read_capped(io.BytesIO(b"abc"), cap=3), b"abc")
        with self.assertRaises(netguard.BodyTooLarge):
            netguard.read_capped(io.BytesIO(b"abcd"), cap=3)

    def test_gunzip_capped_stops_a_bomb(self):
        bomb = gzip.compress(b"\0" * 5_000_000)
        self.assertLess(len(bomb), 20_000)
        self.assertEqual(len(netguard.gunzip_capped(bomb, cap=5_000_000)), 5_000_000)
        with self.assertRaises(netguard.BodyTooLarge):
            netguard.gunzip_capped(bomb, cap=1_000_000)

    def test_url_check_refuses_scheme_and_private_addresses(self):
        def resolver(addr):
            return lambda host, port, proto=0: [(2, 1, 6, "", (addr, port))]

        for url in ("file:///etc/passwd", "ftp://a.example/x", "gopher://a.example/"):
            with self.assertRaises(netguard.UnsafeUrl):
                netguard.check_public_url(url, resolve=resolver("93.184.216.34"))
        for addr in ("127.0.0.1", "10.0.0.8", "169.254.169.254", "192.168.1.1", "::1", "fe80::1", "::ffff:10.0.0.1"):
            with self.assertRaises(netguard.UnsafeUrl, msg=addr):
                netguard.check_public_url("https://a.example/x", resolve=resolver(addr))
        netguard.check_public_url("https://a.example/x", resolve=resolver("93.184.216.34"))

    def test_one_private_answer_among_public_ones_refuses(self):
        def resolver(host, port, proto=0):
            return [(2, 1, 6, "", ("93.184.216.34", port)), (2, 1, 6, "", ("127.0.0.1", port))]

        with self.assertRaises(netguard.UnsafeUrl):
            netguard.check_public_url("https://a.example/", resolve=resolver)


class FakeResp:
    def __init__(self, body, headers=None, status=200):
        self.fp = io.BytesIO(body)
        self.headers = headers or {}
        self.status = status

    def read(self, n=-1):
        return self.fp.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class CrawlerWiringTest(unittest.TestCase):
    def make(self, resp, public=True):
        crawler = crawler_mod.PoliteCrawler(cache_dir=Path(__import__("tempfile").mkdtemp()), rate_limit_interval=0)
        crawler._opener = mock.Mock()
        crawler._opener.open.return_value = resp
        check = mock.patch.object(netguard, "check_public_url", side_effect=None if public else netguard.UnsafeUrl("x"))
        check.start()
        self.addCleanup(check.stop)
        return crawler

    def test_http_get_refuses_a_body_over_the_cap(self):
        with mock.patch.object(netguard, "MAX_BODY_BYTES", 100), mock.patch.object(crawler_mod.netguard, "MAX_BODY_BYTES", 100):
            crawler = self.make(FakeResp(b"x" * 101))
            with self.assertRaises(netguard.BodyTooLarge):
                crawler._http_get("https://a.example/x")

    def test_http_get_refuses_a_gzip_bomb(self):
        with mock.patch.object(crawler_mod.netguard, "MAX_BODY_BYTES", 1000):
            crawler = self.make(FakeResp(gzip.compress(b"\0" * 5000), {"Content-Encoding": "gzip"}))
            with self.assertRaises(netguard.BodyTooLarge):
                crawler._http_get("https://a.example/x")

    def test_http_get_refuses_a_private_address_before_the_request(self):
        crawler = self.make(FakeResp(b"ok"), public=False)
        with self.assertRaises(netguard.UnsafeUrl):
            crawler._http_get("http://127.0.0.1/x")
        crawler._opener.open.assert_not_called()

    def test_a_refused_url_is_not_retried(self):
        crawler = self.make(FakeResp(b"ok"), public=False)
        with mock.patch("tools.newsfetch.crawler.time.sleep") as sleep:
            self.assertEqual(crawler._request_with_retry("http://127.0.0.1/x", "127.0.0.1"), (None, {}, b""))
        sleep.assert_not_called()
        self.assertEqual(crawler._opener.open.call_count, 0)

    def test_a_normal_body_passes(self):
        crawler = self.make(FakeResp(gzip.compress(b"hello"), {"Content-Encoding": "gzip"}))
        self.assertEqual(crawler._http_get("https://a.example/x")[2], b"hello")


class ArticleStepGuardTest(unittest.TestCase):
    def test_extract_refuses_a_private_url_before_the_browser(self):
        from tools.newsfetch import article

        class C:
            def load_robots(self, host, scheme="https"):
                raise AssertionError("robots must not load")

        calls = []
        step = article.ArticleStep(C(), browser=lambda u, ua: calls.append(u) or {})
        for url in ("file:///etc/passwd", "http://127.0.0.1/a", "http://169.254.169.254/latest"):
            self.assertEqual(step.extract(url)["status"], "url_refused", url)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
