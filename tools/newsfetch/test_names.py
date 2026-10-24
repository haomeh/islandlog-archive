"""Tests for the person-name masker and the remask tool. No network."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.newsfetch.parser import make_snippet, mask_title
from tools.newsfetch import remask


class TestNameMask(unittest.TestCase):
    def test_name_after_action_word(self):
        out = mask_title("開車載張俊傑台南、高雄繞行避追查")
        self.assertNotIn("張俊傑", out)
        self.assertIn("高雄", out)
        self.assertIn("台南", out)
        self.assertNotIn("張俊傑", make_snippet("開車載張俊傑台南、高雄繞行避追查"))

    def test_name_after_role_word(self):
        for raw, name in (("男子林志明闖入民宅", "林志明"), ("員警黃建國遭檢舉", "黃建國"),
                          ("警方帶回李大同詢問", "李大同"), ("醫師吳美玲涉收賄", "吳美玲")):
            self.assertNotIn(name, mask_title(raw), raw)

    def test_name_before_verdict_and_age(self):
        for raw, name in (("鄭小華獲判無罪", "鄭小華"), ("周文德肇事逃逸", "周文德"),
                          ("謝志豪(41)落網", "謝志豪"), ("洪大偉羈押禁見", "洪大偉")):
            self.assertNotIn(name, mask_title(raw), raw)

    def test_public_figure_kept(self):
        for t in ("載蔣萬安視察災區", "與賴清德會面", "陳其邁遭質疑", "柯文哲被起訴"):
            self.assertEqual(mask_title(t), t)

    def test_place_org_and_title_kept(self):
        for t in ("與高雄市政府協商", "載運貨物前往林口", "張家界旅遊團遭困", "林口電廠停機",
                  "李先生說明", "草屯8旬翁採筍失蹤11天", "熱湯淋賊判拘役", "孫綻規劃結婚", "高下立判", "逆溫層危害", "與林務局協調", "帶高鐵乘客返鄉", "和平島遭淹"):
            self.assertEqual(mask_title(t), t)

    def test_idempotent(self):
        once = mask_title("開車載張俊傑台南、高雄繞行避追查")
        self.assertEqual(mask_title(once), once)


class TestRemask(unittest.TestCase):
    def item(self, title, snippet=None, day="2026-06-01"):
        return {"url": "https://x/" + str(len(title)) + "-" + str(ord(title[0])), "title": title, "snippet": snippet or title,
                "published_on": day, "publisher": "p"}

    def test_title_and_snippet_masked(self):
        out = remask.remask_item(self.item("開車載張俊傑台南避追查", "警方指張俊傑在台南落網"))
        self.assertNotIn("張俊傑", out["title"])
        self.assertNotIn("張俊傑", out["snippet"])

    def test_idempotent(self):
        once = remask.remask_item(self.item("開車載張俊傑台南避追查"))
        self.assertEqual(remask.remask_item(once), once)

    def test_noise_dropped(self):
        for t in ("生活小撇步：冰箱除臭", "專欄／能源政策的盲點", "社論－電價", "時事評論 預算案"):
            self.assertIsNone(remask.remask_item(self.item(t)), t)

    def test_name_propagates_to_other_titles(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d, "a.jsonl"), Path(d, "b.jsonl")
            rows = [self.item("開車載張俊傑台南避追查"), self.item("張俊傑逃亡爽住五星酒店")]
            src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
            remask.main(["--in", str(src), "--out", str(dst)])
            self.assertNotIn("張俊傑", dst.read_text(encoding="utf-8").replace(rows[0]["url"], ""))

    def test_news_with_comment_word_in_body_kept(self):
        item = self.item("王定宇轟國台辦", "網友評論兩岸關係")
        self.assertIsNotNone(remask.remask_item(item))

    def test_window(self):
        self.assertIsNone(remask.remask_item(self.item("市府公告", day="2026-04-23"), since="2026-04-24", until="2026-10-24"))
        self.assertIsNone(remask.remask_item(self.item("市府公告", day="2026-10-25"), since="2026-04-24", until="2026-10-24"))
        self.assertIsNotNone(remask.remask_item(self.item("市府公告", day="2026-10-24"), since="2026-04-24", until="2026-10-24"))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d, "a.jsonl"), Path(d, "b.jsonl")
            rows = [self.item("開車載張俊傑台南避追查"), self.item("生活小撇步：除臭")]
            src.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
            self.assertEqual(remask.main(["--in", str(src), "--out", str(dst)]), 0)
            lines = dst.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertNotIn("張俊傑", lines[0])


if __name__ == "__main__":
    unittest.main()
