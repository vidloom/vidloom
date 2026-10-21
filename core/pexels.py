import requests
from pathlib import Path
from typing import Optional, List, Dict
from config.settings import PEXELS_API_KEY, BACKGROUNDS_DIR, TEMP_DIR

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"

def search_pexels_videos(query: str, per_page: int = 10) -> List[Dict]:
    """
    Searches vertical videos on Pexels.
    """
    if not PEXELS_API_KEY:
        raise ValueError("PEXELS_API_KEY is not configured in environment or settings.")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": per_page
    }

    response = requests.get(PEXELS_SEARCH_URL, headers=headers, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data.get("videos", [])

def get_best_video_file_url(video: Dict) -> Optional[str]:
    """
    Finds the best portrait MP4 file link (preferring HD 1080x1920 or 720x1280).
    """
    video_files = video.get("video_files", [])
    # Filter for mp4
    mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4"]
    if not mp4_files:
        return None

    # Sort prioritizing portrait resolution close to 1080x1920
    def resolution_score(f):
        w = f.get("width") or 0
        h = f.get("height") or 0
        is_portrait = h > w
        # Prefer HD vertical
        score = (1 if is_portrait else 0) * 10000 + (w * h)
        return score

    mp4_files.sort(key=resolution_score, reverse=True)
    return mp4_files[0].get("link")

import random
import re

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "just", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "tells", "told", "like", "said", "says",
    # Abstract, non-visual filler words that ruin stock search
    "number", "one", "two", "three", "four", "five", "first", "second", "third",
    "fact", "facts", "thing", "things", "everything", "anything", "nothing",
    "matter", "total", "completely", "really", "almost", "actually", "probably",
    "chills", "perish", "stillness", "path", "miles", "hour", "hours", "minute",
    "minutes", "seconds", "way", "ways", "people", "someone", "anyone", "everyone",
    "today", "yesterday", "tomorrow", "week", "last", "next", "ago", "know", "knew"
}

def derive_context_theme(title: str, category: str = "") -> str:
    """
    Extracts the visual subject theme of the video (e.g. 'space', 'ocean', 'office', 'house').
    """
    combined = f"{category} {title}".lower()
    if any(k in combined for k in ["space", "galaxy", "cosmos", "universe", "planet", "stars", "alien"]):
        return "space"
    elif any(k in combined for k in ["ocean", "sea", "underwater", "water", "marine", "shark", "deep"]):
        return "ocean underwater"
    elif any(k in combined for k in ["handbag", "bag", "purse", "tote", "fashion", "luxury", "leather", "outfit", "style", "accessories", "promo"]):
        return "luxury handbag fashion"
    elif any(k in combined for k in ["house", "room", "basement", "door", "attic", "haunted"]):
        return "dark room interior"
    elif any(k in combined for k in ["office", "boss", "work", "presentation", "job", "hr"]):
        return "modern office workplace"
    elif any(k in combined for k in ["car", "road", "trip", "drive", "keys"]):
        return "city street night"
    elif any(k in combined for k in ["psychology", "mind", "brain", "human"]):
        return "human face dramatic"
    return "cinematic aesthetic"

def extract_search_query(sentence: str, context_theme: str = "") -> str:
    """
    Extracts 2-3 high-relevance visual keywords anchored to the video's core topic.
    Guarantees B-roll remains 100% relevant to the video subject.
    """
    words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
    meaningful = [w for w in words if w not in STOPWORDS]
    
    anchor = context_theme.strip()
    
    # Fashion & luxury promo handling
    if any(k in anchor.lower() for k in ["handbag", "fashion", "luxury", "promo"]):
        fashion_hits = [w for w in meaningful if w in {
            "bag", "bags", "handbag", "handbags", "tote", "leather", "luxury", "outfit",
            "fashion", "accessories", "purse", "designer", "strap", "craftsmanship",
            "boutique", "model", "style", "velvet", "closure"
        }]
        if fashion_hits:
            return f"handbag {' '.join(fashion_hits[:2])}"
        # If the sentence is call-to-action or abstract, use guaranteed handbag visual queries
        curated_fashion = [
            "woman carrying luxury handbag",
            "handbag leather craftsmanship",
            "fashion model handbag outfit",
            "designer luxury handbag",
            "luxury handbag boutique store"
        ]
        return random.choice(curated_fashion)

    # Space & astronomy handling
    if any(k in anchor.lower() for k in ["space", "cosmos", "galaxy", "astronomy"]):
        space_hits = [w for w in meaningful if w in {
            "space", "galaxy", "cosmos", "universe", "planet", "planets", "stars", "star",
            "nebula", "earth", "moon", "orbit", "solar", "telescope", "astronaut", "blackhole"
        }]
        if space_hits:
            return f"space {' '.join(space_hits[:2])}"
        return "space galaxy cosmos 4k vertical"

    if meaningful:
        # Pick top 2 visual words
        specific_keywords = " ".join(meaningful[:2])
        if anchor and anchor not in specific_keywords:
            return f"{anchor} {specific_keywords}"
        return specific_keywords
    elif anchor:
        return f"{anchor} 4k vertical"
        
    return "cinematic aesthetic"

def download_pexels_video(query: str = "cinematic aesthetic", context_theme: str = "", output_path: Optional[Path] = None) -> Path:
    """
    Searches and downloads a relevant vertical video clip from Pexels.
    Uses context-aware fallbacks to avoid genre mismatches.
    """
    videos = search_pexels_videos(query=query)
    
    # If no results for full query, try first word
    if not videos and " " in query:
        first_word = query.split()[0]
        videos = search_pexels_videos(query=first_word)
        
    # If still no results, use genre-appropriate fallbacks
    if not videos:
        if any(k in context_theme.lower() for k in ["handbag", "fashion", "luxury", "promo"]):
            fallbacks = ["handbag luxury", "luxury fashion model", "leather bag", "fashion boutique", "woman street style"]
        elif any(k in context_theme.lower() for k in ["space", "cosmos", "galaxy"]):
            fallbacks = ["space galaxy", "universe stars", "nebula cosmos", "planet earth space"]
        else:
            fallbacks = ["cinematic aesthetic", "nature aesthetic", "abstract motion", "city night"]

        for fallback in fallbacks:
            videos = search_pexels_videos(query=fallback)
            if videos:
                break

    if not videos:
        raise RuntimeError(f"No vertical videos found on Pexels for '{query}'.")

    # Filter videos that have a valid vertical MP4 download link
    valid_candidates = []
    for vid in videos:
        url = get_best_video_file_url(vid)
        if url:
            valid_candidates.append((vid.get("id"), url))

    if not valid_candidates:
        raise RuntimeError("No valid MP4 download link found in retrieved Pexels videos.")

    # Pick randomly among top 5 candidates for scene variety
    video_id, selected_url = random.choice(valid_candidates[:5])

    target_file = output_path or (BACKGROUNDS_DIR / f"pexels_{video_id}.mp4")
    if target_file.exists() and target_file.stat().st_size > 0:
        return target_file

    target_file.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(selected_url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(target_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    return target_file
