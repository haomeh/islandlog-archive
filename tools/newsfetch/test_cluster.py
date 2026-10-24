import unittest

import json
import random
import re
import tempfile
import time
from pathlib import Path

from tools.newsfetch.cluster import (
    as_news_groups, cluster_items, main, normalize_title, same_content,
)


FIXTURE = [
    {"url": "https://www.cna.com.tw/news/aipl/202508230199.aspx", "title": "核三重啟公投案投票率29.53%史上第3低　同意票破7成未過門檻", "publisher": "中央通訊社", "published_on": "2025-08-23", "snippet": "同意票未達投票權人總額1/4以上門檻，因此不通過。", "fixture": False},
    {"url": "https://news.example/a-pts", "title": "核三重啟公投案投票率29.53%史上第3低 同意票破7成未過門檻 - 公視新聞網", "publisher": "公視新聞網", "published_on": "2025-08-24", "snippet": "", "fixture": True},
    {"url": "https://news.example/a-clarify", "title": "核三重啟公投案投票率未過門檻中選會回應", "publisher": "中央通訊社", "published_on": "2025-08-25", "snippet": "", "fixture": True},
    {"url": "https://news.example/a-repeat", "title": "核三重啟公投案投票率未過門檻中選會說明", "publisher": "其他媒體", "published_on": "2025-08-26", "snippet": "", "fixture": True},
    {"url": "https://news.pts.org.tw/article/751042", "title": "《核管法》修正案三讀通過 核電廠最長可延役20年", "publisher": "公視新聞網", "published_on": "2025-05-13", "snippet": "運轉執照效期屆滿後，須再繼續運轉者。", "fixture": False},
    {"url": "https://www.ey.gov.tw/Page/9277F759E41CCD91/d2eb93ee-111f-40e5-a98e-390755b3321b", "title": "行政院尊重113年憲判字第9號判決結果 將配合判決內容行使憲法職權", "publisher": "行政院", "published_on": "2024-10-25", "snippet": "將配合判決內容行使憲法職權", "fixture": False},
]


def item(url, title, date, publisher="中央通訊社", fixture=True):
    return {"url": url, "title": title, "publisher": publisher,
            "published_on": date, "snippet": "", "fixture": fixture}


class ClusterTests(unittest.TestCase):
    def test_same_content_merges_and_prefers_pts_on_date_tie(self):
        items = [item("u-cna", "同一事件報導標題共同文字內容", "2025-01-01"),
                 item("u-pts", "同一事件報導標題共同文字內容 - 公視新聞網", "2025-01-01", "公視新聞網")]
        result = cluster_items(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["groups"]), 1)
        self.assertEqual(result[0]["groups"][0]["representative_url"], "u-pts")

    def test_different_content_stays_apart(self):
        result = cluster_items([item("u1", "核三重啟公投案投票率未過門檻", "2025-01-01"),
                                item("u2", "颱風豪雨造成花蓮道路中斷", "2025-01-01")])
        self.assertEqual(len(result), 2)

    def test_clarification_makes_a_new_group(self):
        result = cluster_items(FIXTURE[:3])
        self.assertEqual([g["kind"] for g in result[0]["groups"]], ["report", "clarification"])

    def test_repeat_after_clarification_joins_clarification_group(self):
        result = cluster_items(FIXTURE[:4])
        groups = result[0]["groups"]
        self.assertEqual(groups[1]["member_urls"], ["https://news.example/a-clarify", "https://news.example/a-repeat"])

    def test_cluster_id_uses_earliest_url(self):
        first = cluster_items(FIXTURE[:2])[0]["cluster_id"]
        second = cluster_items(list(reversed(FIXTURE[:2])))[0]["cluster_id"]
        self.assertEqual(first, second)

    def test_three_day_rule_is_inclusive(self):
        a = item("u1", "完全一樣的新聞報導標題內容", "2025-01-01")
        b = item("u2", "完全一樣的新聞報導標題內容", "2025-01-04")
        c = item("u3", "完全一樣的新聞報導標題內容", "2025-01-05")
        self.assertTrue(same_content(a, b))
        self.assertFalse(same_content(a, c))

    def test_fixture_has_thirty_items_and_notes_known_errors(self):
        self.assertEqual(len(FIXTURE_30), 30)
        self.assertTrue(any(x["case"] == "false-merge" for x in KNOWN_CASES))
        self.assertTrue(any(x["case"] == "false-split" for x in KNOWN_CASES))
        by_url = {entry["url"]: entry for entry in FIXTURE_30}
        self.assertTrue(same_content(by_url[KNOWN_CASES[0]["items"][0]], by_url[KNOWN_CASES[0]["items"][1]]))
        self.assertFalse(same_content(by_url[KNOWN_CASES[1]["items"][0]], by_url[KNOWN_CASES[1]["items"][1]]))


# The remaining fixture items are made-up near neighbors for threshold review.
FIXTURE_30 = FIXTURE + [
    item(f"https://fixture.example/{i}", title, date)
    for i, title, date in [
        (1, "核三重啟公投案投票率與投票結果中選會說明", "2025-08-24"),
        (2, "核三重啟公投案投票率未過門檻與投票結果中選會說明", "2025-08-24"),
        (3, "核三重啟公投案投票率未過門檻完整結果報告含各地區分析與歷史資料", "2025-08-24"),
    ] + [(i, f"核三重啟公投第{i}項結果與各界最新反應", f"2025-08-{20 + (i % 10):02d}") for i in range(4, 25)]
]
KNOWN_CASES = [
    {"case": "false-merge", "items": ["https://fixture.example/1", "https://fixture.example/2"], "reason": "Shared topic words can exceed the report threshold."},
    {"case": "false-split", "items": ["https://www.cna.com.tw/news/aipl/202508230199.aspx", "https://fixture.example/3"], "reason": "A short title can lower bigram Jaccard."},
]


class TopicUnionTest(unittest.TestCase):
    def test_topic_links_use_union_of_group_bigrams(self):
        def item(url, title, day):
            return {"url": url, "title": title, "publisher": "x", "published_on": day}

        items = [
            item("u1", "縣政府公布環評審查結果引發爭議", "2026-06-01"),
            item("u2", "縣政府公布環評審查結果引發爭議 居民反應", "2026-06-02"),
            item("u3", "環評審查結果居民提出異議", "2026-06-10"),
        ]
        self.assertEqual(len(cluster_items(items)), 1)


def make(url, title, day, publisher="x"):
    return {"url": url, "title": title, "publisher": publisher, "published_on": day}


A = "甲乙丙丁戊己庚辛壬癸"
B = "丙丁戊己庚辛壬癸子丑"
C = "戊己庚辛壬癸子丑寅卯"


class AnchorTests(unittest.TestCase):
    def test_chain_does_not_merge_into_one_report_group(self):
        result = cluster_items([make("u1", A, "2026-06-01"), make("u2", B, "2026-06-02"),
                                make("u3", C, "2026-06-03")])
        self.assertEqual(len(result), 1)
        self.assertEqual([g["member_urls"] for g in result[0]["groups"]], [["u1", "u2"], ["u3"]])
        self.assertEqual([g["kind"] for g in result[0]["groups"]], ["report", "report"])

    def test_date_window_is_measured_from_representative(self):
        items = [make(f"u{i}", A, d) for i, d in enumerate(["2026-06-01", "2026-06-03", "2026-06-05"])]
        groups = cluster_items(items)[0]["groups"]
        self.assertEqual([g["member_urls"] for g in groups], [["u0", "u1"], ["u2"]])

    def test_clarification_word_item_does_not_join_plain_report(self):
        items = [make("u1", A, "2026-06-01"), make("u2", A + "回應", "2026-06-01")]
        groups = cluster_items(items)[0]["groups"]
        self.assertEqual([g["kind"] for g in groups], ["report", "clarification"])


class ClarificationTests(unittest.TestCase):
    def test_lone_clarification_word_is_a_report(self):
        result = cluster_items([make("u1", "縣府澄清道路工程預算案", "2026-06-01")])
        self.assertEqual(result[0]["groups"][0]["kind"], "report")

    def test_first_group_is_never_clarification(self):
        items = [make("u1", A + "說明", "2026-06-01"), make("u2", C + "更正", "2026-06-02")]
        kinds = [g["kind"] for g in cluster_items(items)[0]["groups"]]
        self.assertEqual(kinds, ["report", "clarification"])


class NormalizeTests(unittest.TestCase):
    def test_publisher_suffixes_after_separators(self):
        for suffix in ["｜風傳媒", " | Newtalk新聞", " - 自由時報", "｜聯合新聞網", " | TVBS新聞網", " - TVBS"]:
            self.assertEqual(normalize_title("核三公投結果" + suffix), "核三公投結果", suffix)

    def test_brackets_removed_only_at_start(self):
        self.assertEqual(normalize_title("【快訊】[獨家]核三公投"), "核三公投")
        self.assertEqual(normalize_title("核三【重點】公投"), "核三重點公投")

    def test_nfkc(self):
        self.assertEqual(normalize_title("公投１２３％"), normalize_title("公投123%"))


class RobustnessTests(unittest.TestCase):
    def test_bad_date_is_skipped_with_warning(self):
        items = [make("u1", A, "2026-06-01"), make("u2", B, "not-a-date"), make("u3", B, None)]
        with self.assertLogs("tools.newsfetch.cluster", level="WARNING") as logs:
            result = cluster_items(items)
        self.assertEqual(len(logs.records), 2)
        self.assertEqual(result[0]["groups"][0]["member_urls"], ["u1"])

    def test_cluster_id_ignores_input_order(self):
        items = [make("u1", A, "2026-06-01"), make("u2", B, "2026-06-02"), make("u3", C, "2026-06-03")]
        self.assertEqual(cluster_items(items)[0]["cluster_id"], cluster_items(items[::-1])[0]["cluster_id"])

    def test_twenty_thousand_items_under_thirty_seconds(self):
        rng = random.Random(1)
        pool = [chr(0x4E00 + i) for i in range(600)]
        items = [make(f"https://x.example/{i}", "".join(rng.choices(pool, k=14)),
                      f"2026-{1 + (i % 120) // 30:02d}-{1 + i % 28:02d}")
                 for i in range(20000)]
        start = time.monotonic()
        cluster_items(items)
        self.assertLess(time.monotonic() - start, 30)


class NewsGroupsTests(unittest.TestCase):
    def setUp(self):
        self.items = [make("https://a.example/news/1", A, "2026-06-01"),
                      make("https://b.example/news/2", A, "2026-06-02"),
                      make("https://c.example/news/3", C + "回應", "2026-06-03")]

    def test_shape_and_mapping(self):
        clusters = cluster_items(self.items)
        groups, mapping = as_news_groups(clusters, self.items)
        self.assertEqual([g["id"] for g in groups[0]["news_groups"]], ["ng-01", "ng-02"])
        first = groups[0]["news_groups"][0]
        self.assertEqual(first["source_ids"], ["https://a.example/news/1", "https://b.example/news/2"])
        self.assertEqual(first["kind"], "report")
        for url in (i["url"] for i in self.items):
            self.assertRegex(mapping[url], r"^src-[0-9]{8}-[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertEqual(len(set(mapping.values())), 3)
        self.assertTrue(mapping["https://b.example/news/2"].startswith("src-20260602-"))

    def test_main_writes_sources_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp, "in.jsonl"), Path(tmp, "out.json")
            src.write_text("\n".join(json.dumps(i, ensure_ascii=False) for i in self.items), encoding="utf-8")
            main([str(src), str(out), "--as-news-groups"])
            self.assertIn("news_groups", json.loads(out.read_text(encoding="utf-8"))[0])
            mapping = json.loads(Path(tmp, "out.json.sources.json").read_text(encoding="utf-8"))
            self.assertEqual(len(mapping), 3)


class SourceGroupTests(unittest.TestCase):
    TITLE = "行政院宣布調整電價方案內容說明重點"

    def mixed(self):
        official = item("https://ey.example/1", self.TITLE, "2026-06-01", "行政院")
        official["source_class"] = "official_statement"
        news = item("https://n.example/1", self.TITLE, "2026-06-01")
        return [official, news]

    def test_defaults(self):
        result = cluster_items(self.mixed())
        groups = {g["source_group"]: g for g in result[0]["groups"]}
        self.assertEqual(groups["official"]["kind"], "official")
        self.assertEqual(groups["news"]["kind"], "report")

    def test_official_record_defaults_to_official(self):
        record = item("https://ey.example/2", "公報紀錄標題", "2026-06-01")
        record["source_class"] = "official_record"
        self.assertEqual(cluster_items([record])[0]["groups"][0]["source_group"], "official")

    def test_explicit_source_group_wins(self):
        news = item("https://n.example/2", "某標題內容文字", "2026-06-01")
        news["source_class"] = "official_statement"
        news["source_group"] = "news"
        self.assertEqual(cluster_items([news])[0]["groups"][0]["kind"], "report")

    def test_never_merge_across_source_group(self):
        result = cluster_items(self.mixed())
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["groups"]), 2)

    def test_official_items_dedupe_among_themselves(self):
        a, b = self.mixed()[0], self.mixed()[0]
        b["url"] = "https://ey.example/2"
        groups = cluster_items([a, b])[0]["groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["member_urls"]), 2)

    def test_official_never_clarification(self):
        base = self.mixed()[0]
        later = dict(base, url="https://ey.example/9", title="行政院回應電價方案內容", published_on="2026-06-20")
        later["source_class"] = "official_statement"
        for group in cluster_items([base, later])[0]["groups"]:
            self.assertEqual(group["kind"], "official")

    def test_routine_propagation(self):
        a = item("https://n.example/a", self.TITLE, "2026-06-01")
        b = dict(a, url="https://n.example/b")
        a["routine"] = b["routine"] = True
        self.assertTrue(cluster_items([a, b])[0]["groups"][0]["routine"])
        b["routine"] = False
        self.assertNotIn("routine", cluster_items([a, b])[0]["groups"][0])

    def test_as_news_groups_keeps_kind_and_source_group(self):
        items = self.mixed()
        items[0]["routine"] = True
        groups, _ = as_news_groups(cluster_items(items), items)
        by_kind = {g["kind"]: g for g in groups[0]["news_groups"]}
        self.assertEqual(by_kind["official"]["source_group"], "official")
        self.assertTrue(by_kind["official"]["routine"])
        self.assertEqual(by_kind["report"]["source_group"], "news")
        self.assertNotIn("routine", by_kind["report"])


class PairingTests(unittest.TestCase):
    NEG = "某縣市工廠爆炸造成多人受傷消防局到場搶救"
    CLAR = "某縣市工廠爆炸消防局澄清起火原因"

    def negative(self, **extra):
        base = item("https://n.example/neg", self.NEG, "2026-06-01")
        base.update(source_class="news", negative=True, topics=["fire"], clarification=False, sensitive=False)
        base.update(extra)
        return base

    def official(self, **extra):
        base = item("https://gov.example/clar", self.CLAR, "2026-06-02", "消防局")
        base.update(source_class="official_statement", negative=False, topics=["accident"],
                    clarification=True, sensitive=False, routine=False)
        base.update(extra)
        return base

    def test_official_clarification_pairs_with_negative_news(self):
        result = cluster_items([self.negative(), self.official()])
        self.assertEqual(len(result), 1)
        kinds = {g["source_group"]: g["kind"] for g in result[0]["groups"]}
        self.assertEqual(kinds, {"news": "report", "official": "clarification"})
        self.assertTrue(result[0]["has_negative_and_clarification"])

    def test_fact_check_is_official_group_and_keeps_source_class(self):
        check = self.official(source_class="fact_check")
        group = [g for g in cluster_items([self.negative(), check])[0]["groups"]
                 if g["kind"] == "clarification"][0]
        self.assertEqual(group["source_group"], "official")
        self.assertEqual(group["source_class"], "fact_check")

    def test_news_clarification_needs_flag_and_word(self):
        clar = item("https://n.example/c", self.CLAR, "2026-06-02")
        clar.update(source_class="news", clarification=True, negative=False, topics=[], sensitive=False)
        groups = cluster_items([self.negative(), clar])[0]["groups"]
        self.assertEqual([g["kind"] for g in groups], ["report", "clarification"])
        clar["title"] = "某縣市工廠爆炸消防局公布搜救進度"
        groups = cluster_items([self.negative(), clar])[0]["groups"]
        self.assertNotIn("clarification", [g["kind"] for g in groups])

    def test_routine_official_is_not_clarification(self):
        plain = self.official(clarification=False)
        result = cluster_items([self.negative(), plain])
        self.assertEqual([g["kind"] for g in result[0]["groups"]], ["report", "official"])
        self.assertFalse(result[0]["has_negative_and_clarification"])

    def test_clarification_alone_has_no_pair(self):
        result = cluster_items([self.official()])
        self.assertFalse(result[0]["has_negative_and_clarification"])

    def test_flags_and_topics_propagate(self):
        second = self.negative(url="https://n.example/neg2", topics=["disaster"], negative=False,
                               sensitive=True)
        result = cluster_items([self.negative(), second, self.official()])[0]
        news = [g for g in result["groups"] if g["source_group"] == "news"][0]
        self.assertTrue(news["negative"])
        self.assertTrue(news["sensitive"])
        self.assertEqual(news["topics"], ["disaster", "fire"])
        self.assertTrue(result["negative"] and result["clarification"] and result["sensitive"])
        self.assertEqual(result["topics"], ["accident", "disaster", "fire"])

    def test_flags_default_to_false(self):
        result = cluster_items([item("u1", A, "2026-06-01")])[0]
        self.assertFalse(result["negative"] or result["clarification"] or result["sensitive"])
        self.assertEqual(result["topics"], [])

    def test_as_news_groups_carries_flags(self):
        items = [self.negative(sensitive=True), self.official()]
        out, _ = as_news_groups(cluster_items(items), items)
        self.assertTrue(out[0]["has_negative_and_clarification"])
        self.assertTrue(out[0]["sensitive"])
        entry = [g for g in out[0]["news_groups"] if g["kind"] == "clarification"][0]
        self.assertEqual(entry["source_class"], "official_statement")
        self.assertTrue(entry["clarification"])


if __name__ == "__main__":
    unittest.main()
