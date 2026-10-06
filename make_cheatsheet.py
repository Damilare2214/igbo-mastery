#!/usr/bin/env python3
"""Printable one-page Igbo starter cheat sheet: A4 PDF + shareable PNG."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont

BASE = "/home/user/igbo-mastery"
OUT = os.path.join(BASE, "marketing")
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

pdfmetrics.registerFont(TTFont("DVB", FONT_B))
pdfmetrics.registerFont(TTFont("DVR", FONT_R))

GREEN = (0.043, 0.431, 0.310)
GOLD = (0.91, 0.64, 0.24)
INK = (0.11, 0.17, 0.15)
MUTED = (0.36, 0.42, 0.40)

W, H = A4  # 595 x 842

def make_pdf(path):
    c = canvas.Canvas(path, pagesize=A4)
    # header band
    c.setFillColorRGB(*GREEN)
    c.rect(0, H - 86, W, 86, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("DVB", 21)
    c.drawString(40, H - 42, "IGBO MASTERY")
    c.setFont("DVR", 11.5)
    c.drawString(40, H - 62, "Igbo Starter Cheat Sheet  ·  tones · alphabet · first words")
    c.setFillColorRGB(*GOLD)
    c.setFont("DVB", 12)
    c.drawRightString(W - 40, H - 52, "igbomastery.com")

    colL, colR = 40, 320
    y = H - 118

    def section(x, y, title):
        c.setFillColorRGB(*GOLD)
        c.rect(x, y - 3, 235, 20, stroke=0, fill=1)
        c.setFillColorRGB(0.15, 0.12, 0.05)
        c.setFont("DVB", 11)
        c.drawString(x + 8, y + 2, title)
        return y - 24

    def rows(x, y, items, size=10.5, gap=17, bold_first=True):
        c.setFillColorRGB(*INK)
        for ig, en in items:
            c.setFont("DVB" if bold_first else "DVR", size)
            c.drawString(x + 4, y, ig)
            c.setFont("DVR", size - 0.5)
            c.setFillColorRGB(*MUTED)
            c.drawString(x + 118, y, en)
            c.setFillColorRGB(*INK)
            y -= gap
        return y

    # ---- left column: tones ----
    y = section(colL, y, "THE TONES — pitch is meaning")
    c.setFillColorRGB(*INK); c.setFont("DVR", 9.5)
    c.drawString(colL + 4, y, "Written without marks, akwa is one word.")
    y -= 15
    c.drawString(colL + 4, y, "Spoken four ways, it is four words:")
    y -= 22
    tones = [("ákwá", "cry"), ("àkwá", "egg"), ("ákwà", "cloth"), ("àkwà", "bed")]
    for ig, en in tones:
        c.setFillColorRGB(*GOLD); c.setFont("DVB", 15)
        c.drawString(colL + 10, y, ig)
        c.setFillColorRGB(*INK); c.setFont("DVR", 10.5)
        c.drawString(colL + 100, y + 1, "— " + en)
        y -= 21
    y -= 6
    c.setFillColorRGB(*MUTED); c.setFont("DVR", 9)
    c.drawString(colL + 4, y, "eze can mean king or teeth — tone decides.")
    y -= 30

    # ---- alphabet ----
    y = section(colL, y, "THE ALPHABET — 36 letters")
    c.setFillColorRGB(*INK); c.setFont("DVB", 12)
    c.drawString(colL + 4, y, "Vowels:  a  e  i  ị  o  ọ  u  ụ")
    y -= 20
    c.setFont("DVB", 11)
    c.drawString(colL + 4, y, "Digraphs:  ch  gb  gh  gw  kp  kw  nw  ny  sh")
    y -= 20
    c.setFont("DVR", 9)
    c.setFillColorRGB(*MUTED)
    c.drawString(colL + 4, y, "q and x are not used in standard Igbo.")
    y -= 30

    # ---- dotted letters ----
    y = section(colL, y, "THE DOTTED LETTERS — not decoration")
    dotted = [("ị", "tight “ih”"), ("ọ", "“aw” of saw"), ("ụ", "“oo” of book"), ("ṅ", "starting “ng”")]
    for letter, guide in dotted:
        c.setFillColorRGB(*GOLD); c.setFont("DVB", 17)
        c.drawString(colL + 10, y - 2, letter)
        c.setFillColorRGB(*INK); c.setFont("DVR", 10.5)
        c.drawString(colL + 60, y, guide)
        y -= 24
    y -= 10

    # ---- greetings ----
    y = section(colL, y, "GREETINGS")
    y = rows(colL, y, [
        ("Ndeewo!", "Hello / Welcome"),
        ("Kedu ka ị mere?", "How are you?"),
        ("Ọ dị mma.", "I'm fine."),
        ("Aha m bụ …", "My name is …"),
        ("Daalụ.", "Thank you."),
        ("Biko.", "Please."),
        ("Ka ọ dị.", "Goodbye."),
    ])

    # ---- right column: numbers ----
    y2 = H - 118
    y2 = section(colR, y2, "NUMBERS & MONEY")
    nums = [("otu", "1"), ("abụọ", "2"), ("atọ", "3"), ("anọ", "4"), ("ise", "5"),
            ("isii", "6"), ("asaa", "7"), ("asatọ", "8"), ("itoolu", "9"), ("iri", "10"),
            ("iri abụọ", "20"), ("otu narị", "100"), ("otu puku", "1,000")]
    c.setFillColorRGB(*INK)
    for i in range(0, len(nums), 2):
        pair = nums[i:i + 2]
        x = colR + 4
        for ig, en in pair:
            c.setFont("DVB", 10.5); c.drawString(x, y2, ig)
            c.setFont("DVR", 10); c.setFillColorRGB(*MUTED)
            c.drawString(x + 92, y2, "— " + en)
            c.setFillColorRGB(*INK)
            x += 118
        y2 -= 18
    y2 -= 6
    y2 = rows(colR, y2, [("Ego ole?", "How much?"), ("Ọ dị ọnụ.", "It's expensive.")], gap=16)
    y2 -= 16

    # ---- family ----
    y2 = section(colR, y2, "FAMILY & PEOPLE")
    y2 = rows(colR, y2, [
        ("nne", "mother"), ("nna", "father"), ("nwa", "child"),
        ("nwanne", "sibling"), ("nwoke", "man"), ("nwaanyị", "woman"),
        ("ụmụ", "children"), ("umunna", "kinsfolk"),
    ])
    y2 -= 12

    # ---- food & market ----
    y2 = section(colR, y2, "FOOD & MARKET")
    y2 = rows(colR, y2, [
        ("nri", "food"), ("ofe", "soup"), ("ji", "yam"),
        ("mmiri", "water"), ("ahịa", "market"), ("ego", "money"),
    ])
    y2 -= 12

    # ---- proverbs ----
    y2 = section(colR, y2, "PROVERBS (ILU)")
    prov = [("Gidi gidi bụ ugwu eze.", "Unity is strength."),
            ("Oge adịghị eche mmadụ.", "Time and tide wait for nobody."),
            ("Onye ajụghị ase,", "The person who asks questions"),
            ("anaghị efu ụzọ.", "does not lose the way.")]
    c.setFillColorRGB(*INK)
    for ig, en in prov:
        c.setFont("DVB", 9.8); c.drawString(colR + 4, y2, ig)
        c.setFont("DVR", 8.8); c.setFillColorRGB(*MUTED)
        c.drawString(colR + 4, y2 - 11, en)
        c.setFillColorRGB(*INK)
        y2 -= 25
    y2 -= 4

    # ---- daily life ----
    y2 = section(colR, y2, "DAILY LIFE")
    y2 = rows(colR, y2, [
        ("ụlọ", "house"), ("ụlọ akwụkwọ", "school"),
        ("Ebee ka ị na-aga?", "Where are you going?"),
        ("Ana m aga ahịa.", "I am going to the market."),
    ], gap=16)

    # footer
    c.setFillColorRGB(*GREEN)
    c.rect(0, 0, W, 46, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("DVB", 11)
    c.drawString(40, 26, "igbomastery.com")
    c.setFont("DVR", 9.5)
    c.drawString(40, 12, "Free foundation course: tones · alphabet · dotted letters · first words")
    c.setFillColorRGB(*GOLD)
    c.setFont("DVB", 11)
    c.drawRightString(W - 40, 19, "@igbo.mastery")
    c.showPage()
    c.save()
    print("PDF written:", path)

def make_png(path):
    """1080x1920 shareable version of the cheat sheet."""
    Wp, Hp = 1080, 1920
    im = Image.new("RGB", (Wp, Hp), (252, 251, 247))
    d = ImageDraw.Draw(im)
    fB = lambda s: ImageFont.truetype(FONT_B, s)
    fR = lambda s: ImageFont.truetype(FONT_R, s)
    d.rectangle([0, 0, Wp, 190], fill=(11, 110, 79))
    d.text((50, 48), "IGBO MASTERY", font=fB(58), fill=(255, 255, 255))
    d.text((50, 118), "Igbo Starter Cheat Sheet — save this", font=fR(34), fill=(223, 240, 232))
    d.text((50, 2050 - 120), "", font=fR(20), fill=(0, 0, 0))

    def sect(y, title):
        d.rectangle([50, y, 1030, y + 58], fill=(255, 209, 102))
        d.text((66, y + 10), title, font=fB(32), fill=(38, 31, 13))
        return y + 78

    def kv(y, pairs, size=30, gap=44, keyw=430):
        for ig, en in pairs:
            d.text((60, y), ig, font=fB(size), fill=(28, 43, 38))
            d.text((60 + keyw, y), en, font=fR(size - 2), fill=(91, 107, 102))
            y += gap
        return y

    y = 225
    y = sect(y, "THE TONES — pitch is meaning")
    d.text((60, y), "ákwá = cry · àkwá = egg · ákwà = cloth · àkwà = bed", font=fB(34), fill=(28, 43, 38))
    y += 52
    d.text((60, y), "eze = king or teeth — tone decides", font=fR(28), fill=(91, 107, 102))
    y += 66

    y = sect(y, "THE ALPHABET & DOTTED LETTERS")
    d.text((60, y), "Vowels: a e i ị o ọ u ụ", font=fB(34), fill=(28, 43, 38))
    y += 50
    d.text((60, y), "Digraphs: ch gb gh gw kp kw nw ny sh", font=fB(32), fill=(28, 43, 38))
    y += 50
    y = kv(y, [("ị — tight “ih”", "ahịa · nwaanyị"),
               ("ọ — “aw” of saw", "ọkụ · ọrụ"),
               ("ụ — “oo” of book", "ụlọ · ụzọ"),
               ("ṅ — starting “ng”", "ṅụ — to drink")], size=30, gap=46, keyw=430)
    y += 20

    y = sect(y, "GREETINGS & FIRST WORDS")
    y = kv(y, [("Ndeewo!", "Hello / Welcome"), ("Kedu ka ị mere?", "How are you?"),
               ("Ọ dị mma, daalụ.", "I'm fine, thank you"), ("Aha m bụ …", "My name is …"),
               ("Biko. · Ndo.", "Please. · Sorry."), ("Ka ọ dị.", "Goodbye.")], size=32, gap=52, keyw=470)
    y += 20

    y = sect(y, "NUMBERS · FAMILY · FOOD · MARKET")
    y = kv(y, [("otu abụọ atọ anọ ise", "1 2 3 4 5"), ("isii asaa asatọ itoolu iri", "6 7 8 9 10"),
               ("nne · nna · nwanne · ụmụ", "mother father sibling children"),
               ("nri · ofe · ji · mmiri", "food soup yam water"),
               ("ahịa · ego · Ego ole?", "market money how much?")], size=30, gap=50, keyw=560)
    y += 20

    y = sect(y, "PROVERBS (ILU)")
    d.text((60, y), "Gidi gidi bụ ugwu eze.", font=fB(34), fill=(11, 110, 79))
    d.text((640, y), "Unity is strength.", font=fR(30), fill=(91, 107, 102))
    y += 52
    d.text((60, y), "Ilu bụ mmanụ e ji eri okwu.", font=fB(34), fill=(11, 110, 79))
    d.text((640, y), "Proverbs are the palm oil", font=fR(28), fill=(91, 107, 102))
    y += 44
    d.text((640, y), "with which words are eaten.", font=fR(28), fill=(91, 107, 102))
    y += 70

    d.rectangle([0, Hp - 130, Wp, Hp], fill=(11, 110, 79))
    d.text((50, Hp - 108), "igbomastery.com", font=fB(44), fill=(255, 255, 255))
    d.text((50, Hp - 58), "Free foundation course — @igbo.mastery", font=fR(30), fill=(223, 240, 232))
    im.save(path)
    print("PNG written:", path)

if __name__ == "__main__":
    make_pdf(os.path.join(OUT, "CHEAT-SHEET.pdf"))
    make_png(os.path.join(OUT, "cheat-sheet-share.png"))
