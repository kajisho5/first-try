# first-try

**Can an agent that has not read your docs use your command-line tools on the first try?**

Your tests call each tool the way you spell it. An agent reads one line about the tool and types
what it expects the option to be called. `first-try` measures that gap, and turns every miss into
something that stays fixed.

When this was first run, on 42 tools that were built for agents, **27 of 126 blind calls ran**.
One of the 27 ran and was wrong.

## What is here

| | |
|---|---|
| `first_try.py` | Four commands: `brief` (what a blind agent may read), `run` (run the calls it wrote), `edges` (0, -1 and a huge value on every option), `replay` (the ledger of misses as a test). |
| `teach.py` | Twenty lines that make an argparse parser answer a guessed option name with the right one. |
| `skills/first-try-probe` | The loop for an agent: have a fresh agent guess, run, read, teach, record. |
| `skills/edge-probe` | The loop for values: what does the tool do with a zero, a negative, a billion? |
| `examples/ffmpeg-skill` | The round this came from, with its 126 guesses and its ledger. |

Python 3.10 or newer, standard library only. The skills are plain `SKILL.md` files: copy the two
folders into your agent's skills directory (`.claude/skills/` for Claude Code).

## Five minutes

Describe your tools in `tools.json`:

```json
{"placeholders": {"clip": "sample.mp4"},
 "always": ["--dry-run"],
 "tools": [{"name": "cut",
            "run": ["python3", "scripts/cut.py"],
            "base": ["{clip}", "--start", "0", "--end", "1"],
            "output": ["-o", "{tmp}/out.mp4"]}]}
```

1. `python3 first_try.py brief tools.json > tools.txt`
2. Give `tools.txt`, and nothing else, to a fresh agent. Ask it for three realistic requests per
   tool and the arguments it would type first, as JSON: `[{"tool", "request", "argv"}]`.
3. `python3 first_try.py run tools.json guesses.json`

```
126 calls: 33 ran, 53 taught, 10 silent, 30 refused
silent   deinterlace {clip} --mode bwdif --double-rate  (deinterlace to double frame rate)
```

| Row | Meaning |
|---|---|
| `ran` | exit 0. Read these: a call can run and be wrong. |
| `taught` | an unknown flag, and the tool's answer names one of its own options |
| `silent` | an unknown flag, and the answer names none |
| `refused` | any other refusal |
| `hung` | no answer in time |

For values, add a minimal valid call as `"base"` and run `python3 first_try.py edges tools.json`.

## Making a miss stay fixed

A guess is not a bug in the agent. If three agents type `--angle` and your option is `--degrees`,
the tool can say so:

```python
import teach
teach.install(parser)
```

```
$ tool in.png --angle 5
tool: error: the following arguments are required: --degrees
--angle is not an option of this tool; --degrees mention 'angle'
```

`teach` looks at each unknown flag and names the options that share a word with it, a near
spelling, and the options whose help text uses the word. So the cheapest fix is often one word in
a help string. It reports a help-text match as "mention", never as "did you mean": a loose guess
is worse than none.

Then write the miss down, one JSON line each, and replay the file in CI:

```json
{"tool": "rotate", "argv": ["{clip}", "--angle", "5"], "got": "only: --degrees is required", "right": "--degrees 5", "must_say": ["--angle is not an option", "--degrees"], "status": "taught"}
```

```
python3 first_try.py replay tools.json stumbles.jsonl    # exit 1 when a taught line is no longer answered
```

## What it found the first time

- **A call that ran and was wrong.** `freeze.py --time 3 --hold 1` exited 0. argparse had read
  `--time` as the start of `--timeout`. The run got a three second limit and froze the wrong frame.
  argparse does this for any unambiguous start of an option name, on every parser that has not
  turned it off.
- **Options that hang** on a count of a billion.
- **Why agents guessed wrong**: the same thing had three names across the tools, and one name
  meant two things. That is a property of the tools, and it showed up only when something that
  did not know the names tried to use them.

The numbers and the files are in [examples/ffmpeg-skill](examples/ffmpeg-skill/README.md).

## What it does not do

- It does not write the guesses. A fresh agent does, and it must not be the one that knows the
  code. Reusing one round's guesses as the next round's measurement measures nothing.
- It does not judge a row. `ran` is not a pass and `refused` is not a failure until someone reads
  it.
- `edges` tries every option whose help shows it taking a value. It does not know which are
  numbers, so a text option that takes "0" as text shows up as `ran`.
- `teach.py` is for argparse. The method is not: any parser with an error hook can do the same.

## Related work

The idea of handing a tool to a model with fresh eyes is not new.
[Fresh Eyes as a Service](https://recursion.wtf/posts/llms_as_ux_testers/) describes it for CLI
ergonomics. [cli-agent-lint](https://github.com/Camil-H/cli-agent-lint) checks a CLI against rules
for agent use, and [AXI](https://github.com/kunchenguid/axi) is a set of design principles for
tools agents call. The edge-value loop follows Trail of Bits' `sharp-edges` and
`property-based-testing` [skills](https://github.com/trailofbits/skills).

What this adds is the rest of the loop: the misses become answers the tool gives, and a ledger a
test replays, so the next agent that types the same thing is told.

## Tests

```
python3 -m unittest discover -s tests
```

MIT licensed. [日本語の説明](README.ja.md)
