from __future__ import annotations


"""Typed records and derivations. Every number rendered anywhere is computed here from live payloads."""


import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from kit import (BUILD_POOL, BUILD_ROTATION_DAYS, FALLBACK_LANG_COLOR,
                 SEASON_DAYS, die, parse_time)


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
    shots: list[tuple[Day, int]] = field(default_factory=list)  # (day, angle)


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
    print(
        f"cricket: runs={stats.runs} wickets={stats.wickets} overs={stats.overs} "
        f"top={stats.top} fours={stats.fours} sixes={stats.sixes} "
        f"avg={stats.avg}/day active={stats.active_days}"
    )
    return stats


def select_build_repos(
    repos: list[Repo], user: str, now: datetime
) -> list[Repo]:
    """The 4-card showcase: freshest 8 public repos form the pool, and a
    4-wide window slides by 2 every BUILD_ROTATION_DAYS. Deterministic per
    day: same date renders the same cards, and the set visibly refreshes
    every two weeks so nothing sits stale. Fewer than 4 eligible repos ->
    render fewer cards honestly."""
    eligible = [
        repo
        for repo in repos
        if repo.visibility == "PUBLIC" and repo.name.lower() != user.lower()
    ]
    eligible.sort(key=lambda r: (-r.pushed.timestamp(), r.name))
    pool = eligible[:BUILD_POOL]
    if not pool:
        return []
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc).date()
    period = max(0, (now.date() - epoch).days) // BUILD_ROTATION_DAYS
    start = (period * 2) % len(pool)
    return [pool[(start + k) % len(pool)] for k in range(min(4, len(pool)))]


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
