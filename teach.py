"""teach: make an argparse parser answer a guessed option name with the right one.

    import teach
    parser = argparse.ArgumentParser(...)
    parser.add_argument("--degrees", help="rotation angle in degrees")
    teach.install(parser)

    $ tool --angle 5
    tool: error: unrecognized arguments: --angle 5
    --angle is not an option of this tool; --degrees mention 'angle'

For each --flag on the command line the parser does not have, the usage error gains one line:
options that share a word with it (--pad-color, --fill-color), else a near spelling
(--treshold, --threshold), and the options whose help text uses the word. A help-text match is
reported as "mention", never as "did you mean": the loose guess is worse than none.

It also says so when a required option is missing, where argparse names only that one and never
reaches the unknown flag. Standard library only.
"""
import difflib
import re
import sys

STOP = {"to", "at", "in", "no", "min", "max", "from"}  # too common to mean two options are related


def hints(parser, argv=None):
    acts = {o: a for o, a in parser._option_string_actions.items() if o.startswith("--")}
    lines = []
    for flag in dict.fromkeys(a.split("=")[0] for a in (sys.argv[1:] if argv is None else argv) if re.match(r"--[a-z]", a)):
        if any(o.startswith(flag) for o in acts):
            continue  # an option, or a shortened one argparse will take
        word = flag[2:] if len(flag) > 5 and flag != "--from" else "\0"
        near = [o for o in acts if set(flag[2:].split("-")) - STOP & set(o[2:].split("-"))][:5] \
            or difflib.get_close_matches(flag, acts, 2, 0.85)
        said = [o for o, a in acts.items() if o not in near
                and re.search(rf"\b{re.escape(word)}".replace("\\-", "[- ]"), str(a.help or ""), re.I)][:2]
        lines.append(f"{flag} is not an option of this tool"
                     + (f"; did you mean {' or '.join(near)}?" if near else "")
                     + (f"; {' and '.join(said)} mention '{word}'" if said else ""))
    return lines


def install(parser):
    """Wrap parser.error so every usage error carries the hints."""
    plain = parser.error

    def error(message):
        plain("\n".join([message, *hints(parser)]))

    parser.error = error
    return parser
