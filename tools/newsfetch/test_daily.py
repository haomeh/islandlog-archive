"""T79: daily.py on fixtures. No network, no real crawl. The fixture repo holds stub tools (R346)."""

import contextlib
import datetime
import hashlib
import http.server
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from tools.newsfetch import daily

HERE = Path(__file__).resolve().parent
TODAY = "2026-10-31"

STUB_BACKFILL = r'''
import argparse, datetime, json, os, sys
from pathlib import Path
ap = argparse.ArgumentParser()
for a in ("--since", "--until", "--out-dir", "--log-dir", "--route"):
    ap.add_argument(a)
ap.add_argument("--source", action="append")
ap.add_argument("--no-resume", action="store_true")
a = ap.parse_args()
plan = json.load(open(os.environ["STUB_PLAN"], encoding="utf-8"))
sid = a.source[0]
spec = plan.get(sid, {})
out, logs = Path(a.out_dir), Path(a.log_dir)
out.mkdir(parents=True, exist_ok=True); logs.mkdir(parents=True, exist_ok=True)
with open(out / "args.txt", "a") as f:
    f.write(json.dumps({"id": sid, "since": a.since, "until": a.until, "route": a.route, "no_resume": a.no_resume, "hash_seed": os.environ.get("PYTHONHASHSEED"), "log": bool(os.environ.get("NEWSFETCH_REQUEST_LOG"))}) + "\n")
if spec.get("fail"):
    sys.exit(1)
host = spec.get("host", sid + ".example")
t0 = datetime.datetime(2026, 10, 31, 4, 30, 0, tzinfo=datetime.timezone.utc)
gap = spec.get("gap_ms", 1200)
with open(os.environ["NEWSFETCH_REQUEST_LOG"], "a") as f:
    for i in range(4):
        ts = (t0 + datetime.timedelta(milliseconds=gap * i)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        f.write(f"{ts} list {host} {i + 1} /p{i}\n")
    if spec.get("robots_abort"):
        f.write(f"{t0.strftime('%Y-%m-%dT%H:%M:%S.000')}Z list {host} ROBOTS-ABORT /private\n")
with open(logs / f"backfill-{sid}.log", "a") as f:
    f.write(f"2026-10-31T04:30:00.100 [INFO] newsfetch.crawler: GET {host} https://{host}/a\n")
    f.write(f"2026-10-31T04:30:01.300 [INFO] newsfetch.crawler: GET {host} https://{host}/b\n")
    for _ in range(spec.get("refused", 0)):
        f.write(f"2026-10-31T04:30:02.000 [WARNING] newsfetch.crawler: Refused https://{host}/x: refused address for {host}\n")
rows = spec.get("rows", [])
with open(out / f"news-{sid}.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("[]")
'''

STUB_CLUSTER = '''import os, sys
if os.environ.get("STUB_CLUSTER_FAIL"):
    sys.exit(3)
'''

STUB_TOPICS = r'''
import json, os, sys
from pathlib import Path
if os.environ.get("STUB_DRY_FAIL"):
    sys.exit(4)
args = sys.argv[1:]
corpus, clusters, seeds, root, report = args[:5]
today = args[args.index("--today") + 1]
Path(root, "events", "2026").mkdir(parents=True, exist_ok=True)
Path(root, "events", "2026", "ev-20261030-topic-aaaaaaaa.md").write_text("---\nid: ev-20261030-topic-aaaaaaaa\n---\n", encoding="utf-8")
Path(root, "tools", "newsfetch", "topic_state.json").write_text("{}", encoding="utf-8")
rep = {"stats": {"published": 1, "regate_checked": 3, "regate_passed": 2, "regate_failed": 1, "withdraw_blocked": 1, "withdrawn": 0},
       "published": [{"id": "ev-20260101-old", "title": "舊", "sources": 3, "key": "舊"}, {"id": "ev-20261030-topic-aaaaaaaa", "title": "新主題", "sources": 4, "key": "新"}],
       "regate": [{"id": "ev-20260101-old", "gate": None}, {"id": "ev-20260102-bad", "gate": "rejected_name_quality"}],
       "withdraw_blocked": {"ev-20260102-bad": "rejected_name_quality"},
       "withdraw_blocked_reason": {"ev-20260102-bad": "needs_user_approval"}, "today_seen": today}
Path(report).write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
print(json.dumps(rep["stats"]))
'''

FEEDS = [
    {"id": "aaa", "publisher": "甲報", "status": "ok", "type": "browser_list", "route": {"url": "https://aaa.example/list"}},
    {"id": "bbb", "publisher": "乙報", "status": "ok", "type": "dated_list", "route": {"url": "https://bbb.example/list/{date}"}},
    {"id": "ccc", "publisher": "丙報", "status": "blocked", "type": "sitemap", "route": {"url": "https://ccc.example/map"}},
]


def row(url, publisher, day, title=None):
    return {"url": url, "title": title or ("標題" + url[-4:]), "publisher": publisher, "published_on": day, "snippet": "",
            "fetched_on": "2026-10-31T00:00:00Z", "matched_terms": [], "negative": False, "topics": [], "clarification": False,
            "sensitive": False, "source_class": "news", "publisher_group": publisher}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")).stdout.strip()


def make_repo(root):
    repo = Path(root) / "repo"
    nf = repo / "tools" / "newsfetch"
    nf.mkdir(parents=True)
    (repo / "tools" / "__init__.py").write_text("")
    (nf / "__init__.py").write_text("")
    (nf / "feeds.json").write_text(json.dumps(FEEDS, ensure_ascii=False))
    (nf / "backfill.py").write_text(STUB_BACKFILL)
    (nf / "cluster.py").write_text(STUB_CLUSTER + (HERE / "cluster.py").read_text(encoding="utf-8"))
    (nf / "topics_full.py").write_text(STUB_TOPICS)
    (nf / "topic_seeds.json").write_text("[]")
    (repo / "events" / "2026").mkdir(parents=True)
    (repo / "events" / "2026" / "ev-20260101-old.md").write_text("---\nid: ev-20260101-old\n---\n")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def tree_hash(root):
    h = hashlib.sha256()
    for p in sorted(Path(root).rglob("*")):
        h.update(str(p.relative_to(root)).encode())
        if p.is_file() and not p.is_symlink():
            h.update(p.read_bytes())
    return h.hexdigest()


class ApiHandler(http.server.BaseHTTPRequestHandler):
    commit = ""

    def do_GET(self):
        body = json.dumps({"events": [], "archive_commit": self.commit}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class DailyBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo = make_repo(self.tmp)
        self.data = self.tmp / "news"
        (self.data / "corpus").mkdir(parents=True)
        self.corpus = self.data / "corpus" / "corpus.jsonl"
        old = [row("https://aaa.example/0001", "甲報", "2026-10-29"), row("https://bbb.example/0001", "乙報", "2026-10-30")]
        self.corpus.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in old), encoding="utf-8")
        self.plan_path = self.tmp / "plan.json"
        self.set_plan({"aaa": {"rows": [row("https://aaa.example/1001", "甲報", "2026-10-31"), row("https://aaa.example/1002", "甲報", "2026-10-31")]},
                       "bbb": {"rows": [row("https://bbb.example/1001", "乙報", "2026-10-31")]}})
        env = {"STUB_PLAN": str(self.plan_path)}
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)
        for k in ("STUB_CLUSTER_FAIL", "STUB_DRY_FAIL", "NEWSFETCH_VALIDATOR", "NEWSFETCH_SERVER_REPO", "ISLANDLOG_ARCHIVE_REPO"):
            os.environ.pop(k, None)
        self.server = http.server.HTTPServer(("127.0.0.1", 0), ApiHandler)
        ApiHandler.commit = git(self.repo, "rev-parse", "origin/main")
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def set_plan(self, plan):
        self.plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    def run_daily(self, *extra, today=TODAY, min_rows="1"):
        argv = ["--repo", str(self.repo), "--data-dir", str(self.data), "--today", today, "--min-new-rows", min_rows,
                "--api-url", f"http://127.0.0.1:{self.server.server_port}", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = daily.main(argv)
        return rc

    def report(self, day=TODAY):
        return json.loads((self.data / "reports" / f"{day}.json").read_text(encoding="utf-8"))


class EndToEndTest(DailyBase):
    def test_good_run_writes_both_reports(self):
        before = self.corpus.read_bytes()
        rc = self.run_daily()
        self.assertEqual(rc, 0)
        rep = self.report()
        md = (self.data / "reports" / f"{TODAY}.md").read_text(encoding="utf-8")
        self.assertEqual(rep["status"], "ok")
        names = [s["name"] for s in rep["steps"]]
        self.assertEqual(names, ["lock", "crawl", "merge", "cluster", "promote", "dry_run", "validate", "report"])
        for s in rep["steps"]:
            for key in ("start", "end", "rc", "status", "counts"):
                self.assertIn(key, s)
        status = {s["name"]: s["status"] for s in rep["steps"]}
        self.assertEqual(status["validate"], "BLOCKED")
        self.assertEqual(rep["new_rows_by_outlet"], {"甲報": 2, "乙報": 1})
        self.assertEqual(rep["zero_row_outlets"], [])
        self.assertEqual([t["id"] for t in rep["new_topics"]], ["ev-20261030-topic-aaaaaaaa"])
        self.assertEqual(rep["regate"]["counters"]["regate_failed"], 1)
        self.assertEqual(rep["withdraw_blocked"], [{"id": "ev-20260102-bad", "reason": "needs_user_approval", "gate": "rejected_name_quality"}])
        self.assertIn("enrich_candidates", rep)
        self.assertEqual(rep["lan_api"]["match"], True)
        self.assertIn("free_bytes", rep["disk"])
        self.assertIn("guard_refusals", rep)
        self.assertIn("robots_aborts", rep)
        self.assertGreaterEqual(rep["min_gap_ms_by_host"]["aaa.example"], 1099)
        self.assertIn("每日報告", md)
        self.assertIn("甲報", md)
        self.assertFalse((self.data / "ALERT").exists())
        self.assertEqual(len(self.corpus.read_text(encoding="utf-8").splitlines()), 5)
        self.assertTrue(self.corpus.read_bytes().startswith(before))
        state = json.loads((self.data / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["last_good_date"], TODAY)

    def test_crawl_options(self):
        self.run_daily()
        lines = [json.loads(l) for l in (self.data / "runs" / TODAY / "out" / "args.txt").read_text().splitlines()]
        by_id = {l["id"]: l for l in lines}
        self.assertEqual(sorted(by_id), ["aaa", "bbb"])
        self.assertEqual(by_id["aaa"]["since"], "2026-10-30")
        self.assertEqual(by_id["aaa"]["until"], TODAY)
        self.assertEqual(by_id["aaa"]["route"], "click")
        self.assertEqual(by_id["bbb"]["route"], "click")
        self.assertTrue(all(l["no_resume"] and l["log"] and l["hash_seed"] == "0" for l in lines))

    def test_state_date_sets_since(self):
        (self.data / "state.json").write_text(json.dumps({"last_good_date": "2026-10-28", "zero_streak": {}}))
        self.run_daily()
        lines = [json.loads(l) for l in (self.data / "runs" / TODAY / "out" / "args.txt").read_text().splitlines()]
        self.assertEqual({l["since"] for l in lines}, {"2026-10-28"})

    def test_repo_tree_and_dry_source_unchanged(self):
        before = tree_hash(self.repo)
        head, base = git(self.repo, "rev-parse", "HEAD"), git(self.repo, "rev-parse", "origin/main")
        self.assertEqual(self.run_daily(), 0)
        self.assertEqual(tree_hash(self.repo), before)
        self.assertEqual((git(self.repo, "rev-parse", "HEAD"), git(self.repo, "rev-parse", "origin/main")), (head, base))
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        dry = self.data / "runs" / TODAY / "dry"
        self.assertTrue((dry / "events" / "2026" / "ev-20261030-topic-aaaaaaaa.md").exists())
        self.assertFalse((self.repo / "events" / "2026" / "ev-20261030-topic-aaaaaaaa.md").exists())

    def test_zero_row_outlet_alerts_on_second_run(self):
        self.set_plan({"aaa": {"rows": []}, "bbb": {"rows": [row("https://bbb.example/2001", "乙報", "2026-10-31")]}})
        self.assertEqual(self.run_daily(), 0)
        self.assertEqual(self.report()["zero_row_outlets"], ["甲報"])
        self.assertFalse((self.data / "ALERT").exists())
        self.set_plan({"aaa": {"rows": []}, "bbb": {"rows": [row("https://bbb.example/2002", "乙報", "2026-11-01")]}})
        self.assertEqual(self.run_daily(today="2026-11-01"), 1)
        self.assertIn("甲報", (self.data / "ALERT").read_text(encoding="utf-8"))

    def test_row_floor_alert(self):
        self.assertEqual(self.run_daily(min_rows="50"), 1)
        self.assertIn("50", (self.data / "ALERT").read_text(encoding="utf-8"))
        self.assertEqual(len(self.corpus.read_text(encoding="utf-8").splitlines()), 5)

    def test_good_run_removes_alert(self):
        (self.data / "ALERT").write_text("old reason\n")
        self.assertEqual(self.run_daily(), 0)
        self.assertFalse((self.data / "ALERT").exists())

    def test_guard_refusals_and_robots_aborts_are_counted(self):
        self.set_plan({"aaa": {"rows": [row("https://aaa.example/1001", "甲報", "2026-10-31")], "refused": 2, "robots_abort": True},
                       "bbb": {"rows": [row("https://bbb.example/1001", "乙報", "2026-10-31")]}})
        self.assertEqual(self.run_daily(), 0)
        rep = self.report()
        self.assertEqual(rep["guard_refusals"], {"aaa.example": 2})
        self.assertEqual(rep["robots_aborts"], {"aaa.example": 1})

    def test_old_work_dirs_go_and_reports_are_kept_14(self):
        old = self.data / "runs" / "2026-10-01"
        old.mkdir(parents=True)
        (old / "x").write_text("x")
        (self.data / "reports").mkdir()
        for d in range(1, 21):
            for ext in ("json", "md"):
                (self.data / "reports" / f"2026-10-{d:02d}.{ext}").write_text("{}")
        self.assertEqual(self.run_daily(), 0)
        self.assertFalse(old.exists())
        self.assertTrue((self.data / "runs" / TODAY).exists())
        kept = sorted({p.stem for p in (self.data / "reports").iterdir()})
        self.assertEqual(len(kept), 14)
        self.assertEqual(kept[-1], TODAY)
        self.assertTrue(self.corpus.exists())


class FailureTest(DailyBase):
    def assert_failed(self, step):
        before = self.corpus.read_bytes()
        rc = self.run_daily()
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.corpus.read_bytes(), before)
        self.assertFalse(list(self.corpus.parent.glob("*.tmp")))
        alert = (self.data / "ALERT").read_text(encoding="utf-8")
        self.assertIn(step, alert)
        rep = self.report()
        self.assertEqual(rep["status"], "fail")
        by = {s["name"]: s for s in rep["steps"]}
        self.assertEqual(by[step]["status"], "fail")
        self.assertFalse((self.data / "state.json").exists() and json.loads((self.data / "state.json").read_text()).get("last_good_date") == TODAY)

    def test_crawl_process_fails(self):
        self.set_plan({"aaa": {"fail": True}, "bbb": {"rows": [row("https://bbb.example/1001", "乙報", "2026-10-31")]}})
        self.assert_failed("crawl")

    def test_gap_under_1099_ms_fails_crawl(self):
        self.set_plan({"aaa": {"gap_ms": 500, "rows": [row("https://aaa.example/1001", "甲報", "2026-10-31")]},
                       "bbb": {"rows": [row("https://bbb.example/1001", "乙報", "2026-10-31")]}})
        self.assert_failed("crawl")

    def test_merge_fails(self):
        self.set_plan({"aaa": {"rows": [{"title": "no url"}]}, "bbb": {"rows": []}})
        self.assert_failed("merge")

    def test_cluster_fails(self):
        os.environ["STUB_CLUSTER_FAIL"] = "1"
        self.assert_failed("cluster")

    def test_later_steps_are_skipped_after_failure(self):
        os.environ["STUB_CLUSTER_FAIL"] = "1"
        self.run_daily()
        by = {s["name"]: s["status"] for s in self.report()["steps"]}
        self.assertEqual(by["promote"], "skipped")
        self.assertEqual(by["dry_run"], "skipped")
        self.assertEqual(by["report"], "ok")

    def test_dry_run_fails_after_corpus_promotion(self):
        os.environ["STUB_DRY_FAIL"] = "1"
        self.assertEqual(self.run_daily(), 1)
        self.assertIn("dry_run", (self.data / "ALERT").read_text(encoding="utf-8"))
        self.assertEqual(len(self.corpus.read_text(encoding="utf-8").splitlines()), 5)


class LockTest(DailyBase):
    def test_lock_stops_second_run(self):
        before = self.corpus.read_bytes()
        fd = daily.acquire_lock(self.data / "daily.lock")
        self.assertIsNotNone(fd)
        try:
            self.assertEqual(self.run_daily(), daily.EXIT_LOCKED)
        finally:
            fd.close()
        self.assertEqual(self.corpus.read_bytes(), before)
        self.assertFalse((self.data / "runs").exists())
        self.assertFalse((self.data / "ALERT").exists())
        self.assertEqual(self.run_daily(), 0)

    def test_second_acquire_is_refused(self):
        a = daily.acquire_lock(self.data / "daily.lock")
        self.assertIsNone(daily.acquire_lock(self.data / "daily.lock"))
        a.close()
        b = daily.acquire_lock(self.data / "daily.lock")
        self.assertIsNotNone(b)
        b.close()


class FreshnessTest(DailyBase):
    def put_report(self, finished):
        (self.data / "reports").mkdir(exist_ok=True)
        (self.data / "reports" / "2026-10-30.json").write_text(json.dumps({"finished_at": finished, "status": "ok"}))

    def check(self, now):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            return daily.main(["--data-dir", str(self.data), "--check-freshness", "--now", now])

    def test_old_report_alerts(self):
        self.put_report("2026-10-30T04:30:00+08:00")
        self.assertEqual(self.check("2026-10-31T07:00:00+08:00"), 1)
        self.assertIn("26", (self.data / "ALERT").read_text(encoding="utf-8"))

    def test_fresh_report_is_quiet(self):
        self.put_report("2026-10-31T04:30:00+08:00")
        self.assertEqual(self.check("2026-10-31T20:00:00+08:00"), 0)
        self.assertFalse((self.data / "ALERT").exists())

    def test_no_report_alerts(self):
        self.assertEqual(self.check("2026-10-31T20:00:00+08:00"), 1)
        self.assertTrue((self.data / "ALERT").exists())


class HelperTest(unittest.TestCase):
    def test_host_gaps_from_logs(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "reqlog-a.jsonl").write_text("2026-10-31T04:30:00.000Z list h1.example 1 /a\n2026-10-31T04:30:01.100Z list h1.example 2 /b\n2026-10-31T04:30:01.900Z list h1.example 3 /c\n")
        (tmp / "backfill-a.log").write_text("2026-10-31T04:30:00.000 [INFO] newsfetch.crawler: GET h2.example https://h2.example/a\n2026-10-31T04:30:02.000 [INFO] newsfetch.crawler: GET h2.example https://h2.example/b\n")
        gaps = daily.host_gaps(tmp)
        self.assertEqual(gaps["h1.example"], 800)
        self.assertEqual(gaps["h2.example"], 2000)

    def test_enrich_candidates(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "events" / "2026").mkdir(parents=True)
        (tmp / "events" / "2026" / "ev-1.md").write_text("sources: src-20261030-a-11111111\n")
        clusters = [
            {"cluster_id": "c1", "title": "大案", "news_groups": [{"source_ids": ["u1", "u2", "u3"]}]},
            {"cluster_id": "c2", "title": "已發布", "news_groups": [{"source_ids": ["u4", "u5"]}]},
            {"cluster_id": "c3", "title": "舊案", "news_groups": [{"source_ids": ["u6", "u7"]}]},
            {"cluster_id": "c4", "title": "單篇", "news_groups": [{"source_ids": ["u8"]}]},
        ]
        mapping = {"u4": "src-20261030-a-11111111"}
        corpus = {"u1": ("甲", "2026-10-30"), "u2": ("乙", "2026-10-29"), "u3": ("甲", "2026-10-28"), "u4": ("甲", "2026-10-30"),
                  "u5": ("乙", "2026-10-30"), "u6": ("甲", "2026-09-01"), "u7": ("乙", "2026-09-01"), "u8": ("甲", "2026-10-30")}
        got = daily.enrich_candidates(clusters, mapping, corpus, tmp, TODAY, recent_days=3, limit=10)
        self.assertEqual([c["cluster_id"] for c in got], ["c1"])
        self.assertEqual(got[0]["publishers"], 2)
        self.assertEqual(got[0]["size"], 3)
        self.assertEqual(got[0]["newest"], "2026-10-30")


class DeployFilesTest(unittest.TestCase):
    def read(self, name):
        return (HERE / "deploy" / name).read_text(encoding="utf-8")

    def test_service_runs_daily_and_reads_the_repo_path_from_the_env_file(self):
        svc = self.read("islandlog-newsfetch.service")
        self.assertIn("tools.newsfetch.daily", svc)
        self.assertIn("EnvironmentFile=%h/.config/islandlog-newsfetch.env", svc)
        self.assertIn("$ISLANDLOG_ARCHIVE_REPO", svc)
        self.assertNotIn("islandlog/archive", svc)
        self.assertRegex(svc, r"TimeoutStartSec=([3-9]|\d\d)h")
        self.assertIn("ISLANDLOG_ARCHIVE_REPO=", self.read("newsfetch.env.example"))

    def test_timers(self):
        self.assertIn("OnCalendar=*-*-* 04:30:00 Asia/Taipei", self.read("islandlog-newsfetch.timer"))
        self.assertIn("Persistent=true", self.read("islandlog-newsfetch.timer"))
        self.assertIn("--check-freshness", self.read("islandlog-newsfetch-fresh.service"))
        self.assertIn("ReadWritePaths=%h/islandlog-news", self.read("islandlog-newsfetch-fresh.service"))


if __name__ == "__main__":
    unittest.main()
