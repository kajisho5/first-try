---
name: edge-probe
description: Find the option values a command-line tool accepts without anyone having decided what they mean — zero, a negative number, a value far past anything real — by running first_try.py edges over every option that takes a value, reading each call that ran or hung against the option's help, and checking a few properties a tool should keep (doing it twice changes nothing more, an inverse returns the input's shape, the output is what the tool said). Use when looking for defects nobody has reported, before a tool is called stable, after a numeric option is added, or when a report says a tool "hung", "wrote a strange file" or "accepted nonsense".
---

# Edge Probe

Tests give each option the values its author had in mind. Most defects nobody has reported sit
just outside them: a 0 that one option reads as "off" and another as "no limit", a negative
length, a count of a billion.

The first-try probe asks whether an agent can find the right option. This asks what the tool does
once it has one and the value is wrong.

## The loop

1. **Give each tool a minimal call.** In `tools.json`, add `"base"`: the shortest argument list
   that is valid for the tool. Put the harmless-run flag under `always`.

2. **Run it.** `python3 first_try.py edges tools.json` gives every option the help shows taking a
   value the values 0, -1 and 1000000000, one at a time, on that call. It prints the calls that
   ran and the ones that gave no answer in time (`--timeout`, 45 s by default). A refusal is the
   good answer and is not printed.

3. **Drop what is decided.** Most rows that ran are fine, and the help tells you: 0 is the
   documented default, -1 is inside the range, the option does nothing without another flag, or
   the option takes text and "0" is text.

4. **Run what is left for real**, without the harmless-run flag, on a small input, under a
   timeout. A dry run does not reach the checks the real work makes. Sort the result:

   | What happened | What it needs |
   |---|---|
   | no answer | a refusal with the largest value that makes sense |
   | an output was written for a value outside the help's range | a refusal that names the range |
   | the engine underneath failed with its own message | the tool's own refusal, before the engine runs |
   | 0 or a negative ran and the help does not say what it means | the help says it, or the value is refused |

5. **Check the properties that cost nothing to check.** Each is two or three calls:
   - *Again changes nothing more.* A normaliser on its own output, a resize to the size it already
     has: the second result has the first's facts.
   - *An inverse returns the shape.* Reverse twice, rotate by +N then -N, speed up then slow down:
     length and layout come back.
   - *The result is what the tool said.* Measure the output and compare with what the tool
     reported.
   - *One more input changes one thing.* Joining N+1 pieces is longer than N by the last piece,
     and nothing else differs.
   A property that fails is a finding with its reproduction already written.

6. **Look for the shared step before fixing.** A value that hangs one tool usually hangs the
   others that take a count or a length. One bound in a shared place (a registered argument type,
   a common check) beats a check per tool.

## What a round should not do

- Do not report a row because it ran. In the round this came from, 213 of 558 ran and a handful
  were defects.
- Do not add a bound the help does not state. Decide the range, write it in the help, then refuse
  outside it, in that order.
- Do not run the real calls without a timeout or on a large input: a value that is taken can fill
  the disk before it fails.

## Where the method comes from

Probing what zero, empty and negative mean, and treating an easy wrong call as the design's
fault, follows Trail of Bits' `sharp-edges` skill; the properties in step 5 follow their
`property-based-testing` skill (github.com/trailofbits/skills, CC BY-SA 4.0). No text is taken
from either, and nothing here needs a test library.
