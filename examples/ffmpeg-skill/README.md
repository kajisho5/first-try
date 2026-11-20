# The round this came from: ffmpeg-skill

[ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) is 42 Python tools around FFmpeg, made for
coding agents. Its tests called every tool the way its author spells it. On 2026-11-20 an agent
that had seen only each tool's name and one line about it wrote three calls per tool.

| | Calls | Result |
|---|---|---|
| Blind calls, before any change | 126 | 27 ran |
| ... that used an option the tool does not have | 64 | 33 were pointed at the tool's own option |
| The same 64 after help strings and one shared hint changed | 64 | 49 were pointed at the tool's own option |
| Edge values (0, -1, 1000000000) on every numeric option of 28 tools | 558 | 344 refused, 213 ran, 1 hung |

What the numbers did not show, and reading the rows did:

- **A call that ran and was wrong.** `freeze.py --time 3 --hold 1` exited 0. argparse had read
  `--time` as the start of `--timeout`: the run got a three second limit, froze the last frame
  instead of the one at 3 s, and said nothing.
- **Two options that hang.** `cropdetect.py --samples 1000000000` and
  `graphics.py --template countdown --from 1000000000` gave no answer.
- **The reason for most misses was not the agent.** The same thing had several names across the
  tools (an angle was `--angle`, `--rotate` and `--degrees`), and one name meant several things
  (`--scale` was pixels on one tool and a factor on another).

Files here:

- `guesses.json`: the 126 blind calls, as the agent wrote them. They are model output.
- `stumbles.jsonl`: the ledger at the end of the day, 78 lines. `taught` lines are replayed by
  that project's tests.

The fixes are in ffmpeg-skill 4.1.1 and 4.1.2; the open edge-value findings are its issue #645.
