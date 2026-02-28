import os
import random

def generate_cricket_svg():
    WIDTH = 800
    HEIGHT = 200
    
    # 52 weeks x 7 days
    COLS = 52
    ROWS = 7
    CELL_SIZE = 12
    CELL_GAP = 3
    
    # Calculate offset to center the grid
    GRID_W = COLS * (CELL_SIZE + CELL_GAP)
    GRID_H = ROWS * (CELL_SIZE + CELL_GAP)
    OFFSET_X = (WIDTH - GRID_W) / 2
    OFFSET_Y = (HEIGHT - GRID_H) / 2 + 10 # slightly lower
    
    # Generate mock contribution data
    days = []
    highlights = [] # days with hits
    
    for c in range(COLS):
        for r in range(ROWS):
            val = random.random()
            if val > 0.95:
                commits = random.randint(6, 12)
                css_class = "cricket-level-4"
            elif val > 0.85:
                commits = random.randint(3, 5)
                css_class = "cricket-level-3"
            elif val > 0.6:
                commits = random.randint(1, 2)
                css_class = "cricket-level-2"
            else:
                commits = 0
                css_class = "cricket-level-1"
                
            x = OFFSET_X + c * (CELL_SIZE + CELL_GAP)
            y = OFFSET_Y + r * (CELL_SIZE + CELL_GAP)
            
            days.append({'x': x, 'y': y, 'class': css_class, 'commits': commits})
            
            # Select random moments for the highlight animations
            if random.random() > 0.96 and len(highlights) < 8:
                if commits >= 6: score = "6"
                elif commits >= 3: score = "4"
                elif commits == 2: score = "2"
                elif commits == 1: score = "1"
                else: score = "W"
                
                highlights.append({
                    'x': x + CELL_SIZE/2, 
                    'y': y + CELL_SIZE/2, 
                    'delay': len(highlights) * 2.5, # 2.5 seconds between hits
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
