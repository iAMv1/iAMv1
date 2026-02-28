import json
import os
from datetime import datetime

# Load tasks
try:
    with open('tasks.json', 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {"status": "NO DATA", "missions": []}

missions = data.get('missions', [])
status = "System Nominal"

# Calculate lines
total_lines = 4 + (len(missions) * 4) + 1
line_height = 24
top_padding = 60
HEIGHT = top_padding + (total_lines * line_height) + 20
WIDTH = 700

# CSS Colors based on strict 3-color theme
svg = f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&amp;display=swap');
      
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
      
      .vscode-bg {{ fill: var(--bg-color); rx: 10px; stroke: #27272a; stroke-width: 1px; }}
      .vscode-title {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px; fill: var(--fg-color); opacity: 0.6; text-anchor: middle; }}
      .vscode-text {{ font-family: 'Fira Code', monospace; font-size: 15px; fill: var(--fg-color); }}
      
      .mac-btn {{ fill: var(--fg-color); opacity: 0.3; }}
      .line-num {{ fill: var(--fg-color); opacity: 0.3; font-size: 14px; text-anchor: end; }}
      
      .t-key {{ fill: var(--fg-color); }}
      .t-str {{ fill: var(--ac-color); }}
      .t-comment {{ fill: var(--fg-color); opacity: 0.4; }}
      .t-punct {{ fill: var(--fg-color); opacity: 0.7; }}
      
      .bar-fill {{ fill: var(--ac-color); }}
      .bar-empty {{ fill: var(--fg-color); opacity: 0.2; }}
    </style>
  </defs>

  <rect class="vscode-bg" width="{WIDTH}" height="{HEIGHT}" />
  
  <!-- Mac Window Controls -->
  <circle cx="20" cy="20" r="6" class="mac-btn" />
  <circle cx="40" cy="20" r="6" class="mac-btn" />
  <circle cx="60" cy="20" r="6" class="mac-btn" />
  
  <text x="{WIDTH/2}" y="24" class="vscode-title">mission_control.yaml - Visual Studio Code</text>
  
  <rect x="0" y="40" width="{WIDTH}" height="1" fill="var(--fg-color)" opacity="0.1" />
"""

current_line = 1
y_pos = top_padding + 20

def add_line(content_svg):
    global current_line, y_pos, svg
    # Line number
    svg += f'  <text x="40" y="{y_pos}" class="vscode-text line-num">{current_line}</text>\n'
    # Content
    svg += f'  <text x="60" y="{y_pos}" class="vscode-text">{content_svg}</text>\n'
    y_pos += line_height
    current_line += 1

# Render YAML in 3-Color Theme
time_str = datetime.now().strftime('%Y-%m-%d %H:%M')

add_line(f'<tspan class="t-key">status</tspan> <tspan class="t-punct">:</tspan> <tspan class="t-str">\'{status}\'</tspan>')
add_line(f'<tspan class="t-key">last_uplink</tspan> <tspan class="t-punct">:</tspan> <tspan class="t-str">\'{time_str}\'</tspan>')
add_line('')
add_line(f'<tspan class="t-key">current_missions</tspan> <tspan class="t-punct">:</tspan>')

for i, m in enumerate(missions):
    name = m.get('title', 'Unknown Mission')
    prog = m.get('progress', 0)
    
    # 20 blocks
    bars = int(prog / 5)
    bar_str = "█" * bars
    empty_str = "░" * (20 - bars)
    
    add_line(f'<tspan class="t-punct">-   </tspan><tspan class="t-key">name</tspan><tspan class="t-punct">:</tspan> <tspan class="t-str">\'- {name}\'</tspan>')
    add_line(f'<tspan class="t-key" dx="36">progress</tspan> <tspan class="t-punct">:</tspan><tspan class="t-str">{prog}%</tspan>')
    
    bar_svg = f'<tspan class="t-key" dx="36">status_bar</tspan> <tspan class="t-punct">:\'</tspan><tspan class="bar-fill">{bar_str}</tspan><tspan class="bar-empty">{empty_str}</tspan><tspan class="t-punct">\'</tspan>   <tspan class="t-comment"># {prog}%</tspan>'
    add_line(bar_svg)
    if i < len(missions) - 1:
        add_line('')

add_line('')

svg += "</svg>"

os.makedirs('assets', exist_ok=True)
with open('assets/crt_terminal_missions.svg', 'w', encoding='utf-8') as f:
    f.write(svg)

print("Generated 3-Color VS Code Mission Control SVG.")
