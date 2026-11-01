"""T88 tests: the report-label workflow (R388) keeps the least permission and never reads issue text."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT = (ROOT / ".github" / "workflows" / "report-label.yml").read_text(encoding="utf-8")
CODE = "\n".join(line for line in TEXT.splitlines() if not line.lstrip().startswith("#"))


class ReportLabelWorkflowTest(unittest.TestCase):
    def test_the_trigger_is_issues_opened_only(self):
        self.assertEqual(len(re.findall(r"(?m)^on:", CODE)), 1)
        match = re.search(r"(?m)^on:\n((?:[ ]+.*\n|\n)*)", CODE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip("\n"), "  issues:\n    types: [opened]")

    def test_the_top_permissions_are_issues_write_only(self):
        match = re.search(r"(?m)^permissions:\n((?:  .+\n)+)", CODE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1).strip(), "issues: write")
        self.assertNotRegex(CODE, r"(?m)^\s{4,}permissions:")

    def test_there_is_no_checkout_and_no_third_party_action(self):
        self.assertNotIn("actions/checkout", CODE)
        self.assertNotRegex(CODE, r"(?m)^\s*-?\s*uses:")

    def test_the_only_secret_is_the_default_token(self):
        self.assertNotIn("secrets.", CODE)
        self.assertIn("GH_TOKEN: ${{ github.token }}", CODE)

    def test_the_condition_reads_the_app_slug_and_a_non_empty_variable(self):
        self.assertIn("vars.REPORT_APP_SLUG != ''", CODE)
        self.assertIn("github.event.issue.performed_via_github_app.slug == vars.REPORT_APP_SLUG", CODE)
        self.assertIn(
            "if: vars.REPORT_APP_SLUG != '' && github.event.issue.performed_via_github_app.slug == vars.REPORT_APP_SLUG\n",
            CODE,
        )
        self.assertNotIn("||", CODE)

    def test_the_runner_version_is_pinned(self):
        self.assertRegex(CODE, r"runs-on: ubuntu-\d+\.\d+")
        self.assertNotIn("ubuntu-latest", CODE)

    def test_no_expression_reads_the_issue_title_or_body(self):
        for expr in re.findall(r"\$\{\{(.*?)\}\}", CODE, re.S):
            self.assertNotRegex(expr, r"issue\.(title|body)|\.title|\.body|head_commit|comment")
        self.assertNotRegex(CODE, r"issue\.(title|body)")

    def test_the_issue_number_goes_through_an_env_value(self):
        run = CODE.split("run: |", 1)[1]
        self.assertNotIn("${{", run)
        self.assertIn('"$ISSUE_NUMBER"', run)
        self.assertIn("--add-label news-report", run)
        self.assertIn("ISSUE_NUMBER: ${{ github.event.issue.number }}", CODE)


if __name__ == "__main__":
    unittest.main()
