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
    def test_new_events_require_what_how_why_body(self):
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        rule = text.split("## 2A. New event body (R488, C7)", 1)[-1].split("\n## ", 1)[0]
        for requirement in (
            "Events created after 2026-11-06 must have both body sections below.",
            "`## 各方理由`",
            "For each main actor, give the reason stated by a cited source.",
            "If no source gives a reason, state that no public reason was found for that actor.",
            "`## 公共影響`",
            "State the effect on the public that a cited source states.",
            "Do not add the agent's own view.",
            "Each sentence in these sections must have attribution and a source marker: `[@src-YYYYMMDD-slug]`.",
            "Existing events do not change under this rule.",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, rule)

    def test_manual_check_note(self):
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("CI uses the pinned server image `main-ee91d722`.", text)
        self.assertIn("If the token is absent, CI warns and skips validation. Fork PRs do not receive secrets.", text)
        self.assertIn("Reviewers must run `islandlog validate .` on the PR branch before approval when CI skips validation.", text)


class ServiceSandboxTest(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "tools" / "newsfetch" / "deploy" / "islandlog-newsfetch.service").read_text(encoding="utf-8")
        self.service = text.split("[Service]", 1)[1]

    def test_sandbox_lines(self):
        for line in ("NoNewPrivileges=yes", "ProtectSystem=strict", "PrivateTmp=yes"):
            self.assertIn(line, self.service)

    def test_write_path_is_the_data_folder_only(self):
        # T79: the daily layer writes below ~/islandlog-news and never in the repo tree. The cache goes to the run folder.
        m = re.search(r"^ReadWritePaths=(.+)$", self.service, re.M)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).split(), ["%h/islandlog-news"])


if __name__ == "__main__":
    unittest.main()
