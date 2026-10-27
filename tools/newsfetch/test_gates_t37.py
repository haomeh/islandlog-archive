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


if __name__ == "__main__":
    unittest.main()
