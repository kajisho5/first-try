#!/usr/bin/env python3
"""first-try: can an agent that has not read your docs use your command-line tools?

    python3 first_try.py brief  tools.json                      # what a blind agent may read
    python3 first_try.py run    tools.json guesses.json         # run the calls it wrote
    python3 first_try.py edges  tools.json                      # 0, -1 and a huge value on every option
    python3 first_try.py replay tools.json stumbles.jsonl       # the ledger as a test (exit 1 on a miss)

tools.json describes the tools under test:

    {"placeholders": {"clip": "sample.mp4"},      values for {clip} and friends in any argument
     "always": ["--dry-run"],                     appended to every call, so nothing real happens
     "tools": [{"name": "cut",
                "run": ["python3", "scripts/cut.py"],
                "about": "Cut a time range out of a video.",   optional: else the first --help line
                "base": ["{clip}", "--start", "0", "--end", "1"],   a minimal valid call, for `edges`
                "output": ["-o", "{tmp}/out.mp4"]}]}                optional, added to every call

{tmp} is a fresh temporary folder. Standard library only; Python 3.9 or newer.
"""
import argparse
import collections
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EDGES = ("0", "-1", "1000000000")
OPTION = re.compile(r"(?<![\w-])--[a-z][\w-]*")


def load(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    return config, {t["name"]: t for t in config["tools"]}


def fill(args, values):
    return [re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), m.group(0))), str(a)) for a in args]


def help_text(tool, seconds):
    try:
        proc = subprocess.run([*tool["run"], "--help"], capture_output=True, text=True, timeout=seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"(no --help: {exc})"
    return proc.stdout or proc.stderr


def own_options(text):
    """Every --option the help names, and the ones the help shows taking a value."""
    names = set(OPTION.findall(text))
    valued = {m.group(1) for m in re.finditer(r"(--[a-z][\w-]*)[ =](?:[A-Z][A-Z0-9_]*\b|\{|<)", text)}
    return names, valued


def call(tool, argv, config, values, seconds):
    cmd = [*tool["run"], *fill(argv, values), *fill(tool.get("output", []), values), *config.get("always", [])]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds)
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        return None, f"no answer after {seconds} s"
    except OSError as exc:
        return 127, str(exc)


def answer_of(text):
    """What the tool said about the failure: the text from the last line that mentions an error
    (the usage block above it lists every option, so a name found there teaches nothing)."""
    lines = text.strip().splitlines()
    last = max((i for i, line in enumerate(lines) if re.search(r"\berror\b", line, re.I)), default=max(len(lines) - 3, 0))
    return "\n".join(lines[last:])


def judge(code, text, argv, names):
    """ran / hung / refused (not about a name) / taught (an own option is named) / silent."""
    if code is None:
        return "hung"
    if code == 0:
        return "ran"
    typed = [a.split("=")[0] for a in argv if OPTION.fullmatch(a.split("=")[0])]
    unknown = [f for f in typed if not any(n == f or n.startswith(f) for n in names)]
    if not unknown:
        return "refused"
    # taught: the answer speaks of the flag that was typed and names an option the tool does have.
    # "the following arguments are required: --degrees" names one and never mentions --angle.
    answer = answer_of(text)
    said = set(OPTION.findall(answer)) & names - set(typed)
    return "taught" if said and all(f in answer for f in unknown) else "silent"


def cmd_brief(args):
    config, tools = load(args.tools)
    for tool in tools.values():
        # the first paragraph of --help that is not the usage block
        about = tool.get("about") or next((" ".join(block.split()) for block in re.split(r"\n\s*\n", help_text(tool, args.timeout))
                                           if block.strip() and not block.lstrip().lower().startswith("usage")), "")
        print(f"{tool['name']}: {about[:200]}")
    return 0


def cmd_run(args):
    config, tools = load(args.tools)
    guesses = json.loads(Path(args.guesses).read_text(encoding="utf-8"))
    rows, names = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        values = dict(config.get("placeholders", {}), tmp=tmp)
        for guess in guesses:
            tool = tools.get(guess["tool"])
            if not tool:
                rows.append(dict(guess, kind="no such tool", answer=""))
                continue
            if tool["name"] not in names:
                names[tool["name"]] = own_options(help_text(tool, args.timeout))[0]
            code, text = call(tool, guess["argv"], config, values, args.timeout)
            rows.append(dict(guess, kind=judge(code, text, guess["argv"], names[tool["name"]]), answer=answer_of(text)[:600]))
    return report(rows, args, ("ran", "taught", "silent", "refused", "hung"), ("silent", "hung"),
                  lambda r: f"{r['tool']} {' '.join(r['argv'])[:70]}  ({r.get('request', '')[:50]})")


def cmd_edges(args):
    config, tools = load(args.tools)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        values = dict(config.get("placeholders", {}), tmp=tmp)
        for tool in tools.values():
            if "base" not in tool or (args.only and tool["name"] not in args.only.split(",")):
                continue
            shared = set(config.get("always", [])) | set(a for a in tool.get("output", []) if a.startswith("--"))
            for flag in sorted(own_options(help_text(tool, args.timeout))[1] - shared):
                for value in EDGES:
                    code, text = call(tool, [*tool["base"], f"{flag}={value}"], config, values, args.timeout)
                    kind = "hung" if code is None else "ran" if code == 0 else "refused"
                    rows.append({"tool": tool["name"], "flag": flag, "value": value, "kind": kind,
                                 "answer": (text.strip().splitlines() or [""])[-1][:300]})
    return report(rows, args, ("refused", "ran", "hung"), ("hung", "ran"), lambda r: f"{r['tool']} {r['flag']}={r['value']}")


def cmd_replay(args):
    config, tools = load(args.tools)
    missed = total = 0
    with tempfile.TemporaryDirectory() as tmp:
        values = dict(config.get("placeholders", {}), tmp=tmp)
        for number, line in enumerate(Path(args.ledger).read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("status", "taught") != "taught":
                continue
            total += 1
            code, text = call(tools[row["tool"]], row["argv"], config, values, args.timeout)
            lacking = [p for p in row["must_say"] if p not in answer_of(text)]
            if code == 0 or lacking:
                missed += 1
                print(f"line {number}: {row['tool']} {' '.join(row['argv'])}: "
                      + ("it ran" if code == 0 else "the answer does not say " + ", ".join(lacking)))
    print(f"{total} taught lines replayed, {missed} missed")
    return 1 if missed else 0


def report(rows, args, kinds, shown, describe):
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    counts = collections.Counter(r["kind"] for r in rows)
    print(f"{len(rows)} calls: " + ", ".join(f"{counts[k]} {k}" for k in kinds if counts[k] or k in ("ran", "refused")))
    for kind in shown:
        for row in (r for r in rows if r["kind"] == kind):
            print(f"{kind:8} {describe(row)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n", 2)[2])
    sub = ap.add_subparsers(dest="command", required=True)
    for name, fn, extra in (("brief", cmd_brief, ()), ("run", cmd_run, ("guesses",)), ("edges", cmd_edges, ()), ("replay", cmd_replay, ("ledger",))):
        p = sub.add_parser(name)
        p.add_argument("tools", help="tools.json")
        for positional in extra:
            p.add_argument(positional)
        p.add_argument("--timeout", type=float, default=45.0, help="seconds before a call counts as hung (default 45)")
        p.add_argument("--json", action="store_true", help="print every row as JSON")
        if name == "edges":
            p.add_argument("--only", help="comma-separated tool names")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
