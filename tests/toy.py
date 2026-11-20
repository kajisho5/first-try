#!/usr/bin/env python3
"""A small tool with the faults first-try looks for, for the tests."""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import teach  # noqa: E402

ap = argparse.ArgumentParser(description="Rotate a picture by an angle.")
ap.add_argument("input")
ap.add_argument("--degrees", type=float, required=True, metavar="DEG", help="rotation angle in degrees, -45..45")
ap.add_argument("--fill-color", default="black", metavar="COLOR", help="what fills the corners")
ap.add_argument("--count", type=int, default=1, metavar="N", help="how many times")
ap.add_argument("--timeout", type=float, default=10, metavar="SECONDS", help="time limit")
ap.add_argument("--dry-run", action="store_true")
if "--plain" not in sys.argv:
    teach.install(ap)
else:
    sys.argv.remove("--plain")
args = ap.parse_args()
if not -45 <= args.degrees <= 45:
    ap.error("--degrees is -45..45")
if args.count > 1000:
    time.sleep(30)  # an unbounded count: the value is taken and worked on
print("ok")
