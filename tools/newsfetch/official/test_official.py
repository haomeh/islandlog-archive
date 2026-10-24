"""Offline tests for the official fetcher. Run: python3 -m unittest discover -s tools/newsfetch/official"""

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import classify  # noqa: E402
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
        rec = fetch_official.build_record(src, item, "2026-10-24T00:00:00Z", classify.load_lexicons(HERE), {})
        self.assertIn("negative", rec)
        self.assertIn("[當事人]", rec["snippet"])
        self.assertLessEqual(len(rec["snippet"]), 150)


if __name__ == "__main__":
    unittest.main()


class MaskTests(unittest.TestCase):
    """F6 examples (origin: branch m1/news-fetch, test_rules.py)."""

    def test_name_before_verdict_word_masked(self):
        self.assertEqual(textutil.mask_title("新北市陳大文被控詐欺"), "新北市[當事人]被控詐欺")
        self.assertEqual(textutil.mask_title("王小明涉貪遭起訴"), "[當事人]涉貪遭起訴")

    def test_public_figure_kept(self):
        self.assertEqual(textutil.mask_title("蔣萬安遭質疑"), "蔣萬安遭質疑")
        self.assertEqual(textutil.mask_title("憂蔡康永遭跨境鎮壓加派警力"), "憂蔡康永遭跨境鎮壓加派警力")

    def test_false_positive_not_masked(self):
        self.assertEqual(textutil.mask_title("內政部：照顧民眾比較少"), "內政部：照顧民眾比較少")
        self.assertEqual(textutil.mask_title("內政部：照[當事人]比較少"), "內政部：照[當事人]比較少")

    def test_place_and_number_words_not_masked(self):
        for t in ("台大陸生被驅逐出境　陸委會：這只是個案", "地方選戰恐被國會攻防牽動",
                  "索賄370萬元涉貪 桃市經發局前科長"):
            self.assertEqual(textutil.mask_title(t), t)

    def test_snippet_uses_title_mask(self):
        self.assertEqual(textutil.make_snippet("王小明涉貪遭起訴"), "[當事人]涉貪遭起訴")

    def test_civilian_suffix_still_masked(self):
        self.assertEqual(textutil.mask_title("陳姓男子涉詐"), "[當事人]涉詐")


class RoutineTests(unittest.TestCase):
    def test_routine_words(self):
        for w in ("活動", "開幕", "表揚", "補助", "招募", "比賽", "市集", "展覽", "報名", "慶典"):
            self.assertTrue(fetch_official.is_routine(f"市府辦理{w}公告"), w)

    def test_not_routine(self):
        self.assertFalse(fetch_official.is_routine("行政院會通過預算案"))

    def test_record_has_routine_flag(self):
        src = {"publisher": "X", "source_class": "official_statement"}
        rec = fetch_official.build_record(src, {"url": "u", "title": "春季市集開幕", "published_on": "2026-05-01"}, "t", classify.load_lexicons(HERE), {})
        self.assertIs(rec["routine"], True)


class TitleAttrListTests(unittest.TestCase):
    def test_parse_anchor_with_inner_date(self):
        html_str = (FIX / "sample_titleattr_list.html").read_text(encoding="utf-8")
        items = listing.parse_titleattr_list(html_str, "https://www.ey.gov.tw/Page/6485009ABEC1CB9C")
        self.assertEqual([(i["title"], i["published_on"]) for i in items],
                         [("行政院會通過預算案", "2026-10-08"), ("頒獎表彰選手", "2026-09-24")])
        self.assertEqual(items[0]["url"], "https://www.ey.gov.tw/Page/9277F759E41CCD91/aaa-111")
        self.assertEqual(items[0]["summary"], "")



class ClassifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = classify.load_lexicons(HERE)

    def test_lexicon_shape(self):
        self.assertIn("topics", classify.json.loads((HERE / "negative_terms.json").read_text(encoding="utf-8")))
        self.assertIn("terms", classify.json.loads((HERE / "clarification_terms.json").read_text(encoding="utf-8")))
        self.assertIn("terms", classify.json.loads((HERE / "sensitive_terms.json").read_text(encoding="utf-8")))

    def test_negative_topics(self):
        r = classify.classify("工廠大火造成3人死亡", "", self.lex)
        self.assertTrue(r["negative"])
        self.assertIn("fire", r["topics"])

    def test_neutral_title(self):
        r = classify.classify("行政院會通過預算案", "", self.lex)
        self.assertFalse(r["negative"])
        self.assertEqual(r["topics"], [])
        self.assertFalse(r["clarification"])
        self.assertFalse(r["sensitive"])

    def test_clarification_term(self):
        self.assertTrue(classify.classify("疾管署澄清網傳疫苗訊息為錯誤訊息", "", self.lex)["clarification"])

    def test_feed_flag_forces_clarification(self):
        self.assertTrue(classify.classify("院會報告", "", self.lex, force_clarification=True)["clarification"])

    def test_sensitive_term(self):
        self.assertTrue(classify.classify("國中生輕生事件", "", self.lex)["sensitive"])
        self.assertTrue(classify.classify("男子涉性侵未成年少女", "", self.lex)["sensitive"])


class RedactTests(unittest.TestCase):
    def test_age_removed(self):
        self.assertNotIn("歲", textutil.redact_victim("35歲男子墜樓"))
        self.assertNotIn("歲", textutil.redact_victim("八十歲長者走失"))

    def test_address_removed(self):
        out = textutil.redact_victim("民權路100號3樓發生火警")
        self.assertNotIn("100號", out)
        self.assertIn("火警", out)

    def test_workplace_removed(self):
        self.assertNotIn("某某科技", textutil.redact_victim("任職於某某科技公司的員工受傷"))

    def test_plain_text_kept(self):
        self.assertEqual(textutil.redact_victim("行政院會通過預算案"), "行政院會通過預算案")


class RecordV2Tests(unittest.TestCase):
    LEX = None

    def rec(self, title, summary="", src=None, feed=None):
        lex = classify.load_lexicons(HERE)
        src = src or {"publisher": "X", "source_class": "official_statement"}
        item = {"url": "u", "title": title, "published_on": "2026-05-01", "summary": summary}
        return fetch_official.build_record(src, item, "t", lex, feed or {})

    def test_schema_fields(self):
        r = self.rec("行政院會通過預算案")
        self.assertEqual(
            sorted(r),
            sorted(["url", "title", "publisher", "published_on", "snippet", "fetched_on", "negative",
                    "topics", "clarification", "sensitive", "source_class", "routine"]),
        )

    def test_feed_clarification_flag(self):
        r = self.rec("院會報告", feed={"clarification": True})
        self.assertIs(r["clarification"], True)
        self.assertEqual(r["source_class"], "official_statement")

    def test_fact_check_class_and_no_routine(self):
        r = self.rec("【錯誤】網傳某事", src={"publisher": "TFC", "source_class": "fact_check"})
        self.assertEqual(r["source_class"], "fact_check")
        self.assertNotIn("routine", r)

    def test_snippet_title_only_when_requested(self):
        r = self.rec("標題文字測試", summary="全文內容很長" * 20, feed={"snippet": "title"})
        self.assertEqual(r["snippet"], "標題文字測試")

    def test_sensitive_item_uses_title_only_and_redacts(self):
        r = self.rec("35歲男子涉性侵", summary="受害者住民權路100號任職於某某公司")
        self.assertIs(r["sensitive"], True)
        self.assertNotIn("民權路", r["snippet"])
        self.assertNotIn("歲", r["title"])
        self.assertNotIn("歲", r["snippet"])

    def test_keeps_all_news_no_term_filter(self):
        r = self.rec("職棒球員全壘打")
        self.assertEqual(r["url"], "u")


class FeedFlagTests(unittest.TestCase):
    def test_sources_json_valid_and_flags(self):
        import json
        srcs = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
        ids = {s["id"] for s in srcs}
        self.assertTrue({"ey", "moi", "fda", "tfc", "mygopen"} <= ids)
        for s in srcs:
            for f in s.get("feeds", []):
                self.assertIn(f["type"], ("rss", "html_list", "titleattr_list"))
        tfc = next(s for s in srcs if s["id"] == "tfc")
        self.assertEqual(tfc["source_class"], "fact_check")
