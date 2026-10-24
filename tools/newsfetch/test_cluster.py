import unittest

from tools.newsfetch.cluster import cluster_items, same_content


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


if __name__ == "__main__":
    unittest.main()
