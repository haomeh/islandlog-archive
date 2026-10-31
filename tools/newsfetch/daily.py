#!/usr/bin/env python3
"""Daily news layer (T79, R346). It never changes public content and never writes to the repo tree.

Usage:
    python3 -m tools.newsfetch.daily [--repo DIR] [--data-dir DIR] [--today YYYY-MM-DD]
    python3 -m tools.newsfetch.daily --check-freshness [--data-dir DIR]

Steps, each logged with start, end, counts and rc:
    lock, crawl, merge, cluster, promote, dry_run, validate, report. Then the work dirs are cleaned.
1. lock      one run at a time (flock on DATA/daily.lock).
2. crawl     incremental crawl from the last good date, one process per host, NEWSFETCH_REQUEST_LOG set.
            The step fails when a host gap is under 1099 ms (R61).
3. merge     merge_corpus into a staged file. The corpus stays unchanged.
4. cluster   cluster.py --as-news-groups with PYTHONHASHSEED=0 (R149).
5. promote   rename the staged file onto the corpus. A failed step before this one leaves the corpus unchanged.
6. dry_run   git archive of the base ref in RUN/dry, then topics_full with --today set to the Taipei date.
7. validate  the validator if a binary or go with a server repo exists, else BLOCKED.
8. report    DATA/reports/DATE.json and .md. An alert writes DATA/ALERT and gives a non-zero exit.
Settings come from options, then from the environment (see deploy/newsfetch.env.example).
"""

import argparse
import collections
import datetime
import fcntl
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.newsfetch import merge_corpus

TAIPEI = ZoneInfo("Asia/Taipei")
MIN_GAP_MS = 1099                # R61: 1 request per 1.1 s per host, with a 1 ms tolerance
STALE_HOURS = 26
KEEP_REPORTS = 14
EXIT_LOCKED = 75
AUTO_ROUTE = {"ltn", "ettoday", "newtalk"}   # the same routes as T66; every other outlet uses the click route (R179)
RECENT_DAYS = 3
ENRICH_LIMIT = 20
SRC_ID = re.compile(r"src-\d{8}-[a-z0-9-]+-[0-9a-f]{8}")
REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.(json|md)$")
TIMEOUTS = {"crawl": 3 * 3600, "cluster": 3600, "dry_run": 3 * 3600, "validate": 1800}
logger = logging.getLogger("newsfetch.daily")


class StepFailed(Exception):
    def __init__(self, message, rc=1):
        super().__init__(message)
        self.rc = rc


# ---------------------------------------------------------------- small helpers

def iso(moment=None):
    return (moment or datetime.datetime.now(TAIPEI)).isoformat(timespec="seconds")


def write_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def acquire_lock(path):
    """Returns an open file that holds the lock, or None when another run holds it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    f.seek(0)
    f.truncate()
    f.write(f"{os.getpid()}\n")
    f.flush()
    return f


def git_env():
    return dict(os.environ, GIT_OPTIONAL_LOCKS="0")   # a read-only git call must not refresh the index


def git_out(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=git_env())
    return p.stdout.strip() if p.returncode == 0 else None


def tool_env(extra=None):
    env = dict(os.environ, PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    env.update(extra or {})
    return env


def run_cmd(cmd, cwd, env, timeout, out_path):
    """Runs a command with stdout and stderr in one file. Returns the rc (124 for a timeout)."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "ab") as out:
        try:
            return subprocess.run(cmd, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            return 124


# ---------------------------------------------------------------- crawl logs

def _stamp(text):
    return datetime.datetime.fromisoformat(text)


def host_gaps(logs_dir):
    """Minimum gap in ms per host over all request logs. Browser lines come from reqlog-*.jsonl, HTTP lines from backfill-*.log."""
    times = collections.defaultdict(list)
    for p in sorted(Path(logs_dir).glob("reqlog-*.jsonl")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            f = line.split()
            if len(f) >= 3 and f[3:4] != ["ROBOTS-ABORT"]:
                try:
                    times[("browser", f[2])].append(_stamp(f[0]))
                except ValueError:
                    pass
    pat = re.compile(r"(\S+) \[\w+\] newsfetch\.crawler: GET (\S+) ")
    for p in sorted(Path(logs_dir).glob("backfill-*.log")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = pat.match(line)
            if m:
                try:
                    times[("http", m[2])].append(_stamp(m[1]))
                except ValueError:
                    pass
    result = {}
    for (_, host), stamps in times.items():
        stamps.sort()
        gaps = [(b - a).total_seconds() * 1000 for a, b in zip(stamps, stamps[1:])]
        if gaps:
            result[host] = min(result.get(host, float("inf")), round(min(gaps)))
    return result


def count_refusals(logs_dir):
    """Guard refusals per host (netguard, url guard) and robots aborts per host (browser log and HTTP log)."""
    refused, aborted = collections.Counter(), collections.Counter()
    for p in Path(logs_dir).glob("backfill-*.log"):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"(?:Refused|Refusing non-HTTP URL:?) (\S+)", line)
            if m:
                refused[urllib.parse.urlsplit(m[1].rstrip(":")).hostname or "unknown"] += 1
            m = re.search(r"Blocked by robots\.txt: (\S+)", line)
            if m:
                aborted[urllib.parse.urlsplit(m[1]).hostname or "unknown"] += 1
    for p in Path(logs_dir).glob("reqlog-*.jsonl"):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            f = line.split()
            if len(f) >= 4 and f[3] == "ROBOTS-ABORT":
                aborted[f[2]] += 1
    return dict(refused), dict(aborted)


# ---------------------------------------------------------------- report parts

def load_meta(corpus, wanted):
    """url -> (publisher, published_on) for the wanted URLs only."""
    meta = {}
    with open(corpus, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["url"] in wanted:
                meta[row["url"]] = (row["publisher"], str(row.get("published_on", "")))
    return meta


def cluster_urls(cluster):
    return {u for g in cluster.get("news_groups", []) for u in g.get("source_ids", [])}


def published_source_ids(root):
    ids = set()
    for p in Path(root).glob("events/*/*.md"):
        ids.update(SRC_ID.findall(p.read_text(encoding="utf-8", errors="replace")))
    return ids


def enrich_candidates(clusters, mapping, meta, dry_root, today, recent_days=RECENT_DAYS, limit=ENRICH_LIMIT):
    """The largest clusters with a recent row and no published event. A list for a person: nothing is written."""
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=recent_days)).isoformat()
    published = published_source_ids(dry_root)
    out = []
    for c in clusters:
        urls = cluster_urls(c)
        if len(urls) < 2 or any(mapping.get(u) in published for u in urls):
            continue
        rows = [meta[u] for u in urls if u in meta]
        if not rows or max(d for _, d in rows) < cutoff:
            continue
        out.append({"cluster_id": c.get("cluster_id"), "title": c.get("title"), "size": len(urls),
                    "publishers": len({p for p, _ in rows}), "newest": max(d for _, d in rows)})
    out.sort(key=lambda r: (-r["size"], -r["publishers"], r["cluster_id"] or ""))
    return out[:limit]


def lan_api_state(api_url, origin_commit):
    url = api_url.rstrip("/") + "/v1/events?page_size=1"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            commit = json.load(resp).get("archive_commit")
    except (OSError, ValueError, urllib.error.URLError) as err:
        return {"url": url, "archive_commit": None, "origin_main": origin_commit, "match": None, "error": str(err)[:200]}
    match = bool(commit and origin_commit and (commit == origin_commit or origin_commit.startswith(commit) or commit.startswith(origin_commit)))
    return {"url": url, "archive_commit": commit, "origin_main": origin_commit, "match": match, "error": None}


def dir_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file() and not p.is_symlink())


def render_md(rep):
    L = [f"# 每日報告 {rep['date']}", "", f"- 狀態：{'正常' if rep['status'] == 'ok' else '失敗'}",
         f"- 開始：{rep['started_at']}；結束：{rep['finished_at']}",
         f"- origin/main：{rep.get('base_commit') or '無'}；工作樹 HEAD：{rep.get('repo_head') or '無'}"
         + ("（工作樹有未提交的變更）" if rep.get("repo_dirty") else ""), ""]
    if rep["alerts"]:
        L += ["## 警報", ""] + [f"- {a}" for a in rep["alerts"]] + [""]
    L += ["## 步驟", "", "| 步驟 | 狀態 | rc | 開始 | 結束 | 計數 |", "|---|---|---|---|---|---|"]
    for s in rep["steps"]:
        L.append(f"| {s['name']} | {s['status']} | {s['rc']} | {s['start']} | {s['end']} | {json.dumps(s['counts'], ensure_ascii=False)} |")
    L += ["", "## 各媒體新增列數", ""]
    L += [f"- {k}：{v}" for k, v in sorted(rep["new_rows_by_outlet"].items(), key=lambda kv: -kv[1])] or ["- 無"]
    L += ["", f"新增列數合計：{rep['new_rows_total']}。語料總列數：{rep['corpus_rows']}。", "",
          "## 零列媒體", ""]
    L += [f"- {k}（連續 {rep['zero_streak'].get(k, 0)} 次）" for k in rep["zero_row_outlets"]] or ["- 無"]
    L += ["", "## 抓取限制（R61）", ""]
    L += [f"- {h}：最小間隔 {g} ms" for h, g in sorted(rep["min_gap_ms_by_host"].items())] or ["- 無資料"]
    L += ["", f"- 防護拒絕（依主機）：{json.dumps(rep['guard_refusals'], ensure_ascii=False)}",
          f"- robots 中止（依主機）：{json.dumps(rep['robots_aborts'], ensure_ascii=False)}", "", "## 新主題", ""]
    L += [f"- {t['id']} {t['title']}（來源 {t['sources']}）" for t in rep["new_topics"]] or ["- 無"]
    c = rep["regate"]["counters"]
    L += ["", "## 重新檢查（re-gate）", "", f"- 計數：{json.dumps(c, ensure_ascii=False)}", "", "## 撤回被擋清單（withdraw_blocked）", ""]
    L += [f"- {w['id']}：{w['reason']}（{w.get('gate') or '無'}）" for w in rep["withdraw_blocked"]] or ["- 無"]
    L += ["", "## 補寫候選（給人看，不寫入）", ""]
    L += [f"- {e['cluster_id']} {e['title']}｜{e['size']} 則｜{e['publishers']} 家媒體｜最新 {e['newest']}" for e in rep["enrich_candidates"]] or ["- 無"]
    api = rep["lan_api"]
    state = "相同" if api["match"] else ("不同，LAN 快照過期" if api["match"] is False else f"無法讀取（{api.get('error')}）")
    L += ["", "## LAN API", "", f"- archive_commit：{api['archive_commit']}；origin/main：{api['origin_main']}；結果：{state}",
          "", "## 磁碟", "", f"- 資料夾：{rep['disk']['data_bytes']} bytes；語料：{rep['disk']['corpus_bytes']} bytes；剩餘空間：{rep['disk']['free_bytes']} bytes", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- the run

class Run:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = Path(cfg.data_dir)
        self.today = cfg.today
        self.run_dir = self.data / "runs" / self.today
        self.out_dir, self.logs = self.run_dir / "out", self.run_dir / "logs"
        self.dry = self.run_dir / "dry"
        self.corpus = self.data / "corpus" / "corpus.jsonl"
        self.staged = self.run_dir / "corpus.next.jsonl"
        self.clusters = self.run_dir / "clusters-ng.json"
        self.state_path = self.data / "state.json"
        self.state = read_json(self.state_path, {})
        self.steps, self.failed = [], None
        self.started = iso()
        self.feeds = [f for f in json.loads((Path(cfg.repo) / "tools/newsfetch/feeds.json").read_text(encoding="utf-8"))
                      if f.get("status") != "blocked"]
        self.crawled, self.merge_result, self.base_commit = [], None, None
        self.dry_report, self.new_topics, self.enrich = {}, [], []
        self.events_before = set()
        self.zero, self.streak = [], dict(self.state.get("zero_streak", {}))
        self.gaps, self.refused, self.aborted = {}, {}, {}

    # -- step runner
    def step(self, name, fn, always=False):
        rec = {"name": name, "start": iso(), "end": None, "rc": None, "status": None, "counts": {}}
        if self.failed and not always:
            rec.update(end=iso(), status="skipped")
        else:
            try:
                counts = dict(fn() or {})
                rec.update(status=counts.pop("_status", "ok"), rc=0, counts=counts)
            except StepFailed as err:
                rec.update(status="fail", rc=err.rc, error=str(err))
                self.failed = self.failed or name
            except Exception as err:   # a bug in a step is a failed step, not a crash
                rec.update(status="fail", rc=1, error=f"{type(err).__name__}: {err}")
                self.failed = self.failed or name
            rec["end"] = iso()
        self.steps[:] = [r for r in self.steps if r["name"] != name] + [rec]   # the report step puts itself in the report first
        print(f"{rec['end']} step {name} {rec['status']} rc={rec['rc']} {json.dumps(rec['counts'], ensure_ascii=False)} {rec.get('error', '')}", flush=True)
        return rec

    # -- steps
    def corpus_newest(self):
        newest = ""
        with open(self.corpus, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    newest = max(newest, str(json.loads(line).get("published_on", "")))
        return newest

    def crawl(self):
        if not self.corpus.exists():
            raise StepFailed(f"corpus not found: {self.corpus}")
        since = self.state.get("last_good_date") or self.corpus_newest()
        if not since:
            raise StepFailed("no start date")
        by_host = collections.OrderedDict()
        for feed in self.feeds:
            cr = (feed.get("click_route") or {}).get("urls") or []
            url = cr[0] if cr else (feed.get("route") or {}).get("url") or feed.get("latest_sitemap") or ""
            by_host.setdefault(urllib.parse.urlsplit(url).hostname or feed["id"], []).append(feed)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        rcs = {}

        def worker(host, feeds):
            reqlog = self.logs / f"reqlog-{host}.jsonl"
            for feed in feeds:
                route = "auto" if feed["id"] in AUTO_ROUTE else "click"
                cmd = [self.cfg.python, "-m", "tools.newsfetch.backfill", "--since", since, "--until", self.today,
                       "--out-dir", str(self.out_dir), "--log-dir", str(self.logs), "--source", feed["id"], "--route", route, "--no-resume"]
                rcs[feed["id"]] = run_cmd(cmd, self.cfg.repo, tool_env({"NEWSFETCH_REQUEST_LOG": str(reqlog)}),
                                          TIMEOUTS["crawl"], self.logs / f"run-{feed['id']}.out")

        threads = [threading.Thread(target=worker, args=(h, fs)) for h, fs in by_host.items()]   # one process per host at a time
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.crawled = [f for f in self.feeds if rcs.get(f["id"]) == 0]
        self.gaps = host_gaps(self.logs)
        self.refused, self.aborted = count_refusals(self.logs)
        bad = {k: v for k, v in rcs.items() if v != 0}
        low = {h: g for h, g in self.gaps.items() if g < MIN_GAP_MS}
        if bad or low:
            raise StepFailed(f"crawl rc {bad}; hosts under {MIN_GAP_MS} ms: {low}")
        return {"since": since, "until": self.today, "processes": len(by_host), "outlets": len(rcs), "min_gap_ms": min(self.gaps.values(), default=None)}

    def merge(self):
        files = [self.out_dir / f"news-{f['id']}.jsonl" for f in self.crawled if (self.out_dir / f"news-{f['id']}.jsonl").exists()]
        if not files:
            raise StepFailed("the crawl wrote no news file")
        try:
            self.merge_result = merge_corpus.merge(self.corpus, files, self.staged)
        except merge_corpus.MergeError as err:
            raise StepFailed(str(err)) from err
        pubs = {f["publisher"] for f in self.crawled}
        new = self.merge_result["new_by_outlet"]
        self.zero = sorted(p for p in pubs if not new.get(p))
        return {"rows_new": self.merge_result["rows_new"], "rows_total": self.merge_result["rows_total"], "sha256": self.merge_result["sha256"]}

    def cluster(self):
        cmd = [self.cfg.python, "-m", "tools.newsfetch.cluster", str(self.staged), str(self.clusters), "--as-news-groups"]
        rc = run_cmd(cmd, self.cfg.repo, tool_env(), TIMEOUTS["cluster"], self.logs / "cluster.out")
        if rc != 0:
            raise StepFailed(f"cluster rc {rc}", rc)
        return {"clusters": len(json.loads(self.clusters.read_text(encoding="utf-8")))}

    def promote(self):
        os.replace(self.staged, self.corpus)
        pubs = {f["publisher"] for f in self.crawled}
        for p in pubs:
            self.streak[p] = self.streak.get(p, 0) + 1 if p in self.zero else 0
        write_atomic(self.state_path, json.dumps({"last_good_date": self.today, "zero_streak": self.streak, "updated_at": iso()}, ensure_ascii=False, indent=1) + "\n")
        return {"rows_total": self.merge_result["rows_total"]}

    def dry_run(self):
        repo, ref = str(self.cfg.repo), self.cfg.base_ref
        self.base_commit = git_out(repo, "rev-parse", ref)
        if not self.base_commit:
            raise StepFailed(f"git ref not found: {ref}")
        shutil.rmtree(self.dry, ignore_errors=True)
        self.dry.mkdir(parents=True)
        arch = subprocess.Popen(["git", "-C", repo, "archive", "--format=tar", ref], stdout=subprocess.PIPE, env=git_env())
        tar = subprocess.run(["tar", "-x", "-C", str(self.dry)], stdin=arch.stdout)
        arch.stdout.close()
        if arch.wait() != 0 or tar.returncode != 0:
            raise StepFailed("git archive failed")
        self.events_before = {p.stem for p in self.dry.glob("events/*/*.md")}
        report = self.run_dir / "dry-report.json"
        cmd = [self.cfg.python, "-m", "tools.newsfetch.topics_full", str(self.corpus), str(self.clusters), "tools/newsfetch/topic_seeds.json",
               ".", str(report), "--today", self.today]
        rc = run_cmd(cmd, self.dry, tool_env(), TIMEOUTS["dry_run"], self.run_dir / "dry.out")
        if rc != 0:
            raise StepFailed(f"topics_full rc {rc}", rc)
        self.dry_report = read_json(report, {})
        self.new_topics = [p for p in self.dry_report.get("published", []) if p["id"] not in self.events_before]
        stats = self.dry_report.get("stats", {})
        return {"base_commit": self.base_commit, "published": stats.get("published"), "new_topics": len(self.new_topics)}

    def validate(self):
        binary = self.cfg.validator or shutil.which("islandlog")
        if binary:
            cmd, cwd, env = [binary, "validate", "--mode", "full", str(self.dry)], str(self.run_dir), tool_env()
        elif self.cfg.server_repo and shutil.which("go"):
            cmd, cwd = ["go", "run", ".", "validate", "--mode", "full", str(self.dry)], str(self.cfg.server_repo)
            env = tool_env({"GOCACHE": str(self.data / "cache" / "go-build")})
        else:
            return {"_status": "BLOCKED", "reason": "no validator binary and no server repo with go"}
        out = self.run_dir / "validate.out"
        rc = run_cmd(cmd, cwd, env, TIMEOUTS["validate"], out)
        last = (out.read_text(encoding="utf-8", errors="replace").strip().splitlines() or [""])[-1][:200]
        if rc != 0:
            raise StepFailed(f"validator rc {rc}: {last}", rc)
        return {"last_line": last}

    # -- report
    def alerts(self):
        reasons = [f"step {s['name']} failed: {s.get('error', '')}" for s in self.steps if s["status"] == "fail"]
        for p, n in sorted(self.streak.items()):
            if n >= 2:
                reasons.append(f"outlet {p} had 0 new rows in {n} runs")
        if self.merge_result and self.merge_result["rows_new"] < self.cfg.min_new_rows:
            reasons.append(f"new rows {self.merge_result['rows_new']} are under the floor {self.cfg.min_new_rows}")
        return reasons

    def build_report(self, alerts):
        repo = str(self.cfg.repo)
        new = self.merge_result["new_by_outlet"] if self.merge_result else {}
        stats = self.dry_report.get("stats", {})
        blocked = self.dry_report.get("withdraw_blocked", {})
        reasons = self.dry_report.get("withdraw_blocked_reason", {})
        origin = self.base_commit or git_out(repo, "rev-parse", self.cfg.base_ref)
        data_bytes = dir_bytes(self.data) if self.data.exists() else 0
        return {
            "date": self.today, "started_at": self.started, "finished_at": iso(), "status": "fail" if self.failed else "ok",
            "steps": self.steps, "alerts": alerts, "base_commit": origin, "repo_head": git_out(repo, "rev-parse", "HEAD"),
            "repo_dirty": bool(git_out(repo, "status", "--porcelain")),
            "new_rows_by_outlet": new, "new_rows_total": sum(new.values()), "corpus_rows": self.merge_result["rows_total"] if self.merge_result else None,
            "zero_row_outlets": self.zero, "zero_streak": self.streak,
            "min_gap_ms_by_host": self.gaps, "guard_refusals": self.refused, "robots_aborts": self.aborted,
            "new_topics": self.new_topics,
            "regate": {"counters": {k: v for k, v in stats.items() if k.startswith("regate_") or k.startswith("withdraw")},
                       "failed": [r["id"] for r in self.dry_report.get("regate", []) if r.get("gate")]},
            "withdraw_blocked": [{"id": k, "reason": reasons.get(k, "unknown"), "gate": v} for k, v in sorted(blocked.items())],
            "enrich_candidates": self.enrich,
            "lan_api": lan_api_state(self.cfg.api_url, origin),
            "disk": {"data_bytes": data_bytes, "corpus_bytes": self.corpus.stat().st_size if self.corpus.exists() else 0,
                     "free_bytes": shutil.disk_usage(self.data if self.data.exists() else "/").free},
        }

    def compute_enrich(self):
        if not (self.clusters.exists() and self.dry.exists()):
            return []
        clusters = json.loads(self.clusters.read_text(encoding="utf-8"))
        wanted = set()
        for c in clusters:
            urls = cluster_urls(c)
            if len(urls) >= 2:
                wanted |= urls
        mapping = read_json(str(self.clusters) + ".sources.json", {})
        return enrich_candidates(clusters, mapping, load_meta(self.corpus, wanted), self.dry, self.today)

    def report(self):
        try:
            self.enrich = self.compute_enrich()
        except (OSError, ValueError, KeyError) as err:
            logger.warning("enrich candidates failed: %s", err)
        self.steps.append({"name": "report", "start": iso(), "end": iso(), "rc": 0, "status": "ok", "counts": {}})
        alerts = self.alerts()
        rep = self.build_report(alerts)
        self.steps[-1]["counts"] = {"alerts": len(alerts)}
        write_atomic(self.data / "reports" / f"{self.today}.json", json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
        write_atomic(self.data / "reports" / f"{self.today}.md", render_md(rep))
        if alerts:
            write_atomic(self.data / "ALERT", f"{iso()}\n" + "\n".join(alerts) + "\n")
        else:
            (self.data / "ALERT").unlink(missing_ok=True)
        self._alerts = alerts
        return {"alerts": len(alerts)}

    def cleanup(self):
        runs = self.data / "runs"
        for p in runs.iterdir() if runs.exists() else []:
            if p.name != self.today and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
        reports = self.data / "reports"
        names = sorted({m[1] for p in reports.iterdir() if (m := REPORT_NAME.match(p.name))}) if reports.exists() else []
        for day in names[:-KEEP_REPORTS]:
            for ext in ("json", "md"):
                (reports / f"{day}.{ext}").unlink(missing_ok=True)

    def go(self):
        self._alerts = []
        shutil.rmtree(self.run_dir, ignore_errors=True)   # a rerun on the same day starts clean
        self.run_dir.mkdir(parents=True)
        self.step("crawl", self.crawl)
        self.step("merge", self.merge)
        self.step("cluster", self.cluster)
        self.step("promote", self.promote)
        self.step("dry_run", self.dry_run)
        self.step("validate", self.validate)
        rec = self.step("report", self.report, always=True)
        if rec["status"] == "fail":   # no report file: the alert file still has to exist
            self._alerts = self.alerts()
            write_atomic(self.data / "ALERT", f"{iso()}\n" + "\n".join(self._alerts) + "\n")
        try:
            self.cleanup()
        except OSError as err:
            print(f"cleanup failed: {err}", flush=True)
        return 1 if (self.failed or self._alerts) else 0


# ---------------------------------------------------------------- freshness and entry

def check_freshness(data_dir, now):
    data = Path(data_dir)
    reports = sorted(p for p in (data / "reports").glob("*.json")) if (data / "reports").exists() else []
    if not reports:
        reason = "no report found"
    else:
        last = reports[-1]
        finished = read_json(last, {}).get("finished_at")
        try:
            moment = datetime.datetime.fromisoformat(finished)
        except (TypeError, ValueError):
            moment = datetime.datetime.fromtimestamp(last.stat().st_mtime, TAIPEI)
        age = (now - moment).total_seconds() / 3600
        reason = f"the newest report {last.name} is {age:.1f} hours old (limit {STALE_HOURS})" if age > STALE_HOURS else None
    if reason:
        write_atomic(data / "ALERT", f"{iso(now)}\nstale: {reason}\n")
        print(f"ALERT {reason}", flush=True)
        return 1
    print("fresh", flush=True)
    return 0


def main(argv=None):
    env = os.environ
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=env.get("ISLANDLOG_ARCHIVE_REPO"))
    ap.add_argument("--data-dir", default=env.get("NEWSFETCH_DATA_DIR") or str(Path.home() / "islandlog-news"))
    ap.add_argument("--today", help="Taipei date YYYY-MM-DD (default: now)")
    ap.add_argument("--base-ref", default=env.get("NEWSFETCH_BASE_REF", "origin/main"))
    ap.add_argument("--api-url", default=env.get("NEWSFETCH_API_URL", "http://localhost:8080"))
    ap.add_argument("--min-new-rows", type=int, default=int(env.get("NEWSFETCH_MIN_NEW_ROWS", "300")))
    ap.add_argument("--validator", default=env.get("NEWSFETCH_VALIDATOR"))
    ap.add_argument("--server-repo", default=env.get("NEWSFETCH_SERVER_REPO"))
    ap.add_argument("--python", default=env.get("NEWSFETCH_PYTHON") or sys.executable)
    ap.add_argument("--check-freshness", action="store_true")
    ap.add_argument("--now", help="ISO time for --check-freshness (tests)")
    args = ap.parse_args(argv)
    if args.check_freshness:
        now = datetime.datetime.fromisoformat(args.now) if args.now else datetime.datetime.now(TAIPEI)
        return check_freshness(args.data_dir, now)
    if not args.repo:
        print("set ISLANDLOG_ARCHIVE_REPO or --repo", file=sys.stderr)
        return 2
    args.today = args.today or datetime.datetime.now(TAIPEI).date().isoformat()
    datetime.date.fromisoformat(args.today)
    lock = acquire_lock(Path(args.data_dir) / "daily.lock")
    if lock is None:
        print(f"{iso()} step lock fail: another run holds the lock", flush=True)
        return EXIT_LOCKED
    try:
        print(f"{iso()} step lock ok", flush=True)
        run = Run(args)
        run.steps.append({"name": "lock", "start": iso(), "end": iso(), "rc": 0, "status": "ok", "counts": {}})
        return run.go()
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
