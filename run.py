import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from config.settings import DEFAULT_VOICE, DEFAULT_SUBREDDIT, FINAL_DIR
from core.scraper import get_random_story, FALLBACK_STORIES
from core.scriptgen import generate_script
from core.tts import generate_voiceover, AVAILABLE_VOICES
from core.subtitles import generate_ass_subtitles
from core.video import render_multi_scene_video
from core.reddit_card import create_reddit_card, create_fact_card, create_promo_card
from core.pexels import derive_context_theme

def run_pipeline(
    subreddit: str = DEFAULT_SUBREDDIT,
    custom_text: str = None,
    voice: str = DEFAULT_VOICE,
    custom_bg: str = None,
    use_sample: bool = False,
    use_facts: bool = False,
    use_promo: bool = False
):
    start_time = time.time()
    print("=" * 60)
    print(">> VIDLOOM - Automated Short Video Generator")
    print("=" * 60)
    
    # 1. Content Ingestion
    print("\n[1/5] Ingesting Content...")
    hook_card = None
    if custom_text:
        raw_story = {
            "title": "Custom Story",
            "body": custom_text,
            "author": "User"
        }
        print("  -> Using custom user input text.")
    elif use_promo:
        raw_story = {
            "title": "The Luxury Italian Leather Tote",
            "body": (
                "Meet the everyday luxury tote designed for women who refuse to compromise. "
                "Handcrafted from supple Italian full-grain leather, it seamlessly transitions "
                "from your morning commute to high-end evening dinners. "
                "Featuring an organized padded compartment, water-resistant velvet lining, and magnetic gold closures. "
                "Upgrade your everyday aesthetic today. "
                "Tap the link below to claim thirty percent off your first order."
            ),
            "category": "luxury handbag fashion",
            "is_promo": True,
            "brand": "AURORA LUXE",
            "tag": "LIMITED COLLECTION"
        }
        print(f"  -> Generating luxury promotional video for: \"{raw_story['title']}\"")
        hook_card = create_promo_card(
            title=raw_story["title"],
            brand=raw_story["brand"],
            tag=raw_story["tag"]
        )
        # Use an elegant female commercial voice if default voice wasn't overridden
        if voice == DEFAULT_VOICE:
            voice = AVAILABLE_VOICES.get("us_female", "en-US-EmmaNeural")
    elif use_facts:
        from core.facts import get_random_fact
        fact_item = get_random_fact()
        raw_story = {
            "title": fact_item["title"],
            "body": fact_item["narration"],
            "category": fact_item["category"],
            "is_fact": True
        }
        print(f"  -> Using viral facts topic: \"{raw_story['title']}\" [{raw_story['category']}]")
        hook_card = create_fact_card(
            title=raw_story["title"],
            category=raw_story["category"]
        )
    elif use_sample:
        import random
        raw_story = random.choice(FALLBACK_STORIES)
        print(f"  -> Using built-in viral test story: \"{raw_story['title']}\"")
        hook_card = create_reddit_card(
            title=raw_story["title"],
            subreddit=raw_story.get("subreddit", "AskReddit"),
            author=raw_story.get("author", "anon")
        )
    else:
        raw_story = get_random_story(subreddit)
        print(f"  -> Fetched from r/{subreddit}: \"{raw_story['title']}\" (by u/{raw_story.get('author', 'anon')})")
        hook_card = create_reddit_card(
            title=raw_story["title"],
            subreddit=raw_story.get("subreddit", "AskReddit"),
            author=raw_story.get("author", "anon")
        )

    # 2. Script Optimization
    print("\n[2/5] Optimizing Script for Retention & 3s Hook...")
    if raw_story.get("is_fact") or raw_story.get("is_promo"):
        script_data = {
            "hook": raw_story["title"],
            "full_narration": raw_story["body"]
        }
    else:
        script_data = generate_script(raw_story)
        
    print(f"  -> Hook: \"{script_data['hook']}\"")
    print(f"  -> Words: {len(script_data['full_narration'].split())} words")

    # 3. Voice Synthesis
    print(f"\n[3/5] Synthesizing Voiceover ({voice})...")
    tts_result = generate_voiceover(
        text=script_data["full_narration"],
        voice=voice,
        rate="+5%"
    )
    print(f"  -> Audio generated: {tts_result['duration']:.1f}s ({len(tts_result['words'])} words timed)")

    # 4. Dynamic Subtitle Generation
    print("\n[4/5] Generating Dynamic Karaoke ASS Subtitles...")
    sub_path = generate_ass_subtitles(tts_result["words"])
    print(f"  -> Subtitles compiled: {sub_path.name}")

    # 5. FFmpeg Assembly
    print("\n[5/5] Assembling Multi-Scene Video with FFmpeg & Hook Card...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = FINAL_DIR / f"vidloom_short_{timestamp}.mp4"

    context_theme = derive_context_theme(raw_story["title"], raw_story.get("category", ""))

    final_video = render_multi_scene_video(
        words_data=tts_result["words"],
        audio_path=tts_result["audio_path"],
        subtitles_path=sub_path,
        duration=tts_result["duration"],
        reddit_card_path=hook_card,
        context_theme=context_theme,
        output_path=out_name
    )

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("[SUCCESS] VIDEO GENERATION COMPLETE!")
    print(f"[TIME]    Total Pipeline Time: {elapsed:.1f} seconds")
    print(f"[OUTPUT]  File: {final_video.resolve()}")
    print("=" * 60)
    return final_video

def main():
    parser = argparse.ArgumentParser(description="VidLoom Video Automation CLI")
    parser.add_argument("--test", action="store_true", help="Run with built-in test story")
    parser.add_argument("--facts", action="store_true", help="Generate viral facts short")
    parser.add_argument("--promo", action="store_true", help="Generate luxury product promo short (e.g. handbag)")
    parser.add_argument("--reddit", type=str, default=DEFAULT_SUBREDDIT, help="Subreddit name (default: AskReddit)")
    parser.add_argument("--text", type=str, default=None, help="Custom text to produce")
    parser.add_argument("--voice", type=str, default=DEFAULT_VOICE, help="TTS Voice (default: en-US-BrianMultilingualNeural)")
    parser.add_argument("--bg", type=str, default=None, help="Path to custom background video")
    
    args = parser.parse_args()
    
    chosen_voice = AVAILABLE_VOICES.get(args.voice, args.voice)
    
    run_pipeline(
        subreddit=args.reddit,
        custom_text=args.text,
        voice=chosen_voice,
        custom_bg=args.bg,
        use_sample=args.test,
        use_facts=args.facts,
        use_promo=args.promo
    )

if __name__ == "__main__":
    main()
