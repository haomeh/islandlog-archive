"""Regression tests for R427 date buckets and display caps."""

import unittest

from tools.newsfetch import test_gates_t85 as t85


class ResidualTest(unittest.TestCase):
    def build(self, groups, cap=40):
        return t85.DisplayCapShortFormTest().build(groups, cap=cap)

    def test_each_report_day_has_its_own_timeline_entry(self):
        groups = [t85._group([(f"https://x.example/{day}", f"中聯油脂 報導 {day}", f"2026-06-{day:02d}")])
                  for day in range(1, 13)]
        ev = self.build(groups)
        self.assertEqual(len(ev["timeline"]), 12)
        for entry in ev["timeline"]:
            for url in entry["source_urls"]:
                self.assertEqual(entry["date"], ev["used"][url]["published_on"])
        self.assertIn("2026-06-12", ev["summary"])
        self.assertTrue(ev["body"][-1].startswith("## 2026-06-12"))

    def test_short_form_can_displace_exact_key_at_the_cap(self):
        short = t85._group([("https://x.example/s1", "中聯1300噸 回收", "2026-06-02"),
                           ("https://x.example/s2", "中聯257家 交檢調", "2026-06-02")])
        exact = t85._group([("https://x.example/f", "中聯油脂 停產", "2026-06-02")])
        first = t85._group([("https://x.example/first", "首次報導", "2026-06-01")])
        ev = self.build([first, exact, short], cap=2)
        self.assertIn("https://x.example/first", ev["used"])
        self.assertIn("https://x.example/s1", ev["used"])
        self.assertNotIn("https://x.example/f", ev["used"])

    def test_equal_size_short_form_keeps_the_stable_order(self):
        short = t85._group([("https://x.example/s", "中聯257家 回收", "2026-06-01")])
        exact = t85._group([("https://x.example/f", "中聯油脂 停產", "2026-06-01")])
        ev = self.build([short, exact], cap=1)
        self.assertEqual(list(ev["used"]), ["https://x.example/s"])


if __name__ == "__main__":
    unittest.main()
