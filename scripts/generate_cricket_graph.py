import os
import sys
import requests
from datetime import datetime

# GitHub API setup
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "iAMv1"

def fetch_contributions():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN is not set. Cannot fetch live contribution data.")
        sys.exit(1)
        
    query = """
    query($userName:String!) {
      user(login: $userName){
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    variables = {"userName": GITHUB_USER}
    
    try:
        response = requests.post(
            'https://api.github.com/graphql', 
            json={'query': query, 'variables': variables}, 
            headers=headers
        )
        response.raise_for_status()
        payload = response.json()
        if 'errors' in payload:
            print(f"Error: GitHub GraphQL returned errors: {payload['errors']}")
            sys.exit(1)

        # Flatten the weeks into a single list of days tracking exact grid coordinates
        weeks = payload['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
        days = []
        for week_idx, week in enumerate(weeks):
            for day in week['contributionDays']:
                days.append({
                    'date': day['date'],
                    'count': day['contributionCount'],
                    'weekday': day.get('weekday', 0),
                    'week_idx': week_idx
                })
        return days
    except requests.RequestException as e:
        print(f"Error: GitHub API network request failed: {e}")
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"Error: Unexpected GitHub API response structure: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching contributions: {e}")
        sys.exit(1)

def generate_cricket_svg():
    WIDTH = 800
    HEIGHT = 200
    
    # Up to 53 weeks * 7 days
    COLS = 53
    ROWS = 7
    CELL_SIZE = 12
    CELL_GAP = 3
    
    # Calculate offset to center the grid
    GRID_W = COLS * (CELL_SIZE + CELL_GAP)
    GRID_H = ROWS * (CELL_SIZE + CELL_GAP)
    OFFSET_X = (WIDTH - GRID_W) / 2
    OFFSET_Y = (HEIGHT - GRID_H) / 2 + 10 # slightly lower
    
    # Fetch real data
    contrib_data = fetch_contributions()
    
    # We need to map up to 53 weeks. Let's process exact real data
    days = []
    
    for d in contrib_data:
        commits = d['count']
        
        if commits >= 15: css_class = "cricket-level-4"
        elif commits >= 8: css_class = "cricket-level-3"
        elif commits >= 3: css_class = "cricket-level-2"
        elif commits >= 1: css_class = "cricket-level-1"
        else: css_class = "cricket-level-0"
            
        x = OFFSET_X + d['week_idx'] * (CELL_SIZE + CELL_GAP)
        y = OFFSET_Y + d['weekday'] * (CELL_SIZE + CELL_GAP)
        
        days.append({'x': x, 'y': y, 'class': css_class, 'commits': commits, 'date': d['date']})

    # Pick the top N days with the highest commits strictly (no random!)
    valid_days = [d for d in days if d['commits'] > 0]
    top_days = sorted(valid_days, key=lambda d: d['commits'], reverse=True)[:8]

    # Sort them by x-coordinate (time) so the animation flows left-to-right
    top_days = sorted(top_days, key=lambda d: d['x'])
    
    highlights = []
    for i, d in enumerate(top_days):
        commits = d['commits']
        if commits >= 20: score = "6"
        elif commits >= 12: score = "4"
        elif commits >= 6: score = "2"
        elif commits >= 3: score = "1"
        else: score = "W"
        
        highlights.append({
            'x': d['x'] + CELL_SIZE/2, 
            'y': d['y'] + CELL_SIZE/2, 
            'delay': i * 2.0, # 2.0 seconds between each chronological hit
            'score': score
        })

    # Render Base Grid
    grid_svg = ""
    for d in days:
        grid_svg += f'<rect x="{d["x"]}" y="{d["y"]}" width="{CELL_SIZE}" height="{CELL_SIZE}" rx="2" class="{d["class"]}" />\n'

    # Render Animations
    anim_css = ""
    anim_elements = ""
    
    # Batsman pos (left of grid)
    START_X = OFFSET_X - 40
    START_Y = OFFSET_Y + GRID_H/2
    
    for i, h in enumerate(highlights):
        anim_name = f"cricket-hit{i}"
        pop_name = f"cricket-pop{i}"
        delay = h['delay']
        
        # Calculate a Bezier curve control point for the arc
        mid_x = (START_X + h['x']) / 2
        mid_y = min(START_Y, h['y']) - 60 # Arc goes UP
        
        # KEYFRAMES for BALL
        anim_css += f"""
        @keyframes {anim_name} {{
            0%, {delay/16 * 100}% {{ offset-distance: 0%; opacity: 0; }}
            {(delay+0.1)/16 * 100}% {{ opacity: 1; }}
            {(delay+1.5)/16 * 100}% {{ offset-distance: 100%; opacity: 1; }}
            {(delay+1.6)/16 * 100}%, 100% {{ offset-distance: 100%; opacity: 0; }}
        }}
        """
        
        # KEYFRAMES for POPUP TEXT
        anim_css += f"""
        @keyframes {pop_name} {{
            0%, {(delay+1.4)/16 * 100}% {{ transform: translate(0,0) scale(0.5); opacity: 0; }}
            {(delay+1.5)/16 * 100}% {{ transform: translate(0,-10px) scale(1.5); opacity: 1; }}
            {(delay+2.5)/16 * 100}% {{ transform: translate(0,-30px) scale(1); opacity: 1; }}
            {(delay+3.0)/16 * 100}%, 100% {{ transform: translate(0,-40px) scale(1); opacity: 0; }}
        }}
        """
        
        # The invisible path the ball follows
        path_id = f"cricket-path{i}"
        anim_elements += f'<path id="{path_id}" d="M {START_X} {START_Y} Q {mid_x} {mid_y} {h["x"]} {h["y"]}" fill="none" />\n'
        
        # The Ball
        anim_elements += f'<circle r="4" class="cricket-ball" style="offset-path: url(#{path_id}); animation: {anim_name} 16s linear infinite;" />\n'        
        
        # The Popup Text (Always Accent / Red in this theme to stick to 3-colors, or Contrast for numbers and Accent for W)
        text_class = "cricket-popup-accent" if h['score'] == 'W' else "cricket-popup-contrast"
        
        anim_elements += f"""
        <g style="animation: {pop_name} 16s ease-out infinite; transform-origin: {h['x']}px {h['y']}px;">
            <text x="{h['x']}" y="{h['y']}" class="cricket-popup {text_class}">{h['score']}</text>
        </g>
        """

    svg = f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@900&amp;display=swap');
      
      :root {{
        --bg-color: #0f172a;
        --fg-color: #f8fafc;
        --ac-color: #38bdf8;
      }}
      
      @media (prefers-color-scheme: light) {{
        :root {{
          --bg-color: #ffffff;
          --fg-color: #0f172a;
          --ac-color: #38bdf8;
        }}
      }}
      
      .cricket-bg {{ fill: var(--bg-color); }}
      .cricket-title {{ font-family: 'Outfit', sans-serif; font-size: 14px; fill: var(--fg-color); opacity: 0.6; font-weight: bold; letter-spacing: 2px; }}
      
      /* 3-Color Logic: Variations of Contrast (White) on Base (Navy) */
      .cricket-level-1 {{ fill: var(--fg-color); opacity: 0.05; }}
      .cricket-level-2 {{ fill: var(--fg-color); opacity: 0.3; }}
      .cricket-level-3 {{ fill: var(--fg-color); opacity: 0.6; }}
      .cricket-level-4 {{ fill: var(--fg-color); opacity: 1.0; }}
      
      .cricket-ball {{ fill: var(--ac-color); filter: drop-shadow(0 0 4px var(--ac-color)); }}
      .cricket-popup {{ font-family: 'Outfit', sans-serif; font-size: 24px; font-weight: 900; text-anchor: middle; }}
      
      .cricket-popup-contrast {{ fill: var(--fg-color); filter: drop-shadow(0 0 8px rgba(255,255,255,0.2)); }}
      .cricket-popup-accent {{ fill: var(--ac-color); filter: drop-shadow(0 0 8px var(--ac-color)); }}
      
      /* The Batsman Silhouette */
      .cricket-batsman {{ fill: var(--fg-color); opacity: 0.5; }}
      .cricket-bat {{ fill: var(--ac-color); }}
      
      {anim_css}
    </style>
  </defs>

  <!-- Background -->
  <rect class="cricket-bg" width="{WIDTH}" height="{HEIGHT}" />
  <text x="20" y="30" class="cricket-title">CRICKET CONTRIBUTION GRAPH // LAST 365 DAYS</text>

  <!-- Grid -->
  {grid_svg}
  
  <!-- Batsman minimal pixel art / silhouette -->
  <g transform="translate({START_X - 15}, {START_Y - 20})" class="cricket-batsman">
    <rect x="10" y="0" width="10" height="10" rx="5" /> <!-- Head -->
    <rect x="5" y="12" width="20" height="20" rx="3" /> <!-- Torso -->
    <rect x="5" y="34" width="8" height="15" rx="3" /> <!-- Leg -->
    <rect x="17" y="34" width="8" height="15" rx="3" /> <!-- Leg -->
    <!-- Bat -->
    <rect x="22" y="10" width="5" height="25" class="cricket-bat" transform="rotate(-30 22 10)" /> 
  </g>

  <!-- Animations -->
  {anim_elements}

</svg>"""

    os.makedirs('assets', exist_ok=True)
    with open('assets/cricket_graph.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated 3-Color Cricket Contribution Graph SVG.")

if __name__ == "__main__":
    generate_cricket_svg()
