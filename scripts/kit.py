from __future__ import annotations


"""Shared chalk kit: canvas constants, CSS, geometry helpers, text utilities. No local imports."""


import sys
from datetime import datetime, timedelta, timezone
from typing import NoReturn
from xml.sax.saxutils import escape


FONT_STACK = "ui-monospace, 'Cascadia Mono', Consolas, monospace"


FALLBACK_LANG_COLOR = "#7dd3fc"  # chalk-cyan, used when GitHub reports no color


SEASON_DAYS = 365


CHALK_CSS = (
    ".bg{fill:#0d1117}"
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
    ".halo{stroke:#0d1117}"
    ".bgf{fill:#0d1117}"
    "@media (prefers-color-scheme: light){"
    ".bg{fill:#ffffff}"
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
    ".halo{stroke:#ffffff}"
    ".bgf{fill:#ffffff}"
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


CX = 400.0  # horizontal centre used by the now-building card tilt


def notebook_kit(w: int, h: int, stamp_text: str, top: int = 10) -> str:
    """Notebook identity: faint ruled lines + red-pen date stamp + one red tick."""
    ys = [round(h * f) for f in (0.28, 0.46, 0.64, 0.82)]
    rules = "".join(
        f'<line x1="24" y1="{y}" x2="{w - 24}" y2="{y}" '
        'stroke="#ffffff" stroke-opacity="0.06" stroke-width="1"/>'
        for y in ys
    )
    return f'<g id="rules">{rules}</g>{stamp_box(w, top, stamp_text)}'


def stamp_box(w: int, top: int, stamp_text: str) -> str:
    """The red-pen date stamp. One implementation; notebook_kit and the hero
    share it so the boxes can never drift apart."""
    box_w = 72
    return (
        f'<g id="stamp">'
        f'<rect x="{w - box_w - 14}" y="{top}" width="{box_w}" height="20" rx="4" '
        f'fill="none" class="st-r" stroke-width="1.6"/>'
        f'<text x="{w - 14 - box_w // 2}" y="{top + 14}" class="tx-r" font-size="11" '
        f'text-anchor="middle">{stamp_text}</text>'
        f'<text x="{w - 14 - box_w // 2}" y="{top + 32}" class="tx-r" font-size="11" '
        f'text-anchor="middle">\u2713</text>'
        f'</g>'
    )


def short_stamp(stamp: str) -> str:
    """'2026-09-12' style stamp -> '12·09·26' for the red date box."""
    parts = stamp.strip().split("-")
    if len(parts) == 3 and all(p.isdigit() and len(p) in (2, 4) for p in parts):
        year = parts[0][-2:]
        return f"{parts[2]}\u00b7{parts[1]}\u00b7{year}"
    return stamp[:10]


HERO_STYLE = '<style>.bg{fill:#0d1117}.field{fill:#161a22}.panel{fill:#1a1e27}.st-c{stroke:#f4f1e8}.st-d{stroke:#d9dde3}.st-y{stroke:#fbbf24}.st-cy{stroke:#7dd3fc}.st-r{stroke:#e26d5c}.tx{fill:#f4f1e8}.tx-d{fill:#d9dde3}.tx-y{fill:#fbbf24}.tx-cy{fill:#7dd3fc}.tx-r{fill:#e26d5c}.halo{stroke:#0d1117}@media (prefers-color-scheme: light){.bg{fill:#ffffff}.field{fill:#ece5d2}.panel{fill:#ffffff}.st-c{stroke:#2d3142}.st-d{stroke:#5b6270}.st-y{stroke:#b45309}.st-cy{stroke:#0369a1}.st-r{stroke:#b91c1c}.tx{fill:#2d3142}.tx-d{fill:#5b6270}.tx-y{fill:#b45309}.tx-cy{fill:#0369a1}.tx-r{fill:#b91c1c}.halo{stroke:#ffffff}}</style>'


HERO_DEFS = '<defs>\n<filter id="wob" x="-6%" y="-6%" width="112%" height="112%"><feTurbulence type="fractalNoise" baseFrequency="0.028" numOctaves="2" seed="4" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3"/></filter>\n<filter id="wob2" x="-6%" y="-6%" width="112%" height="112%"><feTurbulence type="fractalNoise" baseFrequency="0.038" numOctaves="2" seed="11" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"/></filter>\n</defs>'


IST = timezone(timedelta(hours=5, minutes=30))


BUILD_STYLE = (
    "<style>"
    "@media (prefers-color-scheme: light){"
    ".bg{fill:#ffffff}"
    ".panel{fill:#ffffff}"
    ".s{stroke:#2d3142}"
    ".tchalk{fill:#2d3142}"
    ".tdim{fill:#9aa2b1}"
    ".ay{stroke:#b45309}"
    ".ac{stroke:#0369a1}"
    ".acf{fill:#0369a1}"
    ".apr{stroke:#b91c1c}"
    ".aprf{fill:#b91c1c}"
    "}"
    ".st-r{stroke:#e26d5c}.tx-r{fill:#e26d5c}"
    "@media (prefers-color-scheme: light){.st-r{stroke:#b91c1c}.tx-r{fill:#b91c1c}}"
    "</style>"
)


BUILD_DEFS = (
    "<defs>"
    '<filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" '
    'seed="11" result="n"/>'
    '<feDisplacementMap in="SourceGraphic" in2="n" scale="3"/>'
    "</filter>"
    "</defs>"
)


BUILD_DOODLES: dict[str, str] = {
    "Go": (
        '<g filter="url(#wob)" fill="none" stroke="#7dd3fc" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round" class="ac">'
        '<path d="M34,2 L18,28"/>'
        '<path d="M18,28 L8,42 M18,28 L15,43 M18,28 L23,43 M18,28 L29,40"/>'
        '<path d="M11,34 L27,32"/>'
        "</g>"
    ),
    "JavaScript": (
        '<g filter="url(#wob)" fill="none" stroke="#fbbf24" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round" class="ay">'
        '<path d="M26,2 L8,26 L20,26 L18,44 L36,18 L23,18 Z"/>'
        "</g>"
    ),
    "TypeScript": (
        '<g filter="url(#wob)" fill="none" stroke="#fbbf24" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round" class="ay">'
        '<path d="M26,2 L8,26 L20,26 L18,44 L36,18 L23,18 Z"/>'
        "</g>"
    ),
    "Python": (
        '<g filter="url(#wob)" fill="none" stroke="#f9a8d4" stroke-width="2.6" '
        'stroke-linecap="round" stroke-linejoin="round" class="ap">'
        '<path d="M4,24 L14,24 L19,10 L26,36 L31,20 L35,24 L42,24"/>'
        '<circle cx="42" cy="24" r="2.4" fill="#f9a8d4" stroke="none"/>'
        "</g>"
    ),
}


BUILD_DOODLE_DEFAULT = (
    '<g filter="url(#wob)" fill="none" stroke="#f4f1e8" stroke-width="2.6" '
    'stroke-linecap="round" stroke-linejoin="round" class="s">'
    '<path d="M23,2 L39,8 L39,21 C39,32 31,39 23,43 C15,39 7,32 7,21 L7,8 Z"/>'
    '<path d="M15,21 L21,27 L31,16" stroke="#7dd3fc" class="ac"/>'
    "</g>"
)


def wrap_two(text: str, first: int = 34, second: int = 36) -> tuple[str, str]:
    """Split a blurb into two word-boundary lines, ending with an ellipsis
    when words are dropped so a card never ends mid-thought unmarked."""
    words = (text or "no description yet").split()
    line1: list[str] = []
    line2: list[str] = []
    dropped = False
    for word in words:
        if not dropped and len(" ".join(line1 + [word])) <= first:
            line1.append(word)
        elif not dropped and len(" ".join(line2 + [word])) <= second:
            line2.append(word)
        else:
            dropped = True
    if dropped:
        if line2:
            line2 = [(" ".join(line2)[: second - 1].rstrip() + "\u2026")]
        else:
            line1 = [(" ".join(line1)[: first - 1].rstrip() + "\u2026")]
    return " ".join(line1), " ".join(line2)


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


BUILD_POOL = 8            # freshest public repos considered for the showcase


BUILD_ROTATION_DAYS = 14  # the 4-card window slides every two weeks
