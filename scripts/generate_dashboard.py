import os
import sys
import math
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_USER = "iAMv1"

def fetch_top_languages():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN is not set. Cannot fetch live language data.")
        sys.exit(1)

    query = """
    query($userName:String!) {
      user(login: $userName){
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes {
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                }
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

        repos = payload['data']['user']['repositories']['nodes']
        lang_stats = {}
        
        for repo in repos:
            for edge in repo['languages']['edges']:
                lang_name = edge['node']['name'].upper()
                # Group common ones if needed
                if lang_name in ["HTML", "CSS"]: lang_name = "UI/VIBES"
                if lang_name == "JUPYTER NOTEBOOK": lang_name = "PYTHON (AI)"
                
                lang_stats[lang_name] = lang_stats.get(lang_name, 0) + edge['size']

        # Sort and take top 6
        sorted_langs = sorted(lang_stats.items(), key=lambda x: x[1], reverse=True)[:6]
        
        # Normalize to max 1.0 (or max value representing 1.0)
        max_size = max([l[1] for l in sorted_langs]) if sorted_langs else 1
        
        skills = []
        for name, size in sorted_langs:
            val = max(0.2, (size / max_size) * 0.95)
            skills.append({"name": name[:10], "value": val})
            
        # Pad to exactly 6 for the hexagon shape
        while len(skills) < 6:
            skills.append({"name": "---", "value": 0.2})
            
        return skills

    except requests.RequestException as e:
        print(f"Error: GitHub API network request failed: {e}")
        sys.exit(1)
    except (KeyError, TypeError) as e:
        print(f"Error: Unexpected GitHub API response structure: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching languages: {e}")
        sys.exit(1)

def generate_radar_svg():
    # Fetch real data
    skills = fetch_top_languages()
    
    WIDTH = 420
    HEIGHT = 420
    CX = 210
    CY = 210
    MAX_RADIUS = 110
    
    # Generate Polygon Points
    points = []
    labels = []
    axes = []
    
    num_skills = len(skills)
    angle_step = (2 * math.pi) / max(1, num_skills)
    
    for i, skill in enumerate(skills):
        angle = i * angle_step - (math.pi / 2) # Start at top
        
        # Max axis line
        ax_x = CX + MAX_RADIUS * math.cos(angle)
        ax_y = CY + MAX_RADIUS * math.sin(angle)
        axes.append(f'<line x1="{CX}" y1="{CY}" x2="{ax_x}" y2="{ax_y}" class="st-stroke st-dim" />')
        
        # Skill data point
        px = CX + (MAX_RADIUS * skill["value"]) * math.cos(angle)
        py = CY + (MAX_RADIUS * skill["value"]) * math.sin(angle)
        points.append(f"{px},{py}")
        
        # Label placement (push outward more to prevent overlap)
        # Using 45 instead of 25 pushes them significantly clear of the grid lines
        lx = CX + (MAX_RADIUS + 40) * math.cos(angle)
        ly = CY + (MAX_RADIUS + 40) * math.sin(angle)
        
        # Align text based on quadrant
        anchor = "middle"
        if math.cos(angle) > 0.1: anchor = "start"
        elif math.cos(angle) < -0.1: anchor = "end"
        
        labels.append(f'<text x="{lx}" y="{ly + 4}" text-anchor="{anchor}" class="st-text-small">{skill["name"]}</text>')

    polygon_str = " ".join(points)
    
    # SVG string
    svg = f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700;900&amp;display=swap');
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');

      .st-bg {{ fill: #0f172a; }}
      .st-stroke {{ stroke: #f8fafc; fill: none; stroke-width: 2; }}
      .st-border {{ fill: none; stroke: #334155; stroke-width: 1.5; }}
      .st-poly {{ stroke: #38bdf8; fill: #38bdf8; fill-opacity: 0.3; stroke-width: 2; stroke-linejoin: round; }}
      .st-fill {{ fill: #f8fafc; }}
      .st-accent {{ fill: #38bdf8; }}

      .st-text {{ font-family: 'Outfit', sans-serif; fill: #f8fafc; font-size: 16px; font-weight: 700; letter-spacing: 1px;}}
      .st-text-small {{ font-family: 'Fira Code', monospace; fill: #f8fafc; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
      .st-dim {{ stroke-opacity: 0.4; }}

      @keyframes radar-pulse {{
        0% {{ transform: scale(0.95); opacity: 0.8; }}
        50% {{ transform: scale(1.05); opacity: 1; }}
        100% {{ transform: scale(0.95); opacity: 0.8; }}
      }}
      .st-animate-poly {{ transform-origin: {CX}px {CY}px; animation: radar-pulse 4s ease-in-out infinite; }}
    </style>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="16" class="st-bg" />
  <rect x="1" y="1" width="{WIDTH-2}" height="{HEIGHT-2}" rx="16" class="st-border" />
  
  <!-- Title -->
  <text x="20" y="35" class="st-text">SYSTEM.CAPABILITIES()</text>
  <line x1="20" y1="45" x2="380" y2="45" class="st-stroke" />

  <!-- Radar Grid Background Concentric Circles -->
  <circle cx="{CX}" cy="{CY}" r="20" class="st-stroke st-dim" stroke-dasharray="2 4" />
  <circle cx="{CX}" cy="{CY}" r="50" class="st-stroke st-dim" stroke-dasharray="2 4" />
  <circle cx="{CX}" cy="{CY}" r="80" class="st-stroke st-dim" />

  <!-- Radar Axes -->
  {"".join(axes)}

  <!-- Data Polygon -->
  <polygon points="{polygon_str}" class="st-poly st-animate-poly" />
  
  <!-- Vertices Dots -->
  """
    
    for pt in points:
        coords = pt.split(',')
        svg += f'<circle cx="{coords[0]}" cy="{coords[1]}" r="3" class="st-accent st-animate-poly" />\n  '

    svg += f"""
  <!-- Labels -->
  {"".join(labels)}

  <!-- Crosshair Accents -->
  <line x1="10" y1="125" x2="30" y2="125" class="st-stroke" />
  <line x1="370" y1="125" x2="390" y2="125" class="st-stroke" />
  <line x1="200" y1="10" x2="200" y2="30" class="st-stroke" />
  <line x1="200" y1="220" x2="200" y2="240" class="st-stroke" />

</svg>"""

    os.makedirs('assets', exist_ok=True)
    with open('assets/contribution_dashboard.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated 3-Color Artistic Radar SVG.")

if __name__ == "__main__":
    generate_radar_svg()
