"""T82: the optimized structures give the same counts and the same rows as the old methods, on a small corpus.

The old methods are written out here: document_frequency with Counter, the month Counter table, the scan of the corpus."""
import random
import re
import unittest
from collections import Counter, defaultdict
from datetime import date, timedelta

from tools.newsfetch import topics as tp
from tools.newsfetch import topics_full as tf

WORDS = ["颱風", "停班停課", "行政院", "預算", "立法院", "三讀", "核能", "臺北市", "高雄", "捷運", "ＡＢＣ", "２０２６", "「政治獻金案」", "政治獻金", "民族團結法", "薔琵", "護病比"]


def corpus(n=400, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        title = " ".join(rng.sample(WORDS, rng.randint(1, 4)))
        day = date(2026, 4, 1) + timedelta(days=rng.randint(0, 200))
        rows.append({"url": f"https://example.com/{i}", "title": title, "published_on": day.isoformat(), "publisher": "p", "source_class": "news"})
    rows.append({"url": "https://example.com/none", "title": "", "published_on": "2026-05-05", "publisher": "p", "source_class": "news"})
    return rows


def old_months(rows):
    months = defaultdict(Counter)
    for it in rows:
        months[it["published_on"][:7]].update(tp._grams(it["title"]))
    return months


class GramIndexTest(unittest.TestCase):
    def test_total_counts_equal_the_counter_for_every_gram_and_for_phrases_that_are_no_gram(self):
        rows = corpus()
        df, gi = tp.document_frequency(rows), tp.GramIndex(rows)
        for g in df:
            self.assertEqual(gi.get(g, 0), df[g], g)
            self.assertEqual(gi[g], df[g], g)
        for g in ["", "颱", "ab", "颱風A", "颱風 停班", "颱風停班停課行政院預算", "鑫鑫", "三讀核能", "２０", "20", "ＡＢ", "政治獻金案」", "停課行"]:
            self.assertEqual(gi.get(g, 0), df.get(g, 0), g)
        self.assertEqual(gi.get("鑫鑫", 5), df.get("鑫鑫", 5))

    def test_window_counts_equal_the_month_counters(self):
        rows = corpus()
        old, new = old_months(rows), tf.MonthFrequency(rows)
        self.assertEqual(sorted(new.months), sorted(old))
        grams = set().union(*(set(c) for c in old.values())) | {"鑫鑫", "颱風A"}
        for lo, hi in [(date(2026, 4, 3), date(2026, 4, 9)), (date(2026, 5, 20), date(2026, 8, 2)), (date(2026, 1, 1), date(2026, 12, 31)), (date(2027, 1, 1), date(2027, 2, 1))]:
            keys, d = [], date(lo.year, lo.month, 1)
            while d <= hi:
                keys.append(d.strftime("%Y-%m"))
                d = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
            counters = [old[k] for k in keys if k in old]
            view = new.window(lo, hi)
            for g in grams:
                self.assertEqual(view.get(g, 0), sum(c.get(g, 0) for c in counters), (g, lo, hi))
        for month, counter in old.items():
            for g in list(counter)[:200]:
                self.assertEqual(new.months[month].get(g, 0), counter[g])


class DayIndexTest(unittest.TestCase):
    def test_slice_equals_the_scan(self):
        rows = corpus()
        ix = tf.DayIndex(rows)
        scan = sorted(rows, key=lambda j: j["published_on"])
        for lo, hi in [(date(2026, 4, 3), date(2026, 4, 9)), (date(2026, 6, 1), date(2026, 6, 1)), (date(2026, 1, 1), date(2026, 12, 31)), (date(2027, 1, 1), date(2027, 2, 1))]:
            want = [it for it in scan if lo <= tf._day(it["published_on"]) <= hi]
            self.assertEqual([id(x) for x in ix.between(lo, hi)], [id(x) for x in want])


class PersonCacheTest(unittest.TestCase):
    def test_the_cached_test_equals_the_direct_test(self):
        titles = ["柯文哲表示 預算", "行政院說明 颱風", "三讀 核能"]
        for g in ["柯文哲", "行政院", "颱風", "預算", "核能", "停班停課", "三讀", "文哲"]:
            direct = any(n in g for n in tp.PUBLIC_FIGURES if len(n) >= 2)
            if not direct and 2 <= len(g) <= 3 and not tp.NOUN_END.search(g):
                direct = sum(1 for t in titles if re.compile(re.escape(g) + tp.SPEECH_AFTER).search(t)) >= 1
            self.assertEqual(tp._is_person_or_speaker(g, titles), direct, g)


class SlimRowsTest(unittest.TestCase):
    def test_only_the_unused_fields_go(self):
        rows = corpus(20)
        for r in rows:
            r["snippet"], r["matched_terms"] = "x" * 50, ["a"]
        want = [{k: v for k, v in r.items() if k not in ("snippet", "matched_terms")} for r in rows]
        self.assertEqual(tf.slim_rows(rows), want)

    def test_read_slim_equals_read_jsonl_then_slim(self):
        import json
        import tempfile
        rows = corpus(30)
        for r in rows:
            r["snippet"] = "x"
        with tempfile.TemporaryDirectory() as d:
            path = d + "/c.jsonl"
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n\n")
            self.assertEqual(tf.read_slim(path), tf.slim_rows(tp.read_jsonl(path)))


class ReadClustersTest(unittest.TestCase):
    def test_the_reduced_clusters_give_the_same_url_lists(self):
        import json
        import tempfile
        data = [{"cluster_id": "c1", "title": "x", "topics": ["a"], "news_groups": [{"id": "ng-01", "kind": "report", "source_ids": ["u1", "u2"], "extra": {"source_ids": ["no"]}},
                                                                              {"id": "ng-02", "source_ids": ["u3"]}]},
                {"cluster_id": "c2", "news_groups": []}, {"cluster_id": "c3"}]
        with tempfile.TemporaryDirectory() as d:
            path = d + "/c.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            got = tf.read_clusters(path)
            for block in (1, 2, 7, 64):  # the block ends inside a value, inside a string, between values
                self.assertEqual(tf.read_clusters(path, block), got)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n [ " + json.dumps(data, ensure_ascii=False)[1:-1].replace("},", "}\n ,\n") + "\n]\n")
            self.assertEqual(tf.read_clusters(path, 5), got)
            with open(path, "w", encoding="utf-8") as f:
                f.write("[]")
            self.assertEqual(tf.read_clusters(path, 1), [])
        urls = lambda cs: [[u for g in c.get("news_groups", []) for u in g.get("source_ids", [])] for c in cs]
        self.assertEqual(urls(got), urls(data))


if __name__ == "__main__":
    unittest.main()
