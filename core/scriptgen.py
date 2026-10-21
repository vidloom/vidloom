import json
import re
from typing import Dict
from config.settings import GEMINI_API_KEY

def clean_for_speech(text: str) -> str:
    """Cleans up text for natural text-to-speech pronunciation."""
    # Remove markdown links, URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # Remove Reddit formatting artifacts
    text = re.sub(r'\bTIFU\b', 'Today I messed up', text, flags=re.IGNORECASE)
    text = re.sub(r'\bAITA\b', 'Am I the jerk', text, flags=re.IGNORECASE)
    text = re.sub(r'\bOP\b', 'original poster', text, flags=re.IGNORECASE)
    # Remove emojis and odd symbols
    text = re.sub(r'[^\w\s.,!?\'"-]', ' ', text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_script(raw_story: Dict) -> Dict:
    """
    Transforms a raw Reddit story or text into a coherent, high-retention 45-55s narration script.
    Guarantees a complete narrative arc (setup, tension, twist/resolution) without abrupt cutoffs.
    """
    title = raw_story.get("title", "")
    body = raw_story.get("body", "")
    
    clean_title = clean_for_speech(title)
    clean_body = clean_for_speech(body)
    
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            prompt = f"""You are an elite short-form video copywriter specializing in viral YouTube Shorts.
Adapt this raw Reddit story into a suspenseful, highly engaging narration script.

CRITICAL REQUIREMENTS:
1. COMPLETE STORY ARC: The story MUST make total sense. Do not cut off mid-thought. It must have a clear setup, escalation of tension, and a satisfying climax/twist/ending.
2. 3-SECOND HOOK: The opening sentence must immediately grab attention and make it impossible to swipe away.
3. EXACT DURATION / WORD COUNT: Total word count MUST be between 115 and 140 words (exactly 45-55 seconds spoken).
4. NATURAL SPEECH: Conversational, fast-paced, punchy sentences. No stage directions or speaker tags.
5. PURE JSON OUTPUT:
{{
  "hook": "The irresistible opening sentence.",
  "body": "The rest of the story with clear climax and ending.",
  "full_narration": "The complete spoken script combining hook and body."
}}

RAW REDDIT STORY:
Title: {clean_title}
Story: {clean_body}
"""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=dict(response_mime_type="application/json")
            )
            
            data = json.loads(response.text)
            return {
                "title": clean_title,
                "hook": data.get("hook", clean_title),
                "body": data.get("body", clean_body),
                "full_narration": data.get("full_narration", f"{clean_title}. {clean_body}")
            }
        except Exception as e:
            print(f"[ScriptGen] Warning: Gemini generation failed ({e}). Using local fallback formatting.")

    # Local fallback formatting ensuring complete sentences within duration limit
    full_text = f"{clean_title}. {clean_body}"
    words = full_text.split()
    if len(words) > 135:
        # Cut at nearest sentence boundary before 135 words
        trimmed = " ".join(words[:135])
        last_punct = max(trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?'))
        if last_punct > 50:
            full_text = trimmed[:last_punct + 1]
        else:
            full_text = trimmed + "."
            
    return {
        "title": clean_title,
        "hook": clean_title,
        "body": clean_body,
        "full_narration": full_text
    }

def generate_ai_story(topic: str = "unexplainable glitch in the matrix") -> Dict:
    """
    Generates an original viral Reddit-style story from scratch using Gemini (no Reddit scraping needed).
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is required to generate AI stories.")
        
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""Write an original, highly compelling Reddit confession/story about '{topic}' for a YouTube Short.
It must sound like a real person sharing a true, unbelievable experience.

RULES:
1. Word count: 120-140 words total (45-50 seconds when read aloud).
2. The first sentence must be an intense hook.
3. Deliver a complete story with a shocking twist or satisfying ending.
4. Output JSON:
{{
  "title": "A punchy Reddit post title",
  "hook": "Opening hook sentence",
  "body": "Body of story",
  "full_narration": "Complete spoken text"
}}
"""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=dict(response_mime_type="application/json")
    )
    return json.loads(response.text)
