"""Fixture self-check: render scripts/fixture.json to a directory, then run
`python scripts/selfcheck.py <dir>`. Fails (exit 1) on any mismatch."""

import json
import os
import re
import sys
from typing import NoReturn
from xml.etree import ElementTree as ET

EXPECTED_FILES = (
    "chalk-hero.svg",
    "chalk-cricket.svg",
    "chalk-now.svg",
    "chalk-ledger.svg",
    "chalk-build-1.svg",
    "chalk-build-2.svg",
    "chalk-build-3.svg",
    "chalk-build-4.svg",
)


def fail(message: str) -> NoReturn:
    print(f"selfcheck: FAIL: {message}")
    sys.exit(1)


def main() -> int:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    if not out_dir or not os.path.isdir(out_dir):
        fail("usage: selfcheck.py <rendered out-dir>")
    fixture_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixture.json")
    with open(fixture_path, encoding="utf-8") as handle:
        fixture = json.load(handle)
    cal = fixture["contributionsCollection"]["contributionCalendar"]
    total = cal["totalContributions"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    top = max(int(d["contributionCount"]) for d in days)

    for name in EXPECTED_FILES:
        path = os.path.join(out_dir, name)
        if not os.path.isfile(path):
            fail(f"missing {name}")
        with open(path, encoding="utf-8") as handle:
            svg = handle.read()
        if len(svg.encode("utf-8")) > 60 * 1024:
            fail(f"{name} exceeds 60KB")
        try:
            ET.fromstring(svg)
        except ET.ParseError as exc:
            fail(f"{name} is not valid XML: {exc}")

    cricket = open(os.path.join(out_dir, "chalk-cricket.svg"),
                   encoding="utf-8").read()
    for marker in ("THE PITCH", "wagon wheel", "top days", "week by week",
                   f">{total:,}" if total >= 1000 else f">{total}<",
                   f">{top}<"):
        if marker not in cricket:
            fail(f"chalk-cricket.svg missing {marker!r}")
    builds = "".join(
        open(os.path.join(out_dir, f"chalk-build-{i}.svg"),
             encoding="utf-8").read() for i in (1, 2, 3, 4))
    for marker in ("no. 1", "no. 4", "pushed"):
        if marker not in builds:
            fail(f"build cards missing {marker!r}")
    hero = open(os.path.join(out_dir, "chalk-hero.svg"),
                encoding="utf-8").read()
    if "PRATHAM" not in hero or "window" not in hero.lower():
        fail("chalk-hero.svg missing room content")
    print(f"selfcheck: OK (8 files, total={total}, top={top})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
