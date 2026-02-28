import os
import requests
import html

LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "demo_mode_if_no_key")
LASTFM_USER = os.environ.get("LASTFM_USER", "your_lastfm_username")

def generate_cassette_svg(song, artist, album, is_playing):
    status_text = "PLAYING" if is_playing else "STOPPED"
    
    # Use CSS animations with transform-origin 0 0. GitHub Camo strips <animateTransform>.
    animation_css = "animation: st-spin 4s linear infinite;" if is_playing else ""

    svg = f"""<svg width="400" height="250" viewBox="0 0 400 250" xmlns="http://www.w3.org/2000/svg">
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
      
      .st-bg {{ fill: var(--bg-color); }}
      .st-stroke {{ stroke: var(--fg-color); fill: none; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
      .st-fill {{ fill: var(--fg-color); }}
      .st-accent {{ fill: var(--ac-color); }}
      .st-accent-stroke {{ stroke: var(--ac-color); fill: none; stroke-width: 8; stroke-linecap: round; }}
      
      .st-text {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 16px; font-weight: 700; }}
      .st-text-small {{ font-family: 'Space Mono', monospace; fill: var(--fg-color); font-size: 12px; font-weight: 400; opacity: 0.7; }}
      .st-text-accent {{ font-family: 'Space Mono', monospace; fill: var(--ac-color); font-size: 12px; font-weight: 700; letter-spacing: 2px; }}
      
      @keyframes st-spin {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
      }}
      .st-spin-anim {{
        {animation_css}
        transform-origin: 0px 0px;
      }}
    </style>
  </defs>

  <!-- Background -->
  <rect width="400" height="250" class="st-bg" />
  
  <!-- Outer Cassette Shell -->
  <rect x="20" y="20" width="360" height="210" class="st-stroke" rx="10" />
  
  <!-- Geometric Tape Bridge -->
  <path d="M 80 230 L 100 180 L 300 180 L 320 230" class="st-stroke" />
  <circle cx="120" cy="205" r="5" class="st-stroke" />
  <circle cx="280" cy="205" r="5" class="st-stroke" />

  <!-- Central Window Line -->
  <line x1="20" y1="125" x2="380" y2="125" class="st-stroke" />

  <!-- Left Reel Geometry (Crosshair Theme) -->
  <g transform="translate(130, 125)">
    <circle cx="0" cy="0" r="35" class="st-stroke" />
    <g class="st-spin-anim">
      <line x1="0" y1="-35" x2="0" y2="35" class="st-stroke" />
      <line x1="-35" y1="0" x2="35" y2="0" class="st-stroke" />
      <circle cx="0" cy="0" r="12" class="st-stroke" fill="var(--bg-color)" />
    </g>
  </g>
  
  <!-- Right Reel Geometry -->
  <g transform="translate(270, 125)">
    <circle cx="0" cy="0" r="35" class="st-stroke" />
    <g class="st-spin-anim">
      <line x1="0" y1="-35" x2="0" y2="35" class="st-stroke" />
      <line x1="-35" y1="0" x2="35" y2="0" class="st-stroke" />
      <circle cx="0" cy="0" r="12" class="st-stroke" fill="var(--bg-color)" />
    </g>
  </g>

  <!-- Red Accent Dot (Top Right) -->
  <circle cx="340" cy="60" r="8" class="st-accent" />
  
  <!-- Red Accent Line (Bottom Right) -->
  <line x1="330" y1="200" x2="360" y2="200" class="st-accent-stroke" />

  <!-- Four Corner Screws -->
  <circle cx="40" cy="40" r="3" class="st-fill" />
  <circle cx="360" cy="40" r="3" class="st-fill" />
  <circle cx="40" cy="210" r="3" class="st-fill" />
  <circle cx="360" cy="210" r="3" class="st-fill" />

  <!-- Typography -->
  <text x="40" y="65" class="st-text">{html.escape(song)}</text>
  <text x="40" y="85" class="st-text-small">{html.escape(artist)}</text>
  
  <text x="360" y="160" text-anchor="end" class="st-text-accent">{status_text}</text>

</svg>"""
    return svg

def main():
    if LASTFM_API_KEY == "demo_mode_if_no_key":
        svg_content = generate_cassette_svg("Memory Allocation", "System Daemon", "EP", True)
    else:
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={LASTFM_USER}&api_key={LASTFM_API_KEY}&format=json&limit=1"
        try:
            response = requests.get(url)
            data = response.json()
            track = data['recenttracks']['track'][0]
            
            song = track['name']
            artist = track['artist']['#text']
            album = track['album']['#text']
            is_playing = '@attr' in track and track['@attr'].get('nowplaying') == 'true'
            
            svg_content = generate_cassette_svg(song, artist, album, is_playing)
        except Exception as e:
            svg_content = generate_cassette_svg("Silence", "Connection Error", str(e), False)

    os.makedirs('assets', exist_ok=True)
    with open('assets/now_playing.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print("Generated 3-Color Artistic Cassette SVG.")

if __name__ == "__main__":
    main()
