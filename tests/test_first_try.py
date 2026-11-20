import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import first_try  # noqa: E402


class FirstTryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.tools = self.write("tools.json", {
            "placeholders": {"clip": "in.png"}, "always": ["--dry-run"],
            "tools": [{"name": "toy", "run": [sys.executable, str(ROOT / "tests" / "toy.py")], "base": ["{clip}", "--degrees", "2"]},
                      {"name": "plain", "run": [sys.executable, str(ROOT / "tests" / "toy.py"), "--plain"], "about": "The same, without teach."}]})

    def write(self, name, doc):
        path = self.dir / name
        path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
        return str(path)

    def run_cli(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = first_try.main(list(argv))
        return code, out.getvalue()

    def test_brief_is_one_line_per_tool(self):
        code, out = self.run_cli("brief", self.tools)
        self.assertEqual(out.splitlines(), ["toy: Rotate a picture by an angle.", "plain: The same, without teach."])

    def test_a_blind_call_is_sorted_by_what_the_tool_answered(self):
        guesses = self.write("g.json", [
            {"tool": "toy", "request": "rotate 5", "argv": ["{clip}", "--degrees", "5"]},
            {"tool": "toy", "request": "rotate 5", "argv": ["{clip}", "--angle", "5"]},
            {"tool": "plain", "request": "rotate 5", "argv": ["{clip}", "--angle", "5"]},
            {"tool": "toy", "request": "rotate 90", "argv": ["{clip}", "--degrees", "90"]},
            {"tool": "toy", "request": "quickly", "argv": ["{clip}", "--degrees", "5", "--time", "3"]}])
        code, out = self.run_cli("run", self.tools, guesses, "--json")
        kinds = [row["kind"] for row in json.loads(out)]
        # the last one RAN: argparse read --time as --timeout, which is why a row that ran is read too
        self.assertEqual(kinds, ["ran", "taught", "silent", "refused", "ran"])

    def test_edges_finds_the_value_that_is_taken(self):
        code, out = self.run_cli("edges", self.tools, "--timeout", "3", "--json")
        rows = {(r["flag"], r["value"]): r["kind"] for r in json.loads(out)}
        self.assertEqual(rows[("--count", "1000000000")], "hung")
        self.assertEqual(rows[("--degrees", "1000000000")], "refused")
        self.assertEqual(rows[("--degrees", "0")], "ran")
        self.assertNotIn(("--dry-run", "0"), rows)

    def test_replay_fails_when_a_taught_line_is_no_longer_answered(self):
        line = {"tool": "toy", "argv": ["{clip}", "--angle", "5"], "must_say": ["--angle is not an option", "--degrees"], "status": "taught"}
        still_open = {"tool": "toy", "argv": ["{clip}", "--degrees", "5", "--time", "3"], "must_say": [], "status": "open"}
        ledger = self.write("s.jsonl", json.dumps(line) + "\n" + json.dumps(still_open) + "\n")
        self.assertEqual(self.run_cli("replay", self.tools, ledger)[0], 0)
        ledger = self.write("s.jsonl", json.dumps(dict(line, tool="plain")) + "\n")
        code, out = self.run_cli("replay", self.tools, ledger)
        self.assertEqual(code, 1)
        self.assertIn("does not say", out)


class TeachTests(unittest.TestCase):
    def parser(self):
        import argparse
        import teach
        ap = argparse.ArgumentParser(prog="t")
        ap.add_argument("--degrees", help="rotation angle in degrees")
        ap.add_argument("--fill-color", help="what fills the corners")
        ap.add_argument("--threshold", help="level in dB")
        ap.add_argument("--max-mb", help="the max size of the file")
        return ap, teach

    def test_hints(self):
        ap, teach = self.parser()
        hint = lambda *argv: teach.hints(ap, list(argv))
        self.assertEqual(hint("--angle", "5"), ["--angle is not an option of this tool; --degrees mention 'angle'"])
        self.assertEqual(hint("--pad-color=red"), ["--pad-color is not an option of this tool; did you mean --fill-color?"])
        self.assertEqual(hint("--treshold", "1"), ["--treshold is not an option of this tool; did you mean --threshold?"])
        self.assertEqual(hint("--max-size", "5"), ["--max-size is not an option of this tool; --max-mb mention 'max-size'"])
        self.assertEqual(hint("--verbose"), ["--verbose is not an option of this tool"])
        # an option, a shortened option and a negative number are left alone
        self.assertEqual(hint("--degrees", "-5", "--thresh", "-30"), [])


if __name__ == "__main__":
    unittest.main()
