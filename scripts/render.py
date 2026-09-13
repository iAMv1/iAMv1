from __future__ import annotations


"""Chalk renderers. Pure functions: stats in, SVG out. No I/O, no fetching, deterministic."""


import calendar
import math
from datetime import datetime

from compute import CricketStats, Day, Repo
from kit import (BUILD_DEFS, BUILD_DOODLES, BUILD_DOODLE_DEFAULT,
                 BUILD_POOL, BUILD_ROTATION_DAYS, BUILD_STYLE,
                 CHALK_CSS, CHALK_DEFS, FALLBACK_LANG_COLOR,
                 CX,
                 FONT_STACK, HERO_DEFS, HERO_STYLE, SEASON_DAYS, esc,
                 f1, notebook_kit, pushed_ago, short_stamp, stamp_box,
                 truncate_words, wrap_two)


def hero_scene(hour: int) -> str:
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 16:
        return "noon"
    if 16 <= hour < 20:
        return "evening"
    return "night"


SCENE_CAPTIONS = {
    "morning": ("sun's up over Delhi.", "standup in ten."),
    "noon": ("Delhi at noon.", "brightness: yes."),
    "evening": ("golden hour.", "compiles faster."),
    "night": ("the moon keeps attendance", "for the stars too."),
}


FESTIVALS = (
    ((3, 20), (3, 24), "holi"),
    ((8, 13), (8, 16), "independence"),
    ((11, 6), (11, 11), "diwali"),
    ((12, 22), (12, 27), "christmas"),
    ((12, 30), (1, 2), "newyear"),
)


def hero_festival(month: int, day: int) -> str | None:
    for (sm, sd), (em, ed), key in FESTIVALS:
        if sm <= em:
            if (month, day) >= (sm, sd) and (month, day) <= (em, ed):
                return key
        elif (month, day) >= (sm, sd) or (month, day) <= (em, ed):
            return key
    return None


WMO_WORDS = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog", 51: "drizzle", 53: "drizzle", 55: "drizzle",
    56: "drizzle", 57: "drizzle", 61: "rain", 63: "rain", 65: "rain",
    66: "rain", 67: "rain", 71: "snow", 73: "snow", 75: "snow", 77: "snow",
    80: "showers", 81: "showers", 82: "showers", 95: "storm", 96: "storm",
    99: "storm",
}


def sun_disc(cx: float, cy: float, r: float) -> str:
    rays = []
    for k in range(8):
        rad = math.radians(k * 45.0 + 22.5)
        x1, y1 = cx + (r + 3) * math.cos(rad), cy + (r + 3) * math.sin(rad)
        x2, y2 = cx + (r + 9) * math.cos(rad), cy + (r + 9) * math.sin(rad)
        rays.append(f"M{f1(x1)},{f1(y1)} L{f1(x2)},{f1(y2)}")
    return (
        f'<circle class="st-y" cx="{f1(cx)}" cy="{f1(cy)}" r="{f1(r)}" '
        f'stroke-width="2.4"/>'
        f'<path class="st-y" d="{" ".join(rays)}" stroke-width="2"/>'
    )


def chalk_cloud(x: float, y: float, s: float) -> str:
    return (
        f'<path class="st-d" d="M{f1(x)},{f1(y)} '
        f'a{f1(9 * s)},{f1(9 * s)} 0 0 1 {f1(10 * s)},{f1(-8 * s)} '
        f'a{f1(8 * s)},{f1(8 * s)} 0 0 1 {f1(16 * s)},{f1(-2 * s)} '
        f'a{f1(8 * s)},{f1(8 * s)} 0 0 1 {f1(12 * s)},{f1(10 * s)} Z" '
        f'stroke-width="2" fill="none"/>'
    )


def rain_streaks(x: float, y: float) -> str:
    return " ".join(
        f"M{f1(x + i * 16)},{f1(y)} l-6,15" for i in range(6)
    )


def hero_sky(scene: str, code: int | None) -> str:
    """Everything inside the window pane: sun/moon by IST scene, then real
    Delhi weather over it (clouds, rain). Cross bars are drawn over this."""
    parts: list[str] = []
    if scene == "night":
        parts.append(
            '<path class="st-cy" d="M116,84 A20,20 0 1 0 116,126 '
            'A15,15 0 1 1 116,84 Z" stroke-width="2.4"/>'
        )
        parts.append(
            '<path class="st-cy" d="M228,74 L228,86 M222,80 L234,80" '
            'stroke-width="2">'
            '<animate attributeName="opacity" values="1;0.35;1" dur="2.4s" '
            'repeatCount="indefinite"/></path>'
            '<path class="st-cy" d="M244,148 L244,158 M239,153 L249,153" '
            'stroke-width="1.8">'
            '<animate attributeName="opacity" values="1;0.35;1" dur="3.1s" '
            'begin="0.7s" repeatCount="indefinite"/></path>'
            '<path class="st-cy" d="M212,166 L212,174 M208,170 L216,170" '
            'stroke-width="1.6">'
            '<animate attributeName="opacity" values="1;0.35;1" dur="2.8s" '
            'begin="1.3s" repeatCount="indefinite"/></path>'
        )
    elif scene == "morning":
        parts.append(sun_disc(110, 140, 13))
        parts.append(chalk_cloud(190, 100, 0.9))
    elif scene == "noon":
        parts.append(sun_disc(190, 85, 15))
    else:  # evening
        parts.append(sun_disc(215, 140, 14))
        parts.append(chalk_cloud(90, 130, 1.0))
    if code is not None:
        if code == 1:
            parts.append(chalk_cloud(200, 120, 0.8))
        elif code in (2, 3, 45, 48):
            parts.append(chalk_cloud(120, 110, 1.0))
            parts.append(chalk_cloud(200, 140, 0.8))
        if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
                    71, 73, 75, 77, 80, 81, 82, 95, 96, 99):
            parts.append(
                f'<path class="st-cy" d="{rain_streaks(80, 140)}" '
                f'stroke-width="1.6"/>'
            )
    return "".join(parts)


def diya(x: float, y: float) -> str:
    return (
        f'<path class="st-y" d="M{f1(x - 10)},{f1(y)} Q{f1(x)},{f1(y + 8)} '
        f'{f1(x + 10)},{f1(y)}" stroke-width="2.2"/>'
        f'<path class="st-d" d="M{f1(x - 6)},{f1(y + 8)} L{f1(x + 6)},{f1(y + 8)}" '
        f'stroke-width="1.6"/>'
        f'<path class="st-y" d="M{f1(x)},{f1(y - 4)} Q{f1(x + 3)},{f1(y - 10)} '
        f'{f1(x)},{f1(y - 16)} Q{f1(x - 3)},{f1(y - 10)} {f1(x)},{f1(y - 4)} Z" '
        f'stroke-width="1.8">'
        f'<animate attributeName="opacity" values="0.65;1;0.65" dur="1.6s" '
        f'repeatCount="indefinite"/></path>'
    )


def hero_festival_layer(key: str | None, year: int) -> str:
    """Doodles that appear on their own: diyas, fairy lights, fireworks,
    color splashes, a tiny tricolor. Positions avoid every fixed element."""
    if key == "diwali":
        return "".join(diya(x, 346) for x in (340, 450, 650))
    if key == "christmas":
        bulbs = []
        for i, x in enumerate((70, 108, 146, 184, 222, 256)):
            cls = "st-y" if i % 2 == 0 else "st-cy"
            bulbs.append(
                f'<circle class="{cls}" cx="{x}" cy="48" r="3.4" '
                f'stroke-width="1.8">'
                f'<animate attributeName="opacity" values="1;0.4;1" dur="1.2s" '
                f'begin="{i * 0.2:.1f}s" repeatCount="indefinite"/></circle>'
            )
        return "".join(bulbs)
    if key == "newyear":
        bursts = []
        for cx, cy in ((670, 70), (705, 55), (690, 95)):
            spokes = " ".join(
                f"M{cx},{cy} l{f1(10 * math.cos(math.radians(k * 45)))},"
                f"{f1(10 * math.sin(math.radians(k * 45)))}"
                for k in range(8)
            )
            bursts.append(
                f'<path class="st-y" d="{spokes}" stroke-width="1.6"/>'
            )
        return "".join(bursts) + (
            f'<text class="tx-y" x="688" y="132" font-size="12" '
            f'text-anchor="middle">{year}</text>'
        )
    if key == "holi":
        blobs = [
            (300, 110, 10, "#f9a8d4"), (695, 150, 8, "#fbbf24"),
            (90, 280, 9, "#7dd3fc"), (620, 320, 8, "#86efac"),
        ]
        return "".join(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" '
            f'fill-opacity="0.45" stroke="none"/>'
            for x, y, r, color in blobs
        ) + ('<text class="tx-d" x="90" y="306" font-size="11">holi hai</text>')
    if key == "independence":
        return (
            '<path class="st-c" d="M760,352 L760,310" stroke-width="2"/>'
            '<rect x="760" y="310" width="24" height="6" fill="#fbbf24" '
            'stroke="none"/>'
            '<rect x="760" y="316" width="24" height="6" fill="#f4f1e8" '
            'stroke="none"/>'
            '<rect x="760" y="322" width="24" height="6" fill="#7dd3fc" '
            'stroke="none"/>'
        )
    return ""


def hero_laptop_line(rows: list[Repo], now: datetime) -> str:
    if not rows:
        return "idle · nothing pushed"
    repo = rows[0]
    ago = pushed_ago(repo.pushed, now)
    short = {"pushed today": "today", "pushed yesterday": "yday"}.get(
        ago, ago.replace("pushed ", "").replace(" ago", "")
    )
    line = f"{repo.name} · {short}"
    return line if len(line) <= 17 else repo.name[:16]


def render_hero(
    rows: list[Repo], stamp: str, moment: datetime,
    weather: tuple[int, int] | None,
) -> str:
    """The room, faithful to the approved hand art, with a living window:
    IST scene (sun/moon), real Delhi weather over it, festival doodles on
    their dates, and the laptop screen showing the latest live push."""
    scene = hero_scene(moment.hour)
    cap1, cap2 = SCENE_CAPTIONS[scene]
    code = weather[1] if weather else None
    sky = hero_sky(scene, code)
    fest = hero_festival_layer(hero_festival(moment.month, moment.day),
                               moment.year + (1 if (moment.month, moment.day) >= (12, 30) else 0))
    readout = ""
    if weather:
        temp, wcode = weather
        readout = (
            f'<text class="tx-d" x="58" y="182" font-size="10">'
            f"{temp}\u00b0 \u00b7 {WMO_WORDS.get(wcode, 'sky')}</text>"
        )
    laptop = esc(hero_laptop_line(rows, moment))
    stamp_txt = esc(short_stamp(stamp))
    desc = (
        "The room as hero: chalk name on the wall, a window showing the real "
        f"Delhi sky for the current IST {scene}, tool posters, desk with a "
        "laptop on the latest live push, streak plant, mug."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 400" role="img" '
        f'aria-labelledby="heroTitle heroDesc" font-family="{FONT_STACK}">'
        f"<title id=\"heroTitle\">PRATHAM, at the desk at {esc(scene)} "
        f"(IST)</title>"
        f'<desc id="heroDesc">{esc(desc)}</desc>'
        f"{HERO_STYLE}"
        f"{HERO_DEFS}"
        '<rect class="bg" x="0" y="0" width="860" height="400"/>'
        '<g id="rules">'
        '<line x1="24" y1="104" x2="836" y2="104" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="176" x2="836" y2="176" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="248" x2="836" y2="248" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="320" x2="836" y2="320" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        "</g>"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round">'
        '<path class="st-c" d="M48,48 Q156.5,48.8 268,48 Q268.6,119.9 268,192 '
        'Q156.8,193.3 48,192 Z" stroke-width="3"/>'
        f"{sky}"
        f"{readout}"
        '<path class="st-c" d="M158,50 L158,190 M50,120 L266,120" '
        'stroke-width="2.2"/>'
        "</g>"
        f'<text class="tx-d" x="48" y="216" font-size="12">{esc(cap1)}</text>'
        f'<text class="tx-d" x="48" y="232" font-size="12">{esc(cap2)}</text>'
        '<text class="tx-d" x="330" y="86" font-size="15" '
        'letter-spacing="2">hey, i\'m</text>'
        '<text class="tx-y" x="326" y="152" font-size="64" font-weight="900" '
        'letter-spacing="4" font-family="system-ui, -apple-system, '
        "'Segoe UI', sans-serif\" filter=\"url(#wob2)\">PRATHAM</text>"
        '<path class="st-y" d="M326,174 Q444.8,171.0 560,170 Q590.4,175.9 624,178" '
        'stroke-width="3.2" fill="none" stroke-linecap="round"/>'
        '<text class="tx" x="328" y="206" font-size="16">3D web \u00b7 applied AI '
        "\u00b7 Delhi \u00b7 ships after midnight</text>"
        '<g filter="url(#wob)" fill="none">'
        '<rect class="st-y" x="328" y="224" width="196" height="26" rx="13" '
        'stroke-width="2"/>'
        '<text class="tx-y" x="426" y="241" font-size="12" '
        'text-anchor="middle">3D web \u00b7 three.js enjoyer</text>'
        "</g>"
        '<g filter="url(#wob)" fill="none">'
        '<rect class="st-cy" x="536" y="224" width="182" height="26" rx="13" '
        'stroke-width="2"/>'
        '<text class="tx-cy" x="627" y="241" font-size="12" '
        'text-anchor="middle">AI \u00b7 pytorch gremlin</text>'
        "</g>"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round">'
        '<g transform="rotate(-2.5 782 96)">'
        '<rect class="st-c" x="736" y="48" width="92" height="96" rx="4" '
        'stroke-width="2.4"/>'
        '<path class="st-y" d="M764,72 L800,88 L764,104 L730,88 Z" '
        'stroke-width="2"/>'
        '<path class="st-d" d="M764,72 L764,104 M730,88 L730,120 L764,104 '
        'M800,88 L764,104 L764,136" stroke-width="1.6"/>'
        '<text class="tx" x="782" y="136" font-size="12" text-anchor="middle" '
        'font-weight="bold">three.js</text>'
        "</g>"
        '<g transform="rotate(2 782 236)">'
        '<rect class="st-c" x="736" y="188" width="92" height="96" rx="4" '
        'stroke-width="2.4"/>'
        '<path class="st-cy" d="M782,204 C772,216 774,226 782,234 C790,242 '
        '788,250 782,254 C794,250 800,240 796,240 C804,254 794,268 782,270 '
        'C770,268 764,256 770,246 C760,236 766,210 782,204 Z" '
        'stroke-width="1.8"/>'
        '<text class="tx" x="782" y="276" font-size="12" text-anchor="middle" '
        'font-weight="bold">pytorch</text>'
        "</g>"
        "</g>"
        '<g transform="rotate(-3 344 252)">'
        '<rect class="panel st-y" x="304" y="224" width="80" height="56" rx="4" '
        'stroke-width="2" filter="url(#wob)"/>'
        '<text class="tx" x="344" y="246" font-size="12" '
        'text-anchor="middle">shipping</text>'
        '<text class="tx-y" x="344" y="264" font-size="12" '
        'text-anchor="middle" font-weight="bold">week</text>'
        '<path class="st-y" d="M322,262 C338,266 356,266 370,262" '
        'stroke-width="1.6" fill="none"/>'
        "</g>"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round">'
        '<path class="st-c" d="M48,356 Q430.4,352.5 812,352" stroke-width="3"/>'
        '<path class="st-c" d="M84,356 L80,406 M290,354 L294,406 M560,353 '
        'L556,406 M770,352 L766,406" stroke-width="2.4"/>'
        '<g transform="rotate(-1 180 320)">'
        '<rect class="st-c" x="106" y="240" width="150" height="94" rx="6" '
        'stroke-width="2.6"/>'
        '<rect class="panel st-c" x="114" y="246" width="134" height="76" '
        'stroke-width="1.8"/>'
        '<text class="tx-d" x="122" y="264" font-size="11">'
        "$ git push origin</text>"
        f'<text class="tx-y" x="122" y="280" font-size="10">{laptop}</text>'
        '<rect x="122" y="288" width="7" height="12" fill="#fbbf24" '
        'stroke="none">'
        '<animate attributeName="opacity" values="1;1;0;0;1" '
        'keyTimes="0;0.45;0.5;0.95;1" dur="1.1s" repeatCount="indefinite"/>'
        '</rect>'
        '<rect class="st-c" x="98" y="334" width="166" height="8" rx="4" '
        'stroke-width="2"/>'
        "</g>"
        '<g id="plant">'
        '<path class="st-c" d="M702,333 L701,310 C700.6,296 701.4,292 702,288" '
        'stroke-width="2.6"/>'
        '<path class="st-c" d="M702,318 C692,312 682,304 680,292" '
        'stroke-width="2"/>'
        '<path class="st-c" d="M702,306 C712,300 720,292 723,282" '
        'stroke-width="2"/>'
        '<path class="st-c" d="M702,296 C697,288 695,278 698,274" '
        'stroke-width="2"/>'
        '<path class="st-c" d="M702,296 C710,288 716,282 728,278" '
        'stroke-width="2"/>'
        '<path class="st-c" d="M701,310 C693,316 686,322 679,320" '
        'stroke-width="1.8"/>'
        "</g>"
        '<g id="leaves">'
        '<path class="st-c" d="M680,292 Q687,284 683,275 Q676,284 680,292 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.34"/>'
        '<path class="st-c" d="M728,278 Q736,271 732,263 Q724,271 728,278 Z" '
        'stroke-width="1.8" fill="#fbbf24" fill-opacity="0.3"/>'
        '<path class="st-c" d="M698,274 Q705,266 701,260 Q693,266 698,274 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.34"/>'
        '<path class="st-c" d="M679,320 Q686,312 682,304 Q672,312 679,320 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.28"/>'
        '<path class="st-c" d="M723,282 Q731,274 727,266 Q719,274 723,282 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.3"/>'
        '<path class="st-c" d="M706,296 Q714,288 710,280 Q700,288 706,296 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.28"/>'
        '<path class="st-c" d="M688,314 Q695,306 691,298 Q681,306 688,314 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.26"/>'
        '<path class="st-c" d="M714,320 Q721,312 717,304 Q709,312 714,320 Z" '
        'stroke-width="1.8" fill="#7dd3fc" fill-opacity="0.28"/>'
        '<path class="st-c" d="M702,288 Q709,280 705,272 Q695,280 702,288 Z" '
        'stroke-width="1.8" fill="#fbbf24" fill-opacity="0.26"/>'
        "</g>"
        '<path class="st-y" d="M688,331 L720,331 L716,352 L692,352 Z" '
        'stroke-width="2"/>'
        '<path class="st-d" d="M688,331 L720,331" stroke-width="2"/>'
        '<text class="tx-d" x="702" y="370" font-size="11" '
        'text-anchor="middle">9 leaves \u00b7 best 12</text>'
        '<g filter="url(#wob)" fill="none">'
        '<rect class="st-c" x="576" y="318" width="34" height="30" rx="4" '
        'stroke-width="2.2"/>'
        '<path class="st-c" d="M610,324 C622,324 622,340 610,342" '
        'stroke-width="2"/>'
        '<path class="st-d" d="M586,308 C584,302 590,298 588,292" '
        'stroke-width="1.6">'
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 -8" dur="2.4s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.9;0" dur="2.4s" '
        'repeatCount="indefinite"/>'
        '</path>'
        '<path class="st-d" d="M596,308 C594,302 600,298 598,292" '
        'stroke-width="1.6">'
        '<animateTransform attributeName="transform" type="translate" '
        'values="0 0;0 -8" dur="2.4s" begin="1.2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values="0.9;0" dur="2.4s" '
        'begin="1.2s" repeatCount="indefinite"/>'
        '</path>'
        "</g>"
        "</g>"
        '<path class="st-r" d="M394,228 C400,226 400,230 396,234" '
        'stroke-width="1.8" fill="none"/>'
        f"{fest}"
        f"{stamp_box(860, 10, stamp_txt)}"
        "</svg>"
    )


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
        return "st-c", "1.8", 0.30, "", None
    return "st-c", "1.8", 0.18, "", None  # single: thin white, very short


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
        if dx > 0.05:
            # the top-days table lives right of x=568: spokes (tips,
            # arrowheads and all) stop at 560
            length = min(length, (560.0 - WHEEL_CX) / dx)
        ex, ey = WHEEL_CX + length * dx, WHEEL_CY + length * dy
        mx, my = (WHEEL_CX + ex) / 2 - dy * 12.0, (WHEEL_CY + ey) / 2 + dx * 12.0
        delay = 0.15 * n
        shimmer = (
            '<animate attributeName="stroke-dashoffset" values="0;-26" '
            'dur="1.8s" begin="1.2s" repeatCount="indefinite"/>'
        ) if tag == "6" else ""
        lines.append(
            f'<path class="{cls}" d="M{f1(WHEEL_CX)},{f1(WHEEL_CY)} '
            f'Q{f1(mx)},{f1(my)} {f1(ex)},{f1(ey)}" '
            f'stroke-width="{width}"{dash}>'
            f'<animate attributeName="stroke-dashoffset" from="160" to="0" '
            f'dur="0.9s" begin="{delay:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" from="0" to="1" '
            f'dur="0.3s" begin="{delay:.2f}s" fill="freeze"/>{shimmer}</path>'
        )
        if tag:
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
            if lx > 568.0 or ly > 338.0 or ly < 92.0:  # table / legend / scoreboard
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
    peak_bx = ""
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
            peak_bx = f1(x + 2.0)
            if x + 2.0 + STRIP_BAR_W + 44.0 <= 830.0:
                peak_x, peak_anchor = f1(x + 2.0 + STRIP_BAR_W + 5.0), "start"
            else:
                peak_x, peak_anchor = f1(x - 3.0), "end"
    peak_label = (
        f'<text class="tx-y halo" x="{peak_x}" y="390" font-size="10" '
        f'text-anchor="{peak_anchor}" style="paint-order:stroke" '
        f'stroke-width="3">{peak}</text>'
    ) if peak else ""
    if peak_bx:
        pulse = ('<animate attributeName="opacity" values="1;0.7;1" '
                 'dur="2s" repeatCount="indefinite"/>')
        bars = [
            b.replace('stroke="none">', 'stroke="none">' + pulse, 1)
            if f'x="{peak_bx}"' in b else b
            for b in bars
        ]
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
        y = 106 + i * 18  # header sits at 96, box bottom at ~74
        width = max(3.0, 32.0 * day.count / stats.top) if stats.top else 3.0
        cls = "st-y" if day.count >= 6 else ("st-cy" if day.count >= 4 else "st-d")
        rows.append(
            f'<text class="tx-d" x="596" y="{y}" font-size="12">{esc(day.date[5:])}</text>'
            f'<path class="{cls}" d="M688,{f1(y - 4)} L{f1(688 + width)},{f1(y - 4)}" '
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
        '<path class="st-c" d="M26,12 C240,8 560,14 834,11 C837,30 833,56 835,70 '
'C640,74 220,73 25,74 C23,50 27,28 26,12 Z" stroke-width="2.6"/>'
        '<path class="st-y" d="M42,52 C120,48 220,55 286,50" stroke-width="2.6"/>'
        '<path class="st-d" d="M292,18 C290,32 294,52 291,70" stroke-width="2"/>'
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
        "<!-- mini pitch: compact strip, worn patch, stumps both ends -->"
        '<g filter="url(#wob)" fill="none" stroke-linecap="round">'
        '<path class="pitchfill st-c" d="M444,186 C448,185 458,187 460,186 '
'C464,200 462,224 463,240 C457,241 447,239 444,234 C443,218 445,198 '
'444,186 Z" stroke-width="1.8"/>'
        '<ellipse class="st-d" cx="452" cy="210" rx="8" ry="2.6" stroke-width="1.1" '
'stroke-opacity="0.45"/>'
        '<path class="st-c" d="M447,176 L447,186 M452,176 L452,186 M457,176 '
'L457,186 M446,175 L458,175" stroke-width="1.4"/>'
        '<path class="st-c" d="M447,234 L447,244 M452,234 L452,244 M457,234 '
'L457,244 M446,245 L458,245" stroke-width="1.4"/>'
        "</g>"
        "<!-- the ball: rolls the length of the pitch (SMIL), parks mid-pitch -->"
        '<g filter="url(#wob)">'
        '<g id="ball">'
        '<circle class="bgf" cx="452" cy="210" r="7" stroke="none"/>'
        '<circle class="st-y" cx="452" cy="210" r="5" stroke-width="2.4" fill="none"/>'
        '<path class="st-y" d="M449,207 C451,209 453,211 455,213" '
        'stroke-width="1.4" fill="none"/>'
        '<animateMotion dur="2.6s" repeatCount="indefinite" rotate="0" '
        'path="M452,178 L452,206 L446,213 L452,238 '
        'C450,218 454,198 452,178 Z"/>'
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
        '<text class="tx" x="580" y="96" font-size="12">top days</text>'
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




def render_build(
    repo: Repo, index: int, stamp: str, now: datetime
) -> str:
    """One 410x150 chalk project card from a live repo record."""
    name = repo.name[:18]
    lang = (repo.lang or "?")[:14]
    color = repo.color or FALLBACK_LANG_COLOR
    doodle = BUILD_DOODLES.get(repo.lang or "", BUILD_DOODLE_DEFAULT)
    line1, line2 = wrap_two(repo.description)
    ago = pushed_ago(repo.pushed, now)
    dot_x = 86 + len(name) * 9 + 14
    title = f"{repo.name}, {truncate_words(repo.description or 'no description yet', 50)}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 410 150" role="img" '
        f'font-family="{FONT_STACK}">'
        f"<title>{esc(title)}</title>"
        f"<desc>Chalkboard project card for {esc(repo.name)}: live description, "
        f"language and push age, regenerated from GitHub data.</desc>"
        f"{BUILD_STYLE}"
        f"{BUILD_DEFS}"
        '<rect class="bg" x="0" y="0" width="410" height="150" rx="6" fill="#0d1117"/>'
        '<g id="rules">'
        '<line x1="24" y1="42" x2="386" y2="42" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="69" x2="386" y2="69" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="96" x2="386" y2="96" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        '<line x1="24" y1="123" x2="386" y2="123" stroke="#ffffff" '
        'stroke-opacity="0.06" stroke-width="1"/>'
        "</g>"
        '<rect class="panel s" x="3" y="3" width="404" height="144" fill="#171a21" '
        'stroke="#f4f1e8" stroke-width="2.5" filter="url(#wob)" '
        'transform="rotate(-0.6 205 75)"/>'
        '<g transform="translate(24,24)">'
        f"{doodle}"
        "</g>"
        f'<text class="tchalk" x="86" y="50" font-size="17" font-weight="bold" '
        f'fill="#f4f1e8">{esc(name)}</text>'
        f'<circle cx="{dot_x}" cy="44" r="4" fill="{esc(color)}" class="acf"/>'
        f'<text class="tdim" x="{dot_x + 10}" y="49" font-size="12" '
        f'fill="#d9dde3">{esc(lang)}</text>'
        f'<text class="tdim" x="86" y="76" font-size="13" fill="#d9dde3">'
        f"{esc(line1)}</text>"
        f'<text class="tdim" x="86" y="94" font-size="13" fill="#d9dde3">'
        f"{esc(line2)}</text>"
        f'<text class="tdim" x="384" y="68" font-size="10" text-anchor="end" '
        f'fill="#d9dde3">{esc(ago)}</text>'
        '<g filter="url(#wob)" fill="none" stroke="#fbbf24" stroke-width="2.2" '
        'stroke-linecap="round" class="ay">'
        '<path d="M336,120 C356,116 372,120 388,116 M382,110 L389,116 L382,122"/>'
        "</g>"
        '<g filter="url(#wob)" fill="none" stroke="#e26d5c" stroke-width="1.6" '
        'stroke-linecap="round" class="apr">'
        '<rect x="304" y="10" width="88" height="22" rx="4"/>'
        "</g>"
        f'<text x="348" y="25" font-size="11" text-anchor="middle" fill="#e26d5c" '
        f'class="aprf">{esc(short_stamp(stamp))}</text>'
        f'<text x="384" y="50" font-size="11" text-anchor="end" fill="#e26d5c" '
        f'class="aprf">no. {index + 1}</text>'
        "</svg>"
    )


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


def render_ledger(langs: list[tuple[str, str, int, float]], stamp: str) -> str:
    """The ledger: ranked language tracks scaled to the top language, so the
    bars always fill the canvas instead of dying at 28%."""
    if langs:
        top = max(p for _n, _c, _s, p in langs)
        rows = []
        for i, (name, color, _size, pct) in enumerate(langs):
            y = 108 + i * 44
            fill = max(4.0, 360.0 * pct / top) if top else 4.0
            rows.append(
                f'<text class="tx-d" x="42" y="{y}" font-size="12">'
                f"{i + 1:02d}</text>"
                f'<text class="tx" x="76" y="{y}" font-size="14">{esc(name[:14])}</text>'
                f'<rect x="250" y="{y - 12}" width="360" height="14" rx="7" '
                f'fill="#ffffff" fill-opacity="0.07" stroke="none"/>'
                f'<rect x="250" y="{y - 12}" width="{f1(fill)}" height="14" rx="7" '
                f'fill="{esc(color)}" fill-opacity="0.85" stroke="none" '
                f'filter="url(#wob)"/>'
                f'<text class="tx-d" x="624" y="{y}" '
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
