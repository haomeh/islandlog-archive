import unittest

from tools.newsfetch import topics


def item(url, title, day, publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


CORPUS = [
    item("https://news.ltn.com.tw/news/politics/breakingnews/1", "仁愛圓環6年對比「綠樹幾乎消失」！杜奕瑾質疑：這麼多棵同時得絕症？", "2026-09-26"),
    item("https://news.ltn.com.tw/news/life/breakingnews/2", "仁愛圓環6年對比「綠樹幾乎消失」？北市公園處回應了", "2026-09-26"),
    item("https://news.ltn.com.tw/news/life/paper/3", "杜奕瑾揭6年對比 仁愛圓環綠樹消失", "2026-09-27"),
    item("https://news.ltn.com.tw/news/life/breakingnews/4", "仁愛圓環樹木 杜奕瑾臉書PO文再質疑", "2026-09-29"),
    item("https://news.ltn.com.tw/news/life/breakingnews/5", "颱風來襲 北市公園處加強巡查", "2026-09-28"),
    item("https://news.ltn.com.tw/news/life/breakingnews/6", "北市公園處說明行道樹修剪原則", "2026-09-28"),
    item("https://news.ltn.com.tw/news/life/breakingnews/7", "北市公園處舉辦花展", "2026-09-20"),
    item("https://news.ltn.com.tw/news/life/breakingnews/8", "仁愛路車禍 機車騎士送醫", "2026-09-26"),
    item("https://www.ey.gov.tw/Page/1", "行政院說明仁愛圓環周邊交通", "2026-09-27", "行政院", "official_statement"),
]
SEED = {"event_id": "ev-20260926-taipei-renai-roundabout-trees", "seed_urls": [CORPUS[0]["url"], CORPUS[1]["url"]],
        "jurisdiction_names": ["臺北市"]}


class TopicTest(unittest.TestCase):
    def setUp(self):
        self.df = topics.document_frequency(CORPUS)

    def test_name_is_the_distinctive_phrase(self):
        key = topics.pick_key([CORPUS[0]["title"], CORPUS[1]["title"]], self.df, len(CORPUS))
        self.assertEqual(key, "仁愛圓環")

    def test_longer_phrase_wins_when_it_covers_the_same_seeds(self):
        corpus = [item(f"u{i}", t, "2026-05-12") for i, t in enumerate(
            ["淡江大橋通車首日", "淡江大橋機車道太窄", "淡江大橋祈福", "長江大橋觀光"])]
        df = topics.document_frequency(corpus)
        self.assertEqual(topics.pick_key([c["title"] for c in corpus[:3]], df, 60000), "淡江大橋")

    def test_generic_phrase_loses_to_specific_phrase(self):
        corpus = [item("a", "恆春中元豎孤棚網傳假徵才 鎮公所急澄清", "2026-07-12"),
                  item("b", "豎孤棚徵才？ 恆春鎮公所澄清是詐騙", "2026-07-13")]
        corpus += [item(f"g{i}", f"第{i}鄉鎮公所辦活動", "2026-07-01") for i in range(80)]
        df = topics.document_frequency(corpus)
        dfw = topics.window_frequency(corpus, topics._day("2026-07-05"), topics._day("2026-08-12"))
        self.assertEqual(topics.pick_key([corpus[0]["title"], corpus[1]["title"]], df, 60000, dfw=dfw), "豎孤棚")

    def test_title_adds_the_jurisdiction(self):
        self.assertEqual(topics.topic_title("仁愛圓環", ["臺北市"]), "臺北市仁愛圓環")
        self.assertEqual(topics.topic_title("臺北市仁愛圓環", ["臺北市"]), "臺北市仁愛圓環")
        self.assertEqual(topics.topic_title("薔琵颱風", ["高雄市"], national=True), "薔琵颱風")
        self.assertEqual(topics.topic_title("馬鈴薯", ["高雄市"], national=True, generic=True), "高雄市馬鈴薯")

    def test_generic_key_needs_a_place(self):
        corpus = [item("s1", "南投名間焚化爐環評會衝突", "2026-05-01"), item("s2", "南投焚化爐自救會抗爭", "2026-05-02"),
                  item("s3", "名間焚化爐自救會陳情", "2026-05-02"),
                  item("m1", "名間焚化爐環評再開會", "2026-05-03"), item("x1", "台中焚化爐歲修", "2026-05-03")]
        corpus += [item(f"g{i}", f"焚化爐新聞{i}", "2026-01-01") for i in range(30)]
        df = topics.document_frequency(corpus)
        seed = {"event_id": "e", "seed_urls": ["s1", "s2", "s3"], "jurisdiction_names": ["南投縣"], "jurisdiction_ids": ["jur-10008000"]}
        urls = {m["url"] for m in topics.members(seed, corpus, df)}
        self.assertIn("m1", urls)
        self.assertNotIn("x1", urls)  # another county's incinerator

    def test_members_share_the_key_and_window(self):
        members = topics.members(SEED, CORPUS, self.df)
        urls = {m["url"] for m in members}
        self.assertIn(CORPUS[3]["url"], urls)
        self.assertNotIn(CORPUS[7]["url"], urls)  # 仁愛路, not 仁愛圓環
        self.assertNotIn(CORPUS[4]["url"], urls)

    def test_kinds(self):
        self.assertEqual(topics.kind_of(CORPUS[0]), "report")
        self.assertEqual(topics.kind_of(CORPUS[1]), "clarification")
        self.assertEqual(topics.kind_of(CORPUS[3]), "post")
        self.assertEqual(topics.kind_of(CORPUS[8]), "official")
        self.assertEqual(topics.kind_of(item("u", "標題", "2026-09-26", quote="杜奕瑾在臉書PO出對比圖")), "post")

    def test_same_content_groups_merge_paper_copy(self):
        members = topics.members(SEED, CORPUS, self.df)
        groups = topics.group_items(members)
        news = [g for g in groups if g["kind"] != "official"]
        first = [g for g in news if CORPUS[0]["url"] in g["urls"]][0]
        self.assertEqual(first["kind"], "report")
        self.assertIn(CORPUS[2]["url"], first["urls"])  # the paper copy of item 0
        clar = [g for g in news if g["kind"] == "clarification"]
        self.assertEqual([g["urls"] for g in clar], [[CORPUS[1]["url"]]])

    def test_official_never_in_news_groups(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={"www.ey.gov.tw": ("行政院", "ac-executive-yuan", "ey")})
        group_urls = {u for g in event["news_groups"] for u in g["source_urls"]}
        self.assertNotIn(CORPUS[8]["url"], group_urls)
        self.assertTrue(all(g["kind"] in ("report", "clarification", "post") for g in event["news_groups"]))
        self.assertTrue(all(g.get("note") for g in event["news_groups"] if g["kind"] == "clarification"))

    def test_station_titles_are_neutral_counts(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={})
        for t in event["timeline"]:
            self.assertRegex(t["title"], r"^\d+ 則")
            self.assertNotIn("「", t["title"])

    def test_review_status_is_draft(self):
        event = topics.build_event(SEED, CORPUS, self.df, actors_by_host={})
        self.assertEqual(event["review"]["status"], "draft-review")
        self.assertEqual(event["title"], "臺北市仁愛圓環")


if __name__ == "__main__":
    unittest.main()
