"""Back-fill tests: unit split, resume, merge. No network."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import backfill


class TestBackfill(unittest.TestCase):
    def test_dated_list_splits_into_weekly_units_and_others_into_one(self):
        units = backfill.units_for({"type": "dated_list"}, "2026-04-24", "2026-05-10")
        self.assertEqual([u["name"] for u in units], ["20260424_20260430", "20260501_20260507", "20260508_20260510"])
        self.assertEqual(units[0]["since"], "2026-04-24")
        self.assertEqual(backfill.units_for({"type": "paged_list"}, "2026-04-24", "2026-05-10")[0]["name"], "all")

    def test_second_run_skips_done_units(self):
        feeds = [{"id": "t", "publisher": "T", "publisher_group": "G", "type": "dated_list", "route": {}}]
        item = {"url": "https://t/1", "title": "測試標題一二三", "publisher": "T", "published_on": "2026-04-25",
                "snippet": "x", "summary": ""}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            feeds_path = tmp / "feeds.json"
            feeds_path.write_text(json.dumps(feeds), encoding="utf-8")
            argv = ["--feeds", feeds_path, "--out-dir", tmp / "out", "--log-dir", tmp / "log",
                    "--since", "2026-04-24", "--until", "2026-05-02", "--source", "t"]
            with mock.patch("tools.newsfetch.backfill.fetch_source_items", return_value=[item]) as fetch:
                backfill.main([str(a) for a in argv])
                self.assertEqual(fetch.call_count, 2)
                backfill.main([str(a) for a in argv])
                self.assertEqual(fetch.call_count, 2)
            merged = (tmp / "out" / "news-t.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(merged), 1)
            self.assertEqual(json.loads(merged[0])["published_on"], "2026-04-25")


if __name__ == "__main__":
    unittest.main()
