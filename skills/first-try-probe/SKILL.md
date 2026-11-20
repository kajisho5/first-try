---
name: first-try-probe
description: Find where an agent that has not read the docs gets a command-line tool wrong on the first try — a fresh agent writes calls blind from each tool's name and one line about it, first_try.py runs them, the calls that ran are read as carefully as the ones that failed, each miss is taught through a help string or an error hint, and it is recorded in a ledger that a test replays. Use when asked how usable a CLI or tool set is for agents, before a tool is called stable, after options are added or renamed, or when someone reports that an agent "kept guessing the wrong flag".
---

# First-Try Probe

Tests call a tool the way its author spells it. An agent reads one line about the tool and types
what an experienced user of that kind of tool would type. This measures the gap, and turns each
miss into something that stays fixed.

You cannot write the calls yourself. Once you have read `--help` you know the names, and a guess
that knows the answer measures nothing.

## The loop

1. **Describe the tools.** Write `tools.json` (the format is at the top of `first_try.py`): how
   each tool is run, a placeholder for the input file, and the flag that makes a call harmless
   (`--dry-run` or its like) under `always`. If the tools have no such flag, point them at a
   scratch folder.

2. **Make the brief.** `python3 first_try.py brief tools.json > tools.txt` prints each tool's name
   and one line about it. That file is all the blind agent may see.

3. **Have a fresh agent write the calls.** Start an agent with no context of the project. Tell it,
   in these words or close to them: it must not open the source, `--help`, the README or any other
   file; it may read only `tools.txt`; for every tool it invents three realistic requests and
   writes the argument list it would type first, with `{clip}` (or your placeholder) where an
   input goes, as a JSON array of `{"tool", "request", "argv"}`. Ask for honest guesses, not odd
   ones. A different agent or model on the next round guesses differently, which is the point.

4. **Run them.** `python3 first_try.py run tools.json guesses.json` prints the counts and the
   misses; `--json` gives every row with the tool's answer.

5. **Read the rows that ran first.** A wrong call that exits 0 is the worst outcome, and no count
   shows it. For each, compare what happened with the request. Look for an option name the parser
   completed to another option (`--time` read as `--timeout`), a value taken in another unit, and a
   default that did the work instead of the flag.

6. **Sort the misses.**

   | Row | What it means | What to do |
   |---|---|---|
   | `silent` | an unknown flag, and the answer names no option of the tool | if the tool has an option for it, put the word the agent used into that option's help |
   | `taught` | the answer names an option the tool has | check it is the right one; a wrong pointer is worse than none |
   | `refused` | a missing file, a value out of range | usually the probe's own doing; skip unless the message has no way out |
   | `hung` | no answer in time | a defect: see the edge-probe skill |

   A flag for something the tool does not do has no pointer to give. Leave it.

7. **Teach without adding a name.** A help string that uses the word people reach for costs
   nothing and changes no interface. `teach.py` makes an argparse parser use it: for each unknown
   flag it names the options that share a word, a near spelling, and the options whose help
   mentions the word. Do not add an alias for every guess, and do not rename an option to match
   one: decide one name per meaning and let the answer do the teaching.

8. **Record each one.** Add a line to `stumbles.jsonl`: `tool`, `argv`, `got`, `right`,
   `must_say` (what the tool's answer has to contain), `status` (`taught` or `open`). Run
   `python3 first_try.py replay tools.json stumbles.jsonl` in CI: it exits 1 when a taught line is
   no longer answered. A stumble with no answer yet (a result that is wrong and says nothing) goes
   in as `open`.

9. **Run the probe again and report both counts**: calls that ran, and unknown-flag calls that
   were taught, before and after.

## What a round should not do

- Do not count a round as progress because `ran` went up. A change that makes a wrong call succeed
  is a regression.
- Do not reuse one round's guesses as the next round's measurement. They are in the ledger now.
- Do not paste the blind agent's file into a commit without reading every `argv`: it is model
  output, and it becomes a test.
- Do not let the blind agent run the tools. It writes calls; you run them.
