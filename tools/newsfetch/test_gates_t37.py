"""T37 gate round (R225.1, R229): rejected_no_public_act. 2 tests for each of the classes a (natural phenomenon), b (ceremony)
and c (public-power act). The titles are not in any judged list (R156)."""

import unittest

from tools.newsfetch import topics_full as tf


def items(titles, day="2026-10-21"):
    return [{"url": f"u{i}", "title": t, "published_on": day, "publisher": f"出版社{i % 2}", "source_class": "news"} for i, t in enumerate(titles)]


class NaturalPhenomenonTest(unittest.TestCase):
    """R229.2 a: an earthquake, weather, astronomy, animal or plant cluster with no public-power act title fails."""

    def test_earthquake_records_fail(self):
        titles = ["花蓮外海規模5.2地震 全台有感", "地震規模5.2 氣象署測得最大震度4級", "花蓮地震後餘震 氣象署統計次數"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_animal_and_plant_records_fail(self):
        titles = ["黑面琵鷺抵達七股 縣府表示歡迎", "賞鳥人潮湧入七股 黑面琵鷺現蹤 縣府觀察", "候鳥黑面琵鷺越冬 縣府記錄數量"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_weather_with_an_emergency_order_passes(self):
        titles = ["強颱逼近 縣府宣布停班停課", "颱風假爭議 市府說明停課決定", "颱風豪雨 縣府開設避難所"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))


class CeremonyTest(unittest.TestCase):
    """R229.2 b: a ceremony cluster with no public-power act title fails."""

    def test_opening_ceremony_fails(self):
        titles = ["河濱公園景觀橋剪綵 市府邀民眾拍照", "景觀橋啟用典禮 市府安排表演", "景觀橋剪綵儀式 市府貴賓到場"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_parade_and_festival_fail(self):
        titles = ["媽祖遶境遊行 縣府派員到場", "遊行隊伍開幕 縣府嘉年華直擊", "社區嘉年華遊行 縣府花車亮相"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_opening_with_a_subsidy_or_penalty_passes(self):
        titles = ["輕軌通車典禮 市府公布票價補貼", "輕軌啟用 交通局裁罰違規停車", "輕軌通車 交通部核定營運辦法"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))


class PublicPowerActTest(unittest.TestCase):
    """R229.2 c: a government decision, budget, law, ruling, penalty, subsidy or emergency order is an act. A remark is not."""

    def test_acts_are_found(self):
        for title in ("縣府公告停班停課", "立院三讀通過水庫條例", "法院裁定駁回聲請", "環保局開罰罰鍰十萬", "市府編列預算補助農民", "內政部核定疏散計畫", "市府宣布放颱風假", "縣府開設應變中心", "市府發放泡水機車慰助金", "鐵道局履勘新站"):
            self.assertTrue(tf.PUBLIC_POWER_ACT.search(title), title)

    def test_a_remark_is_no_act(self):
        for title in ("市長表示很關心", "氣象署說明地震成因", "專家呼籲民眾留意", "議員批評園區招牌"):
            self.assertFalse(tf.PUBLIC_POWER_ACT.search(title), title)

    def test_a_remark_only_cluster_fails(self):
        titles = ["地震頻傳 市長表示很關心", "地震規模5.0 氣象署說明成因", "地震後餘震 專家呼籲民眾留意"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_the_label_is_a_new_topic_only_label(self):
        self.assertIn("rejected_no_public_act", tf.NEW_TOPIC_ONLY)

    def test_an_old_topic_rebuild_goes_to_deferred(self):  # R205, R229.2d: the old topic gets no fail count, its re-gate decides
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock
        from tools.newsfetch.test_topics_full import RegateTest
        helper = RegateTest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus, seed, _ = helper.setup(root)
            clusters = [{"cluster_id": "c1", "news_groups": [{"source_ids": [it["url"] for it in corpus if it["url"].startswith("t")]}]}]
            real = tf.gate_topic
            calls = []

            def fake(*args, **kwargs):
                calls.append(args[0])
                return ("rejected_no_public_act", None) if len(calls) == 1 else real(*args, **kwargs)  # the re-gate of the old topic uses the real gate
            with mock.patch.object(tf, "gate_topic", fake):
                stats, published, _ = tf.run(corpus, clusters, [], root, root / "report.json", today="2026-10-25")
            self.assertEqual(stats["rejected_no_public_act"], 1)
            state = json.loads((root / "tools/newsfetch/topic_state.json").read_text(encoding="utf-8"))
            self.assertNotIn(helper.ID, state)


# R234.3: the words come from the class definitions (R234.4), one title per word. Each title matches by its own word only (R156).
ACT_WORD_TITLES = {  # R233.3: the 5 words that had no test, and 颱風假
    "驗收": "文化局驗收新圖書館 缺失限期改善",
    "勘查": "水利署赴現場勘查崩塌處",
    "查驗": "海關查驗進口貨櫃",
    "環評": "新電廠環評 專案小組今開會",
    "下令": "市長下令清查校舍",
    "颱風假": "縣府宣布明日颱風假",
}
EMERGENCY_WORD_TITLES = {  # R234.3c: emergency repair and penalty. No public body is needed in the title.
    "搶修": "電桿倒塌 台電連夜搶修",
    "搶通": "土石流阻斷山路 工務段連夜搶通",
    "罰單": "違規施放天燈 警方開出罰單",
    "處罰": "非法棄置廢土 業者遭處罰",
}
WORKS_WORD_TITLES = {  # R234.3a: a public body starts, tenders, sets a schedule or plans a rebuild
    "開工": "市府新校舍開工 預計兩年完成",
    "動工": "縣府動工拓寬農路",
    "發包": "縣府發包堤防新工",
    "決標": "交通部決標高架段",
    "工期": "縣府縮短橋梁工期",
    "通車時程": "交通部公布輕軌通車時程",
    "通車日期": "公路局確認快速道路通車日期",
    "完工期程": "經濟部說明水庫完工期程",
    "重建": "縣府規劃舊市場重建",
    "改建": "市府推動舊活動中心改建",
    "興建": "縣府籌劃興建體育館",
    "擴建": "交通部擴建機場跑道",
}
ADHOC_WORD_TITLES = {  # R234.3c: a public body postpones or sends help
    "延期": "市府宣布考試延期",
    "順延": "縣府宣布運動會順延",
    "延後": "市府將運動會延後舉行",
    "改期": "縣府宣布園遊會改期",
    "派遣": "國防部派遣官兵協助清淤",
    "出動": "市府出動怪手清理溪床",
    "調派": "縣府調派人力支援",
    "馳援": "國防部馳援山區部落",
}


def act_matches(title):
    return tf.PUBLIC_POWER_ACT.findall(title) + tf.PUBLIC_WORKS_ACT.findall(title) + tf.AD_HOC_ACT.findall(title)


class ActWordTest(unittest.TestCase):
    """R233.3, R234.3: each act word has a test title that matches by that word only."""

    def test_each_word_has_a_title_of_its_own(self):
        for table in (ACT_WORD_TITLES, EMERGENCY_WORD_TITLES, WORKS_WORD_TITLES, ADHOC_WORD_TITLES):
            for word, title in table.items():
                self.assertEqual(act_matches(title), [word], title)

    def test_each_word_makes_a_public_act_title(self):
        for table in (ACT_WORD_TITLES, EMERGENCY_WORD_TITLES, WORKS_WORD_TITLES, ADHOC_WORD_TITLES):
            for word, title in table.items():
                self.assertTrue(tf.public_act_title(title), title)

    def test_works_and_ad_hoc_words_need_a_public_body(self):  # a private firm that starts a build or moves an event is no act
        for title in ("民間業者宣布新廠開工", "百貨公司宣布週年慶改期", "科技公司派遣工程師出國", "私人建商興建大樓"):
            self.assertFalse(tf.public_act_title(title), title)


class PublicWorksClusterTest(unittest.TestCase):
    """R234.3a, c: a ceremony or a weather cluster with a public-works or an ad hoc act title passes."""

    def test_ceremony_with_a_tender_passes(self):
        titles = ["輕軌延伸段動土典禮 嘉賓到場", "輕軌延伸段動土儀式 交通部決標得標廠商", "輕軌延伸段典禮 現場剪綵"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_ceremony_with_a_completion_schedule_passes(self):
        titles = ["新橋通車典禮 嘉賓到場", "新橋通車儀式 縣府公布完工期程", "新橋通車慶典 民眾拍照"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_weather_with_a_postponement_passes(self):
        titles = ["豪雨特報 市府宣布考試延期", "颱風豪雨 氣象署發布警報", "豪雨過後 市府出動怪手清淤"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_weather_with_an_emergency_repair_passes(self):
        titles = ["豪雨沖毀橋面 工務段連夜搶修", "豪雨 氣象署發布警報", "豪雨過後 山區道路搶通"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))


class CeremonyRemarkTest(unittest.TestCase):
    """R234.3b, R234.5: a ceremony with a remark only, and a private ceremony, still fail."""

    def test_opening_with_a_remark_only_fails(self):
        titles = ["運動場開幕典禮 局長致詞感謝各界", "運動場開幕儀式 嘉賓表示期待", "運動場開幕典禮 師生合唱"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_training_ceremony_with_a_remark_only_fails(self):
        titles = ["志工訓練結業典禮 市長致詞勉勵", "志工結業典禮 學員代表發言", "志工訓練結業儀式 局長呼籲持續參與"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_private_ceremony_fails(self):
        titles = ["私立診所新院區動土典禮 董事長致詞", "私立診所動土儀式 貴賓到場", "診所新院區動土典禮 院長表示感謝"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_private_firm_start_of_work_fails(self):
        titles = ["科技公司新廠動土典禮 董事長致詞", "科技公司新廠開工儀式 貴賓到場", "科技公司新廠動土 員工期待"]
        self.assertTrue(tf.no_public_act(titles))  # new_topic_reason stops this cluster earlier, as private_matter


if __name__ == "__main__":
    unittest.main()
