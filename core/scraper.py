import random
import requests
from typing import Dict, List, Optional
from config.settings import DEFAULT_SUBREDDIT

# Built-in viral fallbacks for testing or offline generation
FALLBACK_STORIES = [
    {
        "id": "sample_1",
        "subreddit": "AskReddit",
        "title": "What is the creepiest coincidence you have ever experienced?",
        "body": "When I was seventeen, I had a recurring nightmare about an abandoned lighthouse on a rocky cliff under a blood-red sky. Five years later on a road trip along the Oregon coast, my friend pulled over at a scenic overlook. I looked down, and there it was, down to the exact iron weather vane and cracked white paint. When we walked up to it, a rusted wooden plaque read: Rest In Peace to the unnamed traveler found on this shore, 1998, the exact month and year I was born.",
        "author": "cliff_wanderer"
    },
    {
        "id": "sample_2",
        "subreddit": "tifu",
        "title": "TIFU by replying to my boss with an automated voice message",
        "body": "This morning at 6 AM my CEO texted our company group chat asking who could take over an emergency client presentation because our director was out sick. I was half asleep, tapped the voice-to-text dictation button on my phone, muttered 'tell him absolutely not I am way too exhausted for this', and accidentally hit send before realizing it transcribed every single word. Ten minutes later my phone rang, and HR informed me that my access badge was already deactivated.",
        "author": "hungover_dev"
    },
    {
        "id": "sample_3",
        "subreddit": "confessions",
        "title": "I found a hidden room in the basement of my rental house",
        "body": "I moved into an old Victorian house three months ago. Last weekend my cat kept scratching at a false wooden wall behind the furnace. I pried off two loose boards and found a narrow crawlspace leading to a fully furnished concrete room. On a small metal desk sat a dusty tape recorder with a single cassette inside labeled: Do Not Play If You Live Here. Against my better judgment, I pressed play, and heard my own voice whispering from two days ago.",
        "author": "cellar_dweller"
    }
]

def fetch_reddit_posts(subreddit: str = DEFAULT_SUBREDDIT, limit: int = 15) -> List[Dict]:
    """
    Fetches top posts from a given subreddit using Reddit's public JSON API.
    Filters out stickies and posts that are too short or overly long.
    """
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t=day&limit={limit}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 VidLoom/1.0"
    }
    
    posts = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                if post.get("stickied") or post.get("over_18"):
                    continue
                
                title = post.get("title", "").strip()
                selftext = post.get("selftext", "").strip()
                author = post.get("author", "anonymous")
                post_id = post.get("id", "")
                
                # We need posts with some story/content or AskReddit prompts with good comments
                word_count = len((title + " " + selftext).split())
                if 25 <= word_count <= 250:
                    posts.append({
                        "id": post_id,
                        "subreddit": subreddit,
                        "title": title,
                        "body": selftext,
                        "author": author,
                        "score": post.get("score", 0),
                        "url": f"https://reddit.com{post.get('permalink', '')}"
                    })
    except Exception as e:
        print(f"[Scraper] Warning: Could not fetch from Reddit ({e}). Using viral fallback library.")

    if not posts:
        posts = FALLBACK_STORIES
        
    return posts

def get_random_story(subreddit: Optional[str] = None) -> Dict:
    """Returns a single story ready for processing."""
    sub = subreddit or DEFAULT_SUBREDDIT
    posts = fetch_reddit_posts(subreddit=sub)
    return random.choice(posts)
