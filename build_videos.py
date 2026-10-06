#!/usr/bin/env python3
"""Build faceless vertical videos: AI background + Ken Burns zoom + dark
scrim + word-by-word animated captions. 1080x1920, 30fps, H.264 + AAC MP4."""
import os, subprocess, sys, json, shutil

BASE = "/home/user/igbo-mastery"
BG = os.path.join(BASE, "assets/bg")
OUT = os.path.join(BASE, "videos")
TMP = os.path.join(BASE, "assets/tmp")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FFMPEG = "/usr/local/lib/python3.13/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"

W, H, FPS = 1080, 1920, 30
GOLD = "#FFD166"
WHITE = "#FFFFFF"

TONE_CHARS = set("áàíìóòúùịọụṅÁÀÍÌÓÒÚÙỊỌỤṄ")

# ---------------------------------------------------------------- specs
# caption = (text, start_seconds, end_seconds, font_size)
VIDEOS = [
 {"id":"v01-one-word-four-meanings","bg":"bg-01.jpg","dur":26,
  "kicker":"I G B O   M A S T E R Y   ·   T O N E   L E S S O N   1",
  "captions":[
    ("One word. Four meanings.", 0.5, 3.2, 74),
    ("akwa", 3.7, 5.9, 150),
    ("ákwá — cry", 6.4, 8.8, 92),
    ("àkwá — egg", 9.2, 11.6, 92),
    ("ákwà — cloth", 12.0, 14.4, 92),
    ("àkwà — bed", 14.8, 17.2, 92),
    ("Same letters. Different tone. Different word.", 17.8, 21.0, 62),
    ("Learn the tones free — link in bio", 21.6, 25.4, 56),
  ]},
 {"id":"v02-three-tones","bg":"bg-02.jpg","dur":24,
  "kicker":"I G B O   M A S T E R Y   ·   T O N E   L E S S O N   2",
  "captions":[
    ("Igbo has three tones", 0.5, 3.0, 80),
    ("high · low · downstep", 3.5, 6.0, 84),
    ("ákwá = cry", 6.6, 9.0, 96),
    ("àkwá = egg", 9.4, 11.8, 96),
    ("Your voice is part of the word.", 12.4, 15.6, 66),
    ("Train your ear free — link in bio", 16.2, 20.0, 56),
  ]},
 {"id":"v03-king-or-teeth","bg":"bg-03.jpg","dur":24,
  "kicker":"I G B O   M A S T E R Y   ·   T O N E   L E S S O N   3",
  "captions":[
    ("Same spelling.", 0.5, 2.6, 82),
    ("Two meanings.", 3.0, 5.1, 82),
    ("eze", 5.8, 8.2, 160),
    ("king", 8.8, 10.8, 100),
    ("— or —", 11.2, 12.8, 66),
    ("teeth", 13.2, 15.2, 100),
    ("Only the tone tells them apart.", 16.0, 19.4, 62),
    ("Link in bio", 20.2, 23.2, 56),
  ]},
 {"id":"v04-eight-vowels","bg":"bg-04.jpg","dur":24,
  "kicker":"I G B O   M A S T E R Y   ·   T H E   A L P H A B E T",
  "captions":[
    ("The Igbo alphabet has", 0.5, 2.6, 74),
    ("8 vowels", 3.1, 5.6, 120),
    ("a  e  i  ị  o  ọ  u  ụ", 6.4, 9.8, 92),
    ("ị ọ ụ are dotted —", 10.6, 13.0, 74),
    ("they are different letters", 13.4, 15.8, 74),
    ("Learn the alphabet free — link in bio", 16.6, 20.4, 56),
  ]},
 {"id":"v05-dotted-i","bg":"bg-05.jpg","dur":23,
  "kicker":"T H E   D O T T E D   L E T T E R S   ·   1   O F   4",
  "captions":[
    ("ị", 0.5, 3.0, 220),
    ("a tight “ih” sound", 3.6, 6.0, 72),
    ("ị — you", 6.8, 9.2, 104),
    ("ahịa — market", 9.8, 12.2, 96),
    ("nwaanyị — woman", 12.8, 15.2, 96),
    ("The dot is not decoration.", 16.0, 19.2, 62),
    ("Link in bio", 19.8, 22.4, 56),
  ]},
 {"id":"v06-dotted-o","bg":"bg-06.jpg","dur":23,
  "kicker":"T H E   D O T T E D   L E T T E R S   ·   2   O F   4",
  "captions":[
    ("ọ", 0.5, 3.0, 220),
    ("the “aw” of saw", 3.6, 6.0, 72),
    ("ọkụ — fire", 6.8, 9.2, 104),
    ("ọjị — kola nut", 9.8, 12.2, 96),
    ("ọrụ — work", 12.8, 15.2, 96),
    ("Different letter. Different sound.", 16.0, 19.2, 62),
    ("Link in bio", 19.8, 22.4, 56),
  ]},
 {"id":"v07-dotted-u","bg":"bg-07.jpg","dur":23,
  "kicker":"T H E   D O T T E D   L E T T E R S   ·   3   O F   4",
  "captions":[
    ("ụ", 0.5, 3.0, 220),
    ("the “oo” of book", 3.6, 6.0, 72),
    ("ụlọ — house", 6.8, 9.2, 104),
    ("ụzọ — road", 9.8, 12.2, 96),
    ("ụra — sleep", 12.8, 15.2, 96),
    ("Read it right. Say it right.", 16.0, 19.2, 62),
    ("Link in bio", 19.8, 22.4, 56),
  ]},
 {"id":"v08-dotted-ng","bg":"bg-08.jpg","dur":23,
  "kicker":"T H E   D O T T E D   L E T T E R S   ·   4   O F   4",
  "captions":[
    ("ṅ", 0.5, 3.0, 220),
    ("the “ng” that starts a syllable", 3.6, 6.2, 64),
    ("ṅụ — to drink", 6.9, 9.3, 104),
    ("ṅụọ — drink!", 9.9, 12.3, 104),
    ("aṅụ — we drink", 12.9, 15.3, 96),
    ("Four dotted letters. Now you know them all.", 16.1, 19.3, 58),
    ("Link in bio", 19.9, 22.5, 56),
  ]},
 {"id":"v09-digraphs","bg":"bg-09.jpg","dur":25,
  "kicker":"I G B O   M A S T E R Y   ·   D I G R A P H S",
  "captions":[
    ("Nine two-letter sounds", 0.5, 3.0, 78),
    ("ch   gb   gh", 3.6, 6.0, 96),
    ("gw   kp   kw", 6.6, 9.0, 96),
    ("nw   ny   sh", 9.6, 12.0, 96),
    ("Two letters. One sound.", 12.8, 15.8, 74),
    ("gb · as in agba — jaw", 16.6, 19.4, 62),
    ("Full alphabet free — link in bio", 20.2, 24.2, 56),
  ]},
 {"id":"v10-greetings","bg":"bg-10.jpg","dur":26,
  "kicker":"S U R V I V A L   I G B O   ·   G R E E T I N G S",
  "captions":[
    ("Greet someone in Igbo today", 0.5, 3.2, 72),
    ("Ndeewo!", 3.8, 6.2, 128),
    ("Hello / Welcome", 6.8, 9.0, 76),
    ("Kedu ka ị mere?", 9.8, 12.6, 92),
    ("How are you?", 13.2, 15.4, 76),
    ("Ọ dị mma, daalụ.", 16.2, 19.0, 92),
    ("I'm fine, thank you.", 19.6, 21.8, 76),
    ("More phrases — link in bio", 22.6, 25.4, 56),
  ]},
 {"id":"v11-numbers","bg":"bg-11.jpg","dur":26,
  "kicker":"S U R V I V A L   I G B O   ·   N U M B E R S",
  "captions":[
    ("Count in Igbo", 0.5, 2.8, 84),
    ("otu — 1", 3.4, 5.4, 104),
    ("abụọ — 2", 5.9, 7.9, 104),
    ("atọ — 3", 8.4, 10.4, 104),
    ("anọ — 4", 10.9, 12.9, 104),
    ("ise — 5", 13.4, 15.4, 104),
    ("iri — 10", 16.2, 18.6, 104),
    ("Numbers & money — link in bio", 19.6, 23.4, 56),
  ]},
 {"id":"v12-family","bg":"bg-12.jpg","dur":26,
  "kicker":"S U R V I V A L   I G B O   ·   F A M I L Y",
  "captions":[
    ("The first words children learn", 0.5, 3.2, 68),
    ("nne — mother", 3.8, 6.2, 108),
    ("nna — father", 6.8, 9.2, 108),
    ("nwanne — sibling", 9.8, 12.2, 100),
    ("ụmụ — children", 12.8, 15.2, 100),
    ("Start at home. Two words this week.", 16.0, 19.4, 60),
    ("Link in bio", 20.2, 23.2, 56),
  ]},
 {"id":"v13-food","bg":"bg-13.jpg","dur":25,
  "kicker":"S U R V I V A L   I G B O   ·   F O O D",
  "captions":[
    ("At the Igbo table", 0.5, 2.8, 80),
    ("nri — food", 3.4, 5.8, 108),
    ("ofe — soup", 6.4, 8.8, 108),
    ("ji — yam", 9.4, 11.8, 108),
    ("mmiri — water", 12.4, 14.8, 108),
    ("Achọrọ m nri — I want food", 15.6, 18.8, 68),
    ("Link in bio", 19.6, 22.6, 56),
  ]},
 {"id":"v14-market","bg":"bg-14.jpg","dur":26,
  "kicker":"S U R V I V A L   I G B O   ·   T H E   M A R K E T",
  "captions":[
    ("Market day in Igbo", 0.5, 2.8, 80),
    ("ahịa — market", 3.4, 5.8, 104),
    ("Ego ole? — How much?", 6.6, 9.6, 84),
    ("Ọ dị ọnụ — it's expensive", 10.4, 13.4, 80),
    ("A ga-ewere ya — I'll take it", 14.2, 17.2, 76),
    ("Daalụ — thank you", 18.0, 20.6, 96),
    ("Link in bio", 21.4, 24.4, 56),
  ]},
 {"id":"v15-daily-life","bg":"bg-15.jpg","dur":25,
  "kicker":"S U R V I V A L   I G B O   ·   D A I L Y   L I F E",
  "captions":[
    ("Find your way", 0.5, 2.6, 84),
    ("Ebee ka ị na-aga?", 3.2, 6.2, 88),
    ("Where are you going?", 6.8, 9.2, 76),
    ("Ana m aga ahịa.", 10.0, 12.8, 92),
    ("I am going to the market.", 13.4, 15.8, 76),
    ("ụlọ — house", 16.6, 19.0, 104),
    ("Link in bio", 19.8, 22.8, 56),
  ]},
 {"id":"v16-proverb-unity","bg":"bg-16.jpg","dur":24,
  "kicker":"I G B O   P R O V E R B S   ·   I L U",
  "captions":[
    ("A proverb for strength", 0.5, 2.8, 76),
    ("Gidi gidi bụ ugwu eze.", 3.5, 7.3, 78),
    ("Unity is strength.", 8.1, 10.7, 88),
    ("A people who stand together cannot be moved.", 11.5, 15.1, 58),
    ("12 proverbs in the Fluency Kit — link in bio", 15.9, 19.7, 54),
  ]},
 {"id":"v17-proverb-palmoil","bg":"bg-17.jpg","dur":24,
  "kicker":"I G B O   P R O V E R B S   ·   I L U",
  "captions":[
    ("The most famous Igbo proverb", 0.5, 3.0, 72),
    ("Ilu bụ mmanụ e ji eri okwu.", 3.7, 7.5, 70),
    ("Proverbs are the palm oil with which words are eaten.", 8.3, 12.1, 54),
    ("Proverbs make speech rich and wise.", 12.9, 15.9, 62),
    ("Link in bio", 16.7, 19.7, 56),
  ]},
 {"id":"v18-who-this-is-for","bg":"bg-18.jpg","dur":25,
  "kicker":"I G B O   M A S T E R Y",
  "captions":[
    ("Do you understand some Igbo,", 0.5, 3.0, 68),
    ("but can't speak it?", 3.5, 5.7, 68),
    ("You are not alone.", 6.5, 9.0, 76),
    ("Tones · alphabet · dotted letters", 9.8, 12.6, 64),
    ("greetings · numbers · family", 13.0, 15.8, 64),
    ("food · market · daily life", 16.2, 19.0, 64),
    ("Start free — link in bio", 19.8, 23.6, 56),
  ]},
 {"id":"v19-flashcards","bg":"bg-19.jpg","dur":24,
  "kicker":"I G B O   F L U E N C Y   K I T",
  "captions":[
    ("Remember more. Forget less.", 0.5, 3.0, 72),
    ("Spaced-repetition flashcards", 3.6, 6.6, 68),
    ("words you know come back later", 7.2, 10.0, 60),
    ("words you miss come back sooner", 10.6, 13.4, 60),
    ("Writing practice · dialogues · proverbs", 14.2, 17.4, 58),
    ("₦2,000 one time — link in bio", 18.2, 22.0, 54),
  ]},
 {"id":"v20-start-today","bg":"bg-20.jpg","dur":25,
  "kicker":"I G B O   M A S T E R Y",
  "captions":[
    ("Your grandmother's language", 0.5, 3.0, 72),
    ("is one decision away.", 3.5, 5.7, 72),
    ("Igbo is tonal.", 6.5, 8.9, 84),
    ("The alphabet is 36 letters.", 9.5, 12.3, 68),
    ("The dotted letters are ị ọ ụ ṅ.", 12.9, 15.7, 68),
    ("Start the free foundation today.", 16.5, 19.7, 62),
    ("Link in bio", 20.5, 23.5, 56),
  ]},
]

# ---------------------------------------------------------------- helpers
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

def prep_background(bg_path, out_path):
    """Resize to cover 1080x1920, darken, add gradient scrim."""
    im = Image.open(bg_path).convert("RGB")
    sw, sh = im.size
    scale = max(W / sw, H / sh)
    im = im.resize((int(sw * scale) + 1, int(sh * scale) + 1), Image.LANCZOS)
    sw, sh = im.size
    left, top = (sw - W) // 2, (sh - H) // 2
    im = im.crop((left, top, left + W, top + H))
    im = ImageEnhance.Brightness(im).enhance(0.92)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    # scrim overlay
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(scrim)
    for y in range(H):
        a_top = max(0, int(170 * (1 - y / 620)))          # top band for kicker
        a_bot = max(0, int(150 * ((y - 1150) / (H - 1150))))  # bottom band for handle
        a_mid = 60                                          # overall dim
        d.line([(0, y), (W, y)], fill=(4, 16, 12, a_top + a_bot + a_mid))
    im = Image.alpha_composite(im.convert("RGBA"), scrim).convert("RGB")
    im.save(out_path, quality=92)
    return out_path

def ass_color(hexstr):
    """#RRGGBB -> ASS &HAABBGGRR"""
    r, g, b = hexstr[1:3], hexstr[3:5], hexstr[5:7]
    return f"&H00{b}{g}{r}"

def ts(seconds):
    cs = int(round(seconds * 100))
    return f"{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}"

def build_ass(video, path):
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 0",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101410,&H80000000,-1,0,0,0,100,100,0,0,1,3,3,5,20,20,20,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    WHITE_A = ass_color("#FFFFFF")
    GOLD_A = ass_color(GOLD)
    # kicker (top)
    lines.append(f"Dialogue: 0,{ts(0.4)},{ts(video['dur']-0.3)},Cap,,0,0,0,,"
                 f"{{\\pos(540,235)\\c{GOLD_A}\\fs34}} {video['kicker']}")
    # handle (bottom)
    lines.append(f"Dialogue: 0,{ts(0.4)},{ts(video['dur']-0.3)},Cap,,0,0,0,,"
                 f"{{\\pos(540,1800)\\c{WHITE_A}\\alpha&H40&\\fs32}} @igbo.mastery")
    font_cache = {}
    def measure(word, size):
        if size not in font_cache:
            font_cache[size] = ImageFont.truetype(FONT_BOLD, size)
        f = font_cache[size]
        return f.getbbox(word)[2] - f.getbbox(word)[0]

    for (text, start, end, size) in video["captions"]:
        words = text.split(" ")
        while size > 34:
            widths = [measure(w, size) for w in words]
            space_w = measure(" ", size)
            if sum(widths) + space_w * (len(words) - 1) <= 940:
                break
            size -= 4
        widths = [measure(w, size) for w in words]
        space_w = measure(" ", size)
        total = sum(widths) + space_w * (len(words) - 1)
        x = (W - total) / 2.0
        for wi, (w, ww) in enumerate(zip(words, widths)):
            if not w:
                continue
            color = GOLD_A if any(ch in TONE_CHARS for ch in w) else WHITE_A
            cx = x + ww / 2.0
            ws = start + wi * 0.16
            lines.append(
                f"Dialogue: 0,{ts(ws):s},{ts(end):s},Cap,,0,0,0,,"
                f"{{\\pos({cx:.0f},900)\\c{color}\\fs{size}\\fad(300,300)}} {w}")
            x += ww + space_w
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path

def build(video):
    vid = video["id"]
    bg_src = os.path.join(BG, video["bg"])
    if not os.path.exists(bg_src):
        print(f"SKIP {vid}: background {video['bg']} missing")
        return False
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    bg_png = os.path.join(TMP, f"{vid}-bg.png")
    prep_background(bg_src, bg_png)
    ass_file = os.path.join(TMP, f"{vid}.ass")
    build_ass(video, ass_file)
    dur = video["dur"]
    frames = dur * FPS
    fc = (f"[0:v]scale=2160:3840,zoompan=z='1+0.12*on/{frames-1}':"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bgz];"
          f"[bgz]subtitles='{ass_file}':fontsdir=/usr/share/fonts/truetype/dejavu[vout]")
    out_file = os.path.join(OUT, f"{vid}.mp4")
    cmd = [FFMPEG, "-y", "-loop", "1", "-t", str(dur), "-i", bg_png,
           "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-filter_complex", fc, "-map", "[vout]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
           "-t", str(dur), out_file]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL {vid}:\n{r.stderr[-1200:]}")
        return False
    print(f"OK   {vid}.mp4  ({os.path.getsize(out_file)//1024} KB)")
    return True

if __name__ == "__main__":
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    ok = fail = 0
    for v in VIDEOS:
        if only and v["id"] not in only:
            continue
        if build(v):
            ok += 1
        else:
            fail += 1
    print(f"\nbuilt={ok} failed={fail}")
