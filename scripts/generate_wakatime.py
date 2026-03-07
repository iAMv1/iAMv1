import os
import sys
import base64
import requests
from datetime import datetime, timedelta

WAKATIME_API_KEY = os.environ.get("WAKATIME_API_KEY", "")

DAYS_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def _wakatime_headers():
    """Return Basic-auth headers with the API key correctly base64-encoded."""
    encoded_key = base64.b64encode(f"{WAKATIME_API_KEY}:".encode()).decode()
    return {"Authorization": f"Basic {encoded_key}"}


def fetch_wakatime_data():
    """
    Fetch real coding activity from WakaTime.

    Uses:
      /summaries?range=last_7_days  — real per-day totals that drive the heatmap
      /stats/last_7_days            — aggregated summary stats (total time, daily avg, top lang)

    Returns None when WAKATIME_API_KEY is not configured.
    Exits with code 1 when the key is set but the API call fails, so the
    workflow never silently commits fake data.
    """
    if not WAKATIME_API_KEY:
        print("Info: WAKATIME_API_KEY not set — generating 'not configured' placeholder SVG.")
        return None

    headers = _wakatime_headers()

    try:
        # --- Per-day summaries (drives heatmap) ---
        summaries_url = "https://wakatime.com/api/v1/users/current/summaries?range=last_7_days"
        sr = requests.get(summaries_url, headers=headers, timeout=15)
        if sr.status_code != 200:
            print(f"Error: WakaTime summaries API returned HTTP {sr.status_code}: {sr.text[:200]}")
            sys.exit(1)
        summaries = sr.json().get("data", [])

        # --- Aggregated stats (total time, daily avg, top language) ---
        stats_url = "https://wakatime.com/api/v1/users/current/stats/last_7_days"
        tr = requests.get(stats_url, headers=headers, timeout=15)
        if tr.status_code != 200:
            print(f"Error: WakaTime stats API returned HTTP {tr.status_code}: {tr.text[:200]}")
            sys.exit(1)
        stats = tr.json().get("data", {})

        daily_avg = stats.get("human_readable_daily_average", "N/A")
        total_time = stats.get("human_readable_total", "N/A")
        languages = stats.get("languages", [])
        top_lang = languages[0].get("name", "N/A") if languages else "N/A"

        # --- Build real heatmap from per-day total_seconds ---
        # Map abbreviated weekday name → total coding seconds for that day
        day_totals = {}
        for summary in summaries:
            date_str = summary.get("range", {}).get("date", "")
            if not date_str:
                continue
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = dt.strftime("%a")  # "Mon", "Tue", …
            day_totals[day_name] = summary.get("grand_total", {}).get("total_seconds", 0.0)

        max_secs = max(day_totals.values(), default=0) or 1  # avoid division by zero

        heatmap = []
        for day in DAYS_ORDER:
            secs = day_totals.get(day, 0)
            # Intensity 0–4 proportional to that day's real coding time
            intensity = round(secs / max_secs * 4)
            # All 24 hour-columns share the same daily intensity
            # (free-tier WakaTime doesn't expose per-hour breakdowns)
            heatmap.append([intensity] * 24)

        return {
            "heatmap": heatmap,
            "daily_avg": daily_avg,
            "total_time": total_time,
            "top_lang": top_lang,
            "days": DAYS_ORDER,
            "hours": [f"{i:02d}:00" for i in range(24)],
        }

    except requests.RequestException as e:
        print(f"Error: WakaTime network request failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected failure fetching WakaTime data: {e}")
        sys.exit(1)

def generate_not_configured_svg(svg_width, svg_height):
    """Return a clean placeholder SVG shown when WAKATIME_API_KEY is absent."""
    return f'''<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');
      .bg {{ fill: #0f172a; }}
      .border-box {{ fill: none; stroke: #334155; stroke-width: 1.5; }}
      .title {{ font-family: 'Outfit', sans-serif; font-size: 16px; font-weight: 700; fill: #f8fafc; letter-spacing: 1px; }}
      .sub {{ font-family: 'Fira Code', monospace; font-size: 11px; fill: #38bdf8; opacity: 0.8; }}
      .hint {{ font-family: 'Fira Code', monospace; font-size: 10px; fill: #f8fafc; opacity: 0.45; }}
    </style>
  </defs>
  <rect width="{svg_width}" height="{svg_height}" rx="10" class="bg" />
  <rect x="1" y="1" width="{svg_width-2}" height="{svg_height-2}" rx="10" class="border-box" />
  <text x="{svg_width//2}" y="{svg_height//2 - 30}" class="title" text-anchor="middle">WAKATIME / CODING ACTIVITY</text>
  <text x="{svg_width//2}" y="{svg_height//2}" class="sub" text-anchor="middle">⚙ Not Configured</text>
  <text x="{svg_width//2}" y="{svg_height//2 + 24}" class="hint" text-anchor="middle">Add WAKATIME_API_KEY to your repo secrets</text>
  <text x="{svg_width//2}" y="{svg_height//2 + 42}" class="hint" text-anchor="middle">to see real coding activity here.</text>
</svg>'''


def generate_wakatime_svg():
    data = fetch_wakatime_data()

    svg_width = 480
    svg_height = 488

    # No WakaTime key configured — write a clean placeholder and exit cleanly
    if data is None:
        os.makedirs('assets', exist_ok=True)
        with open('assets/wakatime_heatmap.svg', 'w', encoding='utf-8') as f:
            f.write(generate_not_configured_svg(svg_width, svg_height))
        print("Generated WakaTime placeholder SVG (WAKATIME_API_KEY not configured).")
        return

    # Calculate vertical centering offset: (488 - 250) / 2 = 119
    offset_y = 119

    svg = f'''<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');

      .bg {{ fill: #0f172a; }}
      .border-box {{ fill: none; stroke: #334155; stroke-width: 1.5; }}
      .title {{
        font-family: 'Outfit', sans-serif;
        font-size: 14px;
        font-weight: 700;
        fill: #f8fafc;
        letter-spacing: 1px;
      }}
      .val {{
        font-family: 'Outfit', sans-serif;
        font-size: 16px;
        font-weight: 900;
        fill: #38bdf8;
      }}
      .label {{
        font-family: 'Fira Code', monospace;
        font-size: 10px;
        fill: #f8fafc;
        opacity: 0.6;
      }}
      .heat-tile {{
        rx: 3px;
        ry: 3px;
        stroke: #0f172a;
        stroke-width: 2px;
      }}
    </style>
  </defs>

  <rect width="{svg_width}" height="{svg_height}" rx="10" class="bg" />
  <rect x="1" y="1" width="{svg_width-2}" height="{svg_height-2}" rx="10" class="border-box" />

  <g transform="translate(30, {offset_y})">
    <!-- Header -->
    <text x="20" y="30" class="title">WAKATIME / CODING ACTIVITY</text>
    <circle cx="{svg_width - 25}" cy="25" r="4" fill="#38bdf8">
      <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite" />
    </circle>

    <!-- Summary Stats -->
    <text x="20" y="60" class="label">LAST 7 DAYS</text>
    <text x="20" y="80" class="val">{data["total_time"]}</text>
    
    <text x="160" y="60" class="label">DAILY AVG</text>
    <text x="160" y="80" class="val">{data["daily_avg"]}</text>

    <text x="290" y="60" class="label">TOP LANG</text>
    <text x="290" y="80" class="val">{data["top_lang"]}</text>

    <!-- Heatmap Grid -->
    <g transform="translate(20, 110)">'''

    # Grid logic
    cell_size = 14
    
    # Days labels
    for i, day in enumerate(data["days"]):
        y_pos = i * cell_size + 10
        svg += f'<text x="0" y="{y_pos}" class="label" font-size="9px">{day}</text>'

    # Time labels (every 4 hours)
    for i in range(0, 24, 4):
        x_pos = 35 + i * cell_size
        svg += f'<text x="{x_pos}" y="-5" class="label" font-size="8px">{i}h</text>'

    # Heatmap tiles
    color_map = {0: "#1e293b", 1: "#0ea5e940", 2: "#0ea5e970", 3: "#0ea5e9a0", 4: "#38bdf8"}
    
    for day_idx, day_data in enumerate(data["heatmap"]):
        for hour_idx, intensity in enumerate(day_data):
            x = 35 + hour_idx * cell_size
            y = day_idx * cell_size
            color = color_map.get(intensity, "var(--heat-0)")
            
            # Animation delay cascade based on x/y
            delay = (day_idx * 0.05) + (hour_idx * 0.03)
            
            svg += f'''
            <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" class="heat-tile" fill="{color}" opacity="0">
              <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="{delay}s" fill="freeze" />
            </rect>'''

    svg += '''
  </g>
  </g>
</svg>'''

    os.makedirs('assets', exist_ok=True)
    with open('assets/wakatime_heatmap.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated WakaTime Heatmap SVG.")

if __name__ == "__main__":
    generate_wakatime_svg()
