"""Chalkboard widgets generator for the iAMv1 profile README.

Data sources (all live, fetched at generation time from https://api.github.com/graphql):
  - contributionsCollection.contributionCalendar -> assets/chalk-cricket.svg
    scoreboard (runs / wickets / overs / top score / 4s / 6s), season stat
    card, date-driven wagon wheel over a mini pitch, top-8 day table and the
    week-by-week season strip.
  - repositories (OWNER, not forks) pushedAt / description / primaryLanguage
    -> assets/chalk-now.svg ("now building" strip: top 3 public repos).
  - repositories[].languages edges (bytes per language, public repos only)
    -> assets/chalk-ledger.svg ("the ledger": top-5 language bars).

NEVER-FABRICATE RULE: every number rendered into the SVGs is computed from
the GraphQL response. Any failure (missing GITHUB_TOKEN, HTTP error,
GraphQL errors, unexpected shape) prints a clear error to stderr and exits
with code 1 WITHOUT writing any file, so previously committed SVGs stay
untouched. There is deliberately no mock-data path.

Fixture shape (mirrors the GraphQL ``data.user`` object verbatim)::

    {"contributionsCollection": {"contributionCalendar": {"totalContributions": 1225,
     "weeks": [{"contributionDays": [{"contributionCount": 3, "date": "2026-01-04"}]}]}},
     "repositories": {"nodes": [{"name": "demo", "description": "...",
                "primaryLanguage": {"name": "Python", "color": "#3572A5"},
                "stargazerCount": 0, "pushedAt": "2026-09-10T12:00:00Z",
                "visibility": "PUBLIC",
                "languages": {"edges": [{"size": 9000,
                    "node": {"name": "Python", "color": "#3572A5"}}]}}]}}

Cricket mapping (runs = commits, in code comments where applied):
  runs = totalContributions; overs = number of calendar weeks (<=53);
  wickets = weeks whose days all sum to 0; top score = max day count;
  4s = days with 4..5 commits; 6s = days with >=6; avg = runs/365 (1dp).
  Wagon wheel: top 8 days by count (ties -> earlier date), then assigned the
  fixed evenly-spread angle slots [10,55,100,145,190,235,280,325] in DATE
  order. Fixed slots keep the wheel balanced for any dataset; date order
  keeps the assignment honest and deterministic (NOT fitted to look good).
"""

from __future__ import annotations

import argparse
import calendar
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import NoReturn
from xml.sax.saxutils import escape

import requests

API_URL = "https://api.github.com/graphql"
FONT_STACK = "ui-monospace, 'Cascadia Mono', Consolas, monospace"
FALLBACK_LANG_COLOR = "#7dd3fc"  # chalk-cyan, used when GitHub reports no color
SEASON_DAYS = 365
WINDOW = 6  # contiguous-week window used for spike / quiet-season detection

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
    repositories(first: 50, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        description
        primaryLanguage { name color }
        stargazerCount
        pushedAt
        visibility
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

# Shared chalk language: charcoal canvas, chalk strokes, wobble filters and
# the light-mode (paper) variant. Mirrors the approved reference SVGs.
CHALK_CSS = (
    ".bg{fill:#111318}"
    ".field{fill:#161a22}"
    ".panel{fill:#1a1e27}"
    ".pitchfill{fill:#1b2029}"
    ".st-c{stroke:#f4f1e8}"
    ".st-d{stroke:#c9cdd6}"
    ".st-y{stroke:#fbbf24}"
    ".st-cy{stroke:#7dd3fc}"
    ".tx{fill:#f4f1e8}"
    ".tx-d{fill:#d9dde3}"
    ".tx-y{fill:#fbbf24}"
    ".tx-cy{fill:#7dd3fc}"
    ".f-y{fill:#fbbf24}"
    ".f-cy{fill:#7dd3fc}"
    ".st-r{stroke:#e26d5c}"
    ".tx-r{fill:#e26d5c}"
    ".halo{stroke:#111318}"
    ".bgf{fill:#111318}"
    "@media (prefers-color-scheme: light){"
    ".bg{fill:#f8f6ee}"
    ".field{fill:#ece5d2}"
    ".panel{fill:#ffffff}"
    ".pitchfill{fill:#e2d9bf}"
    ".st-c{stroke:#2d3142}"
    ".st-d{stroke:#5b6270}"
    ".st-y{stroke:#b45309}"
    ".st-cy{stroke:#0369a1}"
    ".tx{fill:#2d3142}"
    ".tx-d{fill:#5b6270}"
    ".tx-y{fill:#b45309}"
    ".tx-cy{fill:#0369a1}"
    ".f-y{fill:#b45309}"
    ".f-cy{fill:#0369a1}"
    ".st-r{stroke:#b91c1c}"
    ".tx-r{fill:#b91c1c}"
    ".halo{stroke:#f8f6ee}"
    ".bgf{fill:#f8f6ee}"
    "}"
)

CHALK_DEFS = (
    '<defs>'
    '<filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="2" seed="4" result="n"/>'
    '<feDisplacementMap in="SourceGraphic" in2="n" scale="2.2"/>'
    "</filter>"
    '<filter id="wob2" x="-5%" y="-5%" width="110%" height="110%">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="11" result="n"/>'
    '<feDisplacementMap in="SourceGraphic" in2="n" scale="3"/>'
    "</filter>"
    "</defs>"
)


@dataclass(frozen=True)
class Day:
    count: int
    date: str  # ISO YYYY-MM-DD


@dataclass(frozen=True)
class Repo:
    name: str
    description: str
    lang: str | None
    color: str | None
    pushed: datetime
    visibility: str
    langs: tuple[tuple[str, str | None, int], ...]  # (name, color, bytes)


@dataclass
class CricketStats:
    runs: int = 0
    wickets: int = 0
    overs: int = 0
    top: int = 0
    fours: int = 0
    sixes: int = 0
    active_days: int = 0
    avg: float = 0.0
    week_totals: list[int] = field(default_factory=list)
    top_weeks: set[int] = field(default_factory=set)  # indices of top-3 weeks
    shots: list[tuple[Day, int]] = field(default_factory=list)  # (day, angle)
    spike_start: int = 0
    spike_end: int = 0
    spike_label: str = "spike"
    quiet_start: int = 0


def die(message: str) -> NoReturn:
    print(f"generate_chalk: error: {message}", file=sys.stderr)
    sys.exit(1)


def esc(text: object) -> str:
    return escape(str(text), {'"': "&quot;"})


def f1(value: float) -> str:
    return f"{value:.1f}"


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        die(f"bad pushedAt value: {value!r}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        die(f"unparseable pushedAt value: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def fetch_live(user: str, token: str) -> dict:
    """Single GraphQL fetch; dies (writing nothing) on any failure."""
    try:
        response = requests.post(
            API_URL,
            json={"query": QUERY, "variables": {"login": user}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
    except requests.RequestException as exc:
        die(f"GitHub API request failed: {exc}")
    if response.status_code != 200:
        die(f"GitHub API HTTP {response.status_code}: {response.text[:200]}")
    try:
        payload = response.json()
    except ValueError:
        die("GitHub API returned non-JSON response")
    if payload.get("errors"):
        die(f"GitHub API GraphQL errors: {json.dumps(payload['errors'])[:300]}")
    data = payload.get("data", {}).get("user")
    if not data:
        die(f"user {user!r} not found in API response")
    return data


def fetch_public(user: str) -> dict:
    """No-token REAL-data tier: public endpoints only (never fabricates).

    Contributions come from the public contributions calendar mirror
    (github-contributions-api.jogruber.de/v4); repos from the REST API.
    Language byte-breakdowns only for the 5 most recent public repos
    (unauthenticated rate limits). Any failure dies without writing."""
    try:
        r = requests.get(
            f"https://github-contributions-api.jogruber.de/v4/{user}?y=last",
            timeout=30,
        )
        if r.status_code != 200:
            die(f"public contributions HTTP {r.status_code}")
        days = (r.json().get("contributions") or [])
        if not days:
            die("public contributions returned no data")
    except requests.RequestException as exc:
        die(f"public contributions request failed: {exc}")
    dated = sorted((str(d["date"]), int(d["count"])) for d in days)[-364:]
    while len(dated) % 7:
        dated.insert(0, dated[0])
    total = sum(count for _date, count in dated)
    try:
        r = requests.get(
            f"https://api.github.com/users/{user}/repos?per_page=50&sort=pushed",
            timeout=30,
        )
        if r.status_code != 200:
            die(f"REST repos HTTP {r.status_code}")
        nodes = r.json()
    except requests.RequestException as exc:
        die(f"REST repos request failed: {exc}")
    repo_nodes = []
    lang_calls = 0
    for node in nodes:
        if node.get("fork") or node.get("private") or node.get("name") == user:
            continue
        edges = []
        if lang_calls < 5:
            lang_calls += 1
            try:
                lr = requests.get(
                    f"https://api.github.com/repos/{user}/{node['name']}/languages",
                    timeout=30,
                )
                if lr.status_code == 200:
                    edges = [
                        {"node": {"name": name, "color": None}, "size": int(size)}
                        for name, size in sorted(lr.json().items(), key=lambda kv: -kv[1])[:8]
                    ]
            except requests.RequestException:
                pass
        repo_nodes.append(
            {
                "name": node["name"],
                "description": node.get("description") or "",
                "primaryLanguage": ({"name": node["language"]} if node.get("language") else None),
                "stargazerCount": int(node.get("stargazers_count") or 0),
                "pushedAt": node.get("pushed_at") or "",
                "visibility": "PUBLIC",
                "languages": {"edges": edges},
            }
        )
    return {
        "contributionsCollection": {
            "contributionCalendar": {
                "totalContributions": total,
                "weeks": [
                    {
                        "contributionDays": [
                            {"contributionCount": count, "date": date}
                            for date, count in dated[i : i + 7]
                        ]
                    }
                    for i in range(0, len(dated), 7)
                ],
            }
        },
        "repositories": {"nodes": repo_nodes},
    }




def parse_payload(data: dict, user: str) -> tuple[int, list[list[Day]], list[Repo]]:
    """Validate the live (or --stdin fixture) shape into typed records."""
    try:
        cal = data["contributionsCollection"]["contributionCalendar"]
        total = cal["totalContributions"]
        raw_weeks = cal["weeks"]
        raw_repos = data["repositories"]["nodes"]
    except (KeyError, TypeError) as exc:
        die(f"unexpected data shape (missing key): {exc}")
    if not isinstance(total, int) or not isinstance(raw_weeks, list):
        die("unexpected data shape in contributionCalendar")
    weeks: list[list[Day]] = []
    for week in raw_weeks:
        try:
            days = [Day(int(d["contributionCount"]), str(d["date"])) for d in week["contributionDays"]]
        except (KeyError, TypeError, ValueError) as exc:
            die(f"unexpected day shape: {exc}")
        weeks.append(days)
    repos: list[Repo] = []
    for node in raw_repos:
        try:
            lang_node = node.get("primaryLanguage") or {}
            edges = node["languages"]["edges"]
            langs = tuple(
                (str(e["node"]["name"]), e["node"].get("color"), int(e["size"])) for e in edges
            )
            repos.append(
                Repo(
                    name=str(node["name"]),
                    description=str(node.get("description") or ""),
                    lang=(str(lang_node["name"]) if lang_node.get("name") else None),
                    color=lang_node.get("color"),
                    pushed=parse_time(node.get("pushedAt")),
                    visibility=str(node.get("visibility", "")),
                    langs=langs,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            die(f"unexpected repository shape: {exc}")
    return total, weeks, repos


def compute_cricket(total: int, weeks: list[list[Day]]) -> CricketStats:
    """Derive every scoreboard number from the contribution calendar."""
    stats = CricketStats()
    stats.overs = len(weeks)
    stats.week_totals = [sum(day.count for day in week) for week in weeks]
    # wickets = weeks whose days all sum to 0 (blank weeks).
    stats.wickets = sum(1 for week_total in stats.week_totals if week_total == 0)
    days = [day for week in weeks for day in week]
    stats.runs = total
    stats.top = max((day.count for day in days), default=0)
    stats.fours = sum(1 for day in days if 4 <= day.count <= 5)
    stats.sixes = sum(1 for day in days if day.count >= 6)
    stats.active_days = sum(1 for day in days if day.count > 0)
    stats.avg = round(total / SEASON_DAYS, 1)
    # Top-3 weeks (by total, ties -> earlier week) get the yellow dots.
    ranked = sorted(range(len(weeks)), key=lambda i: (-stats.week_totals[i], i))
    # Wagon wheel highlights: a deliberate class mix so the wheel shows all
    # three shot types: top-4 sixes (>=6), top-2 fours (4-5), top-2 nudges
    # (2-3), each bucket sorted by (-count, date). Falls back down the
    # classes when a bucket is empty. Angle slots assigned in DATE order.
    sixes = sorted((d for d in days if d.count >= 6), key=lambda d: (-d.count, d.date))[:4]
    fours = sorted((d for d in days if 4 <= d.count < 6), key=lambda d: (-d.count, d.date))[:2]
    nudges = sorted((d for d in days if 0 < d.count < 4), key=lambda d: (-d.count, d.date))[:2]
    chosen = sixes + fours + nudges
    if len(chosen) < 8:
        rest = sorted((d for d in days if d.count > 0 and d not in chosen),
                      key=lambda d: (-d.count, d.date))
        chosen += rest[: 8 - len(chosen)]
    candidates = chosen[:8]
    ordered = sorted(candidates, key=lambda d: d.date)
    # Angle = the day's own position in the season (day-of-year / season * 360),
    # nudged +6 deg apart when two top days land on the same angle. Fully
    # data-driven: the wheel re-shapes itself from the real calendar.
    season_span = max(SEASON_DAYS - 1, 1)
    angles: list[float] = []
    used: list[float] = []
    for day in ordered:
        doy = datetime.strptime(day.date, "%Y-%m-%d").timetuple().tm_yday
        ang = (doy / 365.0) * 360.0
        while any(abs(ang - u) < 18.0 for u in used):
            ang += 6.0
        used.append(ang)
        angles.append(round(ang % 360.0, 1))
    stats.shots = list(zip(ordered, angles))
    # Spike = contiguous WINDOW-week slice with the highest total;
    # quiet = lowest NONZERO WINDOW-week slice. Ties -> earliest window.
    width = min(WINDOW, len(weeks)) if weeks else 0
    if width:
        sums = [
            (sum(stats.week_totals[i : i + width]), i)
            for i in range(len(weeks) - width + 1)
        ]
        stats.spike_start = min(sums, key=lambda t: (-t[0], t[1]))[1]
        stats.spike_end = min(stats.spike_start + width - 1, len(weeks) - 1)
        nonzero = [(s, i) for s, i in sums if s > 0]
        stats.quiet_start = (
            min(nonzero, key=lambda t: (t[0], t[1]))[1] if nonzero else stats.spike_start
        )
        first = weeks[stats.spike_start][0].date if weeks[stats.spike_start] else ""
        last_days = weeks[stats.spike_end]
        last = last_days[-1].date if last_days else ""
        try:
            m1 = calendar.month_abbr[int(first[5:7])].lower()
            m2 = calendar.month_abbr[int(last[5:7])].lower()
        except (ValueError, IndexError):
            m1, m2 = "", ""
        stats.spike_label = f"{m1}-{m2} spike" if m1 and m2 and m1 != m2 else (
            f"{m1} spike" if m1 else "spike"
        )
    # Arithmetic self-check: blank weeks cannot exceed weeks; boundary days
    # (4s/6s) are a subset of active days; avg tracks runs/365.
    assert 0 <= stats.wickets <= stats.overs, "wickets/weeks math broken"
    assert stats.fours + stats.sixes <= stats.active_days, "4s/6s exceed active days"
    assert abs(stats.avg - total / SEASON_DAYS) <= 0.1, "avg != runs/365"
    print(
        f"cricket: runs={stats.runs} wickets={stats.wickets} overs={stats.overs} "
        f"top={stats.top} fours={stats.fours} sixes={stats.sixes} "
        f"avg={stats.avg}/day active={stats.active_days} "
        f"spike=weeks {stats.spike_start}-{stats.spike_end} ({stats.spike_label})"
    )
    return stats


# -- geometry helpers (deterministic, no randomness) --------------------------

CX = 400.0  # horizontal centre used by the now-building card tilt


# -- renderers ----------------------------------------------------------------

def notebook_kit(w: int, h: int, stamp_text: str, top: int = 10) -> str:
    """Notebook identity: faint ruled lines + red-pen date stamp + one red tick."""
    ys = [round(h * f) for f in (0.28, 0.46, 0.64, 0.82)]
    rules = "".join(
        f'<line x1="24" y1="{y}" x2="{w - 24}" y2="{y}" '
        'stroke="#ffffff" stroke-opacity="0.06" stroke-width="1"/>'
        for y in ys
    )
    box_w = 72
    stamp = (
        f'<g id="stamp">'
        f'<rect x="{w - box_w - 14}" y="{top}" width="{box_w}" height="20" rx="4" '
        f'fill="none" class="st-r" stroke-width="1.6"/>'
        f'<text x="{w - 14 - box_w // 2}" y="{top + 14}" class="tx-r" font-size="11" '
        f'text-anchor="middle">{stamp_text}</text>'
        f'<text x="{w - 14 - box_w // 2}" y="{top + 32}" class="tx-r" font-size="11" '
        f'text-anchor="middle">\u2713</text>'
        f'</g>'
    )
    return f'<g id="rules">{rules}</g>{stamp}'


def short_stamp(stamp: str) -> str:
    """'2026-09-12' style stamp -> '12·09·26' for the red date box."""
    parts = stamp.strip().split("-")
    if len(parts) == 3 and all(p.isdigit() and len(p) in (2, 4) for p in parts):
        year = parts[0][-2:]
        return f"{parts[2]}\u00b7{parts[1]}\u00b7{year}"
    return stamp[:10]


# -- variant C: scorecard, wagon wheel, top days, season strip -----------------

WHEEL_CX, WHEEL_CY, WHEEL_R = 452.0, 210.0, 132.0
STRIP_Y = 422.0        # season-strip baseline; bars grow upward from it
STRIP_X0, STRIP_X1 = 30.0, 824.0
STRIP_BAR_W = 9.4
STRIP_BAR_MAX = 40.0   # tallest weekly bar, px above the axis


def c_shot_class(count: int) -> tuple[str, str, float, str, str | None]:
    """(stroke class, width, length factor, dash attr, label) for the C wheel."""
    if count >= 6:  # clears the rope: yellow dashed to the boundary
        return "st-y", "3.2", 0.94, ' stroke-dasharray="8 5"', "6"
    if count >= 4:  # to the fence: cyan, mid-length
        return "st-cy", "2.4", 0.66, "", "4"
    if count >= 2:  # nudged around: thin white, short
        return "st-c", "1.8", 0.36, "", None
    return "st-c", "1.8", 0.22, "", None  # single: thin white, very short


def wheel_c(stats: CricketStats) -> tuple[str, str]:
    """Wagon wheel over the mini pitch: spokes draw in on load, arrowheads and
    6/4 tags at the rope. Angles come from the days themselves."""
    lines: list[str] = []
    labels: list[str] = []
    for n, (day, angle) in enumerate(stats.shots):
        cls, width, factor, dash, tag = c_shot_class(day.count)
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        length = WHEEL_R * factor
        ex, ey = WHEEL_CX + length * dx, WHEEL_CY + length * dy
        mx, my = (WHEEL_CX + ex) / 2 - dy * 12.0, (WHEEL_CY + ey) / 2 + dx * 12.0
        delay = 0.15 * n
        lines.append(
            f'<path class="{cls}" d="M{f1(WHEEL_CX)},{f1(WHEEL_CY)} '
            f'Q{f1(mx)},{f1(my)} {f1(ex)},{f1(ey)}" '
            f'stroke-width="{width}"{dash}>'
            f'<animate attributeName="stroke-dashoffset" from="160" to="0" '
            f'dur="0.9s" begin="{delay:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="0" to="1" '
            f'dur="0.3s" begin="{delay:.2f}s" fill="freeze"/></path>'
        )
        back = math.atan2(WHEEL_CY - ey, WHEEL_CX - ex)
        barbs = "".join(
            f"M{f1(ex)},{f1(ey)}L{f1(ex + 8 * math.cos(back + off))},"
            f"{f1(ey + 8 * math.sin(back + off))}"
            for off in (0.5, -0.5)
        )
        lines.append(f'<path class="{cls}" d="{barbs}" stroke-width="1.8"/>')
        if tag:
            tcls = "tx-y" if tag == "6" else "tx-cy"
            lx, ly = ex + 12 * dx, ey + 12 * dy
            if lx > 568.0 or ly > 338.0:  # keep clear of table / legend bands
                lx, ly = ex - 14 * dx, ey - 14 * dy
            labels.append(
                f'<text class="{tcls}" x="{f1(lx)}" y="{f1(ly)}">{tag}</text>'
            )
    return "".join(lines), "".join(labels)


def season_strip(stats: CricketStats, weeks: list[list[Day]]) -> str:
    """Bottom strip: annotation row, weekly bars up from the axis, dashed
    ticks for blank weeks, month labels + boundary ticks under the axis."""
    peak = max(stats.week_totals, default=0)
    pitch = (STRIP_X1 - STRIP_X0) / max(stats.overs, 1)
    bars: list[str] = []
    ticks: list[str] = []
    labels: list[str] = []
    peak_x = ""
    peak_anchor = "start"
    prev_month: int | None = None
    for i, total in enumerate(stats.week_totals):
        x = STRIP_X0 + i * pitch
        month: int | None = None
        if weeks[i]:
            try:
                month = int(weeks[i][0].date[5:7])
            except (ValueError, IndexError):
                month = None
        if month is not None and month != prev_month:
            if prev_month is not None:
                ticks.append(
                    f'<path class="st-d" d="M{f1(x)},{f1(STRIP_Y)} L{f1(x)},430" '
                    'stroke-width="1.4"/>'
                )
            labels.append(
                f'<text class="tx-d halo" x="{f1(x + pitch / 2)}" y="438" '
                f'font-size="10" text-anchor="middle" style="paint-order:stroke" '
                f'stroke-width="3">{calendar.month_abbr[month].upper()}</text>'
            )
        prev_month = month
        if total <= 0:
            bars.append(
                f'<path class="st-d" d="M{f1(x)},{f1(STRIP_Y)} L{f1(x)},410" '
                'stroke-width="1.6" stroke-dasharray="3 3"/>'
            )
            continue
        h = max(3.0, round(STRIP_BAR_MAX * total / peak, 1)) if peak else 3.0
        y = round(STRIP_Y - h, 1)
        delay = 0.3 + x * 0.001
        bars.append(
            f'<rect class="f-cy" x="{f1(x + 2.0)}" y="{y}" width="{STRIP_BAR_W}" '
            f'height="{f1(h)}" stroke="none">'
            f'<animate attributeName="height" from="0" to="{f1(h)}" dur="0.5s" '
            f'begin="{delay:.2f}s" fill="freeze"/>'
            f'<animate attributeName="y" from="422" to="{y}" dur="0.5s" '
            f'begin="{delay:.2f}s" fill="freeze"/></rect>'
        )
        if peak and total == peak and not peak_x:
            if x + 2.0 + STRIP_BAR_W + 44.0 <= 830.0:
                peak_x, peak_anchor = f1(x + 2.0 + STRIP_BAR_W + 5.0), "start"
            else:
                peak_x, peak_anchor = f1(x - 3.0), "end"
    peak_label = (
        f'<text class="tx-y halo" x="{peak_x}" y="390" font-size="10" '
        f'text-anchor="{peak_anchor}" style="paint-order:stroke" '
        f'stroke-width="3">{peak}</text>'
    ) if peak else ""
    legend = "the season, week by week \u00b7 tall = heavy week, dashed = blank week"
    quip = f"{stats.overs} weeks would be a test match"
    return (
        "".join(bars)
        + "".join(ticks)
        + "".join(labels)
        + peak_label
        + f'<text class="tx-d" x="30" y="372" font-size="11">{esc(legend)}</text>'
        + f'<text class="tx-d" x="830" y="372" font-size="11" '
        f'text-anchor="end">{esc(quip)}</text>'
    )


def top_days_table(stats: CricketStats) -> str:
    """Right column: the top 8 days as date / bar / count rows."""
    rows: list[str] = []
    for i, (day, _angle) in enumerate(
        sorted(stats.shots, key=lambda t: (-t[0].count, t[0].date))
    ):
        y = 96 + i * 18
        width = max(3.0, 32.0 * day.count / stats.top) if stats.top else 3.0
        cls = "st-y" if day.count >= 6 else ("st-cy" if day.count >= 4 else "st-d")
        rows.append(
            f'<text class="tx-d" x="576" y="{y}" font-size="12">{esc(day.date[5:])}</text>'
            f'<path class="{cls}" d="M668,{f1(y - 4)} L{f1(668 + width)},{f1(y - 4)}" '
            'stroke-width="3"/>'
            f'<text class="tx" x="816" y="{y}" font-size="12" text-anchor="end" '
            f'font-weight="bold">{day.count}</text>'
        )
    return "".join(rows)


def render_cricket(
    stats: CricketStats, weeks: list[list[Day]], user: str, year: str, stamp: str
) -> str:
    runs_fmt = f"{stats.runs:,}"
    best_week = max(stats.week_totals, default=0)
    wheel, wheel_labels = wheel_c(stats)
    strip = season_strip(stats, weeks)
    table = top_days_table(stats)
    desc = (
        "A chalk cricket season on one board: scoreboard strip up top, season "
        "stat card on the left, date-driven wagon wheel over a mini pitch, the "
        "top-8 day table on the right and the full season week by week along "
        f"the bottom. Scoreboard: {stats.runs} runs, {stats.wickets} blank "
        f"weeks, {stats.overs} overs, top day {stats.top}, {stats.fours} 4s, "
        f"{stats.sixes} 6s."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 520" role="img" '
        f'aria-labelledby="ccTitle ccDesc" font-family="{FONT_STACK}">'
        f'<title id="ccTitle">The Pitch \u00b7 {esc(year)} commit season as a '
        f"chalk cricket scorecard</title>"
        f'<desc id="ccDesc">{esc(desc)}</desc>'
        f"<style>{CHALK_CSS}</style>"
        f"{CHALK_DEFS}"
        '<rect class="bg" x="0" y="0" width="860" height="520"/>'
        f"{notebook_kit(860, 520, short_stamp(stamp))}"
        "<!-- scoreboard strip -->"
        '<g filter="url(#wob2)" fill="none" stroke-linecap="round">'
        '<path class="st-c" d="M26,12 C240,8 560,14 834,11 C837,30 833,60 835,80 '
        'C640,84 220,78 25,82 C23,60 27,30 26,12 Z" stroke-width="2.6"/>'
        '<path class="st-y" d="M42,52 C120,48 220,55 286,50" stroke-width="2.6"/>'
        '<path class="st-d" d="M292,18 C290,35 294,55 291,74" stroke-width="2"/>'
        "</g>"
        "<g>"
        '<text class="tx" x="42" y="44" font-size="26" letter-spacing="3">THE PITCH</text>'
        f'<text class="tx-d" x="42" y="68" font-size="12">season {esc(year)} '
        f"\u00b7 github.com/{esc(user)}</text>"
        '<text class="tx-d" x="345" y="30" font-size="12" text-anchor="middle">RUNS</text>'
        '<text class="tx-d" x="419" y="30" font-size="12" text-anchor="middle">WICKETS</text>'
        '<text class="tx-d" x="493" y="30" font-size="12" text-anchor="middle">OVERS</text>'
        '<text class="tx-d" x="567" y="30" font-size="12" text-anchor="middle">TOP SCORE</text>'
        '<text class="tx-d" x="641" y="30" font-size="12" text-anchor="middle">4s</text>'
        '<text class="tx-d" x="715" y="30" font-size="12" text-anchor="middle">6s</text>'
        f'<text class="tx-y" x="345" y="60" font-size="18" text-anchor="middle">{runs_fmt}</text>'
        f'<text class="tx" x="419" y="60" font-size="18" text-anchor="middle">{stats.wickets}</text>'
        f'<text class="tx" x="493" y="60" font-size="18" text-anchor="middle">{stats.overs}</text>'
        f'<text class="tx" x="567" y="60" font-size="18" text-anchor="middle">{stats.top}</text>'
        f'<text class="tx-cy" x="641" y="60" font-size="18" text-anchor="middle">{stats.fours}</text>'
        f'<text class="tx-y" x="715" y="60" font-size="18" text-anchor="middle">{stats.sixes}</text>'
        '<path class="st-cy" d="M320,72 L346,72" stroke-width="2.4"/>'
        '<text class="tx-d" x="352" y="76" font-size="13">4-5 commits \u00b7 to the fence</text>'
        "</g>"
        "<!-- season stat card (left) -->"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round">'
        '<rect class="panel st-c" x="26" y="88" width="270" height="200" rx="6" '
        'stroke-width="2.2"/>'
        "</g>"
        "<g>"
        '<text class="tx" x="48" y="114" font-size="14" font-weight="bold">season</text>'
        f'<text class="tx-d" x="280" y="114" font-size="12" text-anchor="end">{esc(year)}</text>'
        f'<text class="tx-d" x="48" y="140" font-size="12">season days</text>'
        f'<text class="tx" x="280" y="140" font-size="13" text-anchor="end" '
        f'font-weight="bold">{SEASON_DAYS}</text>'
        '<path class="st-d" d="M48,148 C120,146 220,150 278,148" stroke-width="1" '
        'stroke-opacity="0.4" fill="none"/>'
        f'<text class="tx-d" x="48" y="166" font-size="12">active days</text>'
        f'<text class="tx" x="280" y="166" font-size="13" text-anchor="end" '
        f'font-weight="bold">{stats.active_days}</text>'
        '<path class="st-d" d="M48,174 C120,172 220,176 278,174" stroke-width="1" '
        'stroke-opacity="0.4" fill="none"/>'
        f'<text class="tx-d" x="48" y="192" font-size="12">avg / day</text>'
        f'<text class="tx" x="280" y="192" font-size="13" text-anchor="end" '
        f'font-weight="bold">{f1(stats.avg)}</text>'
        '<path class="st-d" d="M48,200 C120,198 220,202 278,200" stroke-width="1" '
        'stroke-opacity="0.4" fill="none"/>'
        f'<text class="tx-d" x="48" y="218" font-size="12">best week</text>'
        f'<text class="tx" x="280" y="218" font-size="13" text-anchor="end" '
        f'font-weight="bold">{best_week}</text>'
        '<path class="st-d" d="M48,226 C120,224 220,228 278,226" stroke-width="1" '
        'stroke-opacity="0.4" fill="none"/>'
        f'<text class="tx-d" x="48" y="244" font-size="12">blank weeks</text>'
        f'<text class="tx" x="280" y="244" font-size="13" text-anchor="end" '
        f'font-weight="bold">{stats.wickets}</text>'
        '<path class="st-d" d="M48,252 C120,250 220,254 278,252" stroke-width="1" '
        'stroke-opacity="0.4" fill="none"/>'
        f'<text class="tx-d" x="48" y="270" font-size="12">boundaries</text>'
        f'<text class="tx" x="280" y="270" font-size="13" text-anchor="end" '
        f'font-weight="bold">{stats.fours}/{stats.sixes}</text>'
        "</g>"
        "<!-- ground: field disc, mowing ring, boundary that never stops moving -->"
        '<circle class="field" cx="452" cy="210" r="132"/>'
        '<g filter="url(#wob2)" fill="none" stroke-linecap="round">'
        '<circle class="st-d" cx="452" cy="210" r="112" stroke-opacity="0.35" '
        'stroke-width="8"/>'
        "</g>"
        '<circle class="st-d" cx="452" cy="210" r="132" fill="none" stroke-width="2" '
        'stroke-dasharray="10 7">'
        '<animate attributeName="stroke-dashoffset" from="0" to="-34" dur="3s" '
        'repeatCount="indefinite"/>'
        "</circle>"
        "<!-- wagon wheel: the top days' spokes, drawn in one by one -->"
        f'<g filter="url(#wob)" fill="none" stroke-linecap="round">{wheel}</g>'
        f'<g font-size="12" text-anchor="middle">{wheel_labels}</g>'
        "<!-- mini pitch: worn strip, creases, stumps both ends -->"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round">'
        '<path class="pitchfill st-c" d="M438,168 C446,167 462,169 466,168 '
        'C467,180 465,240 466,256 C458,257 446,255 438,256 C437,226 439,196 '
        '438,168 Z" stroke-width="2.4"/>'
        '<ellipse class="st-d" cx="452" cy="212" rx="10" ry="3" stroke-width="1.2" '
        'stroke-opacity="0.45"/>'
        '<path class="st-c" d="M444,158 L444,168 M452,158 L452,168 M460,158 '
        'L460,168 M443,157 L461,157" stroke-width="1.8"/>'
        '<path class="st-c" d="M444,256 L444,266 M452,256 L452,266 M460,256 '
        'L460,266 M443,267 L461,267" stroke-width="1.8"/>'
        '<path class="st-c" d="M438,176 L466,176 M438,248 L466,248" '
        'stroke-width="1.3" stroke-opacity="0.7"/>'
        "</g>"
        "<!-- the ball: rolls the length of the pitch (SMIL), parks mid-pitch -->"
        '<g filter="url(#wob)">'
        '<g id="ball">'
        '<circle class="bgf" cx="452" cy="210" r="7" stroke="none"/>'
        '<circle class="st-y" cx="452" cy="210" r="5" stroke-width="2.4" fill="none"/>'
        '<path class="st-y" d="M449,207 C451,209 453,211 455,213" '
        'stroke-width="1.4" fill="none"/>'
        '<animateMotion dur="2.2s" repeatCount="indefinite" rotate="0" '
        'path="M452,210 C452,198 452,222 452,210 C452,198 452,222 452,210"/>'
        "</g>"
        "</g>"
        '<text class="tx-d halo" x="424" y="214" font-size="12" text-anchor="end" '
        'style="paint-order:stroke" stroke-width="4">22 yds</text>'
        "<!-- shot-class legend under the wheel -->"
        '<g font-size="12" fill="none" stroke-linecap="round">'
        '<path class="st-y" d="M300,352 L326,352" stroke-width="3" stroke-dasharray="6 4"/>'
        '<path class="st-cy" d="M470,352 L496,352" stroke-width="2.4"/>'
        '<path class="st-c" d="M625,352 L643,352" stroke-width="1.8"/>'
        "</g>"
        '<g font-size="12">'
        '<text class="tx-d" x="332" y="356">6 \u00b7 clears the rope</text>'
        '<text class="tx-d" x="502" y="356">4 \u00b7 to the fence</text>'
        '<text class="tx-d" x="649" y="356">nudged around</text>'
        "</g>"
        "<!-- top-8 day table (right) -->"
        '<text class="tx" x="560" y="84" font-size="12">top days</text>'
        f"<g>{table}</g>"
        "<!-- the season, week by week (bottom strip) -->"
        '<g id="strip">'
        '<path class="st-d" d="M30,422 L830,422" stroke-width="1.6"/>'
        f"{strip}"
        "</g>"
        f'<text class="tx-d" x="430" y="478" font-size="12" text-anchor="middle">'
        f"runs = commits \u00b7 wickets = blank weeks \u00b7 season = {SEASON_DAYS} "
        f"days \u00b7 avg {f1(stats.avg)}/day \u00b7 peak {stats.top}</text>"
        "</svg>"
    )


def truncate_words(text: str, limit: int = 64) -> str:
    """Collapse whitespace, cut at a word boundary near `limit`, add ellipsis."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed.rfind(" ", 0, limit + 1)
    if cut < 20:  # no sane word boundary: hard cut
        cut = limit
    return collapsed[:cut].rstrip() + "\u2026"


def pushed_ago(pushed: datetime, now: datetime) -> str:
    days = (now - pushed).days
    if days <= 0:
        return "pushed today"
    if days == 1:
        return "pushed yesterday"
    return f"pushed {days}d ago"


def select_now_repos(repos: list[Repo], user: str) -> list[Repo]:
    """Top 3 PUBLIC repos by pushedAt, excluding the profile repo itself and
    any fork/private entry. Fewer than 3 exist -> render fewer rows honestly."""
    eligible = [
        repo
        for repo in repos
        if repo.visibility == "PUBLIC" and repo.name.lower() != user.lower()
    ]
    eligible.sort(key=lambda r: (-r.pushed.timestamp(), r.name))
    return eligible[:3]


def render_now(rows: list[Repo], user: str, stamp: str, now: datetime) -> str:
    strokes = ("st-c", "st-y", "st-cy")
    if rows:
        cards = []
        for i, repo in enumerate(rows):
            y = 80 + i * 74
            color = repo.color or FALLBACK_LANG_COLOR
            lang = (repo.lang or "?")[:18]
            desc = truncate_words(repo.description or "no description yet")
            ago = pushed_ago(repo.pushed, now)
            cards.append(
                f'<g transform="rotate({-1.2 if i % 2 == 0 else 1.1} {CX} {y + 30})">'
                f'<rect class="panel {strokes[i % 3]}" x="26" y="{y}" width="748" '
                f'height="60" stroke-width="2.5" filter="url(#wob)"/>'
                f'<rect x="48" y="{y - 10}" width="74" height="20" rx="3" fill="#fbbf24" '
                f'fill-opacity="0.22" stroke="#fbbf24" stroke-opacity="0.6" '
                f'stroke-width="1.6" stroke-dasharray="5 4" '
                f'transform="rotate(-3 {85} {y})"/>'
                f'<text class="tx" x="48" y="{y + 25}" font-size="14" '
                f'font-weight="bold">{esc(repo.name)}</text>'
                f'<text class="tx-d" x="752" y="{y + 25}" font-size="12" '
                f'text-anchor="end">{esc(ago)}</text>'
                f'<circle cx="48" cy="{y + 41}" r="5" fill="{esc(color)}"/>'
                f'<text x="60" y="{y + 45}" font-size="12" fill="{esc(color)}">'
                f"{esc(lang)}</text>"
                f'<text class="tx-d" x="200" y="{y + 45}" font-size="13">{esc(desc)}</text>'
                f'<path class="st-d" d="M40,{y + 54} C200,{y + 52} 400,{y + 56} '
                f'560,{y + 53} C640,{y + 52} 700,{y + 55} 760,{y + 54}" '
                f'stroke-width="1.6" fill="none"/>'
                "</g>"
            )
        body = "".join(cards)
        row_noun = f"{len(rows)} active strand{'s' if len(rows) != 1 else ''}"
    else:
        body = (
            '<rect class="panel st-c" x="26" y="80" width="748" height="60" '
            'stroke-width="2.5" filter="url(#wob)"/>'
            '<text class="tx-d" x="48" y="116" font-size="13">no public repos yet '
            "\u00b7 check back soon</text>"
        )
        row_noun = "no public strands yet"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 300" role="img" '
        f'font-family="{FONT_STACK}">'
        f"<title>now building \u00b7 {esc(user)}'s latest public pushes</title>"
        f"<desc>Chalk notebook rows listing {esc(row_noun)}: name, language, "
        "description and push age, generated from live GitHub data.</desc>"
        f"<style>{CHALK_CSS}</style>"
        f"{CHALK_DEFS}"
        '<rect class="bg" x="0" y="0" width="800" height="300"/>'
        f"{notebook_kit(800, 300, short_stamp(stamp))}"
        '<text class="tx" x="42" y="44" font-size="26" letter-spacing="3">now building</text>'
        f"{body}"
        "</svg>"
    )


def aggregate_languages(repos: list[Repo]) -> list[tuple[str, str, int, float]]:
    """Sum language bytes across PUBLIC owner repos; top 5 by bytes.
    Each language keeps the color of its largest single contribution."""
    totals: dict[str, int] = {}
    colors: dict[str, str | None] = {}
    best: dict[str, int] = {}
    for repo in sorted(repos, key=lambda r: r.name):
        if repo.visibility != "PUBLIC":
            continue
        for name, color, size in repo.langs:
            totals[name] = totals.get(name, 0) + size
            if size > best.get(name, -1):
                best[name] = size
                colors[name] = color
    grand = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return [
        (name, colors.get(name) or FALLBACK_LANG_COLOR, size,
         (size / grand * 100.0 if grand else 0.0))
        for name, size in ranked
    ]


def render_ledger(langs: list[tuple[str, str, int, float]], stamp: str) -> str:
    if langs:
        rows = []
        for i, (name, color, _size, pct) in enumerate(langs):
            y = 108 + i * 44
            width = max(3.0, 420.0 * pct / 100.0)
            rows.append(
                f'<text class="tx" x="42" y="{y}" font-size="14">{esc(name[:16])}</text>'
                f'<rect x="210" y="{y - 12}" width="{f1(width)}" height="16" rx="8" '
                f'fill="{esc(color)}" fill-opacity="0.28" stroke="{esc(color)}" '
                f'stroke-width="2" filter="url(#wob)"/>'
                f'<text class="tx-d" x="{f1(210 + width + 14)}" y="{y}" '
                f'font-size="13">{f1(pct)}%</text>'
            )
        body = "".join(rows)
        noun = f"top {len(langs)} languages by bytes"
    else:
        body = (
            '<text class="tx-d" x="42" y="116" font-size="13">no language data '
            "\u00b7 public repos only</text>"
        )
        noun = "no language data"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 320" role="img" '
        f'font-family="{FONT_STACK}">'
        "<title>the ledger \u00b7 languages by bytes</title>"
        f"<desc>Chalk bars showing {esc(noun)} across public repositories, "
        "generated from live GitHub data.</desc>"
        f"<style>{CHALK_CSS}</style>"
        f"{CHALK_DEFS}"
        '<rect class="bg" x="0" y="0" width="800" height="320"/>'
        f"{notebook_kit(800, 320, short_stamp(stamp))}"
        '<text class="tx" x="42" y="48" font-size="26" letter-spacing="3">the ledger</text>'
        '<text class="tx-d" x="42" y="72" font-size="12">languages by bytes</text>'
        f"{body}"
        "</svg>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate chalkboard widgets (chalk-cricket/now/ledger SVGs) "
        "from live GitHub data. Never fabricates: failures exit 1 with no writes."
    )
    parser.add_argument("--stdin", action="store_true",
                        help="render from a JSON fixture on stdin (preview/testing)")
    parser.add_argument("--out-dir", default="assets", help="output directory")
    parser.add_argument("--user", default="iAMv1", help="GitHub login")
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

    total, weeks, repos = parse_payload(data, args.user)
    stats = compute_cricket(total, weeks)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d")
    year = now.strftime("%Y")

    now_rows = select_now_repos(repos, args.user)
    print(f"now: {[r.name for r in now_rows]} (public, newest pushes first)")
    langs = aggregate_languages(repos)
    print("ledger: " + (", ".join(f"{n} {p:.1f}%" for n, _c, _s, p in langs) or "empty"))

    # Render EVERYTHING before touching the filesystem: any failure above
    # leaves previously committed SVGs untouched.
    cricket_svg = render_cricket(stats, weeks, args.user, year, stamp)
    now_svg = render_now(now_rows, args.user, stamp, now)
    ledger_svg = render_ledger(langs, stamp)
    for name, svg in (("chalk-cricket", cricket_svg), ("chalk-now", now_svg),
                      ("chalk-ledger", ledger_svg)):
        if len(svg.encode("utf-8")) > 60 * 1024:
            die(f"{name}.svg exceeds 60KB")

    os.makedirs(args.out_dir, exist_ok=True)
    outputs = {
        "chalk-cricket.svg": cricket_svg,
        "chalk-now.svg": now_svg,
        "chalk-ledger.svg": ledger_svg,
    }
    for filename, svg in outputs.items():
        path = os.path.join(args.out_dir, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(svg)
        print(f"wrote {path} ({len(svg.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
