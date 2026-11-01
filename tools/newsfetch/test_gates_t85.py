"""T85 tests (R384). No test or data here holds the name of a minor or of a victim. Names are fake."""

import unittest

from tools.newsfetch import run_report
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


if __name__ == "__main__":
    unittest.main()
