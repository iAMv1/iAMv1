import math
import os
import sys
import requests
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "iAMv1"

def fetch_top_repos():
    """Fetch the top 3 most recently pushed repos with real activity data."""
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN is not set. Cannot fetch live repo data.")
        sys.exit(1)

    query = """
    query($userName:String!) {
      user(login: $userName) {
        repositories(first: 3, ownerAffiliations: OWNER, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes {
            name
            description
            stargazerCount
            primaryLanguage { name }
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 1) {
                    totalCount
                  }
                }
              }
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
        r.raise_for_status()
        payload = r.json()
        if 'errors' in payload:
            print(f"Error: GitHub GraphQL returned errors: {payload['errors']}")
            sys.exit(1)
        repos = payload['data']['user']['repositories']['nodes']
        results = []
        for repo in repos:
            commits = 0
            try:
                commits = repo['defaultBranchRef']['target']['history']['totalCount']
            except (TypeError, KeyError):
                pass
            progress = min(95, int(math.log(max(1, commits)) / math.log(500) * 100))

            results.append({
                "name": repo['name'],
                "desc": (repo.get('description') or 'No description')[:50],
                "lang": (repo.get('primaryLanguage') or {}).get('name', '?'),
                "stars": repo.get('stargazerCount', 0),
                "progress": max(10, progress),
            })
        if not results:
            print("Error: GitHub API returned no repositories.")
            sys.exit(1)
        return results
    except requests.RequestException as e:
        print(f"Error: GitHub API network request failed: {e}")
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"Error: Unexpected GitHub API response structure: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching repos: {e}")
        sys.exit(1)


def generate_mission_svg():
    repos = fetch_top_repos()
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    status = "System Nominal"

    line_height = 24
    top_padding = 60
    # 3 header lines + 4 lines per repo + 1 footer
    total_lines = 4 + (len(repos) * 4) + 1
    HEIGHT = top_padding + (total_lines * line_height) + 20
    WIDTH = 480

    lines_svg = ""
    current_line = 1
    y_pos = top_padding + 20

    def add_line(content_svg):
        nonlocal current_line, y_pos, lines_svg
        lines_svg += f'  <text x="40" y="{y_pos}" class="vscode-text line-num">{current_line}</text>\n'
        lines_svg += f'  <text x="60" y="{y_pos}" class="vscode-text">{content_svg}</text>\n'
        y_pos += line_height
        current_line += 1

    add_line(f'<tspan class="t-key">status</tspan> <tspan class="t-punct">:</tspan> <tspan class="t-str">\'{status}\'</tspan>')
    add_line(f'<tspan class="t-key">last_uplink</tspan> <tspan class="t-punct">:</tspan> <tspan class="t-str">\'{time_str}\'</tspan>')
    add_line('')
    add_line(f'<tspan class="t-key">active_repos</tspan> <tspan class="t-punct">:</tspan>')

    for i, repo in enumerate(repos):
        bars = int(repo['progress'] / 5)
        bar_str = "█" * bars
        empty_str = "░" * (20 - bars)

        add_line(f'<tspan class="t-punct">-   </tspan><tspan class="t-key">name</tspan><tspan class="t-punct">:</tspan> <tspan class="t-str">\'{repo["name"]}\'</tspan>')
        add_line(f'<tspan class="t-key" dx="36">lang</tspan> <tspan class="t-punct">:</tspan> <tspan class="t-str">{repo["lang"]}</tspan>  <tspan class="t-comment"># ⭐ {repo["stars"]}</tspan>')
        bar_svg = f'<tspan class="t-key" dx="36">commits</tspan> <tspan class="t-punct">:\'</tspan><tspan class="bar-fill">{bar_str}</tspan><tspan class="bar-empty">{empty_str}</tspan><tspan class="t-punct">\'</tspan>   <tspan class="t-comment"># {repo["progress"]}%</tspan>'
        add_line(bar_svg)
        if i < len(repos) - 1:
            add_line('')

    add_line('')

    svg = f'''<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');

      .vscode-bg {{ fill: #0f172a; rx: 10px; stroke: #334155; stroke-width: 1px; }}
      .vscode-title {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px; fill: #f8fafc; opacity: 0.6; text-anchor: middle; }}
      .vscode-text {{ font-family: 'Fira Code', monospace; font-size: 14px; fill: #f8fafc; }}

      .mac-btn {{ fill: #f8fafc; opacity: 0.3; }}
      .line-num {{ fill: #f8fafc; opacity: 0.3; font-size: 13px; text-anchor: end; }}

      .t-key {{ fill: #f8fafc; }}
      .t-str {{ fill: #38bdf8; }}
      .t-comment {{ fill: #f8fafc; opacity: 0.4; }}
      .t-punct {{ fill: #f8fafc; opacity: 0.7; }}

      .bar-fill {{ fill: #38bdf8; }}
      .bar-empty {{ fill: #f8fafc; opacity: 0.2; }}
    </style>
  </defs>

  <rect class="vscode-bg" width="{WIDTH}" height="{HEIGHT}" />

  <!-- Mac Window Controls -->
  <circle cx="20" cy="20" r="6" class="mac-btn" />
  <circle cx="40" cy="20" r="6" class="mac-btn" />
  <circle cx="60" cy="20" r="6" class="mac-btn" />

  <text x="{WIDTH/2}" y="24" class="vscode-title">active_repos.yaml — Visual Studio Code</text>

  <rect x="0" y="40" width="{WIDTH}" height="1" fill="#f8fafc" opacity="0.1" />

{lines_svg}
</svg>'''

    os.makedirs('assets', exist_ok=True)
    with open('assets/crt_terminal_missions.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated Live Directives (Top 3 Repos) SVG.")


if __name__ == "__main__":
    generate_mission_svg()
