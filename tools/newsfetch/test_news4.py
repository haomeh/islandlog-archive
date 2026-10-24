"""Tests for the all-news scope: flags, privacy stripping and LTN breaking-news lists."""

import json
import unittest

from tools.newsfetch import fetch
from tools.newsfetch.classify import Classifier
from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.parser import mask_title, make_snippet, parse_ltn_ajax_json


class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.c = Classifier()

    def test_negative_topics(self):
        r = self.c.classify("國道火燒車釀2死 警方調查事故原因")
        self.assertTrue(r["negative"])
        self.assertIn("fire", r["topics"])
        self.assertIn("accident", r["topics"])
        self.assertFalse(r["clarification"])

    def test_clarification_and_negative_together(self):
        r = self.c.classify("食品業者澄清未使用過期原料 否認食安疑慮")
        self.assertTrue(r["clarification"])
        self.assertTrue(r["negative"])
        self.assertIn("food_safety", r["topics"])

    def test_plain_news_has_no_flags(self):
        r = self.c.classify("縣府公布今年度農業補助申請時程")
        self.assertEqual(
            r, {"negative": False, "topics": [], "clarification": False, "sensitive": False}
        )

    def test_sensitive(self):
        self.assertTrue(self.c.classify("男童遭家暴送醫")["sensitive"])
        self.assertTrue(self.c.classify("民宅陳屍 警方追查")["sensitive"])
        self.assertFalse(self.c.classify("立法院三讀通過預算")["sensitive"])


class TestScopeFilter(unittest.TestCase):
    def setUp(self):
        self.f = NewsFilter()

    def test_item_without_public_body_term_is_kept(self):
        keep, matched = self.f.should_keep("國道火燒車釀2死")
        self.assertTrue(keep)
        self.assertEqual(matched, [])

    def test_crime_news_is_kept_not_dropped(self):
        self.assertTrue(self.f.should_keep("民宅命案 警方偵辦")[0])

    def test_foreign_news_is_kept(self):
        self.assertTrue(self.f.should_keep("日本發生規模6地震")[0])

    def test_gossip_and_sports_still_dropped(self):
        for t in ("男星緋聞纏身 經紀公司道歉", "中職總冠軍賽開打", "羽球年終賽 戴資穎奪冠"):
            self.assertFalse(self.f.should_keep(t)[0], t)

    def test_matched_terms_still_whole_names(self):
        keep, matched = self.f.should_keep("立法院三讀 縣政府澄清")
        self.assertIn("立法院", matched)
        self.assertNotIn("法院", matched)


class TestVictimDetailStripping(unittest.TestCase):
    def test_age_removed(self):
        self.assertNotIn("歲", mask_title("45歲男子酒駕撞傷路人"))
        self.assertNotIn("歲", mask_title("年約30歲女子遭詐騙"))
        self.assertNotIn("歲", mask_title("女子(28歲)墜海失聯"))

    def test_name_with_age_masked(self):
        t = mask_title("王小明(35歲)墜海失聯")
        self.assertNotIn("王小明", t)
        self.assertIn("[當事人]", t)

    def test_name_before_victim_verb_masked(self):
        for raw, name in (("陳大文失聯三天", "陳大文"), ("林小華身亡 家屬發聲", "林小華"),
                          ("李美玲送醫不治", "李美玲")):
            self.assertNotIn(name, mask_title(raw), raw)

    def test_public_figure_kept(self):
        self.assertIn("蔣萬安", mask_title("蔣萬安回應爭議"))

    def test_place_word_not_masked(self):
        self.assertEqual(mask_title("金門漁船失聯 海巡出動"), "金門漁船失聯 海巡出動")

    def test_address_removed(self):
        t = mask_title("中山路123號住戶遭詐")
        self.assertNotIn("123號", t)
        self.assertIn("[地址]", t)
        t2 = make_snippet("嫌犯住在台北市大安區和平東路二段45巷3號5樓，遭逮")
        self.assertNotIn("45巷3號", t2)

    def test_workplace_removed(self):
        t = make_snippet("男子任職於某某科技公司，酒駕被逮")
        self.assertNotIn("某某科技", t)

    def test_medical_removed(self):
        t = make_snippet("女子罹患乳癌多年，遭詐團盯上")
        self.assertNotIn("乳癌", t)


class TestRecord(unittest.TestCase):
    def build(self, title, summary="", publisher="自由時報"):
        item = {"url": "https://x/1", "title": mask_title(title), "published_on": "2026-05-01",
                "snippet": make_snippet(summary or title), "summary": summary}
        return fetch.build_record(item, publisher, "2026-10-24T00:00:00Z", [], Classifier())

    def test_schema_keys(self):
        r = self.build("國道事故釀2死")
        self.assertEqual(
            set(r),
            {"url", "title", "publisher", "published_on", "snippet", "fetched_on", "matched_terms",
             "negative", "topics", "clarification", "sensitive", "source_class"},
        )
        self.assertEqual(r["source_class"], "news")
        self.assertTrue(r["negative"])

    def test_sensitive_item_snippet_is_title_only(self):
        r = self.build("男童遭家暴送醫", summary="王小明之子，住在中山路12號，在某某國小就讀，遭父親毆打")
        self.assertTrue(r["sensitive"])
        self.assertEqual(r["snippet"], r["title"])
        self.assertNotIn("中山路", json.dumps(r, ensure_ascii=False))

    def test_snippet_length(self):
        r = self.build("國道事故", summary="很長" * 200)
        self.assertLessEqual(len(r["snippet"]), 150)


AJAX = {
    "code": 200,
    "data": {
        "1": {"no": "1", "title": "國道追撞釀2死", "url": "https://news.ltn.com.tw/news/society/breakingnews/1",
              "time": "2026/10/23 11:48", "type_en": "society", "summary": "警方調查",
              "photo_S": "https://img/x.jpg"},
        "2": {"no": "2", "title": "立法院三讀", "url": "https://news.ltn.com.tw/news/politics/breakingnews/2",
              "time": "09:30", "type_en": "politics", "summary": ""},
    },
}


class TestLtnAjax(unittest.TestCase):
    def test_parse_dict_and_today_time(self):
        items = parse_ltn_ajax_json(json.dumps(AJAX).encode(), today="2026-10-24")
        self.assertEqual(len(items), 2)
        by_url = {i["url"][-1]: i for i in items}
        self.assertEqual(by_url["1"]["published_on"], "2026-10-23")
        self.assertEqual(by_url["2"]["published_on"], "2026-10-24")
        self.assertNotIn("photo_S", by_url["1"])

    def test_empty_and_bad_json(self):
        self.assertEqual(parse_ltn_ajax_json(b"not json", today="2026-10-24"), [])
        self.assertEqual(parse_ltn_ajax_json(b'{"code":200,"data":[]}', today="2026-10-24"), [])


class ListCrawler:
    def __init__(self, pages):
        self.pages = pages
        self.urls = []

    def fetch_raw(self, url, check_robots=True):
        self.urls.append(url)
        if "/ajax/breakingnews/" in url:
            cat, page = url.rsplit("/ajax/breakingnews/", 1)[1].split("/")
            body = self.pages.get((cat, int(page)))
            return json.dumps({"code": 200, "data": body}).encode() if body else None
        return None


class TestLtnListFetch(unittest.TestCase):
    CFG = {"id": "ltn", "publisher": "自由時報", "type": "ltn_search",
           "url": "https://search.ltn.com.tw/list", "list_categories": ["society"], "search_terms": []}

    def entry(self, i, day):
        return {"no": str(i), "title": f"事故{i}", "time": f"{day} 10:00",
                "url": f"https://news.ltn.com.tw/news/society/breakingnews/{i}", "summary": ""}

    def test_list_stops_when_page_older_than_since(self):
        pages = {
            ("society", 1): {"1": self.entry(1, "2026/10/24")},
            ("society", 2): {"2": self.entry(2, "2026/10/20")},
            ("society", 3): {"3": self.entry(3, "2026/10/10")},
            ("society", 4): {"4": self.entry(4, "2026/10/09")},
        }
        c = ListCrawler(pages)
        items = fetch.fetch_source_items(self.CFG, c, since="2026-10-19", until="2026-10-24")
        # Page 3 is the first page older than since. The date filter in main drops its items.
        self.assertEqual(sorted(i["url"][-1] for i in items), ["1", "2", "3"])
        self.assertEqual(len([u for u in c.urls if "/ajax/" in u]), 3)

    def test_search_window_end_is_exclusive_next_day(self):
        c = ListCrawler({})
        cfg = dict(self.CFG, list_categories=[], search_terms=["事故"])
        fetch.fetch_source_items(cfg, c, since="2026-05-01", until="2026-05-03")
        self.assertTrue(any("start_time=20260501&end_time=20260504" in u for u in c.urls), c.urls)


if __name__ == "__main__":
    unittest.main()
