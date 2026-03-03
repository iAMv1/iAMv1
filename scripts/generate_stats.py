import os
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "iAMv1"


def fetch_github_stats():
    """Fetch comprehensive stats from GitHub GraphQL API."""
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not found. Using mock data.")
        return {"stars": 0, "commits": 0, "prs": 0, "issues": 0, "repos": 0,
                "contrib": 0, "languages": [], "streak": 0}

    query = """
    query($userName:String!) {
      user(login: $userName) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
        pullRequests(first: 1) { totalCount }
        issues(first: 1) { totalCount }
        contributionsCollection {
          totalCommitContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { contributionCount date }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    try:
        r = requests.post('https://api.github.com/graphql',
                          json={'query': query, 'variables': {'userName': GITHUB_USER}},
                          headers=headers)
        data = r.json()['data']['user']

        # Stars
        total_stars = sum(r['stargazerCount'] for r in data['repositories']['nodes'])
        # Languages
        lang_map = {}
        for repo in data['repositories']['nodes']:
            for edge in repo['languages']['edges']:
                name = edge['node']['name']
                color = edge['node'].get('color', '#38bdf8')
                lang_map[name] = lang_map.get(name, {'size': 0, 'color': color})
                lang_map[name]['size'] += edge['size']
        sorted_langs = sorted(lang_map.items(), key=lambda x: x[1]['size'], reverse=True)[:5]
        total_size = sum(l[1]['size'] for l in sorted_langs) or 1
        languages = [{"name": n, "pct": round(s['size'] / total_size * 100, 1), "color": s['color']} for n, s in sorted_langs]

        # Streak calculation
        weeks = data['contributionsCollection']['contributionCalendar']['weeks']
        all_days = []
        for w in weeks:
            for d in w['contributionDays']:
                all_days.append(d)
        # Calculate current streak
        streak = 0
        for day in reversed(all_days):
            if day['contributionCount'] > 0:
                streak += 1
            else:
                break

        return {
            "stars": total_stars,
            "commits": data['contributionsCollection']['totalCommitContributions'],
            "prs": data['pullRequests']['totalCount'],
            "issues": data['issues']['totalCount'],
            "repos": data['repositories']['totalCount'],
            "contrib": data['contributionsCollection']['contributionCalendar']['totalContributions'],
            "languages": languages,
            "streak": streak,
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {"stars": 0, "commits": 0, "prs": 0, "issues": 0, "repos": 0,
                "contrib": 0, "languages": [], "streak": 0}


def generate_stats_svg():
    stats = fetch_github_stats()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Build language bars
    lang_bars = ""
    bar_start_x = 30
    bar_width = 340
    for i, lang in enumerate(stats['languages']):
        segment_w = max(4, lang['pct'] / 100 * bar_width)
        lang_bars += f'<rect x="{bar_start_x}" y="{262 + i * 22}" width="{segment_w}" height="14" rx="3" fill="{lang["color"]}" opacity="0.85">'
        lang_bars += f'<animate attributeName="width" from="0" to="{segment_w}" dur="1.2s" fill="freeze" begin="{0.3 + i * 0.15}s" /></rect>\n'
        lang_bars += f'<text x="{bar_start_x + segment_w + 8}" y="{274 + i * 22}" class="label">{lang["name"]} ({lang["pct"]}%)</text>\n'

    # Stat items
    stat_items = [
        ("⭐", "Stars", stats['stars']),
        ("🔥", "Commits", stats['commits']),
        ("📦", "Repos", stats['repos']),
        ("🔀", "PRs", stats['prs']),
        ("⚡", "Contrib", stats['contrib']),
        ("🏏", "Streak", f"{stats['streak']}d"),
    ]

    stat_grid = ""
    for i, (icon, label, value) in enumerate(stat_items):
        col = i % 3
        row = i // 3
        x = 30 + col * 130
        y = 100 + row * 80
        stat_grid += f'''
        <g transform="translate({x}, {y})">
          <rect width="120" height="65" rx="10" class="stat-card">
            <animate attributeName="opacity" from="0" to="1" dur="0.6s" fill="freeze" begin="{0.1 + i * 0.1}s" />
          </rect>
          <text x="60" y="28" class="stat-value" text-anchor="middle">{value}</text>
          <text x="60" y="48" class="stat-label" text-anchor="middle">{icon} {label}</text>
        </g>'''

    svg = f'''<svg width="420" height="420" viewBox="0 0 420 420" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700;900&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');

      .bg {{ fill: #0f172a; }}
      .border-box {{ fill: none; stroke: #334155; stroke-width: 1.5; }}
      .stat-card {{ fill: #1e293b; stroke: #334155; stroke-width: 1; }}
      .stat-value {{
        font-family: 'Outfit', sans-serif;
        font-size: 22px;
        font-weight: 900;
        fill: #f8fafc;
        letter-spacing: 0.5px;
      }}
      .stat-label {{
        font-family: 'Fira Code', monospace;
        font-size: 10px;
        font-weight: 500;
        fill: #f8fafc;
        opacity: 0.6;
        letter-spacing: 1px;
      }}
      .title {{
        font-family: 'Outfit', sans-serif;
        font-size: 16px;
        font-weight: 700;
        fill: #f8fafc;
        letter-spacing: 1px;
      }}
      .subtitle {{
        font-family: 'Fira Code', monospace;
        font-size: 10px;
        fill: #f8fafc;
        opacity: 0.4;
      }}
      .label {{
        font-family: 'Fira Code', monospace;
        font-size: 10px;
        fill: #f8fafc;
        opacity: 0.7;
      }}
      .section-title {{
        font-family: 'Outfit', sans-serif;
        font-size: 12px;
        font-weight: 700;
        fill: #38bdf8;
        letter-spacing: 2px;
      }}
      .divider {{ stroke: #334155; stroke-width: 1; stroke-dasharray: 4 4; }}
      .accent-dot {{ fill: #38bdf8; }}

      @keyframes glow-pulse {{
        0%, 100% {{ r: 4; opacity: 1; }}
        50% {{ r: 7; opacity: 0.5; }}
      }}
      .pulse {{ animation: glow-pulse 2s ease-in-out infinite; }}

      @keyframes scan {{
        0% {{ transform: translateY(0); }}
        100% {{ transform: translateY(380px); }}
      }}
      .scanline {{
        fill: #38bdf8;
        opacity: 0.03;
        animation: scan 4s linear infinite;
      }}
    </style>

    <linearGradient id="headerGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.15" />
      <stop offset="100%" stop-color="#38bdf8" stop-opacity="0" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="420" height="420" rx="16" class="bg" />
  <rect x="1" y="1" width="418" height="418" rx="16" class="border-box" />

  <!-- Scanline effect -->
  <rect x="0" y="0" width="420" height="4" rx="2" class="scanline" />

  <!-- Header -->
  <rect x="1" y="1" width="418" height="60" rx="16" fill="url(#headerGrad)" />
  <circle cx="20" cy="30" r="4" class="accent-dot pulse" />
  <text x="36" y="26" class="title">{GITHUB_USER.upper()}</text>
  <text x="36" y="42" class="subtitle">LIVE SYSTEM TELEMETRY</text>
  <text x="400" y="36" class="subtitle" text-anchor="end">{ts}</text>

  <!-- Divider -->
  <line x1="20" y1="65" x2="400" y2="65" class="divider" />

  <!-- Section: Core Stats -->
  <text x="30" y="90" class="section-title">▸ CORE METRICS</text>
  {stat_grid}

  <!-- Divider -->
  <line x1="20" y1="245" x2="400" y2="245" class="divider" />

  <!-- Section: Languages -->
  <text x="30" y="258" class="section-title">▸ LANGUAGE PROFILE</text>
  {lang_bars}

  <!-- Bottom accent line -->
  <line x1="30" y1="400" x2="120" y2="400" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" opacity="0.5" />
  <circle cx="126" cy="400" r="3" class="accent-dot" opacity="0.5" />

</svg>'''

    os.makedirs('assets', exist_ok=True)
    with open('assets/github_stats.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated custom GitHub Stats SVG.")


if __name__ == "__main__":
    generate_stats_svg()
