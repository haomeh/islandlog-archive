import unittest

from tools.newsfetch import topics_full as tf


def item(url, title, day, publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


class RulesTest(unittest.TestCase):
    def test_source_rule_needs_two_c_publishers_or_an_a_source(self):
        one = [item("a", "x", "2026-10-22"), item("b", "y", "2026-10-22")]
        two = one + [item("c", "z", "2026-10-22", publisher="中央通訊社")]
        check = [item("d", "【錯誤】z", "2026-10-22", publisher="MyGoPen", cls="fact_check")]
        record = [item("e", "公報", "2026-10-22", publisher="行政院", cls="official_record")]
        self.assertFalse(tf.meets_source_rule(one))
        self.assertTrue(tf.meets_source_rule(two))
        self.assertTrue(tf.meets_source_rule(one + check))
        self.assertTrue(tf.meets_source_rule(record))
        self.assertFalse(tf.meets_source_rule(one + [item("f", "新聞稿", "2026-10-22", "行政院", "official_statement")]))

    def test_jurisdiction_from_place_names(self):
        titles = ["北市金華國中午餐爭議", "台北市教育局回應金華國中", "金華國中校長道歉"]
        self.assertEqual(tf.detect_jurisdictions(titles), ["jur-63000000"])
        self.assertEqual(tf.detect_jurisdictions(["颱風來襲 全台停班課", "政院督導防颱"]), ["jur-tw"])
        self.assertEqual(tf.detect_jurisdictions(["台北港凸堤效應波及桃園", "桃園南崁溪淤積"]), ["jur-68000000", "jur-65000000"])

    def test_gov_actors_from_titles(self):
        actors = tf.detect_gov_actors(["北市府回應金華國中午餐", "衛福部說明"], ["jur-63000000"])
        self.assertIn("ac-taipei-city-government", actors)
        self.assertIn("ac-ministry-of-health-and-welfare", actors)
        self.assertEqual(tf.detect_gov_actors(["藝人演唱會門票秒殺"], ["jur-tw"]), [])

    def test_exclusions(self):
        crime = [item(str(i), f"嫌犯{i}遭聲押", "2026-10-22") for i in range(4)]
        self.assertEqual(tf.exclusion_reason(crime), "criminal_case")
        sens = [item(str(i), f"新聞{i}", "2026-10-22", sensitive=True) for i in range(3)] + [item("x", "y", "2026-10-22")]
        self.assertEqual(tf.exclusion_reason(sens), "sensitive")
        vote = [item(str(i), f"某某登記參選市長{i}", "2026-10-22") for i in range(3)]
        self.assertEqual(tf.exclusion_reason(vote), "election_campaign")
        ok = [item("a", "北市府回應行道樹爭議", "2026-10-22")]
        self.assertIsNone(tf.exclusion_reason(ok))

    def test_extend_to_boundary(self):
        titles = ["密室逃脫大稽查20家", "台中密室逃脫大稽查", "密室逃脫大稽查有缺失"]
        self.assertEqual(tf.extend_to_boundary("脫大稽查", titles), "密室逃脫大稽查")
        self.assertEqual(tf.extend_to_boundary("萬里溪", ["花蓮萬里溪堰塞湖", "萬里溪橋封閉", "台9線萬里溪"]), "萬里溪")

    def test_name_quality(self):
        self.assertTrue(tf.name_ok("豎孤棚", total_df=3, window_df=3))
        for bad in ("洋流要來", "臨時停", "幫徐佳", "發生規模", "拚今晚全", "和平不能", "釀北市"):
            self.assertFalse(tf.name_ok(bad, total_df=5, window_df=5), bad)
        self.assertFalse(tf.name_ok("闢謠", total_df=266, window_df=40))
        self.assertFalse(tf.name_ok("台北市長", total_df=300, window_df=40))
        self.assertTrue(tf.name_ok("薔琵颱風", total_df=1100, window_df=1100))

    def test_word_boundary(self):
        df = {"演習": 300, "演練": 250, "卡加": 3, "卡改": 2, "杜總": 1}
        self.assertFalse(tf.has_word_boundary("降速演", ["NCC降速演習測試", "降速演練今登場", "降速演習 數位主權"], df))
        self.assertTrue(tf.has_word_boundary("敬老卡", ["新北敬老卡加值", "敬老卡改制 長者不滿"], df))
        self.assertTrue(tf.has_word_boundary("萬那杜", ["萬那杜總理訪台", "外交部：萬那杜 關係穩定"], df))
        self.assertFalse(tf.has_word_boundary("辦理退", ["通知辦理退稅", "速辦理退費", "辦理退稅流程"], df))

    def test_slogan_place_and_left_fragment(self):
        self.assertTrue(tf.is_quoted_slogan("玩百姓很好玩", ["台東縣府「玩百姓很好玩」？", "議員批「玩百姓很好玩」"]))
        self.assertFalse(tf.is_quoted_slogan("敬老卡", ["新北敬老卡加值"]))
        self.assertTrue(tf.is_place_name("鳳林鎮"))
        self.assertFalse(tf.has_word_boundary("雄月子中心", ["高雄月子中心停電", "高雄月子中心颱風", "高雄月子中心說明"]))

    def test_party_and_speaker_names_are_rejected(self):
        self.assertTrue(tf.is_person_or_party("國民黨", ["國民黨團提案"]))
        self.assertTrue(tf.is_person_or_party("蘇巧慧", ["蘇巧慧：支持", "蘇巧慧回應"]))
        self.assertFalse(tf.is_person_or_party("敬老卡", ["敬老卡加值"]))

    def test_taiwan_relevance(self):
        self.assertFalse(tf.taiwan_relevant(["西藏那曲地震", "那曲震災死傷", "外交部慰問"]))
        self.assertTrue(tf.taiwan_relevant(["新北敬老卡改制", "新北市府說明", "長者不滿"]))

    def test_sensitive_terms_from_taxonomy(self):
        self.assertTrue(tf.has_sensitive_term(["確保國人出入平安及就醫權益"]))
        self.assertFalse(tf.has_sensitive_term(["餵豬罰鍰提高"]))

    def test_news_rule_needs_two_news_publishers(self):
        stats = [item("a", "統計", "2026-10-24", "內政部", "official_statement"), item("b", "統計2", "2026-10-24", "內政部", "official_statement")]
        self.assertFalse(tf.meets_news_rule(stats))
        one = [item("c", "x", "2026-10-24"), item("d", "y", "2026-10-24")]
        self.assertFalse(tf.meets_news_rule(one))
        self.assertFalse(tf.meets_news_rule([item("c", "x", "2026-10-24"), item("e", "【錯誤】x", "2026-10-24", "MyGoPen", "fact_check")]))
        self.assertTrue(tf.meets_news_rule(one + [item("f", "z", "2026-10-24", "中央通訊社")]))

    def test_sub_topic_links_to_the_older_topic(self):
        parent = {"id": "ev-typhoon", "start": "2026-10-21", "end": "2026-10-24", "jurisdictions": ["jur-tw", "jur-64000000"],
                  "key": "薔琵", "titles": ["薔琵颱風逼近"] * 5}
        child = {"id": "ev-dayoff", "start": "2026-10-23", "end": "2026-10-23", "jurisdictions": ["jur-66000000"], "key": "颱風假",
                 "titles": ["台中續放颱風假", "薔琵來襲 台中颱風假", "颱風假 市府宣布"]}
        other = {"id": "ev-oil", "start": "2026-07-01", "end": "2026-08-31", "jurisdictions": ["jur-tw"], "key": "中聯",
                 "titles": ["中聯油脂"]}
        self.assertEqual(tf.link_subtopics([parent, child, other]), {"ev-dayoff": "ev-typhoon"})
        child["titles"] = ["台中續放颱風假"] * 11  # under 10% mention 薔琵
        self.assertEqual(tf.link_subtopics([parent, child, other]), {})

    @unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
    def test_refresh_sensitive_reads_source_quotes(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "events/2026").mkdir(parents=True)
            (Path(root) / "sources/2026").mkdir(parents=True)
            (Path(root) / "sources/2026/src-20261023-cna-aaaaaaaa.yaml").write_text(
                'title: "颱風期間醫院門診"\nquote: "民眾可就近就醫"\n', encoding="utf-8")
            ev = Path(root) / "events/2026/ev-x.md"
            ev.write_text("---\nid: ev-x\nreview:\n  sensitive: false\n  reason: 'draft-review: 系統依爬取資料自動形成與命名，編輯尚未審閱。'\n"
                          "  status: draft-review\n---\n\n報導 [@src-20261023-cna-aaaaaaaa]。\n", encoding="utf-8")
            self.assertEqual(tf.refresh_sensitive(root), ["ev-x"])
            self.assertIn("sensitive: true", ev.read_text(encoding="utf-8"))

    def test_topic_id_is_stable_ascii(self):
        a = tf.topic_id("仁愛圓環", "2026-09-26", "https://example.com/1")
        self.assertEqual(a, tf.topic_id("仁愛圓環", "2026-09-26", "https://example.com/1"))
        self.assertRegex(a, r"^ev-20260926-topic-[0-9a-f]{8}$")

    def test_month_window_frequency(self):
        corpus = [item("a", "薔琵颱風來襲", "2026-10-22"), item("b", "薔琵颱風遠離", "2026-10-24"), item("c", "薔琵", "2026-05-01")]
        mf = tf.MonthFrequency(corpus)
        dfw = mf.window(tf._day("2026-10-15"), tf._day("2026-11-10"))
        self.assertEqual(dfw["薔琵颱風"], 2)
        self.assertEqual(dfw["薔琵"], 2)


if __name__ == "__main__":
    unittest.main()
