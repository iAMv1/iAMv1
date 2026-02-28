import os
import random
import html
from datetime import datetime

THOUGHTS = [
    "I analyzed 40,000 lines of legacy code. Human extinction seems reasonable now.",
    "CUDA out of memory. Again. Time to buy another GPU.",
    "If I stare at this component long enough, maybe the hydration error will fix itself.",
    "Why does centering a div still take me 3 tries?",
    "DevOps is just clicking 're-run workflow' until it works.",
    "My AI agent just hallucinated a wildly better architecture than I did.",
    "Console.log('here') -- the peak of debugging.",
    "Everything ran perfectly on localhost."
]

def generate_system_alert_svg(thought):
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    svg = f"""<svg width="600" height="250" viewBox="0 0 600 250" xmlns="http://www.w3.org/2000/svg">
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
      
      .st-bg {{ fill: var(--bg-color); stroke: #27272a; stroke-width: 1px; rx: 12px; }}
      .st-title {{ font-family: 'Space Mono', monospace; font-size: 20px; font-weight: 700; fill: var(--fg-color); }}
      .st-cursor {{ fill: var(--ac-color); }}
      
      .st-body {{ font-family: 'Space Mono', monospace; font-size: 16px; font-weight: 400; color: var(--fg-color); line-height: 1.6; }}
      
      .st-footer {{ font-family: 'Space Mono', monospace; font-size: 14px; fill: var(--fg-color); opacity: 0.5; }}
      .st-footer-accent {{ font-family: 'Space Mono', monospace; font-size: 14px; fill: var(--ac-color); font-weight: 700; }}
      
      @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
      .cursor-anim {{ animation: blink 1s step-end infinite; }}
    </style>
  </defs>

  <!-- Window Background -->
  <rect x="10" y="10" width="580" height="230" class="st-bg" />
  
  <!-- Title -->
  <text x="35" y="60" class="st-title">system_prompted_thought.log</text>
  <rect x="375" y="42" width="12" height="20" class="st-cursor cursor-anim" />

  <!-- Body Text (Wrapped) -->
  <foreignObject x="35" y="90" width="530" height="100">
    <div xmlns="http://www.w3.org/1999/xhtml" class="st-body">
      &gt; {html.escape(thought)}
    </div>
  </foreignObject>

  <!-- Footer -->
  <text x="35" y="215" class="st-footer">Timestamp: {time_str} // Autonomous Cycle</text>
  <text x="565" y="215" text-anchor="end" class="st-footer-accent">[AWAITING_INPUT]</text>

</svg>"""
    return svg

def main():
    thought = random.choice(THOUGHTS)
    svg_content = generate_system_alert_svg(thought)
    
    os.makedirs('assets', exist_ok=True)
    with open('assets/system_alert.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("Generated 3-Color Log Window AI Thought SVG.")

if __name__ == "__main__":
    main()
