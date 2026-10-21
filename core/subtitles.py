from pathlib import Path
from typing import Dict, List, Optional
from config.settings import (
    TEMP_DIR,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    SUBTITLE_FONT,
    SUBTITLE_FONT_SIZE,
    SUBTITLE_PRIMARY_COLOR,
    SUBTITLE_HIGHLIGHT_COLOR,
    SUBTITLE_OUTLINE_COLOR,
    SUBTITLE_OUTLINE_WIDTH,
    SUBTITLE_SHADOW_DEPTH,
    SUBTITLE_MARGIN_V
)

def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp format: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_ass_subtitles(
    words_data: List[Dict],
    output_ass: Optional[Path] = None,
    words_per_phrase: int = 2
) -> Path:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file.
    Creates modern Hormozi-style pop-in captions with dynamic active-word highlighting.
    """
    ass_path = output_ass or (TEMP_DIR / "subtitles.ass")
    
    # Chunk words into small phrases (2-4 words each)
    phrases = []
    current_phrase = []
    
    for item in words_data:
        current_phrase.append(item)
        # End phrase on punctuation or length
        word_text = item["word"]
        if len(current_phrase) >= words_per_phrase or word_text.endswith(('.', '!', '?')):
            phrases.append(list(current_phrase))
            current_phrase = []
            
    if current_phrase:
        phrases.append(list(current_phrase))

    # ASS Header and Styles definition
    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {VIDEO_WIDTH}",
        f"PlayResY: {VIDEO_HEIGHT}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{SUBTITLE_FONT},{SUBTITLE_FONT_SIZE},{SUBTITLE_PRIMARY_COLOR},{SUBTITLE_HIGHLIGHT_COLOR},{SUBTITLE_OUTLINE_COLOR},&H80000000,-1,0,0,0,100,100,0,0,1,{SUBTITLE_OUTLINE_WIDTH},{SUBTITLE_SHADOW_DEPTH},2,40,40,{SUBTITLE_MARGIN_V},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    # Generate dialogue events for each word in each phrase
    for phrase in phrases:
        phrase_words = [w["word"].upper() for w in phrase]
        
        for idx, active_item in enumerate(phrase):
            start_t = format_ass_time(active_item["start"])
            end_t = format_ass_time(active_item["end"])
            
            # Highlight current word in highlight color, rest in primary color
            formatted_tokens = []
            for j, token in enumerate(phrase_words):
                if j == idx:
                    formatted_tokens.append(f"{{\\c{SUBTITLE_HIGHLIGHT_COLOR}\\fscx110\\fscy110}}{token}{{\\c{SUBTITLE_PRIMARY_COLOR}\\fscx100\\fscy100}}")
                else:
                    formatted_tokens.append(f"{{\\c{SUBTITLE_PRIMARY_COLOR}}}{token}")
                    
            line_text = " ".join(formatted_tokens)
            ass_content.append(f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{line_text}")
            
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_content))
        
    return ass_path
