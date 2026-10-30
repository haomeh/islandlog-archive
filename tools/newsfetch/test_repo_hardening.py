"""T64 tests: repo files that guard the repo (F-02 CODEOWNERS, F-06 pinned action, F-07 note, F-08 unit sandbox)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def owner_of(path):
    """The owner of path by the last matching rule. Only the rule forms used in this file are handled."""
    owner = None
    for line in (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *owners = line.split()
        if pattern == "*" or (pattern.endswith("/") and path.startswith(pattern.lstrip("/"))) or pattern.lstrip("/") == path:
            owner = owners
    return owner


class CodeownersTest(unittest.TestCase):
    def test_ci_and_crawler_files_need_a_maintainer(self):
        for path in (".github/workflows/validate.yml", ".github/CODEOWNERS", "tools/newsfetch/crawler.py", "tools/newsfetch/filter.py"):
            self.assertEqual(owner_of(path), ["@haomeh/maintainers"], path)

    def test_the_content_rule_is_unchanged(self):
        self.assertEqual(owner_of("events/2026/ev-20261023-a.md"), ["@haomeh/editors"])
        self.assertEqual(owner_of("taxonomy/banned_terms.yaml"), ["@haomeh/senior-editors"])


class WorkflowPinTest(unittest.TestCase):
    def test_every_action_uses_a_commit_sha_and_a_version_comment(self):
        text = (ROOT / ".github" / "workflows" / "validate.yml").read_text(encoding="utf-8")
        uses = re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", text, re.M)
        self.assertTrue(uses)
        for ref, rest in uses:
            self.assertRegex(ref, r"@[0-9a-f]{40}$", ref)
            self.assertRegex(rest, r"#\s*v\d", ref)


class ContributingNoteTest(unittest.TestCase):
    def test_manual_check_note(self):
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("islandlog validate", text)
        self.assertRegex(text, r"(?i)until the first server release")
        self.assertRegex(text, r"(?i)by hand")


class ServiceSandboxTest(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "tools" / "newsfetch" / "deploy" / "islandlog-newsfetch.service").read_text(encoding="utf-8")
        self.service = text.split("[Service]", 1)[1]

    def test_sandbox_lines(self):
        for line in ("NoNewPrivileges=yes", "ProtectSystem=strict", "PrivateTmp=yes"):
            self.assertIn(line, self.service)

    def test_write_paths_are_the_out_log_and_cache_folders(self):
        m = re.search(r"^ReadWritePaths=(.+)$", self.service, re.M)
        self.assertIsNotNone(m)
        self.assertIn("%h/islandlog-news", m.group(1))
        self.assertIn("tools/newsfetch/.cache", m.group(1))


if __name__ == "__main__":
    unittest.main()
