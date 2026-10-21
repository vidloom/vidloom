import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CORE_DIR = BASE_DIR / "core"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = OUTPUT_DIR / "temp"
FINAL_DIR = OUTPUT_DIR / "final"
BACKGROUNDS_DIR = ASSETS_DIR / "backgrounds"
FONTS_DIR = ASSETS_DIR / "fonts"
AUDIO_DIR = ASSETS_DIR / "audio"
MUSIC_DIR = AUDIO_DIR / "music"
SFX_DIR = AUDIO_DIR / "sfx"

# Ensure runtime directories exist
for folder in [TEMP_DIR, FINAL_DIR, BACKGROUNDS_DIR, FONTS_DIR, AUDIO_DIR, MUSIC_DIR, SFX_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# API Keys & Defaults
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en-US-BrianMultilingualNeural")
DEFAULT_SUBREDDIT = os.getenv("DEFAULT_SUBREDDIT", "AskReddit")

# Video Rendering Configuration
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# Subtitle Styling Configuration (ASS)
SUBTITLE_FONT = "Arial Black"
SUBTITLE_FONT_SIZE = 60
SUBTITLE_PRIMARY_COLOR = "&H00FFFFFF"   # Bright White (AABBGGRR)
SUBTITLE_HIGHLIGHT_COLOR = "&H0000FFFF" # Vibrant Neon Yellow / Gold
SUBTITLE_OUTLINE_COLOR = "&H00000000"   # Pitch Black Outline
SUBTITLE_OUTLINE_WIDTH = 5
SUBTITLE_SHADOW_DEPTH = 3
SUBTITLE_MARGIN_V = 680                 # Optimal safe zone for YouTube Shorts UI
