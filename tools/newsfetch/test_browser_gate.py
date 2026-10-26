"""R175 tests: the browser request gate. No network: node runs the gate with a fake clock."""

import json
import subprocess
import unittest
from pathlib import Path

BASE = Path(__file__).parent
LIST_BROWSER = (BASE / "list_browser.mjs").read_text(encoding="utf-8")


class TestBrowserGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        proc = subprocess.run(["node", str(BASE / "browser_gate_check.mjs")], capture_output=True, text=True, timeout=60, check=True)
        cls.out = json.loads(proc.stdout.strip().splitlines()[-1])

    def test_only_document_script_xhr_fetch_pass(self):
        d = self.out["decisions"]
        for kind in ("image", "stylesheet", "font", "media"):
            self.assertEqual(d[kind], "type", kind)
        for kind in ("document", "script", "xhr", "fetch"):
            self.assertEqual(d[kind], "", kind)

    def test_next_data_and_prefetch_are_blocked(self):
        d = self.out["decisions"]
        self.assertEqual(d["nextData"], "next-data")
        self.assertEqual(d["prefetch"], "prefetch")
        self.assertEqual(d["nextPrefetch"], "prefetch")

    def test_gap_is_at_least_1100_ms_for_parallel_requests(self):
        self.assertGreaterEqual(self.out["minGap"], 1100)

    def test_cap_per_host(self):
        a = [ok for host, ok in self.out["admitted"] if host == "a"]
        self.assertEqual(a.count(True), 4)
        self.assertEqual(a.count(False), 6)
        self.assertEqual(self.out["countA"], 4)

    def test_hosts_have_their_own_gate(self):
        b = [ok for host, ok in self.out["admitted"] if host == "b"]
        self.assertEqual(b, [True, True])

    def test_list_browser_uses_the_gate(self):
        self.assertIn("from './browser_gate.mjs'", LIST_BROWSER)
        self.assertIn("gate.admit(", LIST_BROWSER)
        self.assertEqual(LIST_BROWSER.count("route.continue()"), 1)
        self.assertLess(LIST_BROWSER.index("gate.admit("), LIST_BROWSER.index("route.continue()"))

    def test_stop_probe_accepts_python_group_names(self):
        self.assertIn("replace(/\\(\\?P</g", LIST_BROWSER)


if __name__ == "__main__":
    unittest.main()
