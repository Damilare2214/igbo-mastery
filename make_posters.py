#!/usr/bin/env python3
"""Posters: 1080x1920 (Stories/WhatsApp) and 1080x1080 (IG/FB feed) PNG."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

BASE = "/home/user/igbo-mastery"
BG = os.path.join(BASE, "assets/bg")
OUT = os.path.join(BASE, "marketing/posters")
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

GREEN = (11, 110, 79)
GOLD = (255, 209, 102)
WHITE = (255, 255, 255)
SOFT = (207, 232, 221)

def font(path, size):
    return ImageFont.truetype(path, size)

def prep_bg(name, w, h, dark=0.92):
    im = Image.open(os.path.join(BG, name)).convert("RGB")
    sw, sh = im.size
    s = max(w / sw, h / sh)
    im = im.resize((int(sw * s) + 1, int(sh * s) + 1), Image.LANCZOS)
    sw, sh = im.size
    im = im.crop(((sw - w) // 2, (sh - h) // 2, (sw - w) // 2 + w, (sh - h) // 2 + h))
    im = ImageEnhance.Brightness(im).enhance(dark)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(scrim)
    band = int(h * 0.32)
    for y in range(h):
        a = max(0, int(150 * (1 - y / band))) + max(0, int(150 * ((y - h * 0.62) / (h * 0.38))))
        d.line([(0, y), (w, y)], fill=(4, 16, 12, min(a + 55, 220)))
    return Image.alpha_composite(im.convert("RGBA"), scrim).convert("RGB")

def center_text(d, xy, text, f, fill, spacing=0):
    x, y = xy
    if spacing:
        w = sum(d.textlength(ch, font=f) + spacing for ch in text) - spacing
        cx = x - w / 2
        for ch in text:
            d.text((cx, y), ch, font=f, fill=fill)
            cx += d.textlength(ch, font=f) + spacing
        return w
    w = d.textlength(text, font=f)
    d.text((x - w / 2, y), text, font=f, fill=fill)
    return w

def rounded(d, box, radius, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def story_tone_quartet():
    W, H = 1080, 1920
    im = prep_bg("bg-01.jpg", W, H)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 90), "I G B O   M A S T E R Y", font(FONT_B, 40), GOLD)
    center_text(d, (W/2, 200), "ONE WORD. FOUR MEANINGS.", font(FONT_B, 66), WHITE)
    items = [("ákwá", "cry", GOLD), ("àkwá", "egg", (168, 214, 255)),
             ("ákwà", "cloth", GOLD), ("àkwà", "bed", (168, 214, 255))]
    y = 380
    for word, meaning, col in items:
        rounded(d, (140, y, 940, y + 210), 26, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (W/2, y + 55), word, font(FONT_B, 110), col)
        center_text(d, (W/2, y + 160), meaning, font(FONT_R, 44), SOFT)
        y += 250
    d.line([(200, y + 20), (880, y + 20)], fill=(60, 120, 100), width=3)
    center_text(d, (W/2, y + 60), "Same letters. Different tone.", font(FONT_B, 54), WHITE)
    center_text(d, (W/2, y + 130), "Different word.", font(FONT_B, 54), WHITE)
    center_text(d, (W/2, H - 260), "Learn the tones free", font(FONT_B, 58), GOLD)
    center_text(d, (W/2, H - 180), "igbomastery.com  ·  @igbo.mastery", font(FONT_R, 38), SOFT)
    im.save(os.path.join(OUT, "poster-story-tones.png"))

def story_dotted_letters():
    W, H = 1080, 1920
    im = prep_bg("bg-05.jpg", W, H)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 90), "I G B O   M A S T E R Y", font(FONT_B, 40), GOLD)
    center_text(d, (W/2, 200), "THE DOTTED LETTERS", font(FONT_B, 72), WHITE)
    items = [("ị", "a tight “ih”"), ("ọ", "the “aw” of saw"),
             ("ụ", "the “oo” of book"), ("ṅ", "the “ng” that starts a word")]
    y = 360
    for letter, guide in items:
        rounded(d, (140, y, 940, y + 230), 26, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (330, y + 45), letter, font(FONT_B, 150), GOLD)
        center_text(d, (660, y + 90), guide, font(FONT_R, 46), SOFT)
        y += 265
    center_text(d, (W/2, y + 40), "The dot is not decoration.", font(FONT_B, 56), WHITE)
    center_text(d, (W/2, y + 115), "ị ọ ụ ṅ are different letters", font(FONT_B, 56), WHITE)
    center_text(d, (W/2, y + 185), "with different sounds.", font(FONT_B, 56), WHITE)
    center_text(d, (W/2, H - 200), "Free foundation course — link in bio", font(FONT_B, 48), GOLD)
    center_text(d, (W/2, H - 130), "@igbo.mastery", font(FONT_R, 36), SOFT)
    im.save(os.path.join(OUT, "poster-story-dotted.png"))

def story_greetings():
    W, H = 1080, 1920
    im = prep_bg("bg-10.jpg", W, H)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 90), "I G B O   M A S T E R Y", font(FONT_B, 40), GOLD)
    center_text(d, (W/2, 200), "SAY HELLO IN IGBO", font(FONT_B, 68), WHITE)
    rows = [("Ndeewo!", "Hello / Welcome"),
            ("Kedu ka ị mere?", "How are you?"),
            ("Ọ dị mma, daalụ.", "I'm fine, thank you."),
            ("Ka ọ dị.", "Goodbye.")]
    y = 400
    for ig, en in rows:
        rounded(d, (120, y, 960, y + 200), 24, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (W/2, y + 45), ig, font(FONT_B, 76), GOLD)
        center_text(d, (W/2, y + 140), en, font(FONT_R, 40), SOFT)
        y += 235
    center_text(d, (W/2, y + 30), "Three lines, and you have", font(FONT_R, 46), WHITE)
    center_text(d, (W/2, y + 90), "greeted someone properly.", font(FONT_R, 46), WHITE)
    center_text(d, (W/2, H - 210), "Survival Igbo — ₦500 once", font(FONT_B, 52), GOLD)
    center_text(d, (W/2, H - 140), "igbomastery.com", font(FONT_R, 38), SOFT)
    im.save(os.path.join(OUT, "poster-story-greetings.png"))

def story_pricing():
    W, H = 1080, 1920
    im = prep_bg("bg-02.jpg", W, H)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 90), "I G B O   M A S T E R Y", font(FONT_B, 40), GOLD)
    center_text(d, (W/2, 200), "LEARN IGBO — THREE TIERS", font(FONT_B, 62), WHITE)
    tiers = [("₦0", "FREE FOUNDATION", "tones · alphabet · dotted letters", (6, 30, 24), SOFT),
             ("₦500", "SURVIVAL IGBO", "greetings · numbers · family · food · market", (11, 80, 58), WHITE),
             ("₦2,000", "IGBO FLUENCY KIT", "flashcards · writing · dialogues · proverbs · certificate", (90, 62, 10), (255, 240, 200))]
    y = 360
    for price, name, desc, fillc, textc in tiers:
        rounded(d, (110, y, 970, y + 300), 28, fill=fillc, outline=GOLD if price != "₦0" else (30, 80, 64), width=3)
        center_text(d, (W/2, y + 35), price, font(FONT_B, 120), GOLD)
        center_text(d, (W/2, y + 175), name, font(FONT_B, 46), textc)
        center_text(d, (W/2, y + 235), desc, font(FONT_R, 32), textc)
        y += 340
    center_text(d, (W/2, y + 40), "One-time payments. No subscription.", font(FONT_B, 50), WHITE)
    center_text(d, (W/2, y + 105), "International cards accepted", font(FONT_R, 40), SOFT)
    center_text(d, (W/2, H - 190), "Start free — link in bio", font(FONT_B, 54), GOLD)
    center_text(d, (W/2, H - 120), "@igbo.mastery", font(FONT_R, 36), SOFT)
    im.save(os.path.join(OUT, "poster-story-pricing.png"))

def feed_tone_quartet():
    W, H = 1080, 1080
    im = prep_bg("bg-03.jpg", W, H, dark=0.9)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 60), "I G B O   M A S T E R Y", font(FONT_B, 34), GOLD)
    center_text(d, (W/2, 150), "ONE WORD. FOUR MEANINGS.", font(FONT_B, 58), WHITE)
    items = [("ákwá", "cry", GOLD), ("àkwá", "egg", (168, 214, 255)),
             ("ákwà", "cloth", GOLD), ("àkwà", "bed", (168, 214, 255))]
    xs = [160, 560, 160, 560]; ys = [300, 300, 560, 560]
    for (word, meaning, col), x, y in zip(items, xs, ys):
        rounded(d, (x, y, x + 360, y + 210), 22, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (x + 180, y + 40), word, font(FONT_B, 84), col)
        center_text(d, (x + 180, y + 135), meaning, font(FONT_R, 36), SOFT)
    center_text(d, (W/2, 820), "Same letters. Different tone. Different word.", font(FONT_B, 44), WHITE)
    center_text(d, (W/2, 920), "Learn the tones free — @igbo.mastery", font(FONT_B, 40), GOLD)
    im.save(os.path.join(OUT, "poster-feed-tones.png"))

def feed_dotted():
    W, H = 1080, 1080
    im = prep_bg("bg-06.jpg", W, H, dark=0.9)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 60), "I G B O   M A S T E R Y", font(FONT_B, 34), GOLD)
    center_text(d, (W/2, 150), "THE DOTTED LETTERS", font(FONT_B, 62), WHITE)
    items = [("ị", "tight “ih”"), ("ọ", "“aw” of saw"), ("ụ", "“oo” of book"), ("ṅ", "starting “ng”")]
    xs = [130, 550, 130, 550]; ys = [300, 300, 520, 520]
    for (letter, guide), x, y in zip(items, xs, ys):
        rounded(d, (x, y, x + 400, y + 190), 22, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (x + 200, y + 25), letter, font(FONT_B, 120), GOLD)
        center_text(d, (x + 200, y + 140), guide, font(FONT_R, 34), SOFT)
    center_text(d, (W/2, 780), "The dot is not decoration.", font(FONT_B, 48), WHITE)
    center_text(d, (W/2, 880), "Free foundation course — @igbo.mastery", font(FONT_B, 40), GOLD)
    im.save(os.path.join(OUT, "poster-feed-dotted.png"))

def feed_greetings():
    W, H = 1080, 1080
    im = prep_bg("bg-09.jpg", W, H, dark=0.9)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 60), "I G B O   M A S T E R Y", font(FONT_B, 34), GOLD)
    center_text(d, (W/2, 150), "SAY HELLO IN IGBO", font(FONT_B, 58), WHITE)
    rows = [("Ndeewo!", "Hello / Welcome"), ("Kedu ka ị mere?", "How are you?"),
            ("Ọ dị mma, daalụ.", "I'm fine, thank you.")]
    y = 280
    for ig, en in rows:
        rounded(d, (140, y, 940, y + 165), 22, fill=(6, 30, 24), outline=(30, 80, 64), width=2)
        center_text(d, (W/2, y + 25), ig, font(FONT_B, 68), GOLD)
        center_text(d, (W/2, y + 110), en, font(FONT_R, 34), SOFT)
        y += 195
    center_text(d, (W/2, 890), "Survival Igbo — ₦500 once · @igbo.mastery", font(FONT_B, 40), GOLD)
    im.save(os.path.join(OUT, "poster-feed-greetings.png"))

def feed_pricing():
    W, H = 1080, 1080
    im = prep_bg("bg-04.jpg", W, H, dark=0.9)
    d = ImageDraw.Draw(im)
    center_text(d, (W/2, 60), "I G B O   M A S T E R Y", font(FONT_B, 34), GOLD)
    center_text(d, (W/2, 150), "LEARN IGBO — THREE TIERS", font(FONT_B, 56), WHITE)
    tiers = [("₦0", "Free Foundation — tones, alphabet, dotted letters", (6, 30, 24), SOFT),
             ("₦500", "Survival Igbo — greetings, numbers, family, food, market", (11, 80, 58), WHITE),
             ("₦2,000", "Fluency Kit — flashcards, writing, dialogues, proverbs, certificate", (90, 62, 10), (255, 240, 220))]
    y = 270
    for price, desc, fillc, textc in tiers:
        rounded(d, (100, y, 980, y + 190), 24, fill=fillc, outline=GOLD if price != "₦0" else (30, 80, 64), width=3)
        center_text(d, (W/2, y + 25), price, font(FONT_B, 88), GOLD)
        center_text(d, (W/2, y + 125), desc, font(FONT_R, 30), textc)
        y += 220
    center_text(d, (W/2, 950), "One-time payments · international cards accepted · @igbo.mastery", font(FONT_B, 34), GOLD)
    im.save(os.path.join(OUT, "poster-feed-pricing.png"))

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    story_tone_quartet(); story_dotted_letters(); story_greetings(); story_pricing()
    feed_tone_quartet(); feed_dotted(); feed_greetings(); feed_pricing()
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        im = Image.open(p)
        print(f"{f}  {im.size[0]}x{im.size[1]}  {os.path.getsize(p)//1024} KB")
