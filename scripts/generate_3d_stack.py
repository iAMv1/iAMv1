import math
import os

# --- SVG Constants ---
SVG_WIDTH = 800
SVG_HEIGHT = 200
BLOCK_SIZE = 60      # Clean, reasonable block size
Z_HEIGHT = 25        # Slightly flatter, like sleek keyboard keys

# Isometric projection angles (30 degrees in radians)
ANGLE_30 = math.radians(30)
COS_30 = math.cos(ANGLE_30)
SIN_30 = math.sin(ANGLE_30)

# Colors matching the dark cyan slate theme
BASE_COLOR = "#0f172a"
TOP_COLOR = "#1e293b"
LEFT_COLOR = "#020617"
RIGHT_COLOR = "#0f172a"
ACCENT_GREEN = "#38bdf8"


def iso_to_2d(x, y, z=0):
    """
    Converts 3D isometric grid coordinates (x, y, z) to 2D screen coordinates.
    """
    # Center horizontally and position in the middle vertically
    origin_x = SVG_WIDTH / 2
    origin_y = 100

    # Isometric projection formula
    screen_x = origin_x + (x - y) * COS_30 * BLOCK_SIZE
    screen_y = origin_y + (x + y) * SIN_30 * BLOCK_SIZE - (z * Z_HEIGHT)

    return screen_x, screen_y

def draw_block(grid_x, grid_y, label, accent_color=ACCENT_GREEN):
    """
    Draws a single 3D isometric block at the given grid coordinates.
    """
    
    # Calculate the 8 corners of the 3D block
    # Bottom face
    b_front = iso_to_2d(grid_x + 1, grid_y + 1, 0)
    b_back  = iso_to_2d(grid_x,     grid_y,     0)
    b_left  = iso_to_2d(grid_x,     grid_y + 1, 0)
    b_right = iso_to_2d(grid_x + 1, grid_y,     0)
    
    # Top face
    t_front = iso_to_2d(grid_x + 1, grid_y + 1, 1)
    t_back  = iso_to_2d(grid_x,     grid_y,     1)
    t_left  = iso_to_2d(grid_x,     grid_y + 1, 1)
    t_right = iso_to_2d(grid_x + 1, grid_y,     1)

    svg_elements = []

    # 1. Left Face (Darkest shadow)
    left_points = f"{t_left[0]},{t_left[1]} {t_front[0]},{t_front[1]} {b_front[0]},{b_front[1]} {b_left[0]},{b_left[1]}"
    svg_elements.append(f'<polygon points="{left_points}" fill="{LEFT_COLOR}" stroke="{accent_color}" stroke-width="0.5" />')

    # 2. Right Face (Mid-tone shadow)
    right_points = f"{t_front[0]},{t_front[1]} {t_right[0]},{t_right[1]} {b_right[0]},{b_right[1]} {b_front[0]},{b_front[1]}"
    svg_elements.append(f'<polygon points="{right_points}" fill="{RIGHT_COLOR}" stroke="{accent_color}" stroke-width="0.5" />')

    # Top Face (Base color)
    top_points = f"{t_back[0]},{t_back[1]} {t_right[0]},{t_right[1]} {t_front[0]},{t_front[1]} {t_left[0]},{t_left[1]}"
    svg_elements.append(f'<polygon points="{top_points}" fill="{TOP_COLOR}" stroke="{accent_color}" stroke-width="1.5" />')

    # Label on Top Face using matrix transform to lay it flat
    # Matrix: matrix(cos(30), sin(30), -cos(30), sin(30), tx, ty)
    # This skews and rotates the text to match the isometric top plane perfectly.
    
    # Calculate translation to the exact center of the top face
    center_x = (t_front[0] + t_back[0]) / 2
    center_y = (t_front[1] + t_back[1]) / 2
    
    # The matrix values for a standard isometric top plane (assuming the text itself is drawn horizontally first)
    # The standard isometric transform squishes the text.
    # We use a transform origin at the center to make translation easier.
    
    matrix = f"matrix({COS_30}, {SIN_30}, -{COS_30}, {SIN_30}, {center_x}, {center_y})"
    
    svg_elements.append(f'<g transform="{matrix}">')
    svg_elements.append(f'  <text x="0" y="5" fill="{accent_color}" font-family="monospace" font-size="24" font-weight="900" text-anchor="middle" dominant-baseline="middle" style="text-shadow: 0px 0px 8px {accent_color};" >{label}</text>')
    svg_elements.append(f'</g>')
    
    return "\n".join(svg_elements)

def generate_svg():
    svg_content = [
        f'<svg width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" xmlns="http://www.w3.org/2000/svg">',
        f'<defs>',
        f'  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">',
        f'    <feGaussianBlur stdDeviation="5" result="blur" />',
        f'    <feComposite in="SourceGraphic" in2="blur" operator="over" />',
        f'  </filter>',
        f'  <filter id="drop-shadow" x="-20%" y="-20%" width="140%" height="140%">',
        f'    <feDropShadow dx="0" dy="15" stdDeviation="10" flood-color="#000000" flood-opacity="0.8"/>',
        f'  </filter>',
        '  <style>',
        '    @import url("https://fonts.googleapis.com/css2?family=Fira+Code:wght@700&amp;display=swap");',
        '    text { font-family: "Fira Code", monospace; font-weight: 700; letter-spacing: 2px; }',
        '    .block-group { filter: url(#drop-shadow); }',
        '  </style>',
        f'</defs>',
        f'<rect width="100%" height="100%" fill="{BASE_COLOR}" />',
    ]

    # For a purely horizontal row on screen in isometric projection, 
    # we increase 'x' and decrease 'y' by the exact same amount.
    # This keeps screen_y constant.
    SPACING = 1.3  # Adds a nice gap between the blocks
    
    blocks = [
        {"x": -2 * SPACING, "y":  2 * SPACING, "label": "PYTHON",   "color": "#3776AB"},
        {"x": -1 * SPACING, "y":  1 * SPACING, "label": "REACT",    "color": "#61DAFB"},
        {"x":  0 * SPACING, "y":  0 * SPACING, "label": "TAILWIND", "color": "#0ea5e9"},
        {"x":  1 * SPACING, "y": -1 * SPACING, "label": "FASTAPI",  "color": "#009688"},
        {"x":  2 * SPACING, "y": -2 * SPACING, "label": "AI/LLM",   "color": "#d946ef"},
    ]

    # Sort blocks by depth (x + y). For isometric, it's roughly painter's algorithm.
    blocks = sorted(blocks, key=lambda b: (b["y"], b["x"]))

    for block in blocks:
        svg_content.append(f'<g class="block-group">')
        svg_content.append(draw_block(block["x"], block["y"], block["label"], block["color"]))
        svg_content.append(f'</g>')

    svg_content.append('</svg>')

    os.makedirs('assets', exist_ok=True)
    with open('assets/3d_stack.svg', 'w', encoding='utf-8') as f:
        f.write("\n".join(svg_content))
    print("Generated 3D stack SVG!")

if __name__ == "__main__":
    generate_svg()
