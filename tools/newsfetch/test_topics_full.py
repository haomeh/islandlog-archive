import unittest

from tools.newsfetch import topics_full as tf


def item(url, title, day, publisher="自由時報", cls="news", **extra):
    d = {"url": url, "title": title, "published_on": day, "publisher": publisher, "source_class": cls}
    d.update(extra)
    return d


class StableIdTest(unittest.TestCase):
    published = [{"id": "ev-20261023-topic-365f0f47", "title": "臺中市續放颱風假", "first": "2026-10-23", "last": "2026-10-24"}]

    def test_rebuilt_topic_keeps_the_published_id(self):
        got = tf.stable_id(self.published, "臺中市續放颱風假", "2026-10-22", "2026-10-24", "ev-20261022-topic-51b325e0")
        self.assertEqual(got, "ev-20261023-topic-365f0f47")

    def test_other_title_or_window_gets_the_new_id(self):
        new = "ev-20261022-topic-51b325e0"
        self.assertEqual(tf.stable_id(self.published, "高雄颱風假", "2026-10-23", "2026-10-24", new), new)
        self.assertEqual(tf.stable_id(self.published, "臺中市續放颱風假", "2026-12-01", "2026-12-03", new), new)


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

    def test_national_systems_count_as_taiwan(self):  # R84
        titles = ["長者健保費補助爭議　台灣前進陣線全台串連宣講", "藍議員問長者健保費中央買單？周春米：立法院要「精傱」一點啦",
                  "蘇巧慧支持中央補助長者健保費且全國一致", "《少康戰情室專訪》蘇巧慧：長者健保費補助 全國應一致"]
        self.assertTrue(tf.taiwan_relevant(titles))
        self.assertTrue(tf.taiwan_relevant(["勞保年金改革", "國民年金保費調漲", "衛福部說明"]))
        self.assertFalse(tf.taiwan_relevant(["美國醫保改革", "川普簽署醫保法案", "日本年金制度"]))

    def test_name_must_be_a_noun_phrase(self):  # R85
        for bad in ("總統府高層也在場", "總統府高層", "官員表示", "部長指出", "局長回應", "專家強調", "委員認為", "他透露", "名嘴坦言", "市府稱", "北市府說"):
            self.assertFalse(tf.noun_phrase_name(bad), bad)
        for good in ("長者健保費", "敬老卡", "薔琵颱風", "南崁溪淤積", "豎孤棚"):
            self.assertTrue(tf.noun_phrase_name(good), good)

    def test_next_candidate_is_tried_and_none_fails(self):  # R85
        from tools.newsfetch import topics as tp
        titles = ["颱風天燒千萬公帑「幫徐佳青辦慶生趴」？他再曝：總統府高層也在場",
                  "僑委會颱風天燒1492萬幫徐佳青慶生 凌濤再爆：多名總統府高層也在場"]
        corpus = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)] + \
                 [item(str(i), t, "2026-10-24") for i, t in enumerate(titles)]
        df = tp.document_frequency(corpus)
        key = tf.pick_noun_key(titles, df, len(corpus))
        self.assertTrue(key == "" or tf.noun_phrase_name(key), key)

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
            # A benign phrase only: the flag goes back to false.
            (Path(root) / "sources/2026/src-20261023-cna-aaaaaaaa.yaml").write_text(
                'title: "颱風期間醫院門診"\nquote: "為解決民眾就醫需求"\n', encoding="utf-8")
            self.assertEqual(tf.refresh_sensitive(root), ["ev-x"])
            self.assertIn("sensitive: false", ev.read_text(encoding="utf-8"))

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


class NationalSystemActorTest(unittest.TestCase):
    """R94: a national system in a title maps to its agency."""

    def actors(self, title):
        return tf.detect_gov_actors([title], ["jur-tw"])

    def test_each_system_maps_to_its_agency(self):
        cases = {"健保": "ac-ministry-of-health-and-welfare", "國民年金": "ac-ministry-of-health-and-welfare",
                 "勞保": "ac-ministry-of-labor", "勞退": "ac-ministry-of-labor"}
        for term, agency in cases.items():
            self.assertEqual(self.actors(f"長者{term}費 新制上路"), [agency], term)

    def test_a_real_title(self):
        self.assertIn("ac-ministry-of-health-and-welfare", self.actors("爸媽搬去子女家，健保費會取消嗎？"))


class RunHelper:
    EVENT_ID = "ev-20261023-topic-c8f31c28"

    def corpus(self, second_news_publisher):
        filler = [item(f"f{i}", f"無關新聞{i}號 氣象消息", "2026-10-20") for i in range(40)]
        topic = [item("a", "桃園市府會勘南崁溪淤積問題", "2026-10-23"),
                 item("b", "南崁溪石礫堆積 桃園市府將會勘", "2026-10-24", "聯合新聞網" if second_news_publisher else "自由時報"),
                 item("c", "【錯誤】南崁溪淤積謠言", "2026-10-24", "MyGoPen", "fact_check")]
        return filler + topic, topic

    def run_in(self, root, second_news_publisher, today="2026-10-25", seed_event=True):
        from tools.newsfetch import topics as tp
        corpus, topic = self.corpus(second_news_publisher)
        clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [t["url"] for t in topic]}]}]
        ids = [tp.src_id(t, tp.HOSTS) for t in topic]
        event = root / "events/2026" / f"{self.EVENT_ID}.md"
        if seed_event and not event.exists():
            event.parent.mkdir(parents=True)
            (root / "sources/2026").mkdir(parents=True)
            (root / "actors").mkdir()
            event.write_text(f"---\nid: {self.EVENT_ID}\nstatus: published\ntitle: 桃園市南崁溪\ntimeline:\n- date: '2026-10-23'\n"
                             f"  source_ids: [{ids[0]}]\n- date: '2026-10-24'\n  source_ids: [{ids[1]}, {ids[2]}]\n"
                             "review:\n  sensitive: false\n  reason: 'draft-review: 系統依爬取資料自動形成與命名，編輯尚未審閱。'\n"
                             "  status: draft-review\n---\n\n報導。\n", encoding="utf-8")
        stats, _, _ = tf.run(corpus, clusters, [], root, root / "report.json", today=today)
        return stats, event.read_text(encoding="utf-8")

    def records(self, root):
        import yaml
        return [yaml.safe_load(f.read_text(encoding="utf-8")) for f in sorted((root / "corrections").glob("*/cr-*.yaml"))]

    def event_doc(self, root):
        import yaml
        return yaml.safe_load((root / "events/2026" / f"{self.EVENT_ID}.md").read_text(encoding="utf-8").split("---\n")[1])

    def fail_twice(self, root, first="2026-10-25", second="2026-10-26"):
        """R107b: a published topic needs 2 failing runs in a row to be withdrawn."""
        self.run_in(root, second_news_publisher=False, today=first)
        return self.run_in(root, second_news_publisher=False, today=second)


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class WithdrawTest(RunHelper, unittest.TestCase):
    """R82: a published system topic that fails a gate in 2 runs in a row is withdrawn. Its file and id stay."""

    def test_a_topic_that_fails_a_gate_is_withdrawn_not_deleted(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            stats, text = self.fail_twice(Path(tmp))
            self.assertEqual(stats["rejected_news_rule"], 1)
            self.assertEqual(stats["withdrawn"], 1)
            self.assertIn("status: withdrawn", text)
            self.assertIn("reason: 'withdrawn: rejected_news_rule'", text.replace('"', "'"))
            self.assertIn(f"id: {self.EVENT_ID}", text)
            stats, again = self.run_in(Path(tmp), second_news_publisher=False, today="2026-10-27")  # a withdrawn topic stays as it is
            self.assertEqual(again, text)

    def test_a_withdrawal_writes_one_correction_record(self):
        import tempfile
        import yaml
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fail_twice(root, "2026-10-24", "2026-10-25")
            files = sorted((root / "corrections").glob("*/cr-*.yaml"))
            self.assertEqual([f.name for f in files], ["cr-20261025-01.yaml"])
            rec = yaml.safe_load(files[0].read_text(encoding="utf-8"))
            self.assertEqual((rec["made_by"], rec["gate"], rec["rule_id"], rec["type"]), ("tool", "rejected_news_rule", "R82", "withdrawal"))
            self.assertEqual((rec["target_ids"], rec["date"], "mr_url" in rec), ([self.EVENT_ID], "2026-10-25", False))
            doc = yaml.safe_load((root / "events/2026" / f"{self.EVENT_ID}.md").read_text(encoding="utf-8").split("---\n")[1])
            self.assertEqual(doc["correction_ids"], ["cr-20261025-01"])
            self.run_in(root, second_news_publisher=False, today="2026-10-26")  # a later run adds nothing
            self.assertEqual(len(list((root / "corrections").glob("*/cr-*.yaml"))), 1)

    def test_a_topic_that_passes_the_gates_is_not_withdrawn(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            stats, text = self.run_in(Path(tmp), second_news_publisher=True)
            self.assertEqual(stats["withdrawn"], 0)
            self.assertEqual(stats["published"], 1)
            self.assertIn("status: published", text)
            self.assertIn(self.EVENT_ID, text)

    def test_a_withdrawn_topic_that_still_fails_is_restored_from_git_without_a_new_record(self):
        import subprocess
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fail_twice(root, "2026-10-24", "2026-10-25")
            git = lambda *a: subprocess.run(["git", "-C", str(root), "-c", "user.email=a@b", "-c", "user.name=t", *a], check=True, capture_output=True)
            git("init", "-q")
            git("add", "-A")
            git("commit", "-qm", "base")
            before = (root / "events/2026" / f"{self.EVENT_ID}.md").read_text(encoding="utf-8")
            (root / "events/2026" / f"{self.EVENT_ID}.md").unlink()  # the rebuild step removes the file
            self.run_in(root, second_news_publisher=False, today="2026-10-26", seed_event=False)
            self.assertEqual((root / "events/2026" / f"{self.EVENT_ID}.md").read_text(encoding="utf-8"), before)
            self.assertEqual(len(self.records(root)), 1)

    def test_matching_published_needs_half_of_the_sources(self):
        published = [{"id": "ev-1", "src_ids": {"s1", "s2", "s3", "s4"}}, {"id": "ev-2", "src_ids": set()}]
        self.assertEqual(tf.matching_published(published, {"s1", "s2", "x"}), ["ev-1"])
        self.assertEqual(tf.matching_published(published, {"s1", "x"}), [])


REPO = __import__("pathlib").Path(__file__).resolve().parents[2]


class CorrectionTypeTest(unittest.TestCase):
    """R104: a tool withdrawal and a republication have their own correction types."""

    def test_schema_has_withdrawal_and_republication(self):
        import json
        enum = json.load(open(REPO / "schemas/correction.schema.json", encoding="utf-8"))["properties"]["type"]["enum"]
        self.assertIn("withdrawal", enum)
        self.assertIn("republication", enum)

    def test_tool_records_use_a_status_type(self):
        import yaml
        files = sorted((REPO / "corrections").glob("*/cr-*.yaml"))
        self.assertTrue(files)
        for f in files:
            rec = yaml.safe_load(f.read_text(encoding="utf-8"))
            if rec["made_by"] == "tool":
                self.assertIn(rec["type"], ("withdrawal", "republication"), f.name)


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class StatusRecordsTest(RunHelper, unittest.TestCase):
    """R105: every status change of a published id writes a record, in both directions."""

    def test_republication_writes_a_record_and_keeps_the_withdrawal_link(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fail_twice(root, "2026-10-24", "2026-10-25")  # published -> withdrawn
            self.assertEqual(self.event_doc(root)["status"], "withdrawn")
            self.run_in(root, second_news_publisher=True, today="2026-10-26")  # withdrawn -> published
            doc = self.event_doc(root)
            self.assertEqual(doc["status"], "published")
            recs = self.records(root)
            self.assertEqual([(r["type"], r["date"], r["made_by"]) for r in recs],
                             [("withdrawal", "2026-10-25", "tool"), ("republication", "2026-10-26", "tool")])
            self.assertEqual(doc["correction_ids"], [r["id"] for r in recs])
            self.assertEqual(recs[1]["target_ids"], [self.EVENT_ID])
            self.run_in(root, second_news_publisher=True, today="2026-10-27")  # no change: no record
            self.assertEqual(len(self.records(root)), 2)

    def test_a_second_withdrawal_after_republication_writes_a_new_record(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fail_twice(root, "2026-10-23", "2026-10-24")
            self.run_in(root, second_news_publisher=True, today="2026-10-26")
            self.fail_twice(root, "2026-10-27", "2026-10-28")  # R107b: the second fail withdraws
            self.assertEqual([r["type"] for r in self.records(root)], ["withdrawal", "republication", "withdrawal"])
            self.assertEqual(len(self.event_doc(root)["correction_ids"]), 3)

    def test_a_rebuilt_published_topic_keeps_its_correction_ids(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=True, today="2026-10-25")
            path = root / "events/2026" / f"{self.EVENT_ID}.md"
            path.write_text(path.read_text(encoding="utf-8").replace("review:\n", "correction_ids:\n- cr-20260101-01\nreview:\n", 1), encoding="utf-8")
            self.run_in(root, second_news_publisher=True, today="2026-10-26")
            self.assertEqual(self.event_doc(root)["correction_ids"], ["cr-20260101-01"])

    def test_the_back_filled_records_of_the_typhoon_holiday_topic(self):
        import yaml
        text = (REPO / "events/2026/ev-20261023-topic-82b85c15.md").read_text(encoding="utf-8")
        ids = yaml.safe_load(text.split("---\n")[1])["correction_ids"]
        recs = [yaml.safe_load((REPO / "corrections/2026" / f"{i}.yaml").read_text(encoding="utf-8")) for i in ids]
        self.assertEqual([r["type"] for r in recs], ["withdrawal", "republication"])
        self.assertEqual(recs[0]["gate"], "rejected_source_rule")
        self.assertTrue(all(r["target_ids"] == ["ev-20261023-topic-82b85c15"] for r in recs))


@unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "the writer needs PyYAML")
class HysteresisTest(RunHelper, unittest.TestCase):
    """R107b: a published topic is withdrawn only when it fails the gates in 2 runs in a row."""

    def state(self, root):
        import json
        p = root / "tools/newsfetch/topic_state.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def test_one_fail_keeps_the_topic_published(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats, text = self.run_in(root, second_news_publisher=False)
            self.assertEqual(stats["withdrawn"], 0)
            self.assertEqual(stats["withdraw_pending"], 1)
            self.assertIn("status: published", text)
            self.assertEqual(self.records(root), [])
            self.assertEqual(self.state(root)[self.EVENT_ID], {"fails": 1, "gate": "rejected_news_rule", "day": "2026-10-25"})

    def test_two_fails_in_a_row_withdraw_with_a_record(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stats, text = self.fail_twice(root)
            self.assertEqual(stats["withdrawn"], 1)
            self.assertIn("status: withdrawn", text)
            self.assertEqual([r["type"] for r in self.records(root)], ["withdrawal"])
            self.assertEqual(self.records(root)[0]["date"], "2026-10-26")

    def test_fail_pass_fail_does_not_withdraw(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=False, today="2026-10-25")
            self.run_in(root, second_news_publisher=True, today="2026-10-26")
            self.assertEqual(self.state(root).get(self.EVENT_ID, {}).get("fails", 0), 0)
            stats, text = self.run_in(root, second_news_publisher=False, today="2026-10-27")
            self.assertEqual(stats["withdrawn"], 0)
            self.assertIn("status: published", text)
            self.assertEqual(self.records(root), [])


class ElectionCampaignGateTest(unittest.TestCase):
    """R106: campaign phrases that name no election word (對手陣營, 競辦) still count as campaign talk."""
    TITLES_7046975b = ["藍議員問長者健保費中央買單？周春米：立法院要「精傱」一點啦",
                       "長者健保費補助爭議　台灣前進陣線全台串連宣講",
                       "《少康戰情室專訪》蘇巧慧：長者健保費補助 全國應一致",
                       "蘇巧慧支持中央補助長者健保費且全國一致  對手陣營質疑「哪個才是蘇巧慧？」"]

    def items(self, titles):
        return [item(f"u{i}", t, "2026-10-21") for i, t in enumerate(titles)]

    def test_campaign_phrases_match_the_gate(self):
        for t in ("蘇巧慧支持中央補助 對手陣營質疑", "競辦：長者健保費補助是政見", "競總成立 開票所會議", "參選人談長照政見"):
            self.assertTrue(tf.ELECTION.search(t), t)

    def test_a_topic_of_campaign_titles_is_excluded(self):
        titles = ["蘇巧慧支持長照新制 對手陣營質疑", "競辦回應長照政見", "長照政策爭議 競總說明", "長照補助新制上路"]
        self.assertEqual(tf.exclusion_reason(self.items(titles)), "election_campaign")

    def test_policy_titles_are_not_campaign_talk(self):
        for t in ("健保署說明長者健保費補助", "捷運站台門故障 政策陣營之爭？衛福部澄清", "行政院核定長照預算"):
            self.assertFalse(tf.ELECTION.search(t), t)

    def test_the_longer_health_fee_topic_stays_below_the_campaign_share(self):
        """1 of 4 titles is clear campaign talk (25%), under EXCLUDE_SHARE 0.3. The topic is not a campaign topic."""
        items = self.items(self.TITLES_7046975b)
        self.assertEqual(sum(1 for it in items if tf.ELECTION.search(it["title"])), 1)
        self.assertIsNone(tf.exclusion_reason(items))


class NameQualityTest(unittest.TestCase):
    """R112.2 and R112.4: a name that is only a place, a disease or a generic object fails. A noun phrase with a
    government body or a policy noun passes. Cases come from the precision sample T18-AP."""

    def good(self, key, titles):
        return tf.name_quality_ok(key, titles, len(titles), len(titles))

    def test_r112_2_a_disease_alone_is_not_a_name(self):
        titles = ["內政部：國人平均壽命81.7歲 排除惡性腫瘤可增3.2歲", "惡性腫瘤連44年居國人十大死因之首 內政部公布", "內政部：排除惡性腫瘤 國人平均壽命可提升"]
        self.assertFalse(self.good("惡性腫瘤", titles))

    def test_r112_2_a_district_alone_is_not_a_name(self):
        titles = ["臺南市安南區空地火警爆炸", "臺南市安南區爆炸 市府慰問", "臺南市安南區爆炸 消防局說明"]
        self.assertFalse(self.good("臺南市安南區", titles))
        self.assertFalse(self.good("安南區", titles))

    def test_r112_2_a_place_with_a_generic_object_is_not_a_name(self):
        titles = ["屏東縣恆春豎孤棚徵才？鎮公所澄清是詐騙", "恆春中元豎孤棚網傳假徵才 鎮公所澄清", "恆春豎孤棚目前不改期"]
        self.assertTrue(tf.generic_name("屏東縣豎孤棚"))
        self.assertFalse(self.good("豎孤棚", titles))

    def test_r112_2_a_generic_object_alone_is_not_a_name(self):
        titles = ["日本巡視船台海避風 海巡署籲中國勿製造假象", "日本巡視船來台避風遭海警尾隨", "日巡視船航行台海避颱風 海巡署回應"]
        self.assertFalse(self.good("巡視船", titles))

    def test_r112_2_a_named_facility_is_still_a_name(self):
        for key in ("淡江大橋", "金華國中", "大園親子館"):
            self.assertFalse(tf.generic_name(key), key)
            self.assertTrue(self.good(key, [f"{key}爭議 市府回應", f"{key}再爆議題", f"{key}完工"]), key)

    def test_r112_4_a_policy_noun_phrase_in_quotes_passes(self):
        titles = ["北市綠黨團要求建「議員索資公開平台」 蔣萬安回應了", "《北市》綠促設議員索資公開平台 藍也支持",
                  "北市議員提案建置「索資公開平台」 市府允3個月研議", "北市建置索資公開平台須3個月 議員不滿效率差"]
        self.assertTrue(self.good("索資公開平台", titles))

    def test_r112_4_a_quoted_remark_about_a_government_body_passes(self):
        titles = ["蔣萬安的局長脫口「廚餘給弱勢吃」被罵爆  律師轟：把人當豬？", "局長拋「廚餘給弱勢吃」？北市教育局澄清：沒有規劃",
                  "北市把營養午餐廚餘給弱勢團體？ 沈伯洋：發言很不恰當", "午餐廚餘給弱勢？ 北市教育局︰沒有規劃"]
        self.assertTrue(self.good("廚餘給弱勢", titles))

    def test_r112_4_a_policy_noun_with_two_titles_passes(self):
        titles = ["對抗民航重金挖角！空勤總隊留人才 每月獎助金最高10萬", "留住億元國家級飛航人才！ 空勤總隊飛航獎助金，最高調升至每月10萬元"]
        self.assertTrue(self.good("獎助金", titles))

    def test_r112_4_a_warning_of_a_ministry_passes(self):
        titles = ["不只高德地圖！數發部揭4款中製App共同風險：資料全傳回中國伺服器", "數發部示警 不只高德地圖 中國B站、愛奇藝等4款APP 恐偷個資",
                  "不只高德地圖！數發部示警4款中製App   B站、愛奇藝都上榜！"]
        self.assertTrue(self.good("不只高德地圖", titles))

    def test_a_fragment_without_a_policy_noun_or_body_still_fails(self):
        titles = ["他說不只這樣而已", "網友說不只這樣而已吧", "不只這樣而已 網友嘆"]
        self.assertFalse(self.good("不只這樣而已", titles))
        self.assertFalse(self.good("要的了在", titles))


class CentralActorTest(unittest.TestCase):
    def test_r112_4_the_national_security_bureau_is_an_actor(self):
        self.assertIn("ac-national-security-bureau", tf.detect_gov_actors(["國安局︰評估台日3大安全合作"], ["jur-tw"]))
        self.assertIn("ac-central-bank", tf.detect_gov_actors(["央行理監事會議維持利率不變"], ["jur-tw"]))


class ExclusionExceptionsTest(unittest.TestCase):
    def items(self, titles, **extra):
        return [item(f"u{i}", t, "2026-10-21", **extra) for i, t in enumerate(titles)]

    def test_r112_4_a_court_ruling_on_a_candidacy_is_not_campaign_content(self):
        titles = ["聲請暫准參選竹北市長遭北高行駁回　李貞秀：尊重司法", "李貞秀求暫准參選竹北市長　北高行駁回", "李貞秀遞狀聲請保「參選資格」 北高行駁回"]
        self.assertIsNone(tf.exclusion_reason(self.items(titles)))
        self.assertEqual(tf.exclusion_reason(self.items(["某某登記參選市長", "某某參選市長拜票", "某某參選造勢"])), "election_campaign")

    def test_r112_4_a_law_passed_by_the_legislature_is_not_sensitive_by_its_subject(self):
        titles = ["立院三讀毒駕或拒測一律吊銷駕照 致重傷死亡終身禁考照", "立院三讀道交條例》毒駕、拒毒測吊照 致重傷死亡終身禁考照"]
        self.assertIsNone(tf.exclusion_reason(self.items(titles, sensitive=True)))
        self.assertEqual(tf.exclusion_reason(self.items(["男子墜樓死亡", "少女輕生身亡"], sensitive=True)), "sensitive")

    def test_r112_5_a_cinema_discount_is_not_entertainment_news(self):
        self.assertIsNone(tf.exclusion_reason(self.items(["時代的眼淚！彰化人曬出「這張神卡」看電影現省百元"])))
        self.assertEqual(tf.exclusion_reason(self.items(["新電影首映 影帝出席", "電影票房破億"])), "entertainment")

    def test_r112_5_a_domestic_fraud_is_not_foreign(self):
        self.assertFalse(tf.taiwan_relevant(["清潔公司掛羊頭賣狗肉2-2》假洗冷氣真推銷 律師：恐涉加重詐欺未遂"]))
        self.assertFalse(tf.names_foreign(["清潔公司掛羊頭賣狗肉2-2》假洗冷氣真推銷 律師：恐涉加重詐欺未遂", "999洗冷氣進門不洗強推銷  民眾怒批受騙"]))
        self.assertTrue(tf.names_foreign(["美國宣布新關稅", "川普談關稅", "日本首相訪美"]))


class FailCountPerDayTest(RunHelper, unittest.TestCase):
    """R116: a topic gets at most one fail count per calendar day (Asia/Taipei)."""

    def state(self, root):
        import json
        return json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8"))

    def test_two_runs_on_the_same_day_add_one_count(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.run_in(root, second_news_publisher=False, today="2026-10-25")
            stats, text = self.run_in(root, second_news_publisher=False, today="2026-10-25")
            self.assertEqual(self.state(root)[self.EVENT_ID]["fails"], 1)
            self.assertEqual(stats["withdrawn"], 0)
            self.assertIn("status: published", text)
            stats, text = self.run_in(root, second_news_publisher=False, today="2026-10-26")
            self.assertEqual(stats["withdrawn"], 1)

    def test_the_default_day_is_the_taipei_day(self):
        from datetime import datetime, timezone
        self.assertEqual(tf.taipei_day(datetime(2026, 10, 25, 17, 0, tzinfo=timezone.utc)), "2026-10-26")
        self.assertEqual(tf.taipei_day(datetime(2026, 10, 25, 15, 59, tzinfo=timezone.utc)), "2026-10-25")


class TopicConfigTest(unittest.TestCase):
    """R107a: the thresholds live in topic_config.py, each with a comment."""

    def test_every_value_has_a_comment(self):
        import re
        src = (REPO / "tools/newsfetch/topic_config.py").read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(src):
            if re.match(r"^[A-Z_, ]+ = ", src[i]):
                block = [src[i]]
                while block[-1].count("{") > block[-1].count("}") or (len(block) > 1 and block[-1].count("{") == 0 and "}" not in "".join(block)):
                    i += 1
                    block.append(src[i])
                self.assertIn("#", "".join(block), src[i])
            i += 1

    def test_the_modules_use_the_config_values(self):
        from tools.newsfetch import topic_config as tc, topics as tp
        for name in ("ANCHOR_MAX_DF", "COMPANION_SHARE", "ONE_ISSUE_MIN_CORE", "RARE_KEY_SHARE"):
            self.assertEqual(getattr(tp, name), getattr(tc, name))
        for name in ("SAME_EVENT_SHARE", "EXCLUDE_SHARE", "MERGE_OVERLAP", "RELEVANCE_SHARE", "WITHDRAW_AFTER_FAILS"):
            self.assertEqual(getattr(tf, name), getattr(tc, name))

    # R117: a comparison with a number other than 0 and 1 in these functions is a size of text or of an argument list,
    # not a gate. Every other numeric comparison in the two modules must read its number from topic_config.py.
    STRUCTURAL = {("topics.py", "_is_person_or_speaker"), ("topics.py", "display_name"), ("topics.py", "_rare_grams"),
                  ("topics.py", "companion_terms"), ("topics.py", "build_event"), ("topics.py", "main"),
                  ("topics_full.py", "main"), ("topics_full.py", "window")}

    def numeric_comparisons(self, name):
        import ast
        tree = ast.parse((REPO / "tools/newsfetch" / name).read_text(encoding="utf-8"))
        found = []
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare):
                    for side in [node.left] + node.comparators:
                        if isinstance(side, ast.Constant) and type(side.value) in (int, float) and side.value not in (0, 1):
                            found.append((fn.name, node.lineno, ast.unparse(node)))
        return found

    def test_the_modules_define_no_threshold_of_their_own(self):
        import ast
        import re
        for name in ("topics.py", "topics_full.py"):
            text = (REPO / "tools/newsfetch" / name).read_text(encoding="utf-8")
            for const in ("ANCHOR_MAX_DF", "SPECIFIC_KEY_MIN", "COMPANION_SHARE", "ONE_ISSUE_SHARE", "SAME_EVENT_SHARE", "RELEVANCE_SHARE", "BAND"):
                self.assertIsNone(re.search(rf"^{const} *=", text, re.M), f"{name} defines {const}")
            for node in ast.parse(text).body:  # a module level number: PAPER_DAYS, PAPER_OVERLAP = 2, 0.5
                targets = [n.id for t in getattr(node, "targets", []) for n in ast.walk(t) if isinstance(n, ast.Name)]
                if targets and any(isinstance(n, ast.Constant) and type(n.value) in (int, float)
                                for n in (node.value.elts if isinstance(node.value, ast.Tuple) else [node.value])) \
                        and not all(n.startswith("MAX_") for n in targets):  # the display limits stay in topics.py
                    self.fail(f"{name}:{node.lineno} defines a number: {targets}")
            for fn, line, code in self.numeric_comparisons(name):
                if (name, fn) not in self.STRUCTURAL:
                    self.fail(f"{name}:{line} {fn} compares with a number of its own: {code}")

    def test_the_test_finds_a_gate_number(self):
        import tempfile
        src = "def meets(items):\n    return len(items) >= 2\n"
        with tempfile.TemporaryDirectory() as d:
            (__import__("pathlib").Path(d) / "tools/newsfetch").mkdir(parents=True)
            (__import__("pathlib").Path(d) / "tools/newsfetch/x.py").write_text(src, encoding="utf-8")
            global REPO
            old, REPO = REPO, __import__("pathlib").Path(d)
            try:
                self.assertEqual([c[0] for c in self.numeric_comparisons("x.py")], ["meets"])
            finally:
                REPO = old


if __name__ == "__main__":
    unittest.main()
