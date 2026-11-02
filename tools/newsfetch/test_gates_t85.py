"""T85 tests (R384). No test or data here holds the name of a minor or of a victim. Names are fake."""

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import cluster as cl

from tools.newsfetch import run_report
from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

REMOVED_R384 = ["src-20260806-ettoday-9171cd71", "src-20260806-ettoday-bd4f0e3a", "src-20260912-ltn-7a5c57f9", "src-20260912-ettoday-0768633b",
                "src-20260913-ltn-161b87b1", "src-20260914-ltn-f0972166", "src-20260915-chinatimes-046dc50a", "src-20260925-ettoday-794d5f9d",
                "src-20260926-pts-d2f7eecf"]


class RemovedNineTest(unittest.TestCase):
    """R384.1: nine corpus sources hold the name of the minor of R363.1. They are on the removed list. The report flag reads 父母, 學生, 遺屬."""

    def test_each_of_the_nine_sources_is_on_the_removed_list(self):
        removed = tf.load_removed_sources()
        for sid in REMOVED_R384:
            self.assertIn(sid, removed)
            self.assertIn("R384", removed[sid]["ruling"])
            self.assertTrue(removed[sid]["reason"].strip())

    def test_the_first_two_entries_stay(self):
        removed = tf.load_removed_sources()
        self.assertIn("src-20261023-ltn-ef4f6708", removed)
        self.assertIn("src-20261029-ltn-0db0ff7c", removed)

    def test_the_flag_reads_parents_students_and_the_bereaved(self):
        for title in ("某某某父母盼修法", "某某某同學與學生發聲", "遺屬促請修法 某某某案", "某某某的遺屬出席公聽會"):
            self.assertTrue(run_report.victim_flag(title), title)

    def test_a_plain_policy_title_has_no_flag(self):
        for title in ("政院通過少事法修正草案", "淡江大橋通車典禮"):
            self.assertFalse(run_report.victim_flag(title), title)


class ForeignCountryTest(unittest.TestCase):
    """R384.2: the foreign marker reads the countries of the opus and sonnet lists, 韓國, and a class rule for a country that no list names."""

    LISTED = ["希臘", "瑞典", "瑞士", "巴拿馬", "巴拉圭", "約旦", "冰島", "海地", "盧森堡", "蒙古", "瓜地馬拉", "韓國", "卡達", "科威特", "汶萊", "迦納", "剛果", "巴林", "吉爾吉斯", "烏干達"]
    TAIWAN = ["教育部 唾液篩檢", "外交部 自動通關", "交通部 機車後座兒童", "國防部 體位區分標準", "內政部 特搜隊成軍",
              "立委要求教育部說明", "函請外交部協助國人", "送達內政部文件", "傳達教育部指示", "抵達外交部", "採納教育部建議", "接納經濟部方案", "我國外交部抗議", "全國教育部門會議",
              "中華民國外交部聲明", "本國外交部說明", "各國外交部回應", "外國人 教育部新制", "韓國瑜 內政部說明"]

    def test_each_listed_country_before_a_generic_body_is_a_marker(self):
        for place in self.LISTED:
            title = f"{place}外交部召見大使"
            self.assertTrue(tf.foreign_marked(title), title)
            self.assertFalse(tf.taiwan_relevant([title], new=True), title)
            self.assertFalse(tf.taiwan_relevant([f"{place}憲法法庭裁定總統令違憲"], new=True), place)

    def test_the_class_rule_marks_a_country_that_no_list_names(self):
        for title in ("阿曼國外交部召見大使", "史瓦帝尼王國外交部聲明", "賴索托共和國財政部說明", "尚比亞外交部聲明", "塞席爾國防部表示"):
            self.assertTrue(tf.foreign_marked(title), title)
            self.assertFalse(tf.taiwan_relevant([title], new=True), title)

    def test_a_taiwan_word_before_a_body_is_no_marker(self):
        for title in self.TAIWAN:
            self.assertFalse(tf.foreign_marked(title), title)

    def test_a_taiwan_ministry_alone_keeps_the_link(self):
        for title in self.TAIWAN[:5]:
            self.assertTrue(tf.taiwan_relevant([title], new=True), title)

    def test_south_korea_is_a_foreign_name_for_a_new_topic_but_the_speaker_is_not(self):
        self.assertTrue(tf.FOREIGN_NEW.search("韓國政府宣布"))
        self.assertFalse(tf.FOREIGN_NEW.search("韓國瑜宣布"))


class ServeTermTest(unittest.TestCase):
    """R384.3: 服刑 makes a case title only when the title holds no law or act word. The neutral 少事法 title returns."""

    def test_a_prison_title_with_no_law_word_is_still_a_case(self):
        for title in ("統促黨幹部入獄服刑", "某某某服刑期滿出獄", "詐團首腦服刑中再被訴"):
            self.assertTrue(tf.CASE_TITLE.search(title), title)

    def test_a_bill_or_act_title_with_the_word_is_no_case(self):
        for title in ("少事法修正草案 行政院：服刑少年另設矯正機構", "政院通過少年事件處理法 虞犯服刑條文修正", "修法縮短假釋門檻 服刑滿一年可申請",
                      "矯正署：服刑人權益保障條例草案送立院", "《受刑人更生保護法》三讀 出獄服刑人可申請補助"):
            self.assertFalse(tf.CASE_TITLE.search(title), title)

    def test_other_case_words_are_not_cleared_by_a_law_word(self):
        self.assertTrue(tf.CASE_TITLE.search("修法討論中 某某某判3年 入獄"))
        self.assertTrue(tf.CASE_TITLE.search("毒品條例 某某某遭起訴"))

    def test_a_court_or_justice_ministry_word_is_no_law_word(self):
        self.assertTrue(tf.CASE_TITLE.search("法院判決確定 某某某今入獄服刑"))
        self.assertTrue(tf.CASE_TITLE.search("法務部：某某某移監服刑"))

    def test_the_bill_title_stays_in_the_topic_list(self):
        from tools.newsfetch.test_topics_full import item
        titles = ["少事法 行政院通過修正草案", "少事法 服刑少年另設矯正機構條文", "少事法 立院一讀"]
        members = [item(f"b{i}", t, "2026-10-24", f"報{i}") for i, t in enumerate(titles)]
        self.assertEqual(len(tf.split_cases(members)), 1)


class CampaignNamesTest(unittest.TestCase):
    """R384.4: the campaign class reads candidate names and the words 交鋒, 反問, 陣營質疑, 選將, 換人做. A policy statement of an official with no campaign word stays."""

    def setUp(self):
        tf.set_candidates({"王小明", "李大華", "陳小安"})
        self.addCleanup(tf.set_candidates, frozenset())

    CAMPAIGN = ["長者健保補助再交鋒 李大華反問王小明：哪個法案不是全國性的？",
                "王小明支持中央補助長者健保費且全國一致  對手陣營質疑「哪個才是王小明？」",
                "新竹爆食安事件 藍選將也喊：做不好就換人做",
                "「食安」疑慮說不清 陳小安要求王小明下台負責",
                "長者健保補助 李大華交鋒王小明",
                "王小明反問：長者健保補助為何不一致？",
                "快新聞／李大華選情急了？猛打王小明長者健保費態度不一", "長者健保免費排富議題攻防 李大華籲王小明：不要說一套做一套"]
    POLICY = ["兩部會協商長者健保費 交鋒焦點在財源", "行政院長卓榮泰：長者健保費補助將修法", "衛福部反問業者：標示為何不全？",
              "國手選將名單公布 教練團說明", "廠商不行就換人做 工程會：採購法有規定", "王小明：長者健保費補助將於明年上路",
              "立法院交鋒 國防預算三讀", "市府說明長者健保補助新制"]

    def test_each_campaign_title_is_candidate_talk(self):
        for title in self.CAMPAIGN:
            self.assertTrue(tf.candidate_talk(title), title)

    def test_each_policy_title_stays(self):
        for title in self.POLICY:
            self.assertFalse(tf.candidate_talk(title), title)

    def test_the_words_alone_do_not_judge_without_a_candidate_or_a_party_word(self):
        for title in ("議場交鋒 預算審查", "官員被反問 無法答覆", "民眾質疑新制 陣營不明"):
            self.assertFalse(tf.candidate_talk(title), title)

    def test_a_larger_short_form_group_ranks_before_an_exact_key_group(self):
        short = _group([("https://x.example/s1", "中聯1300噸 回收", "2026-06-05"), ("https://x.example/s2", "中聯1300噸 停產", "2026-06-05")])
        full = _group([("https://x.example/f1", "中聯油脂 停產", "2026-06-05")])
        seed = {"event_id": "ev-20260601-x", "seed_urls": [], "_keys": ["中聯油脂"], "_name": "中聯油脂", "jurisdiction_names": [], "jurisdiction_ids": ["jur-tw"],
                "gov_levels": [], "controversy_types": [], "policy_domains": [], "actors": []}
        items = [i for g in (short, full) for i in g["items"]]
        with mock.patch.object(tp, "group_items", lambda its: [short, full]), mock.patch.object(tp, "MAX_GROUPS", 1):
            ev = tp.build_event(seed, items, {}, items=items)
        self.assertEqual(sorted(ev["used"]), ["https://x.example/s1", "https://x.example/s2"])

    def test_the_old_classes_still_work(self):
        for title in ("議員為候選人助講 批新制", "市府新制 某黨競辦回應"):
            self.assertTrue(tf.candidate_talk(title), title)


def _group(rows, kind="report"):
    items = [{"url": u, "title": t, "published_on": d, "publisher": f"報{i}", "source_class": "news", "fetched_on": f"{d}T12:00:00Z"}
             for i, (u, t, d) in enumerate(rows)]
    return {"kind": kind, "items": items, "urls": [i["url"] for i in items]}


class DisplayCapShortFormTest(unittest.TestCase):
    """R384.5: the display cap reads the short forms of the key, keeps the first report so start_date does not move, and gives campaign titles no priority."""

    def build(self, groups, key="中聯油脂", cap=2):
        seed = {"event_id": "ev-20260601-x", "seed_urls": [], "_keys": [key], "_name": key, "jurisdiction_names": [], "jurisdiction_ids": ["jur-tw"],
                "gov_levels": [], "controversy_types": [], "policy_domains": [], "actors": []}
        items = [i for g in groups for i in g["items"]]
        with mock.patch.object(tp, "group_items", lambda its: groups), mock.patch.object(tp, "MAX_GROUPS", cap):
            return tp.build_event(seed, items, {}, items=items)

    def test_the_short_forms_of_a_key_are_prefixes_and_long_suffixes(self):
        forms = tp.key_forms("中聯油脂")
        self.assertEqual(forms[0], "中聯油脂")
        for f in ("中聯", "中聯油", "聯油脂"):
            self.assertIn(f, forms)
        self.assertNotIn("油脂", forms)

    def test_a_key_of_two_characters_has_no_short_form(self):
        self.assertEqual(tp.key_forms("萬里"), ["萬里"])

    def test_a_group_with_a_short_form_ranks_before_a_bigger_group_with_none(self):
        none = _group([("https://x.example/n1", "豆油價格 調漲", "2026-06-05"), ("https://x.example/n2", "豆油價格 再漲", "2026-06-05"), ("https://x.example/n3", "豆油價格 回穩", "2026-06-05")])
        short = _group([("https://x.example/s1", "中聯1300噸 回收", "2026-06-05")])
        full = _group([("https://x.example/f1", "中聯油脂 停產", "2026-06-06")])
        ev = self.build([none, short, full])
        self.assertEqual(sorted(ev["used"]), ["https://x.example/f1", "https://x.example/s1"])

    def test_the_first_report_stays_so_start_date_does_not_move(self):
        first = _group([("https://x.example/a", "颱風外圍環流 豪雨", "2026-06-01")])
        full1 = _group([("https://x.example/b", "中聯油脂 停產", "2026-06-05"), ("https://x.example/b2", "中聯油脂 停產 二", "2026-06-05")])
        full2 = _group([("https://x.example/c", "中聯油脂 回收", "2026-06-06"), ("https://x.example/c2", "中聯油脂 回收 二", "2026-06-06")])
        ev = self.build([first, full1, full2])
        self.assertEqual(ev["start_date"], "2026-06-01")
        self.assertIn("https://x.example/a", ev["used"])

    def test_the_first_report_is_the_one_with_the_best_rank_on_the_first_day(self):
        d1 = _group([("https://x.example/a1", "油價 一般", "2026-06-01")])
        d2 = _group([("https://x.example/a2", "中聯油脂 首報", "2026-06-01")])
        full = _group([("https://x.example/f1", "中聯油脂 停產", "2026-06-06")])
        full2 = _group([("https://x.example/f2", "中聯油脂 回收", "2026-06-07")])
        ev = self.build([d1, d2, full, full2])
        self.assertIn("https://x.example/a2", ev["used"])
        self.assertNotIn("https://x.example/a1", ev["used"])

    def test_a_campaign_title_with_the_key_gets_no_priority(self):
        camp = _group([("https://x.example/c1", "中聯油脂 王小明交鋒李大華", "2026-06-05")])
        plain = _group([("https://x.example/p1", "中聯油脂 停產", "2026-06-05")])
        short = _group([("https://x.example/s1", "中聯1300噸 回收", "2026-06-05")])
        with mock.patch.object(tp, "is_campaign_title", lambda t: "交鋒" in t):
            ev = self.build([camp, plain, short])
        self.assertEqual(sorted(ev["used"]), ["https://x.example/p1", "https://x.example/s1"])

    def test_topics_full_sets_the_campaign_hook(self):
        self.assertIs(tp.is_campaign_title, tf.candidate_talk)


class ClusterTempFileTest(unittest.TestCase):
    """R384.6 (T82b-V G1): cluster writes to a temp file, then renames. A write that stops leaves no partial output and keeps an old output."""

    def rows(self, bad=False):
        title = "測試標題\ud800" if bad else "測試標題"
        return [{"url": f"https://x.example/{i}", "title": f"{title} {i}", "published_on": "2026-10-01", "publisher": f"報{i}", "source_class": "news"} for i in range(3)]

    def write_input(self, d, rows):
        src = os.path.join(d, "in.jsonl")
        with open(src, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(r) for r in rows) + "\n")
        return src

    def test_a_good_run_leaves_the_output_and_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            cl.main([self.write_input(d, self.rows()), out, "--as-news-groups"])
            self.assertEqual(sorted(os.listdir(d)), ["in.jsonl", "o.json", "o.json.sources.json"])

    def test_a_write_that_stops_leaves_no_output_and_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            with self.assertRaises(UnicodeEncodeError):
                cl.main([self.write_input(d, self.rows(bad=True)), out, "--as-news-groups"])
            self.assertEqual(os.listdir(d), ["in.jsonl"])

    def test_a_write_that_stops_keeps_an_old_output_and_old_sources(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            Path(out).write_text("old\n", encoding="utf-8")
            Path(out + ".sources.json").write_text("old-sources\n", encoding="utf-8")
            with self.assertRaises(UnicodeEncodeError):
                cl.main([self.write_input(d, self.rows(bad=True)), out, "--as-news-groups"])
            self.assertEqual(Path(out).read_text(encoding="utf-8"), "old\n")
            self.assertEqual(Path(out + ".sources.json").read_text(encoding="utf-8"), "old-sources\n")
            self.assertEqual(sorted(os.listdir(d)), ["in.jsonl", "o.json", "o.json.sources.json"])

    def test_the_plain_mode_is_atomic_too(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.json")
            with self.assertRaises(UnicodeEncodeError):
                cl.main([self.write_input(d, self.rows(bad=True)), out])
            self.assertEqual(os.listdir(d), ["in.jsonl"])


ROOT = Path(__file__).resolve().parent


class PythonNameTest(unittest.TestCase):
    """R384.6 (T82b-V G3, G2): the WORKFLOW.md lines and deploy/README.md name /usr/bin/python3. The env example holds no local path of a user."""

    def test_no_bare_python3_command_in_the_workflow_or_the_deploy_readme(self):
        for name in ("WORKFLOW.md", "deploy/README.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?<![/\w])python3 -m", text), name)

    def test_the_env_example_holds_no_home_path_of_a_user(self):
        text = (ROOT / "deploy/newsfetch.env.example").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"/home/(?!USER/|linuxbrew/)[^/\s]+|\.config/nvm")

    def test_the_perf_test_class_stands_before_unittest_main(self):
        text = (ROOT / "test_perf_equal.py").read_text(encoding="utf-8")
        self.assertEqual(text.count("unittest.main()"), 1)
        self.assertGreater(text.index("unittest.main()"), text.index("class WindowCorpusIdentityTest"))


class LawObjectNameTest(unittest.TestCase):
    """R384.7: a name that ends with a generic act noun (校事會議) is an issue name when the key stands next to an issue noun in a share of its titles."""

    ISSUE = ["校事會議修正草案送立院 團體呼籲退回", "教育部改革校事會議 案量下降", "校事會議引爭議 議員提案廢除", "校事會議風暴 教師工會抗議", "強化校事會議制度 縣市跟進",
             "教師不堪校事會議壓力", "校事會議開啟惡訴之門？", "校事會議案量降至兩成", "學校啟動校事會議", "校事會議調查報告出爐"]

    def test_the_name_with_issue_neighbors_is_an_issue_name(self):
        self.assertFalse(tf.issue_name("校事會議"))
        self.assertTrue(tf.law_object_name("校事會議", "校事會議", self.ISSUE))

    def test_a_bare_meeting_name_with_no_issue_neighbor_fails(self):
        titles = ["部務會議召開 部長主持", "部務會議今登場", "部務會議後記者會", "出席部務會議 討論人事", "部務會議紀要公布"]
        self.assertFalse(tf.law_object_name("部務會議", "部務會議", titles))

    def test_a_generic_act_noun_alone_fails(self):
        self.assertFalse(tf.law_object_name("協商會議", "協商會議", ["協商會議修正草案", "改革協商會議"] * 3))
        self.assertFalse(tf.law_object_name("記者會", "記者會", ["改革記者會"] * 5))

    def test_a_name_that_is_not_a_noun_phrase_fails(self):
        self.assertFalse(tf.law_object_name("要求校事會議", "要求校事會議", self.ISSUE))

    def test_the_name_with_issue_neighbors_passes_the_gate_test(self):
        self.assertTrue(tf.issue_name_ok("校事會議", "校事會議", self.ISSUE))
        self.assertFalse(tf.issue_name_ok("台英國會外交首例", "台英國會外交首例", ["台英國會外交首例 一", "台英國會外交首例 二", "台英國會外交首例 三"]))


if __name__ == "__main__":
    unittest.main()
