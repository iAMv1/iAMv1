import os
import re
import sys

# Playlist featuring downloaded tracks from legendary Hindi/Urdu artists.
# Place the actual .mp3 files into the `assets/audio/` folder.
SONGS = [
    {"title": "Lag Ja Gale - Lata Mangeshkar", "url": "./assets/audio/lag_ja_gale.mp3"},
    {"title": "Pal Pal Dil Ke Paas - Kishore Kumar", "url": "./assets/audio/pal_pal_dil_ke_paas.mp3"},
    {"title": "Tere Bin Nahin Lagda - Nusrat Fateh Ali Khan", "url": "./assets/audio/tere_bin_nahin_lagda.mp3"},
    {"title": "Ek Pyar Ka Nagma Hai - Lata Mangeshkar", "url": "./assets/audio/ek_pyar_ka_nagma.mp3"},
    {"title": "Mere Sapno Ki Rani - Kishore Kumar", "url": "./assets/audio/mere_sapno_ki_rani.mp3"},
    {"title": "Ye Jo Halka Halka Suroor - Nusrat Fateh Ali Khan", "url": "./assets/audio/halka_halka_suroor.mp3"},
    {"title": "Ajeeb Dastan Hai Yeh - Lata Mangeshkar", "url": "./assets/audio/ajeeb_dastan.mp3"},
    {"title": "O Mere Dil Ke Chain - Kishore Kumar", "url": "./assets/audio/o_mere_dil_ke_chain.mp3"},
    {"title": "Afreen Afreen - Nusrat Fateh Ali Khan", "url": "./assets/audio/afreen_afreen.mp3"},
    {"title": "Tujhse Naraz Nahin Zindagi - Lata Mangeshkar", "url": "./assets/audio/tujhse_naraz.mp3"},
]

README_PATH = "README.md"

def get_current_song_index(readme_content):
    # Find the current song URL in the README
    match = re.search(r'<!-- CASSETTE_LINK_START -->\s*<a href="(.*?)">', readme_content)
    if match:
        current_url = match.group(1)
        for i, song in enumerate(SONGS):
            if song["url"] == current_url:
                return i
    return 0 # Default to 0 if not found

def update_readme(new_index):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_song = SONGS[new_index]
    
    # Replace the audio link
    new_link_html = f'<!-- CASSETTE_LINK_START -->\n  <a href="{new_song["url"]}">'
    content = re.sub(r'<!-- CASSETTE_LINK_START -->\s*<a href=".*?">', new_link_html, content)
    
    # Optional: Update a visible title or now playing text if it exists
    content = re.sub(r'<!-- NOW_PLAYING_TITLE_START -->.*?<!-- NOW_PLAYING_TITLE_END -->',
                     f'<!-- NOW_PLAYING_TITLE_START -->Now Playing: {new_song["title"]}<!-- NOW_PLAYING_TITLE_END -->',
                     content, flags=re.DOTALL)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Updated README to play: {new_song['title']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_audio.py [next|prev|setup]")
        sys.exit(1)

    action = sys.argv[1].lower()
    
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme_content = f.read()
        
    current_index = get_current_song_index(readme_content)
    
    if action == "next":
        new_index = (current_index + 1) % len(SONGS)
    elif action == "prev":
        new_index = (current_index - 1) % len(SONGS)
    elif action == "setup":
        new_index = 0
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
        
    update_readme(new_index)
