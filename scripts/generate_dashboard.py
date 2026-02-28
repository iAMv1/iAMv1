import os
import math

def generate_radar_svg():
    # Mock data for Tech Radar
    skills = [
        {"name": "PYTHON", "value": 0.95},
        {"name": "REACT/3D", "value": 0.85},
        {"name": "AI/Agents", "value": 0.90},
        {"name": "DEVOPS", "value": 0.60},
        {"name": "CSS/VIBES", "value": 0.98},
        {"name": "RUST", "value": 0.20}
    ]
    
    WIDTH = 400
    HEIGHT = 250
    CX = 200
    CY = 125
    MAX_RADIUS = 80
    
    # Generate Polygon Points
    points = []
    labels = []
    axes = []
    
    num_skills = len(skills)
    angle_step = (2 * math.pi) / num_skills
    
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
        
        # Label placement (push outward)
        lx = CX + (MAX_RADIUS + 25) * math.cos(angle)
        ly = CY + (MAX_RADIUS + 25) * math.sin(angle)
        
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
      @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&amp;display=swap');
      
      :root {{
        --bg-color: #0b132b;
        --fg-color: #ffffff;
        --ac-color: #ef233c;
      }}
      
      @media (prefers-color-scheme: light) {{
        :root {{
          --bg-color: #f8fafc;
          --fg-color: #0f172a;
          --ac-color: #ef233c;
        }}
      }}
      
      .st-bg {{ fill: transparent; }}
      .st-stroke {{ stroke: var(--fg-color); fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
      .st-poly {{ stroke: var(--ac-color); fill: var(--ac-color); fill-opacity: 0.15; stroke-width: 2; stroke-linejoin: round; }}
      .st-fill {{ fill: var(--fg-color); }}
      .st-accent {{ fill: var(--ac-color); }}
      
      .st-text {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 14px; font-weight: 700; }}
      .st-text-small {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
      .st-dim {{ stroke-opacity: 0.3; }}
      
      @keyframes radar-pulse {{
        0% {{ transform: scale(0.95); opacity: 0.8; }}
        50% {{ transform: scale(1.05); opacity: 1; }}
        100% {{ transform: scale(0.95); opacity: 0.8; }}
      }}
      .st-animate-poly {{ transform-origin: {CX}px {CY}px; animation: radar-pulse 4s ease-in-out infinite; }}
    </style>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" class="st-bg" />
  
  <!-- Outer Box -->
  <rect x="10" y="10" width="380" height="230" class="st-stroke" rx="10" />
  
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
