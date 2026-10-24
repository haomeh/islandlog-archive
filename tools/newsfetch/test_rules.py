"""Tests for the title masker and the topic filter (real terms.json)."""

import unittest

from tools.newsfetch.filter import NewsFilter
from tools.newsfetch.parser import mask_title


class TestTitleMasking(unittest.TestCase):
    def test_name_before_verdict_word_masked(self):
        self.assertEqual(mask_title("新北市陳大文被控詐欺"), "新北市[當事人]被控詐欺")
        self.assertEqual(mask_title("王小明涉貪遭起訴"), "[當事人]涉貪遭起訴")

    def test_allowlisted_public_figure_kept(self):
        self.assertEqual(mask_title("蔣萬安遭質疑"), "蔣萬安遭質疑")
        self.assertEqual(mask_title("憂蔡康永遭跨境鎮壓加派警力"), "憂蔡康永遭跨境鎮壓加派警力")

    def test_phrase_false_positive_news_line_5(self):
        # 顧 is a surname, but 照顧民眾 is a phrase.
        self.assertEqual(mask_title("內政部：照顧民眾比較少"), "內政部：照顧民眾比較少")

    def test_place_and_number_words_not_masked(self):
        for t in ("台大陸生被驅逐出境　陸委會：這只是個案",
                  "地方選戰恐被國會攻防牽動",
                  "索賄370萬元涉貪 桃市經發局前科長"):
            self.assertEqual(mask_title(t), t)


class TestRealTermsFilter(unittest.TestCase):
    def setUp(self):
        self.filter = NewsFilter()

    def keep(self, title, summary=""):
        return self.filter.should_keep(title, summary)[0]

    def test_foreign_entities_dropped(self):
        for t in ("紐約市議會通過禁令　中央公園觀光馬車2028年走入歷史",
                  "歐洲議會貿委會27日訪中　聚焦產能過剩與不公平競爭",
                  "國際刑事法院獲歐盟最高人權獎",
                  "加州富豪稅公投將登場　黃仁勳：繳得起80億美元稅金是榮幸",
                  "越南越捷航空遭英法院凍結資產",
                  "川普限制跨性別受刑人醫療　美最高法院駁回"):
            self.assertFalse(self.keep(t), t)

    def test_broad_word_needs_taiwan_body(self):
        self.assertFalse(self.keep("民主黨看好重掌國會　已規劃制衡川普方針、擬彈劾赫格塞斯"))
        self.assertFalse(self.keep("印度辦金磚國家議會論壇　聚焦以人為本的發展"))
        self.assertTrue(self.keep("台北市議會三讀通過預算"))
        self.assertTrue(self.keep("立法院通過彈劾案"))

    def test_entertainment_and_victim_dropped(self):
        for t in ("知名演員行政院外拍片", "偶像團體赴立法院", "2個月害死55人！交通部：毒駕涉刑責"):
            self.assertFalse(self.keep(t), t)

    def test_taiwan_government_overrides_soft_foreign(self):
        self.assertTrue(self.keep("比照美國加嚴管制晶片輸中？ 行政院：台美是緊密的貿易夥伴"))


if __name__ == "__main__":
    unittest.main()
