"""Chalkboard widgets: daily regeneration of the profile README art.

Layout: fetch.py (live data) -> compute.py (typed records, every number)
-> render.py (pure SVG builders) -> assets/*.svg. kit.py holds the shared
chalk language. Never fabricates: any failure exits 1 with no writes.
"""


import argparse
from pathlib import Path
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compute import (aggregate_languages, compute_cricket, parse_payload,
                     select_build_repos, select_now_repos)
from fetch import fetch_live, fetch_public, fetch_weather
from kit import IST, esc, truncate_words
from render import (render_build, render_cricket, render_hero,
                    render_ledger, render_now)


def sync_readme_cards(build_rows: list, user: str) -> bool:
    """Point the four showcase anchors at the repos actually rendered, with
    honest per-repo alt text. Deterministic: same rows always rewrite the
    same four lines. Returns True when the file changed."""
    from compute import Repo
    readme = Path(__file__).resolve().parent.parent / "README.md"
    text = readme.read_text(encoding="utf-8")

    def card(g: dict[str, str], n: int, repo: Repo) -> str:
        alt = f"{repo.name}, {truncate_words(repo.description or 'no description yet', 50)}"
        return (f'<a{g["a1"]}href="https://github.com/{user}/{repo.name}"'
                f'{g["a2"]}>{g["a3"]}<img{g["b1"]}src="./assets/chalk-build-{n}.svg"'
                f'{g["b2"]}alt="{esc(alt)}"{g["b3"]}width="100%"'
                f'{g["b4"]}>{g["b5"]}</a>')

    original = text
    for i, repo in enumerate(build_rows):
        pattern = (r'<a(?P<a1>\s+)href="[^"]*"(?P<a2>\s*)>(?P<a3>\s*)<img'
                   r'(?P<b1>\s+)src="(?P<src>\./assets/chalk-build-'
                   + str(i + 1) + r'\.svg)"(?P<b2>\s+)alt="[^"]*"(?P<b3>\s+)'
                   r'width="100%"(?P<b4>\s*/?)>(?P<b5>\s*)</a>')
        text, n = re.subn(pattern,
                           lambda m: card(m.groupdict(), i + 1, repo),
                           text, count=1)
    if text != original:
        readme.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate chalkboard widgets (chalk-cricket/now/ledger SVGs) "
        "from live GitHub data. Never fabricates: failures exit 1 with no writes."
    )
    parser.add_argument("--stdin", action="store_true",
                        help="render from a JSON fixture on stdin (preview/testing)")
    parser.add_argument("--out-dir", default="assets", help="output directory")
    parser.add_argument("--user", default="iAMv1", help="GitHub login")
    parser.add_argument("--at", default=None,
                        help="ISO datetime override for preview "
                        "(e.g. 2026-11-08T08:00+05:30); naive = UTC")
    args = parser.parse_args(argv)

    if args.stdin:
        try:
            data = json.load(sys.stdin)
        except ValueError as exc:
            die(f"could not parse stdin JSON: {exc}")
        if not isinstance(data, dict):
            die("stdin JSON must be an object with the fetched-data shape")
    else:
        token = os.environ.get("GITHUB_TOKEN", "")
        if token:
            data = fetch_live(args.user, token)
        else:
            # no token: still REAL data, from public endpoints only
            data = fetch_public(args.user)

    if args.at:
        try:
            now = datetime.fromisoformat(args.at)
        except ValueError:
            die(f"could not parse --at value: {args.at!r}")
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
    if args.stdin:
        weather = None  # fixture mode: time scenes only, never guessed weather
    else:
        weather = fetch_weather()

    total, weeks, repos = parse_payload(data, args.user)
    stats = compute_cricket(total, weeks)

    stamp = now.strftime("%Y-%m-%d")
    year = now.strftime("%Y")
    ist_now = now.astimezone(IST)

    now_rows = select_now_repos(repos, args.user)
    print(f"now: {[r.name for r in now_rows]} (public, newest pushes first)")
    langs = aggregate_languages(repos)
    print("ledger: " + (", ".join(f"{n} {p:.1f}%" for n, _c, _s, p in langs) or "empty"))

    # Render EVERYTHING before touching the filesystem: any failure above
    # leaves previously committed SVGs untouched.
    hero_svg = render_hero(now_rows, stamp, ist_now, weather)
    cricket_svg = render_cricket(stats, weeks, args.user, year, stamp)
    now_svg = render_now(now_rows, args.user, stamp, now)
    ledger_svg = render_ledger(langs, stamp)
    build_rows = select_build_repos(repos, args.user, now)
    print("builds: " + (", ".join(r.name for r in build_rows) or "empty"))
    build_svgs = [
        (f"chalk-build-{i + 1}", render_build(repo, i, stamp, now))
        for i, repo in enumerate(build_rows)
    ]
    if not args.stdin:
        readme_changed = sync_readme_cards(build_rows, args.user)
        print(f"readme: {'cards synced' if readme_changed else 'cards already current'}")
    for name, svg in (("chalk-hero", hero_svg), ("chalk-cricket", cricket_svg),
                      ("chalk-now", now_svg), ("chalk-ledger", ledger_svg),
                      *build_svgs):
        if len(svg.encode("utf-8")) > 60 * 1024:
            die(f"{name}.svg exceeds 60KB")

    os.makedirs(args.out_dir, exist_ok=True)
    outputs = {
        "chalk-hero.svg": hero_svg,
        "chalk-cricket.svg": cricket_svg,
        "chalk-now.svg": now_svg,
        "chalk-ledger.svg": ledger_svg,
    }
    outputs.update({f"{name}.svg": svg for name, svg in build_svgs})
    for filename, svg in outputs.items():
        path = os.path.join(args.out_dir, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(svg)
        print(f"wrote {path} ({len(svg.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
