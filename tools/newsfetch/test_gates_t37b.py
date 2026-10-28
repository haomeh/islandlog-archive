"""T37b gate round (R247.3): widen the recall of rejected_no_public_act. New act words by class (R234.3a, R234.3c, R229.2c)
and new public bodies by kind (R234.4). One test title for each word and each actor form. The titles are not in any judged list (R156)."""

import unittest

from tools.newsfetch import topic_config as tc
from tools.newsfetch import topics_full as tf
from tools.newsfetch.test_gates_t37 import act_matches, items

POWER_WORD_TITLES = {  # R229.2c: relief, emergency rescue, penalty, approval
    "賑災": "外交部籌組賑災物資",
    "搶險": "山區溪水暴漲 消防人員搶險",
    "開鍘": "違規業者遭開鍘",
    "懲處": "涉案人員遭懲處",
    "獲准": "出口商品獲准進入新市場",
    "核可": "委員會核可新營運計畫",
}
WORKS_WORD_TITLES = {  # R234.3a: a schedule, a tender or a completion set by a public body
    "通車進度": "鐵道局說明捷運通車進度",
    "雙線通車": "交通部宣布橋梁雙線通車",
    "完工通車": "縣府預告新路完工通車",
    "通車目標": "公路局訂定隧道通車目標",
    "竣工": "市府表示體育館竣工",
    "招商": "縣府啟動園區招商",
}
ADHOC_WORD_TITLES = {  # R234.3c: a public body moves a date
    "延至": "衛生局宣布疫苗接種延至下週",
    "改至": "市府宣布市集改至週日",
}
BODY_TITLES = {  # R234.4: a function noun and an agency suffix; no other government word in the title
    "局": "水利局公布清淤進度",
    "署": "營建署公布老屋補強指引",
    "處": "港務處公告船席調整",
}
NATIONAL_BODY_TITLES = {  # R234.4: a national body that has no agency suffix
    "國震中心": "國震中心完成校舍補強評估",
    "大學招聯會": "大學招聯會公布報名日期",
    "大考中心": "大考中心公告試場規則",
}


class NewActWordTest(unittest.TestCase):
    def test_each_new_word_has_a_title_of_its_own(self):
        for table in (POWER_WORD_TITLES, WORKS_WORD_TITLES, ADHOC_WORD_TITLES):
            for word, title in table.items():
                self.assertEqual(act_matches(title), [word], title)

    def test_power_words_make_a_public_act_title(self):
        for word, title in POWER_WORD_TITLES.items():
            self.assertTrue(tf.public_act_title(title), title)

    def test_works_and_ad_hoc_words_make_a_public_act_title_with_a_body(self):
        for table in (WORKS_WORD_TITLES, ADHOC_WORD_TITLES):
            for word, title in table.items():
                self.assertTrue(tf.public_act_title(title), title)

    def test_works_and_ad_hoc_words_fail_with_a_private_firm(self):
        for title in ("科技公司宣布新廠竣工", "建設公司公布大樓通車進度", "百貨公司宣布活動改至週日", "業者啟動園區招商"):
            self.assertFalse(tf.public_act_title(title), title)

    def test_constants_live_in_topic_config(self):
        self.assertIs(tf.PUBLIC_WORKS_ACT, tc.PUBLIC_WORKS_ACT)
        self.assertIs(tf.AD_HOC_ACT, tc.AD_HOC_ACT)


class NewBodyTest(unittest.TestCase):
    def test_agency_suffix_after_a_function_noun(self):
        for suffix, title in BODY_TITLES.items():
            self.assertTrue(tf.names_government(title, True), title)

    def test_national_bodies(self):
        for name, title in NATIONAL_BODY_TITLES.items():
            self.assertTrue(tf.names_government(title, True), title)

    def test_words_with_the_suffix_are_no_body(self):
        for title in ("科技公司結局未明 部署新廠", "球隊開局不順 格局生變", "公司簽署合約 佈局海外", "施工團隊營建局部完成"):
            self.assertFalse(tf.names_government(title, True), title)


class NewClusterTest(unittest.TestCase):
    def test_weather_with_a_relief_title_passes(self):
        titles = ["豪雨成災 外交部籌組賑災物資", "豪雨 氣象署發布警報", "豪雨過後 山區災情擴大"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_ceremony_with_a_schedule_by_a_new_body_passes(self):
        titles = ["新橋通車典禮 嘉賓到場", "新橋通車儀式 鐵道局說明通車進度", "新橋通車慶典 民眾拍照"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_exam_postponement_by_a_national_body_passes(self):
        titles = ["颱風來襲 大學招聯會宣布測驗延期", "颱風豪雨 氣象署發布警報", "颱風過後 考生返家"]
        self.assertIsNone(tf.new_topic_reason(items(titles)))

    def test_ceremony_with_a_remark_only_by_a_new_body_fails(self):
        titles = ["運動場開幕典禮 水利局長致詞感謝各界", "運動場開幕儀式 營建署代表表示期待", "運動場開幕典禮 師生合唱"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")

    def test_acts_in_two_titles_do_not_combine(self):  # R247.3: the match is per title
        titles = ["輕軌延伸段典禮 嘉賓到場", "輕軌延伸段儀式 重建計畫受矚目", "輕軌延伸段典禮 交通部長致詞"]
        self.assertEqual(tf.new_topic_reason(items(titles)), "no_public_act")


if __name__ == "__main__":
    unittest.main()
