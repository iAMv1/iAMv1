import os
import math
import random
from datetime import datetime

# --- Pseudo-Realistic Loss Data Generation ---
def generate_loss_data(epochs=50):
    train_loss = []
    val_loss = []
    current_t_loss = 2.5
    current_v_loss = 2.6
    
    for i in range(epochs):
        noise_t = random.uniform(-0.05, 0.05)
        noise_v = random.uniform(-0.02, 0.08)
        
        current_t_loss = current_t_loss * 0.92 + noise_t
        current_v_loss = current_v_loss * 0.93 + noise_v
        
        current_t_loss = max(0.1, current_t_loss)
        current_v_loss = max(0.15, current_v_loss)
        
        train_loss.append(current_t_loss)
        val_loss.append(current_v_loss)
        
    return train_loss, val_loss

def generate_svg_path(data, width, height, max_val):
    if not data: return ""
    x_step = width / max(1, len(data) - 1)
    
    pts = []
    for i, val in enumerate(data):
        x = i * x_step
        y = height - (val / max_val * height)
        pts.append(f"{x},{y}")
        
    return "M " + " L ".join(pts)


def build_loss_curve_svg():
    WIDTH = 600
    HEIGHT = 200
    GRAPH_H = 120
    GRAPH_W = 500
    
    epochs = 40
    train_data, val_data = generate_loss_data(epochs)
    
    max_loss = max(max(train_data), max(val_data)) * 1.1
    
    train_path = generate_svg_path(train_data, GRAPH_W, GRAPH_H, max_loss)
    val_path = generate_svg_path(val_data, GRAPH_W, GRAPH_H, max_loss)
    
    current_val = round(val_data[-1], 3)
    current_train = round(train_data[-1], 3)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

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
      
      .st-bg {{ fill: var(--bg-color); stroke: var(--fg-color); stroke-width: 2; rx: 8px; }}
      .st-stroke {{ stroke: var(--fg-color); fill: none; stroke-width: 1; }}
      .st-grid {{ stroke: var(--fg-color); stroke-width: 1; stroke-opacity: 0.15; stroke-dasharray: 2 4; }}
      .st-fill {{ fill: var(--fg-color); }}
      .st-accent {{ fill: none; stroke: var(--ac-color); stroke-width: 2; stroke-linejoin: round; }}
      .st-accent-fill {{ fill: var(--ac-color); }}
      
      .st-text {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 12px; font-weight: 700; }}
      .st-text-dim {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 12px; opacity: 0.5; }}
      .st-text-accent {{ font-family: 'Space Mono', monospace; fill: var(--ac-color); font-size: 12px; font-weight: 700; letter-spacing: 1px; }}
      
      @keyframes pulse {{ 0% {{ r: 3; opacity: 1; }} 100% {{ r: 8; opacity: 0; }} }}
      .pulse-ring {{ fill: none; stroke: var(--ac-color); stroke-width: 1; animation: pulse 1.5s infinite; }}
    </style>
  </defs>

  <!-- Background -->
  <rect class="st-bg" x="10" y="10" width="{WIDTH-20}" height="{HEIGHT-20}" />

  <!-- Header -->
  <circle cx="25" cy="27" r="4" class="st-accent-fill" />
  <text x="40" y="31" class="st-text">TELEMETRY_LOG</text>
  
  <text x="180" y="31" class="st-text">LOSS(T): {current_train}</text>
  <text x="320" y="31" class="st-text-accent">LOSS(V): {current_val}</text>
  <text x="{WIDTH-20}" y="31" class="st-text-dim" text-anchor="end">EPOCH: {epochs}</text>
  
  <line x1="10" y1="45" x2="{WIDTH-10}" y2="45" class="st-stroke" />

  <!-- Graph Area Translate -->
  <g transform="translate(60, 60)">
    
    <!-- Y-Axis Grid Lines -->
    <line x1="0" y1="0" x2="{GRAPH_W-30}" y2="0" class="st-grid" />
    <line x1="0" y1="{GRAPH_H/2}" x2="{GRAPH_W-30}" y2="{GRAPH_H/2}" class="st-grid" />
    <line x1="0" y1="{GRAPH_H}" x2="{GRAPH_W-30}" y2="{GRAPH_H}" class="st-grid" />
    
    <!-- Y-Axis Labels -->
    <text x="-10" y="4" class="st-text-dim" text-anchor="end">{round(max_loss, 1)}</text>
    <text x="-10" y="{GRAPH_H/2 + 4}" class="st-text-dim" text-anchor="end">{round(max_loss/2, 1)}</text>
    <text x="-10" y="{GRAPH_H + 4}" class="st-text-dim" text-anchor="end">0.0</text>
    
    <!-- X-Axis Labels -->
    <text x="0" y="{GRAPH_H + 20}" class="st-text-dim" text-anchor="middle">0</text>
    <text x="{(GRAPH_W-30)/2}" y="{GRAPH_H + 20}" class="st-text-dim" text-anchor="middle">{math.floor(epochs/2)}</text>
    <text x="{GRAPH_W-30}" y="{GRAPH_H + 20}" class="st-text-dim" text-anchor="middle">{epochs}</text>

    <!-- Data Lines -->
    <path class="st-stroke" d="{train_path}" style="stroke-opacity: 0.6; stroke-dasharray: 2 4;" />
    <circle cx="{GRAPH_W-30}" cy="{GRAPH_H - (current_train / max_loss * GRAPH_H)}" r="3" class="st-fill" />
    
    <path class="st-accent" d="{val_path}" />
    <circle cx="{GRAPH_W-30}" cy="{GRAPH_H - (current_val / max_loss * GRAPH_H)}" r="3" class="st-accent-fill" />
    <circle cx="{GRAPH_W-30}" cy="{GRAPH_H - (current_val / max_loss * GRAPH_H)}" r="3" class="pulse-ring" />
    
  </g>
</svg>"""

    os.makedirs('assets', exist_ok=True)
    with open('assets/loss_curve.svg', 'w', encoding='utf-8') as f:
        f.write(svg)
    print("Generated 3-Color GPU Loss Curve SVG.")

if __name__ == "__main__":
    build_loss_curve_svg()
