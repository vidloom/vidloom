import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config.settings import TEMP_DIR, ASSETS_DIR

def get_font(font_size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Tries to find a clean system font (Arial/Segoe UI), falls back to default."""
    font_names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arial.ttf"
    ]
    for fn in font_names:
        if os.path.exists(fn):
            try:
                return ImageFont.truetype(fn, font_size)
            except Exception:
                pass
    return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def create_reddit_card(
    title: str,
    subreddit: str = "AskReddit",
    author: str = "glitch_witness",
    output_path: Path = None
) -> Path:
    """
    Renders an authentic, pixel-perfect dark-mode Reddit post card.
    """
    card_path = output_path or (TEMP_DIR / "reddit_card.png")
    
    card_w = 980
    pad_x = 48
    pad_y = 40
    
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)
    
    font_sub = get_font(24, bold=True)
    font_meta = get_font(20, bold=False)
    font_title = get_font(34, bold=True)
    font_footer = get_font(22, bold=True)
    
    max_text_w = card_w - (pad_x * 2)
    title_lines = wrap_text(title, font_title, max_text_w, draw_dummy)
    # Cap to max 4 lines
    if len(title_lines) > 4:
        title_lines = title_lines[:3] + [title_lines[3] + "..."]
        
    line_h = 46
    title_total_h = len(title_lines) * line_h
    
    header_h = 50
    footer_h = 60
    spacing = 24
    
    card_h = pad_y + header_h + spacing + title_total_h + spacing + footer_h + pad_y
    
    # Create high-res card with alpha
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Dark Reddit Card Background with Rounded Corners (#1A1A1B)
    card_bg = (26, 26, 27, 245)
    card_border = (52, 53, 54, 255)
    draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=24, fill=card_bg, outline=card_border, width=2)
    
    # 2. Header: Subreddit Icon + Name + Meta
    curr_y = pad_y
    # Subreddit circle badge (#FF4500 Reddit Orange)
    badge_r = 20
    badge_x = pad_x
    badge_y = curr_y + 4
    draw.ellipse([(badge_x, badge_y), (badge_x + badge_r * 2, badge_y + badge_r * 2)], fill=(255, 69, 0, 255))
    # 'r/' inside circle
    draw.text((badge_x + 10, badge_y + 6), "r/", font=get_font(18, bold=True), fill=(255, 255, 255, 255))
    
    # Text next to badge
    text_x = badge_x + badge_r * 2 + 14
    sub_str = f"r/{subreddit}"
    draw.text((text_x, curr_y), sub_str, font=font_sub, fill=(255, 255, 255, 255))
    
    bbox_sub = draw.textbbox((text_x, curr_y), sub_str, font=font_sub)
    meta_x = bbox_sub[2] + 12
    meta_str = f"• Posted by u/{author} • 6h ago"
    draw.text((meta_x, curr_y + 3), meta_str, font=font_meta, fill=(129, 131, 132, 255))
    
    # 3. Title Lines (Crisp Bold White)
    curr_y += header_h + spacing
    for line in title_lines:
        draw.text((pad_x, curr_y), line, font=font_title, fill=(255, 255, 255, 255))
        curr_y += line_h
        
    # 4. Footer: Authentic Reddit Pill Buttons
    curr_y += spacing
    pill_bg = (39, 41, 42, 255)
    pill_border = (52, 53, 54, 255)
    pill_h = 42
    
    # Upvote Pill
    upvote_w = 160
    draw.rounded_rectangle([(pad_x, curr_y), (pad_x + upvote_w, curr_y + pill_h)], radius=21, fill=pill_bg, outline=pill_border, width=1)
    draw.text((pad_x + 20, curr_y + 8), "▲ 28.4k ▼", font=font_footer, fill=(215, 218, 220, 255))
    
    # Comments Pill
    comm_x = pad_x + upvote_w + 14
    comm_w = 180
    draw.rounded_rectangle([(comm_x, curr_y), (comm_x + comm_w, curr_y + pill_h)], radius=21, fill=pill_bg, outline=pill_border, width=1)
    draw.text((comm_x + 22, curr_y + 8), "3.1k Comments", font=font_footer, fill=(215, 218, 220, 255))
    
    # Share Pill
    share_x = comm_x + comm_w + 14
    share_w = 110
    draw.rounded_rectangle([(share_x, curr_y), (share_x + share_w, curr_y + pill_h)], radius=21, fill=pill_bg, outline=pill_border, width=1)
    draw.text((share_x + 24, curr_y + 8), "Share", font=font_footer, fill=(215, 218, 220, 255))
    
    card_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(card_path, "PNG")
    print(f"[RedditCard] Generated high-res post card: {card_path} ({card_w}x{card_h})")
    return card_path

def create_fact_card(
    title: str,
    category: str = "SPACE FACTS",
    output_path: Path = None
) -> Path:
    """
    Renders a sleek, modern, high-contrast dark topic card for Facts videos.
    """
    card_path = output_path or (TEMP_DIR / "fact_card.png")
    
    card_w = 980
    pad_x = 48
    pad_y = 44
    
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)
    
    font_badge = get_font(20, bold=True)
    font_title = get_font(38, bold=True)
    font_footer = get_font(20, bold=True)
    
    max_text_w = card_w - (pad_x * 2)
    title_lines = wrap_text(title, font_title, max_text_w, draw_dummy)
    if len(title_lines) > 3:
        title_lines = title_lines[:2] + [title_lines[2] + "..."]
        
    line_h = 50
    title_total_h = len(title_lines) * line_h
    
    badge_h = 40
    footer_h = 44
    spacing = 22
    
    card_h = pad_y + badge_h + spacing + title_total_h + spacing + footer_h + pad_y
    
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Dark Glassmorphism Background (#0E1116)
    card_bg = (14, 17, 22, 245)
    card_border = (0, 229, 255, 180)  # Glowing Neon Cyan Accent Border
    draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=24, fill=card_bg, outline=card_border, width=2)
    
    # 2. Header Badge: Neon Cyan Pill
    curr_y = pad_y
    badge_text = f"⚡ {category}"
    bbox_b = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = (bbox_b[2] - bbox_b[0]) + 32
    draw.rounded_rectangle([(pad_x, curr_y), (pad_x + badge_w, curr_y + badge_h)], radius=12, fill=(0, 229, 255, 255))
    draw.text((pad_x + 16, curr_y + 8), badge_text, font=font_badge, fill=(10, 10, 15, 255))
    
    # 3. Title Lines (Bold White Impact)
    curr_y += badge_h + spacing
    for line in title_lines:
        draw.text((pad_x, curr_y), line, font=font_title, fill=(255, 255, 255, 255))
        curr_y += line_h
        
    # 4. Footer: Sleek Red Indicator
    curr_y += spacing
    draw.ellipse([(pad_x, curr_y + 12), (pad_x + 14, curr_y + 26)], fill=(255, 59, 48, 255))
    draw.text((pad_x + 24, curr_y + 8), "WATCH UNTIL THE END", font=font_footer, fill=(160, 170, 185, 255))
    
    card_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(card_path, "PNG")
    print(f"[FactCard] Generated high-res fact card: {card_path} ({card_w}x{card_h})")
    return card_path

def create_promo_card(
    title: str,
    brand: str = "AURORA LUXE",
    tag: str = "LIMITED COLLECTION",
    output_path: Path = None
) -> Path:
    """
    Renders an ultra-sleek, luxury e-commerce promotional product card.
    """
    card_path = output_path or (TEMP_DIR / "promo_card.png")
    
    card_w = 980
    pad_x = 48
    pad_y = 44
    
    dummy_img = Image.new("RGBA", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)
    
    font_brand = get_font(20, bold=True)
    font_title = get_font(36, bold=True)
    font_footer = get_font(20, bold=True)
    
    max_text_w = card_w - (pad_x * 2)
    title_lines = wrap_text(title, font_title, max_text_w, draw_dummy)
    if len(title_lines) > 3:
        title_lines = title_lines[:2] + [title_lines[2] + "..."]
        
    line_h = 48
    title_total_h = len(title_lines) * line_h
    
    badge_h = 38
    footer_h = 40
    spacing = 20
    
    card_h = pad_y + badge_h + spacing + title_total_h + spacing + footer_h + pad_y
    
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 1. Sleek Midnight Luxury Background (#111114) with Gold Accent Border
    card_bg = (17, 17, 20, 245)
    card_border = (212, 175, 55, 220)  # Elegant Champagne Gold
    draw.rounded_rectangle([(0, 0), (card_w - 1, card_h - 1)], radius=24, fill=card_bg, outline=card_border, width=2)
    
    # 2. Header: Luxury Pill Badge
    curr_y = pad_y
    badge_text = f"AURORA LUXE  •  {tag}"
    bbox_b = draw.textbbox((0, 0), badge_text, font=font_brand)
    badge_w = (bbox_b[2] - bbox_b[0]) + 32
    draw.rounded_rectangle([(pad_x, curr_y), (pad_x + badge_w, curr_y + badge_h)], radius=12, fill=(212, 175, 55, 255))
    draw.text((pad_x + 16, curr_y + 7), badge_text, font=font_brand, fill=(15, 15, 18, 255))
    
    # 3. Title Lines (Crisp Luxury White)
    curr_y += badge_h + spacing
    for line in title_lines:
        draw.text((pad_x, curr_y), line, font=font_title, fill=(255, 255, 255, 255))
        curr_y += line_h
        
    # 4. Footer: Call to action pill
    curr_y += spacing
    draw.text((pad_x, curr_y + 6), "EXCLUSIVE 30% OFF • TAP LINK BELOW", font=font_footer, fill=(212, 175, 55, 255))
    
    card_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(card_path, "PNG")
    print(f"[PromoCard] Generated luxury promo card: {card_path} ({card_w}x{card_h})")
    return card_path
