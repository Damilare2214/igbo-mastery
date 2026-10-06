"""
Igbo Mastery - single-file Flask backend.
JWT auth, dual SQLite/Postgres drivers, Paystack payments (naira),
Brevo HTTPS-API email, course content, progress, SRS flashcards, certificate.
"""
import os
import re
import json
import time
import hmac
import hashlib
import secrets
import sqlite3
import datetime
from functools import wraps

import jwt as pyjwt
import requests
from flask import Flask, request, jsonify, send_from_directory, abort, g
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAVE_PG = True
except Exception:  # pragma: no cover
    HAVE_PG = False

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SQLITE_PATH = os.path.join(BASE_DIR, "igbo_mastery.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL) and DATABASE_URL.startswith("postgres")

JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY") or secrets.token_hex(32)
JWT_TTL_HOURS = int(os.environ.get("JWT_TTL_HOURS", "72"))

PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "").strip()
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "").strip()
PAYSTACK_BASE = "https://api.paystack.co"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Igbo Mastery").strip()

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*").strip()

# Naira prices in kobo (1 naira = 100 kobo)
TIERS = {
    "free": {"name": "Free Foundation", "amount": 0, "rank": 0},
    "survival": {"name": "Survival Igbo", "amount": 50000, "rank": 1},
    "fluency": {"name": "Igbo Fluency Kit", "amount": 200000, "rank": 2},
}
TIER_ORDER = ["free", "survival", "fluency"]

PASS_MARK = 70  # percent needed to pass a quiz

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# ----------------------------------------------------------------------------
# Database layer (SQLite dev / Postgres prod)
# ----------------------------------------------------------------------------

def _ph(sql):
    """Convert ? placeholders to %s for Postgres."""
    return sql.replace("?", "%s") if USE_PG else sql


def _connect():
    if USE_PG:
        if not HAVE_PG:
            raise RuntimeError("DATABASE_URL is set but psycopg2 is not installed.")
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_all(sql, params=()):
    conn = _connect()
    try:
        if USE_PG:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(_ph(sql), params)
                return [dict(r) for r in cur.fetchall()]
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_one(sql, params=()):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    conn = _connect()
    try:
        if USE_PG:
            with conn.cursor() as cur:
                cur.execute(_ph(sql), params)
            conn.commit()
        else:
            conn.execute(sql, params)
            conn.commit()
    finally:
        conn.close()


def init_db():
    if USE_PG:
        stmts = [
            """CREATE TABLE IF NOT EXISTS users(
                 id SERIAL PRIMARY KEY,
                 email TEXT UNIQUE NOT NULL,
                 name TEXT,
                 password_hash TEXT NOT NULL,
                 tier TEXT NOT NULL DEFAULT 'free',
                 created_at TEXT,
                 last_seen TEXT)""",
            """CREATE TABLE IF NOT EXISTS payments(
                 id SERIAL PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 reference TEXT UNIQUE NOT NULL,
                 tier TEXT NOT NULL,
                 amount INTEGER NOT NULL,
                 currency TEXT NOT NULL DEFAULT 'NGN',
                 status TEXT NOT NULL DEFAULT 'pending',
                 note TEXT,
                 raw TEXT,
                 created_at TEXT,
                 updated_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS progress(
                 id SERIAL PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 item_id TEXT NOT NULL,
                 item_type TEXT NOT NULL,
                 created_at TEXT,
                 UNIQUE(user_id, item_id))""",
            """CREATE TABLE IF NOT EXISTS flashcards(
                 id SERIAL PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 card_id TEXT NOT NULL,
                 box INTEGER NOT NULL DEFAULT 0,
                 due TEXT,
                 reviews INTEGER NOT NULL DEFAULT 0,
                 lapses INTEGER NOT NULL DEFAULT 0,
                 created_at TEXT,
                 UNIQUE(user_id, card_id))""",
            """CREATE TABLE IF NOT EXISTS quiz_results(
                 id SERIAL PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 quiz_id TEXT NOT NULL,
                 score INTEGER NOT NULL,
                 total INTEGER NOT NULL,
                 created_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS certificates(
                 id SERIAL PRIMARY KEY,
                 user_id INTEGER NOT NULL,
                 serial TEXT UNIQUE NOT NULL,
                 tier TEXT NOT NULL,
                 issued_at TEXT,
                 UNIQUE(user_id))""",
        ]
    else:
        stmts = [
            """CREATE TABLE IF NOT EXISTS users(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email TEXT UNIQUE NOT NULL,
                 name TEXT,
                 password_hash TEXT NOT NULL,
                 tier TEXT NOT NULL DEFAULT 'free',
                 created_at TEXT,
                 last_seen TEXT)""",
            """CREATE TABLE IF NOT EXISTS payments(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 reference TEXT UNIQUE NOT NULL,
                 tier TEXT NOT NULL,
                 amount INTEGER NOT NULL,
                 currency TEXT NOT NULL DEFAULT 'NGN',
                 status TEXT NOT NULL DEFAULT 'pending',
                 note TEXT,
                 raw TEXT,
                 created_at TEXT,
                 updated_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS progress(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 item_id TEXT NOT NULL,
                 item_type TEXT NOT NULL,
                 created_at TEXT,
                 UNIQUE(user_id, item_id))""",
            """CREATE TABLE IF NOT EXISTS flashcards(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 card_id TEXT NOT NULL,
                 box INTEGER NOT NULL DEFAULT 0,
                 due TEXT,
                 reviews INTEGER NOT NULL DEFAULT 0,
                 lapses INTEGER NOT NULL DEFAULT 0,
                 created_at TEXT,
                 UNIQUE(user_id, card_id))""",
            """CREATE TABLE IF NOT EXISTS quiz_results(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 quiz_id TEXT NOT NULL,
                 score INTEGER NOT NULL,
                 total INTEGER NOT NULL,
                 created_at TEXT)""",
            """CREATE TABLE IF NOT EXISTS certificates(
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 serial TEXT UNIQUE NOT NULL,
                 tier TEXT NOT NULL,
                 issued_at TEXT,
                 UNIQUE(user_id))""",
        ]
    for s in stmts:
        execute(s)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------------------
# Email (Brevo HTTPS API - never SMTP: Render free tier blocks SMTP ports)
# ----------------------------------------------------------------------------

def send_email(to_email, to_name, subject, html):
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        app.logger.info("Brevo not configured; skipping email to %s", to_email)
        return False
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "content-type": "application/json",
                     "accept": "application/json"},
            json={
                "sender": {"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
                "to": [{"email": to_email, "name": to_name or to_email}],
                "subject": subject,
                "htmlContent": html,
            },
            timeout=20,
        )
        if r.status_code >= 300:
            app.logger.warning("Brevo error %s: %s", r.status_code, r.text[:300])
            return False
        return True
    except Exception as e:  # never let email break a signup or payment
        app.logger.warning("Brevo send failed: %s", e)
        return False


def email_welcome(user):
    name = user.get("name") or "friend"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
      <h2 style="color:#0b6e4f">Ndeewo, {name}! Welcome to Igbo Mastery.</h2>
      <p>Your account is ready. Your free <strong>Igbo Foundation</strong> course is waiting:
      the tones, the alphabet, and the dotted letters ị ọ ụ ṅ.</p>
      <p>Start with Lesson 1, and finish with the quizzes. Every lesson you complete is saved
      automatically, so you can come back any time.</p>
      <p><a href="{FRONTEND_ORIGIN if FRONTEND_ORIGIN != '*' else '#'}/#/learn"
            style="background:#0b6e4f;color:#fff;padding:12px 22px;border-radius:8px;
                   text-decoration:none;display:inline-block">Start learning</a></p>
      <p style="color:#555;font-size:13px">If you ever want the full Fluency Kit,
      it is a one-time payment of ₦2,000. No subscription, no surprises.</p>
    </div>"""
    send_email(user["email"], name, "Your free Igbo Foundation is ready", html)


def email_receipt(user, tier_name, amount_naira, reference):
    name = user.get("name") or "friend"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
      <h2 style="color:#0b6e4f">Payment received — thank you, {name}!</h2>
      <p>Your <strong>{tier_name}</strong> access is now active on your account.</p>
      <table style="border-collapse:collapse;margin:16px 0">
        <tr><td style="padding:6px 14px;color:#555">Amount paid</td>
            <td style="padding:6px 14px"><strong>₦{amount_naira:,}</strong></td></tr>
        <tr><td style="padding:6px 14px;color:#555">Reference</td>
            <td style="padding:6px 14px">{reference}</td></tr>
      </table>
      <p><a href="{FRONTEND_ORIGIN if FRONTEND_ORIGIN != '*' else '#'}/#/learn"
            style="background:#0b6e4f;color:#fff;padding:12px 22px;border-radius:8px;
                   text-decoration:none;display:inline-block">Continue learning</a></p>
      <p style="color:#555;font-size:13px">Keep this email as your receipt.</p>
    </div>"""
    send_email(user["email"], name, f"Payment received — {tier_name}", html)


def email_certificate(user, serial):
    name = user.get("name") or "friend"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
      <h2 style="color:#0b6e4f">Congratulations, {name}!</h2>
      <p>You have completed every lesson and passed every quiz in the
      <strong>Igbo Fluency Kit</strong>. Your certificate is ready to download
      from your account page.</p>
      <p style="color:#555">Certificate number: {serial}</p>
    </div>"""
    send_email(user["email"], name, "Your Igbo Mastery certificate is ready", html)


# ----------------------------------------------------------------------------
# Auth helpers
# ----------------------------------------------------------------------------

def make_token(user_id):
    payload = {"sub": str(user_id), "iat": int(time.time()),
               "exp": int(time.time()) + JWT_TTL_HOURS * 3600}
    return pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")


def get_user_by_id(uid):
    return query_one("SELECT * FROM users WHERE id = ?", (uid,))


def get_user_by_email(email):
    return query_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))


def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Please sign in to continue."}), 401
        try:
            payload = pyjwt.decode(header[7:], JWT_SECRET, algorithms=["HS256"])
            uid = int(payload.get("sub"))
        except Exception:
            return jsonify({"error": "Your session has expired. Please sign in again."}), 401
        user = get_user_by_id(uid)
        if not user:
            return jsonify({"error": "We could not find your account. Please sign in again."}), 401
        g.user = user
        return f(*args, **kwargs)
    return wrapper


def tier_rank(tier):
    return TIERS.get(tier, {}).get("rank", 0)


def public_user(user):
    return {"id": user["id"], "email": user["email"], "name": user["name"],
            "tier": user["tier"], "tier_name": TIERS.get(user["tier"], TIERS["free"])["name"]}


# ----------------------------------------------------------------------------
# Course content (real, verified Igbo)
# ----------------------------------------------------------------------------
# Tone convention in this course: acute = high tone, grave = low tone.
# Everyday Igbo writing usually omits tone marks; we show them where they
# carry meaning, and every example here has been checked against standard
# references (Igbo-English dictionary tradition, Wikipedia's Igbo phonology
# notes, and Wiktionary headwords).

DOTTED_LETTERS = [
    {"letter": "ị", "guide": "a tight 'i' — the 'i' of 'sit' said with the tongue pulled back",
     "words": [{"word": "ị", "meaning": "you"}, {"word": "ahịa", "meaning": "market"},
               {"word": "nwaanyị", "meaning": "woman"}]},
    {"letter": "ọ", "guide": "the 'aw' of 'saw' — mouth more open than English 'o'",
     "words": [{"word": "ọkụ", "meaning": "fire"}, {"word": "ọjị", "meaning": "kola nut"},
               {"word": "ọrụ", "meaning": "work"}]},
    {"letter": "ụ", "guide": "the 'oo' of 'book' — shorter than English 'oo'",
     "words": [{"word": "ụlọ", "meaning": "house"}, {"word": "ụzọ", "meaning": "road"},
               {"word": "ụra", "meaning": "sleep"}]},
    {"letter": "ṅ", "guide": "an 'ng' sound that starts a syllable, as in 'singing'",
     "words": [{"word": "ṅụ", "meaning": "to drink"}, {"word": "ṅụọ", "meaning": "drink (command)"},
               {"word": "aṅụ", "meaning": "we drink"}]},
]

TONE_QUARTET = [
    {"word": "ákwá", "pattern": "high + high", "meaning": "cry / crying"},
    {"word": "àkwá", "pattern": "low + high", "meaning": "egg"},
    {"word": "ákwà", "pattern": "high + low", "meaning": "cloth"},
    {"word": "àkwà", "pattern": "low + low", "meaning": "bed"},
]

TONE_EXAMPLES = [
    {"word": "eze", "note": "Written the same, said differently: it can mean 'king' or 'teeth'. Only tone tells them apart."},
    {"word": "ọ́kụ́", "meaning": "fire", "pattern": "high + high"},
    {"word": "ḿmírí", "meaning": "water", "pattern": "high + high"},
]

LESSONS = [
    # ---------------- FREE FOUNDATION ----------------
    {
        "id": "igbo-at-a-glance", "tier": "free", "title": "What Igbo is — and why it sounds like music",
        "minutes": 4,
        "blocks": [
            {"type": "p", "text": "Igbo (Asụsụ Igbo) is the language of the Igbo people of south-eastern Nigeria. More than 30 million people speak it — in Nigeria, and across the diaspora in the United Kingdom, the United States, Canada and beyond."},
            {"type": "p", "text": "It is one of Nigeria's three largest languages, alongside Yoruba and Hausa — and it is the language of Chinua Achebe's world, of Nollywood, and of a proverb tradition thousands of years old."},
            {"type": "callout", "title": "The one thing to know first",
             "text": "Igbo is a tonal language. The pitch of your voice is part of the word, exactly the same idea as Mandarin's four tones. Change the tone, and you change the meaning."},
            {"type": "p", "text": "Igbo has been classified by UNESCO as endangered, because many Igbo families — especially abroad — now speak English at home. If you are learning Igbo, you are doing something rare and valuable: you are carrying the language forward."},
            {"type": "p", "text": "In this free foundation you will learn the three tones, the 36-letter alphabet, the four dotted letters ị ọ ụ ṅ, and your first real words. No account tricks, no upsell walls — the foundation is genuinely free."},
        ],
    },
    {
        "id": "the-alphabet", "tier": "free", "title": "The Igbo alphabet — 36 letters",
        "minutes": 6,
        "blocks": [
            {"type": "p", "text": "The Igbo alphabet (Mkpụrụ edemede Igbo) has 36 letters: eight vowels and twenty-eight consonants. It uses the same Latin letters you already know, plus a few letters with dots underneath, and nine two-letter combinations called digraphs."},
            {"type": "h3", "text": "The eight vowels"},
            {"type": "letters", "items": [
                {"letter": "a", "guide": "ah, as in father"},
                {"letter": "e", "guide": "eh, as in wet"},
                {"letter": "i", "guide": "ih, as in sit"},
                {"letter": "ị", "guide": "a tighter 'ih'"},
                {"letter": "o", "guide": "oh, short"},
                {"letter": "ọ", "guide": "aw, as in saw"},
                {"letter": "u", "guide": "uh, as in put"},
                {"letter": "ụ", "guide": "oo, as in book"},
            ]},
            {"type": "p", "text": "The letters q and x are not used in standard Igbo spelling."},
            {"type": "h3", "text": "The nine digraphs — two letters, one sound"},
            {"type": "digraphs", "items": [
                {"letters": "ch", "guide": "like 'ch' in church", "example": "achicha — bread"},
                {"letters": "gb", "guide": "'gb' said as one sound", "example": "agba — jaw/chin"},
                {"letters": "gh", "guide": "a breathy 'gh'", "example": "agha — war"},
                {"letters": "gw", "guide": "'gw' as one sound", "example": "gwa — tell"},
                {"letters": "kp", "guide": "'kp' as one sound", "example": "kpọọ — call"},
                {"letters": "kw", "guide": "'kw' as one sound", "example": "kwe — agree"},
                {"letters": "nw", "guide": "'nw' as one sound", "example": "nwoke — man"},
                {"letters": "ny", "guide": "like 'ny' in canyon", "example": "anya — eye"},
                {"letters": "sh", "guide": "like 'sh' in ship", "example": "oshị — pepper? no: see note"},
            ]},
            {"type": "callout", "title": "A note on 'sh'",
             "text": "'Sh' appears in some Igbo names and loanwords (for example Shasha, a place name). In the standard Ọnwụ spelling, 's' before 'i' already carries that sound — but you will still meet 'sh' in modern writing."},
        ],
    },
    {
        "id": "dotted-letters", "tier": "free", "title": "The dotted letters: ị ọ ụ ṅ",
        "minutes": 6,
        "blocks": [
            {"type": "p", "text": "Four Igbo letters carry a dot underneath (kpom). The dot is not decoration and it is not optional: ị and i are different letters with different sounds, just as Mandarin's b and p are different letters."},
            {"type": "dotted", "items": DOTTED_LETTERS},
            {"type": "callout", "title": "Why this matters",
             "text": "Igbo vowel pairs like i/ị, o/ọ and u/ụ change the meaning of words. If you skip the dots when you read Igbo, you will mispronounce words even when you spell them right."},
            {"type": "p", "text": "When you type Igbo, make sure your keyboard or our on-screen letter pad produces the dotted letters — every exercise in this course accepts both the dotted and undotted spelling, but your goal is the dotted one."},
        ],
    },
    {
        "id": "igbo-tones", "tier": "free", "title": "Igbo tones — where meaning lives",
        "minutes": 8,
        "blocks": [
            {"type": "p", "text": "Igbo has three tones: high, low, and a downstep (a high tone that drops mid-word). For everyday speaking, high and low do most of the work — and this lesson teaches you to hear the difference."},
            {"type": "p", "text": "The famous demonstration is the word akwa. Written without tone marks it is one word. Said four different ways, it is four different words:"},
            {"type": "tones", "items": TONE_QUARTET},
            {"type": "callout", "title": "Same letters. Different tone. Different word.",
             "text": "ákwá is crying. àkwá is an egg. ákwà is cloth. àkwà is a bed. In Mandarin you would learn four tones — in Igbo, these two (high and low) already multiply every word."},
            {"type": "h3", "text": "More tone pairs you will meet"},
            {"type": "table", "head": ["Word", "Tone pattern", "Meaning"],
             "rows": [["ọ́kụ́", "high + high", "fire"], ["ḿmírí", "high + high", "water"],
                      ["eze", "(tone alone decides)", "king — or teeth"]]},
            {"type": "p", "text": "In everyday writing, Igbo people rarely write the tone marks — context does the job. But as a learner you should train your ear now: later lessons will speak Igbo at natural speed, and tone is what separates a word from its neighbour."},
        ],
    },
    {
        "id": "vowel-harmony", "tier": "free", "title": "Vowel harmony — why Igbo words 'match'",
        "minutes": 4,
        "blocks": [
            {"type": "p", "text": "Igbo vowels come in two sets that prefer not to mix inside a word:"},
            {"type": "table", "head": ["Set", "Vowels"],
             "rows": [["Light set", "i · e · u · o"], ["Heavy set", "ị · a · ọ · ụ"]]},
            {"type": "p", "text": "Most Igbo words keep to one set: ụlọ (house) is heavy, ofe (soup) is light. The rule matters most for prefixes and suffixes — small grammatical pieces change their vowel to match the word they attach to."},
            {"type": "callout", "title": "You do not need to memorise this yet",
             "text": "Vowel harmony explains why Igbo words sound so even and musical. You will absorb it naturally as you learn vocabulary — this lesson is here so nothing later surprises you."},
        ],
    },
    {
        "id": "first-words", "tier": "free", "title": "Your first Igbo words",
        "minutes": 5,
        "blocks": [
            {"type": "p", "text": "Here are thirteen words you can use today. Read them aloud slowly — remember, the dotted letters matter."},
            {"type": "words", "items": [
                {"word": "Ndeewo", "meaning": "Hello / welcome"},
                {"word": "Daalụ", "meaning": "Thank you"},
                {"word": "Biko", "meaning": "Please"},
                {"word": "Ndo", "meaning": "Sorry"},
                {"word": "Ee", "meaning": "Yes"},
                {"word": "Mba", "meaning": "No"},
                {"word": "mmiri", "meaning": "water"},
                {"word": "nri", "meaning": "food"},
                {"word": "ụlọ", "meaning": "house"},
                {"word": "ahịa", "meaning": "market"},
                {"word": "ego", "meaning": "money"},
                {"word": "nne", "meaning": "mother"},
                {"word": "nna", "meaning": "father"},
            ]},
            {"type": "callout", "title": "Next step",
             "text": "Take the two quizzes below to lock in the alphabet and the tones. Then, when you are ready to speak, Survival Igbo (₦500 one time) teaches greetings, numbers, family, food, the market and daily life."},
        ],
    },
    # ---------------- SURVIVAL IGBO ----------------
    {
        "id": "greetings", "tier": "survival", "title": "Greetings & introductions",
        "minutes": 8,
        "blocks": [
            {"type": "p", "text": "Igbo greetings are warm and unhurried. Learn these and you can hold a first conversation today."},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["Ndeewo!", "Hello! / Welcome!"],
                      ["Kedu ka ị mere?", "How are you? (to one person)"],
                      ["Ọ dị mma.", "I'm fine. / It's good."],
                      ["Kedu aha gị?", "What is your name?"],
                      ["Aha m bụ ___.", "My name is ___."],
                      ["Daalụ.", "Thank you."],
                      ["Ọ dịghị ihe.", "You're welcome. / It's nothing."],
                      ["Biko.", "Please."],
                      ["Ndo.", "Sorry."],
                      ["Ka ọ dị.", "Goodbye. (lit. 'let it be')"]]},
            {"type": "callout", "title": "Say it the Igbo way",
             "text": "A full greeting is a small ritual: 'Ndeewo!' — 'Kedu ka ị mere?' — 'Ọ dị mma, daalụ.' Three lines, and you have greeted someone properly."},
        ],
    },
    {
        "id": "numbers", "tier": "survival", "title": "Numbers, time & money",
        "minutes": 8,
        "blocks": [
            {"type": "p", "text": "Igbo counts in tens. Once you know one to ten, everything else is built from them."},
            {"type": "table", "head": ["Number", "Igbo", "Number", "Igbo"],
             "rows": [["1", "otu", "11", "iri na otu"], ["2", "abụọ", "12", "iri na abụọ"],
                      ["3", "atọ", "13", "iri na atọ"], ["4", "anọ", "14", "iri na anọ"],
                      ["5", "ise", "15", "iri na ise"], ["6", "isii", "16", "iri na isii"],
                      ["7", "asaa", "17", "iri na asaa"], ["8", "asatọ", "18", "iri na asatọ"],
                      ["9", "itoolu", "19", "iri na itoolu"], ["10", "iri", "20", "iri abụọ"]]},
            {"type": "p", "text": "Bigger numbers: 30 = iri atọ, 100 = otu narị, 1,000 = otu puku."},
            {"type": "h3", "text": "Money talk"},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["ego", "money"], ["Ego ole?", "How much?"],
                      ["ọnụ ahịa", "price"], ["Ọ dị ọnụ.", "It's expensive. (lit. 'it has a mouth')"]]},
        ],
    },
    {
        "id": "family", "tier": "survival", "title": "Family & people",
        "minutes": 7,
        "blocks": [
            {"type": "p", "text": "Family is the heart of Igbo life, and the vocabulary is the fastest way into it."},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["nne", "mother"], ["nna", "father"], ["nwa", "child"],
                      ["nwanne", "sibling / brother / sister"], ["nwoke", "man"],
                      ["nwaanyị", "woman"], ["di", "husband"], ["nwunye", "wife"],
                      ["nna ukwu", "grandfather / elder"], ["ụmụ", "children"],
                      ["umunna", "kinsfolk / extended family"], ["onye", "person"]]},
            {"type": "callout", "title": "Use it at home",
             "text": "Start with two words this week: nne for your mother, nna for your father. Children pick them up almost immediately — that is how a household starts speaking Igbo again."},
        ],
    },
    {
        "id": "food", "tier": "survival", "title": "Food & drink",
        "minutes": 7,
        "blocks": [
            {"type": "p", "text": "Food is a language of its own in Igbo culture. These words cover the table."},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["nri", "food"], ["ofe", "soup"], ["ji", "yam"],
                      ["ede", "cocoyam"], ["mmiri", "water"], ["mmanya", "drink"],
                      ["azụ", "fish"], ["anụ", "meat"], ["ọka", "corn / maize"],
                      ["akpụ", "palm fruit"]]},
            {"type": "h3", "text": "At the table"},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["Achọrọ m nri.", "I want food."],
                      ["Ṅụọ mmiri.", "Drink water."],
                      ["Nri a dị mma.", "This food is good."]]},
        ],
    },
    {
        "id": "market", "tier": "survival", "title": "The market — shopping & bargaining",
        "minutes": 8,
        "blocks": [
            {"type": "p", "text": "The market (ahịa) is where Igbo is spoken fastest and friendliest. Here is your toolkit."},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["ahịa", "market"], ["ego", "money"],
                      ["Ego ole ka ị na-ere ya?", "How much are you selling it for?"],
                      ["Ọ dị ọnụ.", "It's too expensive."],
                      ["Biko, belata ya.", "Please, bring it down."],
                      ["A ga-ewere ya.", "I'll take it."],
                      ["Daalụ.", "Thank you."]]},
            {"type": "callout", "title": "Market manners",
             "text": "Bargaining is expected, not rude — but always greet first, keep it light, and end with 'Daalụ'. A good market exchange is a small piece of theatre."},
        ],
    },
    {
        "id": "daily-life", "tier": "survival", "title": "Daily life & getting around",
        "minutes": 7,
        "blocks": [
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["ụlọ", "house / home"], ["ụlọ akwụkwọ", "school"],
                      ["ụlọ ọgwụ", "hospital"], ["ọrụ", "work"],
                      ["ụzọ", "road / street"], ["ụgbọ", "vehicle / car"],
                      ["ahịa", "market"]]},
            {"type": "h3", "text": "Asking your way"},
            {"type": "table", "head": ["Igbo", "English"],
             "rows": [["Ebee ka ị na-aga?", "Where are you going?"],
                      ["Ana m aga ahịa.", "I am going to the market."],
                      ["Ebee ka ị bi?", "Where do you live?"],
                      ["Achọrọ m ịga ụlọ m.", "I want to go home."]]},
            {"type": "callout", "title": "You now have survival Igbo",
             "text": "Greet, count, talk family, order food, bargain in the market, and find your way. That is a real, usable foundation — the Fluency Kit turns it into fluency."},
        ],
    },
]

QUIZZES = [
    {"id": "quiz-foundation-alphabet", "tier": "free", "title": "Quiz: alphabet & dotted letters",
     "lesson": "the-alphabet", "questions": [
        {"q": "How many letters are in the standard Igbo alphabet?",
         "options": ["24", "26", "36", "40"], "answer": 2,
         "explain": "The Ọnwụ alphabet has 36 letters: 8 vowels and 28 consonants."},
        {"q": "Which of these is NOT one of the four dotted Igbo letters?",
         "options": ["ị", "ọ", "ṅ", "à"], "answer": 3,
         "explain": "à is an 'a' with a tone mark (grave). The dotted letters are ị, ọ, ụ and ṅ."},
        {"q": "What does the dot under ị, ọ and ụ do?",
         "options": ["It shows the tone", "It marks a different vowel sound",
                     "It is only decoration", "It shows stress"], "answer": 1,
         "explain": "The dot marks a different vowel quality — ị and i are separate letters, like different letters in Mandarin pinyin."},
        {"q": "Which pair is a digraph (two letters, one sound)?",
         "options": ["ka", "gb", "ma", "ta"], "answer": 1,
         "explain": "gb is one of the nine Igbo digraphs, pronounced as a single sound."},
        {"q": "Which two Latin letters are not used in standard Igbo?",
         "options": ["q and x", "j and v", "c and k", "b and p"], "answer": 0,
         "explain": "Standard Igbo spelling does not use q or x."},
     ]},
    {"id": "quiz-foundation-tones", "tier": "free", "title": "Quiz: Igbo tones",
     "lesson": "igbo-tones", "questions": [
        {"q": "What kind of language is Igbo?",
         "options": ["A tonal language", "A click language",
                     "A sign language", "A language with no tones"], "answer": 0,
         "explain": "Igbo is tonal: pitch is part of the word, like Mandarin."},
        {"q": "ákwá (high-high) means…",
         "options": ["egg", "cloth", "bed", "cry"], "answer": 3,
         "explain": "ákwá with high tone on both syllables means 'cry'. àkwá is 'egg', ákwà is 'cloth', àkwà is 'bed'."},
        {"q": "àkwá (low-high) means…",
         "options": ["egg", "cloth", "bed", "cry"], "answer": 0,
         "explain": "àkwá, with a low first tone and high second tone, means 'egg'."},
        {"q": "In everyday writing, Igbo people usually…",
         "options": ["Write every tone mark", "Leave tone marks out — context does the work",
                     "Use numbers for tones", "Write in capitals only"], "answer": 1,
         "explain": "Tone marks are usually omitted in everyday Igbo writing; readers rely on context."},
        {"q": "The word 'eze' shows that tone can separate…",
         "options": ["two spellings", "two completely different meanings",
                     "two dialects", "two tenses"], "answer": 1,
         "explain": "eze can mean 'king' or 'teeth' — only the tone tells them apart."},
     ]},
    {"id": "quiz-greetings", "tier": "survival", "title": "Quiz: greetings & introductions",
     "lesson": "greetings", "questions": [
        {"q": "How do you say 'Hello / Welcome' in Igbo?",
         "options": ["Daalụ", "Ndeewo", "Ndo", "Biko"], "answer": 1,
         "explain": "Ndeewo is the standard greeting. Daalụ is 'thank you'."},
        {"q": "'Kedu ka ị mere?' means…",
         "options": ["What is your name?", "How are you?",
                     "Where are you going?", "How much is it?"], "answer": 1,
         "explain": "It is the everyday 'How are you?'"},
        {"q": "The correct reply to 'Kedu ka ị mere?' is…",
         "options": ["Aha m bụ Chidi", "Ọ dị mma", "Ego ole",
                     "Ka ọ dị"], "answer": 1,
         "explain": "Ọ dị mma — 'it is good / I'm fine'."},
        {"q": "What does 'Aha m bụ ___' mean?",
         "options": ["I am from ___", "My name is ___",
                     "I want ___", "I have ___"], "answer": 1,
         "explain": "Aha m bụ = 'my name is'."},
        {"q": "Which word means 'Sorry'?",
         "options": ["Ndo", "Ee", "Mba", "Ndeewo"], "answer": 0,
         "explain": "Ndo is 'sorry'. Ee = yes, Mba = no."},
     ]},
    {"id": "quiz-numbers", "tier": "survival", "title": "Quiz: numbers & money",
     "lesson": "numbers", "questions": [
        {"q": "What is 'two' in Igbo?",
         "options": ["otu", "abụọ", "atọ", "anọ"], "answer": 1,
         "explain": "otu = 1, abụọ = 2, atọ = 3, anọ = 4."},
        {"q": "How do you say 20?",
         "options": ["iri", "iri abụọ", "iri na otu", "otu narị"], "answer": 1,
         "explain": "Igbo counts in tens: iri = 10, iri abụọ = 20."},
        {"q": "What is 100?",
         "options": ["otu puku", "otu narị", "iri narị", "narị iri"], "answer": 1,
         "explain": "otu narị = 100. otu puku = 1,000."},
        {"q": "'Ego ole?' means…",
         "options": ["How much?", "Thank you", "Very good",
                     "Where is it?"], "answer": 0,
         "explain": "Ego = money, ole = how much. 'Ego ole?' = 'How much?'"},
        {"q": "'Ọ dị ọnụ' literally means 'it has a mouth' — but it is used to say…",
         "options": ["It's delicious", "It's expensive", "It's far",
                     "It's finished"], "answer": 1,
         "explain": "A colourful way to say something is too expensive."},
     ]},
    {"id": "quiz-family", "tier": "survival", "title": "Quiz: family & people",
     "lesson": "family", "questions": [
        {"q": "What does 'nne' mean?",
         "options": ["father", "mother", "child", "house"], "answer": 1,
         "explain": "nne = mother; nna = father."},
        {"q": "'nwanne' means…",
         "options": ["elder", "sibling", "friend", "guest"], "answer": 1,
         "explain": "nwanne = brother or sister."},
        {"q": "Which word means 'woman'?",
         "options": ["nwoke", "nwaanyị", "nwunye", "nwa"], "answer": 1,
         "explain": "nwoke = man, nwaanyị = woman, nwunye = wife."},
        {"q": "'ụmụ' means…",
         "options": ["parents", "children", "family home", "elders"], "answer": 1,
         "explain": "ụmụ = children (plural)."},
        {"q": "'umunna' refers to…",
         "options": ["the market", "kinsfolk / extended family",
                     "a village square", "food"], "answer": 1,
         "explain": "umunna is the extended kinship network — central to Igbo life."},
     ]},
    {"id": "quiz-food", "tier": "survival", "title": "Quiz: food & drink",
     "lesson": "food", "questions": [
        {"q": "What is 'soup' in Igbo?",
         "options": ["nri", "ofe", "ji", "ede"], "answer": 1,
         "explain": "ofe = soup; nri = food in general."},
        {"q": "'ji' is…",
         "options": ["water", "yam", "fish", "meat"], "answer": 1,
         "explain": "ji = yam, the most famous Igbo crop."},
        {"q": "What does 'mmiri' mean?",
         "options": ["fire", "water", "milk", "salt"], "answer": 1,
         "explain": "mmiri = water (also river, rain, juice)."},
        {"q": "'Achọrọ m nri' means…",
         "options": ["I cooked food", "I want food",
                     "The food is good", "Where is food?"], "answer": 1,
         "explain": "Achọrọ m = 'I want'."},
        {"q": "Which of these is a drink?",
         "options": ["anụ", "azụ", "mmanya", "ọka"], "answer": 2,
         "explain": "mmanya = drink. anụ = meat, azụ = fish, ọka = corn."},
     ]},
    {"id": "quiz-market", "tier": "survival", "title": "Quiz: market & bargaining",
     "lesson": "market", "questions": [
        {"q": "'ahịa' means…",
         "options": ["money", "market", "food", "road"], "answer": 1,
         "explain": "ahịa = market."},
        {"q": "How do you ask 'How much are you selling it for?'",
         "options": ["Ego ole ka ị na-ere ya?", "Ebee ka ị bi?",
                     "Kedu aha gị?", "Ana m aga ahịa."], "answer": 0,
         "explain": "The full, polite market question."},
        {"q": "To say 'I'll take it' you say…",
         "options": ["A ga-ewere ya", "Ọ dị ọnụ", "Biko",
                     "Daalụ"], "answer": 0,
         "explain": "ewere = to take."},
        {"q": "In Igbo market culture, bargaining is…",
         "options": ["rude and unusual", "expected and friendly",
                     "only for friends", "illegal"], "answer": 1,
         "explain": "It is a friendly ritual — greet, banter, agree, thank."},
        {"q": "'Biko, belata ya' means…",
         "options": ["Please bring it down (the price)", "Please wrap it",
                     "I don't want it", "Where is it?"], "answer": 0,
         "explain": "belata = to reduce."},
     ]},
    {"id": "quiz-daily-life", "tier": "survival", "title": "Quiz: daily life & getting around",
     "lesson": "daily-life", "questions": [
        {"q": "'ụlọ' means…",
         "options": ["road", "house", "market", "car"], "answer": 1,
         "explain": "ụlọ = house/home."},
        {"q": "'ụlọ ọgwụ' is…",
         "options": ["school", "hospital", "church", "office"], "answer": 1,
         "explain": "ọgwụ = medicine; ụlọ ọgwụ = hospital."},
        {"q": "'Ebee ka ị na-aga?' means…",
         "options": ["Where do you live?", "Where are you going?",
                     "Who are you?", "What do you want?"], "answer": 1,
         "explain": "aga = to go."},
        {"q": "'Ana m aga ahịa' means…",
         "options": ["I live in the market", "I am going to the market",
                     "I sell in the market", "I left the market"], "answer": 1,
         "explain": "ana m aga = 'I am going'."},
        {"q": "Which word means 'work'?",
         "options": ["ọrụ", "ụzọ", "ụgbọ", "ego"], "answer": 0,
         "explain": "ọrụ = work. ụzọ = road, ụgbọ = vehicle, ego = money."},
     ]},
]

FLASHCARDS = [
    # greetings
    {"id": "ndeewo", "front": "Ndeewo", "back": "Hello / Welcome", "group": "Greetings"},
    {"id": "kedu", "front": "Kedu ka ị mere?", "back": "How are you?", "group": "Greetings"},
    {"id": "odimma", "front": "Ọ dị mma", "back": "I'm fine / It's good", "group": "Greetings"},
    {"id": "aha", "front": "Aha m bụ…", "back": "My name is…", "group": "Greetings"},
    {"id": "daalu", "front": "Daalụ", "back": "Thank you", "group": "Greetings"},
    {"id": "biko", "front": "Biko", "back": "Please", "group": "Greetings"},
    {"id": "ndo", "front": "Ndo", "back": "Sorry", "group": "Greetings"},
    {"id": "kadị", "front": "Ka ọ dị", "back": "Goodbye", "group": "Greetings"},
    {"id": "ee", "front": "Ee", "back": "Yes", "group": "Greetings"},
    {"id": "mba", "front": "Mba", "back": "No", "group": "Greetings"},
    # numbers
    {"id": "otu", "front": "otu", "back": "one (1)", "group": "Numbers"},
    {"id": "abuo", "front": "abụọ", "back": "two (2)", "group": "Numbers"},
    {"id": "ato", "front": "atọ", "back": "three (3)", "group": "Numbers"},
    {"id": "ano", "front": "anọ", "back": "four (4)", "group": "Numbers"},
    {"id": "ise", "front": "ise", "back": "five (5)", "group": "Numbers"},
    {"id": "isii", "front": "isii", "back": "six (6)", "group": "Numbers"},
    {"id": "asaa", "front": "asaa", "back": "seven (7)", "group": "Numbers"},
    {"id": "asato", "front": "asatọ", "back": "eight (8)", "group": "Numbers"},
    {"id": "itoolu", "front": "itoolu", "back": "nine (9)", "group": "Numbers"},
    {"id": "iri", "front": "iri", "back": "ten (10)", "group": "Numbers"},
    {"id": "nari", "front": "otu narị", "back": "one hundred (100)", "group": "Numbers"},
    {"id": "puku", "front": "otu puku", "back": "one thousand (1,000)", "group": "Numbers"},
    # family
    {"id": "nne", "front": "nne", "back": "mother", "group": "Family"},
    {"id": "nna", "front": "nna", "back": "father", "group": "Family"},
    {"id": "nwa", "front": "nwa", "back": "child", "group": "Family"},
    {"id": "nwanne", "front": "nwanne", "back": "sibling (brother/sister)", "group": "Family"},
    {"id": "nwoke", "front": "nwoke", "back": "man", "group": "Family"},
    {"id": "nwaanyi", "front": "nwaanyị", "back": "woman", "group": "Family"},
    {"id": "di", "front": "di", "back": "husband", "group": "Family"},
    {"id": "nwunye", "front": "nwunye", "back": "wife", "group": "Family"},
    {"id": "umunna", "front": "umunna", "back": "kinsfolk / extended family", "group": "Family"},
    {"id": "umụ", "front": "ụmụ", "back": "children", "group": "Family"},
    # food
    {"id": "nri", "front": "nri", "back": "food", "group": "Food"},
    {"id": "ofe", "front": "ofe", "back": "soup", "group": "Food"},
    {"id": "ji", "front": "ji", "back": "yam", "group": "Food"},
    {"id": "ede", "front": "ede", "back": "cocoyam", "group": "Food"},
    {"id": "mmiri", "front": "mmiri", "back": "water", "group": "Food"},
    {"id": "mmanya", "front": "mmanya", "back": "drink", "group": "Food"},
    {"id": "azu", "front": "azụ", "back": "fish", "group": "Food"},
    {"id": "anu", "front": "anụ", "back": "meat", "group": "Food"},
    {"id": "oka", "front": "ọka", "back": "corn / maize", "group": "Food"},
    {"id": "akpu", "front": "akpụ", "back": "palm fruit", "group": "Food"},
    # market
    {"id": "ahia", "front": "ahịa", "back": "market", "group": "Market"},
    {"id": "ego", "front": "ego", "back": "money", "group": "Market"},
    {"id": "onu-ahia", "front": "ọnụ ahịa", "back": "price", "group": "Market"},
    {"id": "ego-ole", "front": "Ego ole?", "back": "How much?", "group": "Market"},
    {"id": "o-di-onu", "front": "Ọ dị ọnụ", "back": "It's expensive", "group": "Market"},
    {"id": "ewere", "front": "A ga-ewere ya", "back": "I'll take it", "group": "Market"},
    # daily life
    {"id": "ulo", "front": "ụlọ", "back": "house / home", "group": "Daily life"},
    {"id": "ulo-akwukwo", "front": "ụlọ akwụkwọ", "back": "school", "group": "Daily life"},
    {"id": "ulo-ogwu", "front": "ụlọ ọgwụ", "back": "hospital", "group": "Daily life"},
    {"id": "oru", "front": "ọrụ", "back": "work", "group": "Daily life"},
    {"id": "uzo", "front": "ụzọ", "back": "road / street", "group": "Daily life"},
    {"id": "ugbo", "front": "ụgbọ", "back": "vehicle / car", "group": "Daily life"},
    {"id": "ebee", "front": "Ebee ka ị na-aga?", "back": "Where are you going?", "group": "Daily life"},
    {"id": "aga-ahia", "front": "Ana m aga ahịa", "back": "I am going to the market", "group": "Daily life"},
    {"id": "ebee-ibi", "front": "Ebee ka ị bi?", "back": "Where do you live?", "group": "Daily life"},
    # letters & sounds
    {"id": "kpom-ị", "front": "ị", "back": "dotted 'i' — tight 'ih' sound (in: ahịa, nwaanyị)", "group": "Letters"},
    {"id": "kpom-ọ", "front": "ọ", "back": "dotted 'o' — 'aw' sound (in: ọkụ, ọrụ)", "group": "Letters"},
    {"id": "kpom-ụ", "front": "ụ", "back": "dotted 'u' — short 'oo' sound (in: ụlọ, ụzọ)", "group": "Letters"},
    {"id": "kpom-ṅ", "front": "ṅ", "back": "syllabic 'ng' (in: ṅụ — to drink)", "group": "Letters"},
    {"id": "gb-digraph", "front": "gb", "back": "one-sound digraph (in: agba — jaw)", "group": "Letters"},
    {"id": "kp-digraph", "front": "kp", "back": "one-sound digraph (in: kpọọ — to call)", "group": "Letters"},
    # tone words
    {"id": "tone-akwa-cry", "front": "ákwá", "back": "cry / crying (high-high)", "group": "Tones"},
    {"id": "tone-akwa-egg", "front": "àkwá", "back": "egg (low-high)", "group": "Tones"},
    {"id": "tone-akwa-cloth", "front": "ákwà", "back": "cloth (high-low)", "group": "Tones"},
    {"id": "tone-akwa-bed", "front": "àkwà", "back": "bed (low-low)", "group": "Tones"},
    {"id": "tone-oku", "front": "ọ́kụ́", "back": "fire (high-high)", "group": "Tones"},
    {"id": "tone-mmiri", "front": "ḿmírí", "back": "water (high-high)", "group": "Tones"},
    {"id": "tone-eze", "front": "eze", "back": "king — or teeth (tone decides)", "group": "Tones"},
    {"id": "tone-isi", "front": "isi", "back": "head", "group": "Tones"},
    {"id": "tone-aka", "front": "aka", "back": "hand", "group": "Tones"},
]

DIALOGUES = [
    {"id": "dlg-first-meeting", "title": "A first meeting", "scene": "Two people meet at a family gathering.",
     "lines": [
        {"speaker": "A", "igbo": "Ndeewo!", "english": "Hello!"},
        {"speaker": "B", "igbo": "Ndeewo! Kedu ka ị mere?", "english": "Hello! How are you?"},
        {"speaker": "A", "igbo": "Ọ dị mma, daalụ. Kedu aha gị?", "english": "I'm fine, thank you. What is your name?"},
        {"speaker": "B", "igbo": "Aha m bụ Chidi. Gị kwa?", "english": "My name is Chidi. And you?"},
        {"speaker": "A", "igbo": "Aha m bụ Adaeze. Ọ na-amasị m imeete gị.", "english": "My name is Adaeze. I'm pleased to meet you."},
     ]},
    {"id": "dlg-market", "title": "At the market", "scene": "Buying yam at the ahịa.",
     "lines": [
        {"speaker": "Buyer", "igbo": "Nne, daalụ. Ego ole ka ị na-ere ji a?", "english": "Madam, thank you. How much are you selling this yam for?"},
        {"speaker": "Seller", "igbo": "Ego puku naira abụọ.", "english": "Two thousand naira."},
        {"speaker": "Buyer", "igbo": "Ọ dị ọnụ! Biko, belata ya.", "english": "That's expensive! Please bring it down."},
        {"speaker": "Seller", "igbo": "Were ya na puku naira na ọkara.", "english": "Take it for one thousand five hundred."},
        {"speaker": "Buyer", "igbo": "A ga-ewere ya. Daalụ!", "english": "I'll take it. Thank you!"},
     ]},
    {"id": "dlg-family", "title": "Meeting the family", "scene": "Introducing family members.",
     "lines": [
        {"speaker": "A", "igbo": "Onye a bụ nne m.", "english": "This is my mother."},
        {"speaker": "B", "igbo": "Ndeewo, nne m ọhụrụ. Ọ dị mma imeete gị.", "english": "Hello, my new mother. I'm happy to meet you."},
        {"speaker": "A", "igbo": "Onye a bụ nwanne m nwoke.", "english": "This is my brother."},
        {"speaker": "B", "igbo": "Ndeewo, nwanne m.", "english": "Hello, my sibling."},
     ]},
    {"id": "dlg-food", "title": "At the table", "scene": "A meal at a friend's home.",
     "lines": [
        {"speaker": "Host", "igbo": "Biko, rie nri.", "english": "Please, eat some food."},
        {"speaker": "Guest", "igbo": "Daalụ. Isi a dị mma!", "english": "Thank you. This is delicious! (lit. the smell is good)"},
        {"speaker": "Host", "igbo": "Ṅụọ mmiri ma ọ bụ mmanya.", "english": "Drink some water or a drink."},
        {"speaker": "Guest", "igbo": "Mmiri, biko. Daalụ.", "english": "Water, please. Thank you."},
     ]},
    {"id": "dlg-directions", "title": "Asking the way", "scene": "Looking for the market.",
     "lines": [
        {"speaker": "A", "igbo": "Ndo, ebee ka ahịa dị?", "english": "Excuse me, where is the market?"},
        {"speaker": "B", "igbo": "Gaa n'ụzọ a, ma tụgharị n'aka nri.", "english": "Go along this road, then turn right."},
        {"speaker": "A", "igbo": "Ọ dị anya?", "english": "Is it far?"},
        {"speaker": "B", "igbo": "Mba, ọ dị nso. Ị na-ahụ ya n'ebe ahụ.", "english": "No, it's near. You can see it over there."},
        {"speaker": "A", "igbo": "Daalụ nke ukwuu!", "english": "Thank you very much!"},
     ]},
    {"id": "dlg-elders", "title": "Visiting the elders", "scene": "A young person visits an elder.",
     "lines": [
        {"speaker": "Youth", "igbo": "Ndeewo, nna m. Ọ dị mma?", "english": "Welcome, my father. Are you well?"},
        {"speaker": "Elder", "igbo": "Ndeewo, nwa m. Ọ dị mma. Kedu ụlọ gị?", "english": "Welcome, my child. I am well. How is your household?"},
        {"speaker": "Youth", "igbo": "Anyị niile dị mma. Daalụ.", "english": "We are all well. Thank you."},
     ]},
]

PROVERBS = [
    {"igbo": "Ilu bụ mmanụ e ji eri okwu.",
     "english": "Proverbs are the palm oil with which words are eaten.",
     "meaning": "Proverbs make speech richer and wiser — they help you say things gently and well."},
    {"igbo": "Gidi gidi bụ ugwu eze.",
     "english": "Unity is strength.",
     "meaning": "A people who stand together cannot be moved — the best-known Igbo proverb."},
    {"igbo": "Oge adịghị eche mmadụ.",
     "english": "Time and tide wait for nobody.",
     "meaning": "Act when the moment is there; time will not pause for you."},
    {"igbo": "Onye ajụghị ase, anaghị efu ụzọ.",
     "english": "The person who asks questions does not lose the way.",
     "meaning": "Asking is a strength. If you ask, you learn, and you will not get lost."},
    {"igbo": "Otu onye tụọ izu, o gbue ọchụ.",
     "english": "Knowledge is never complete: two heads are better than one.",
     "meaning": "One person's knowledge is always partial — learn from others."},
    {"igbo": "Chọọ ewu ojii ka chi dị.",
     "english": "Make hay while the sun shines.",
     "meaning": "Seize opportunity while you have it."},
    {"igbo": "Aka nri kwo aka ekpe, aka ekpe akwo aka nri.",
     "english": "When the right hand washes the left, the left washes the right.",
     "meaning": "People should help one another — helping others is helping yourself."},
    {"igbo": "Nwata kwụrụ n'ukwu nne ya, hụ anya ọhịa.",
     "english": "A child who stands on the shoulders of their mother sees farther into the forest.",
     "meaning": "When you learn from your elders, you see further than you could alone."},
    {"igbo": "Eze mbe si na nsogbu bụ nke ya, ya jiri kworo ya n'azu.",
     "english": "The turtle said his troubles were his own, so he carried them on his back.",
     "meaning": "Shoulder your own burdens — no one else can carry them for you."},
    {"igbo": "Ohia woro gị nkụ, sere gị ọnụ.",
     "english": "The forest that denies you firewood has massaged your neck.",
     "meaning": "An apparent loss can turn out to be a hidden blessing."},
    {"igbo": "Ọ bụ onye kwe, chi ya ekwe.",
     "english": "If a person agrees, their personal god agrees.",
     "meaning": "Your own willingness is the first step — belief opens the way."},
    {"igbo": "Ihe dị n'ọhịa, a na-ahụ ya n'ahịa.",
     "english": "What is hidden in the bush is seen in the market.",
     "meaning": "Secrets do not stay secret for long."},
]

WRITING_PRACTICE = [
    {"id": "wp-1", "prompt": "Type the Igbo for: Hello / Welcome",
     "answer": "ndeewo", "hint": "N _ _ _ _ _ o — starts with n, ends with o"},
    {"id": "wp-2", "prompt": "Type the Igbo for: Thank you",
     "answer": "daalụ", "hint": "D _ _ _ _ ụ — remember the dotted letter"},
    {"id": "wp-3", "prompt": "Type the Igbo for: mother",
     "answer": "nne", "hint": "n _ e"},
    {"id": "wp-4", "prompt": "Type the Igbo for: water",
     "answer": "mmiri", "hint": "m _ _ _ _ i"},
    {"id": "wp-5", "prompt": "Type the Igbo for: house",
     "answer": "ụlọ", "hint": "dotted u, then l, then dotted o"},
    {"id": "wp-6", "prompt": "Type the Igbo for: market",
     "answer": "ahịa", "hint": "a _ _ ị a"},
    {"id": "wp-7", "prompt": "Type the Igbo for: money",
     "answer": "ego", "hint": "_ _ _ o"},
    {"id": "wp-8", "prompt": "Type the Igbo for: How much?",
     "answer": "ego ole", "hint": "two words"},
    {"id": "wp-9", "prompt": "Type the Igbo for: food",
     "answer": "nri", "hint": "n _ _"},
    {"id": "wp-10", "prompt": "Type the Igbo for: woman",
     "answer": "nwaanyị", "hint": "n w a a n y ị"},
    {"id": "wp-11", "prompt": "Type the Igbo for: Yes",
     "answer": "ee", "hint": "two letters"},
    {"id": "wp-12", "prompt": "Type the Igbo for: Goodbye",
     "answer": "ka ọ dị", "hint": "three words, 'let it be'"},
]


def course_content():
    return {
        "tiers": {k: {"name": v["name"], "amount": v["amount"]} for k, v in TIERS.items()},
        "lessons": LESSONS,
        "quizzes": [{k: q[k] for k in ("id", "tier", "title", "lesson")} for q in QUIZZES],
        "flashcard_count": len(FLASHCARDS),
        "dialogue_count": len(DIALOGUES),
        "proverb_count": len(PROVERBS),
    }


# ----------------------------------------------------------------------------
# Payment safety net: Paystack
# ----------------------------------------------------------------------------

def paystack_headers():
    return {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
            "content-type": "application/json"}


def get_payment_by_reference(reference):
    return query_one("SELECT * FROM payments WHERE reference = ?", (reference,))


def fulfil(payment, paystack_status, amount, note=""):
    """
    Idempotent fulfilment. Never grants access twice, refuses amount
    mismatches and underpayment, never downgrades a higher tier.
    Returns a plain-language outcome string.
    """
    if payment["status"] == "success":
        return "already"  # idempotent: no double grant

    if paystack_status != "success":
        execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                ("failed", note or paystack_status, now_iso(), payment["id"]))
        return "failed"

    expected = TIERS.get(payment["tier"], {}).get("amount")
    if expected is None:
        execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                ("rejected", "unknown tier", now_iso(), payment["id"]))
        return "rejected"

    # refuse underpayment explicitly
    if amount is not None and int(amount) < int(expected):
        execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                ("rejected", f"underpayment: got {amount}, expected {expected}",
                 now_iso(), payment["id"]))
        return "underpayment"

    # refuse any amount mismatch (over- or under-payment)
    if amount is None or int(amount) != int(expected):
        execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                ("rejected", f"amount mismatch: got {amount}, expected {expected}",
                 now_iso(), payment["id"]))
        return "amount_mismatch"

    user = get_user_by_id(payment["user_id"])
    if not user:
        return "no_user"

    if tier_rank(user["tier"]) >= tier_rank(payment["tier"]):
        # already holds this tier or higher: mark payment, do NOT downgrade
        execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                ("success", "already held equal or higher tier", now_iso(), payment["id"]))
        return "no_downgrade"

    execute("UPDATE users SET tier = ? WHERE id = ?", (payment["tier"], user["id"]))
    execute("UPDATE payments SET status = ?, note = ?, updated_at = ? WHERE id = ?",
            ("success", note or "paid", now_iso(), payment["id"]))
    try:
        email_receipt(user, TIERS[payment["tier"]]["name"], expected // 100, payment["reference"])
    except Exception:
        pass
    return "granted"


def verify_with_paystack(reference):
    """Call Paystack verify. Returns (status, amount) or (None, None) on error."""
    if not PAYSTACK_SECRET_KEY:
        return None, None
    try:
        r = requests.get(f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                         headers=paystack_headers(), timeout=20)
        if r.status_code >= 300:
            return None, None
        data = r.json().get("data") or {}
        return data.get("status"), data.get("amount")
    except Exception as e:
        app.logger.warning("Paystack verify failed: %s", e)
        return None, None


def reconcile_user(user_id):
    """Check every pending payment for this user against Paystack."""
    outcomes = []
    pending = query_all(
        "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY id DESC",
        (user_id,))
    for p in pending:
        status, amount = verify_with_paystack(p["reference"])
        if status is None:
            outcomes.append({"reference": p["reference"], "result": "check_failed"})
            continue
        outcome = fulfil(p, status, amount, "reconciled")
        outcomes.append({"reference": p["reference"], "result": outcome})
    return outcomes


# ----------------------------------------------------------------------------
# API routes
# ----------------------------------------------------------------------------

@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin", "")
    allowed = FRONTEND_ORIGIN
    if allowed == "*" or (origin and origin == allowed):
        resp.headers["Access-Control-Allow-Origin"] = allowed if allowed != "*" else origin or "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "database": "postgres" if USE_PG else "sqlite"})


@app.route("/api/config", methods=["GET"])
def config():
    return jsonify({
        "paystack_public_key": PAYSTACK_PUBLIC_KEY,
        "currency": "NGN",
        "tiers": {k: {"name": v["name"], "amount": v["amount"],
                      "naira": v["amount"] // 100} for k, v in TIERS.items()},
        "international_note": "International cards (Visa, Mastercard) are accepted.",
    })


# ---- auth ----

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(name) < 2:
        return jsonify({"error": "Please tell us your name."}), 400
    if len(password) < 8:
        return jsonify({"error": "Please choose a password of at least 8 characters."}), 400
    if get_user_by_email(email):
        return jsonify({"error": "An account with this email already exists. Please sign in."}), 409
    execute("INSERT INTO users(email, name, password_hash, tier, created_at) VALUES (?,?,?,?,?)",
            (email, name, generate_password_hash(password), "free", now_iso()))
    user = get_user_by_email(email)
    try:
        email_welcome(user)
    except Exception:
        pass
    return jsonify({"token": make_token(user["id"]), "user": public_user(user)}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Email or password is not correct."}), 401
    execute("UPDATE users SET last_seen = ? WHERE id = ?", (now_iso(), user["id"]))
    return jsonify({"token": make_token(user["id"]), "user": public_user(user)})


@app.route("/api/auth/me", methods=["GET"])
@auth_required
def me():
    # Payment safety net: self-heal any payment the customer completed
    # but whose popup closed before we could verify it.
    try:
        reconcile_user(g.user["id"])
    except Exception as e:
        app.logger.warning("reconcile on /me failed: %s", e)
    user = get_user_by_id(g.user["id"])
    return jsonify({"user": public_user(user)})


# ---- content & progress ----

@app.route("/api/content", methods=["GET"])
def content():
    return jsonify(course_content())


@app.route("/api/progress/summary", methods=["GET"])
@auth_required
def progress_summary():
    done = query_all("SELECT item_id, item_type FROM progress WHERE user_id = ?", (g.user["id"],))
    quizzes = query_all(
        "SELECT quiz_id, score, total FROM quiz_results WHERE user_id = ?", (g.user["id"],))
    best = {}
    for q in quizzes:
        cur = best.get(q["quiz_id"])
        if cur is None or q["score"] > cur["score"]:
            best[q["quiz_id"]] = q
    return jsonify({
        "completed": [d["item_id"] for d in done],
        "quizzes": best,
        "tier": g.user["tier"],
    })


@app.route("/api/progress/complete", methods=["POST"])
@auth_required
def complete_item():
    data = request.get_json(silent=True) or {}
    item_id = (data.get("item_id") or "").strip()
    item_type = (data.get("item_type") or "lesson").strip()
    valid_ids = {l["id"] for l in LESSONS}
    if item_type != "lesson" or item_id not in valid_ids:
        return jsonify({"error": "Unknown lesson."}), 400
    # tier gate: paid lessons require the matching tier
    lesson = next(l for l in LESSONS if l["id"] == item_id)
    if tier_rank(lesson["tier"]) > tier_rank(g.user["tier"]):
        return jsonify({"error": "This lesson is part of a paid tier.", "need": lesson["tier"]}), 403
    existing = query_one(
        "SELECT id FROM progress WHERE user_id = ? AND item_id = ?", (g.user["id"], item_id))
    if not existing:
        execute("INSERT INTO progress(user_id, item_id, item_type, created_at) VALUES (?,?,?,?)",
                (g.user["id"], item_id, item_type, now_iso()))
    return jsonify({"ok": True})


@app.route("/api/quiz/<quiz_id>", methods=["GET"])
def quiz_detail(quiz_id):
    quiz = next((q for q in QUIZZES if q["id"] == quiz_id), None)
    if not quiz:
        return jsonify({"error": "Quiz not found."}), 404
    return jsonify({
        "id": quiz["id"], "tier": quiz["tier"], "title": quiz["title"],
        "questions": [{"q": q["q"], "options": q["options"]} for q in quiz["questions"]],
    })


@app.route("/api/quiz/submit", methods=["POST"])
@auth_required
def quiz_submit():
    data = request.get_json(silent=True) or {}
    quiz_id = (data.get("quiz_id") or "").strip()
    answers = data.get("answers") or []
    quiz = next((q for q in QUIZZES if q["id"] == quiz_id), None)
    if not quiz:
        return jsonify({"error": "Quiz not found."}), 404
    if tier_rank(quiz["tier"]) > tier_rank(g.user["tier"]):
        return jsonify({"error": "This quiz is part of a paid tier.", "need": quiz["tier"]}), 403
    score = 0
    review = []
    for i, q in enumerate(quiz["questions"]):
        given = answers[i] if i < len(answers) else None
        correct = given == q["answer"]
        if correct:
            score += 1
        review.append({"q": q["q"], "given": given, "answer": q["answer"],
                       "correct": correct, "explain": q["explain"]})
    total = len(quiz["questions"])
    execute("INSERT INTO quiz_results(user_id, quiz_id, score, total, created_at) VALUES (?,?,?,?,?)",
            (g.user["id"], quiz_id, score, total, now_iso()))
    return jsonify({"score": score, "total": total,
                    "passed": score * 100 >= total * PASS_MARK, "review": review})


# ---- flashcards (SRS, Leitner) ----
BOX_INTERVALS_DAYS = [0, 1, 2, 4, 8]


def _due_iso(box):
    days = BOX_INTERVALS_DAYS[min(box, len(BOX_INTERVALS_DAYS) - 1)]
    dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_ignore(table, cols, params):
    """Dialect-aware INSERT ... ignore-duplicate."""
    if USE_PG:
        sql = (f"INSERT INTO {table}({', '.join(cols)}) "
               f"VALUES ({', '.join(['?'] * len(cols))}) ON CONFLICT DO NOTHING")
    else:
        sql = f"INSERT OR IGNORE INTO {table}({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})"
    execute(sql, params)


def seed_flashcards(user_id, groups=None):
    for c in FLASHCARDS:
        if groups is None or c["group"] in groups:
            insert_ignore("flashcards", ["user_id", "card_id", "box", "due", "created_at"],
                          (user_id, c["id"], 0, now_iso(), now_iso()))


def user_cards(user_id, due_only=False):
    cards = query_all(
        "SELECT card_id, box, due, reviews, lapses FROM flashcards WHERE user_id = ?"
        + (" AND (due IS NULL OR due <= ?)" if due_only else ""),
        (user_id, now_iso()) if due_only else (user_id,))
    by_id = {c["id"]: c for c in FLASHCARDS}
    out = []
    for c in cards:
        meta = by_id.get(c["card_id"])
        if meta:
            out.append({**meta, **{k: c[k] for k in ("box", "due", "reviews", "lapses")}})
    return out


@app.route("/api/flashcards", methods=["GET"])
@auth_required
def flashcards_due():
    # Free users get the letters and tone cards as a genuine taste of SRS;
    # Survival/Fluency unlock the full deck.
    if tier_rank(g.user["tier"]) < tier_rank("survival"):
        count = query_one("SELECT COUNT(*) AS c FROM flashcards WHERE user_id = ?",
                          (g.user["id"],))
        if not count or count["c"] == 0:
            seed_flashcards(g.user["id"], groups={"Letters", "Tones"})
        return jsonify({"cards": user_cards(g.user["id"]), "tier": g.user["tier"],
                        "note": "Free preview cards — the full deck unlocks with Survival Igbo."})
    # Paid tiers: make sure the full deck exists (INSERT OR IGNORE /
    # ON CONFLICT DO NOTHING keeps this idempotent), then return only the
    # cards that are due for review today.
    seed_flashcards(g.user["id"])
    return jsonify({"cards": user_cards(g.user["id"], due_only=True),
                    "tier": g.user["tier"]})


@app.route("/api/flashcards/review", methods=["POST"])
@auth_required
def flashcards_review():
    data = request.get_json(silent=True) or {}
    card_id = (data.get("card_id") or "").strip()
    knew = bool(data.get("knew"))
    row = query_one("SELECT * FROM flashcards WHERE user_id = ? AND card_id = ?",
                    (g.user["id"], card_id))
    if not row:
        return jsonify({"error": "Card not found for this account."}), 404
    if knew:
        box = min(row["box"] + 1, len(BOX_INTERVALS_DAYS) - 1)
    else:
        box = 0
    execute(
        "UPDATE flashcards SET box = ?, due = ?, reviews = reviews + 1,"
        " lapses = lapses + ? WHERE id = ?",
        (box, _due_iso(box), 0 if knew else 1, row["id"]))
    return jsonify({"ok": True, "box": box, "due": _due_iso(box)})


# ---- fluency-only content ----

def _require_fluency():
    if tier_rank(g.user["tier"]) < tier_rank("fluency"):
        return jsonify({"error": "This is part of the Igbo Fluency Kit.", "need": "fluency"}), 403
    return None


@app.route("/api/dialogues", methods=["GET"])
@auth_required
def dialogues():
    gate = _require_fluency()
    if gate:
        return gate
    return jsonify({"dialogues": DIALOGUES})


@app.route("/api/proverbs", methods=["GET"])
@auth_required
def proverbs():
    gate = _require_fluency()
    if gate:
        return gate
    return jsonify({"proverbs": PROVERBS})


@app.route("/api/writing-practice", methods=["GET"])
@auth_required
def writing_practice():
    gate = _require_fluency()
    if gate:
        return gate
    items = [{"id": w["id"], "prompt": w["prompt"], "hint": w["hint"]} for w in WRITING_PRACTICE]
    return jsonify({"items": items})


@app.route("/api/writing-practice/check", methods=["POST"])
@auth_required
def writing_check():
    gate = _require_fluency()
    if gate:
        return gate
    data = request.get_json(silent=True) or {}
    wid = (data.get("id") or "").strip()
    given = (data.get("answer") or "").strip().lower()
    given = re.sub(r"\s+", " ", given)
    item = next((w for w in WRITING_PRACTICE if w["id"] == wid), None)
    if not item:
        return jsonify({"error": "Exercise not found."}), 404
    expected = re.sub(r"\s+", " ", item["answer"].strip().lower())
    # accept undotted spellings too, but tell the learner
    undot = expected.replace("ị", "i").replace("ọ", "o").replace("ụ", "u").replace("ṅ", "n")
    given_undot = given.replace("ị", "i").replace("ọ", "o").replace("ụ", "u").replace("ṅ", "n")
    if given == expected:
        return jsonify({"correct": True, "answer": item["answer"], "dotted": True})
    if given_undot == undot:
        return jsonify({"correct": True, "answer": item["answer"], "dotted": False,
                        "note": "Right word! Remember the dotted letter in your final spelling."})
    return jsonify({"correct": False, "answer": item["answer"]})


# ---- certificate ----

def certificate_eligible(user_id):
    user = get_user_by_id(user_id)
    if tier_rank(user["tier"]) < tier_rank("fluency"):
        return False, "The certificate is part of the Igbo Fluency Kit."
    done = {d["item_id"] for d in query_all(
        "SELECT item_id FROM progress WHERE user_id = ?", (user_id,))}
    lessons = {l["id"] for l in LESSONS}
    missing = lessons - done
    if missing:
        return False, "Finish every lesson first — you are almost there."
    quizzes = query_all(
        "SELECT quiz_id, score, total FROM quiz_results WHERE user_id = ?", (user_id,))
    best = {}
    for q in quizzes:
        cur = best.get(q["quiz_id"])
        if cur is None or q["score"] > cur["score"]:
            best[q["quiz_id"]] = q
    for q in QUIZZES:
        r = best.get(q["id"])
        if not r or r["score"] * 100 < r["total"] * PASS_MARK:
            return False, "Pass every quiz first — you are almost there."
    return True, ""


@app.route("/api/certificate", methods=["GET"])
@auth_required
def certificate():
    ok, why = certificate_eligible(g.user["id"])
    if not ok:
        return jsonify({"eligible": False, "reason": why})
    existing = query_one("SELECT * FROM certificates WHERE user_id = ?", (g.user["id"],))
    if not existing:
        serial = f"IGBO-FLUENCY-{datetime.date.today().year}-{secrets.token_hex(3).upper()}"
        execute("INSERT INTO certificates(user_id, serial, tier, issued_at) VALUES (?,?,?,?)",
                (g.user["id"], serial, "fluency", now_iso()))
        existing = query_one("SELECT * FROM certificates WHERE user_id = ?", (g.user["id"],))
        try:
            email_certificate(g.user, serial)
        except Exception:
            pass
    return jsonify({"eligible": True, "serial": existing["serial"],
                    "issued_at": existing["issued_at"], "name": g.user["name"]})


@app.route("/api/certificate/pdf", methods=["GET"])
@auth_required
def certificate_pdf():
    ok, why = certificate_eligible(g.user["id"])
    if not ok:
        return jsonify({"error": why}), 403
    cert = query_one("SELECT * FROM certificates WHERE user_id = ?", (g.user["id"],))
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(ASSETS_DIR, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(ASSETS_DIR, "DejaVuSans-Bold.ttf")))
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=landscape(A4))
        w, h = landscape(A4)
        c.setStrokeColorRGB(0.043, 0.43, 0.31)
        c.setLineWidth(3)
        c.rect(28, 28, w - 56, h - 56)
        c.setFont("DejaVuSans-Bold", 30)
        c.drawCentredString(w / 2, h - 130, "Certificate of Completion")
        c.setFont("DejaVuSans", 14)
        c.drawCentredString(w / 2, h - 165, "Igbo Mastery — Igbo Fluency Kit")
        c.setFont("DejaVuSans", 12)
        c.drawCentredString(w / 2, h - 215, "This certifies that")
        c.setFont("DejaVuSans-Bold", 26)
        c.drawCentredString(w / 2, h - 260, g.user["name"] or g.user["email"])
        c.setFont("DejaVuSans", 12)
        c.drawCentredString(w / 2, h - 300,
                            "has completed every lesson and passed every quiz of the Igbo Fluency Kit:")
        c.drawCentredString(w / 2, h - 322,
                            "tones, alphabet, dotted letters, survival Igbo, flashcards,")
        c.drawCentredString(w / 2, h - 344,
                            "writing practice, dialogues and proverbs (ilu).")
        c.setFont("DejaVuSans", 11)
        c.drawCentredString(w / 2, 110, f"Certificate number: {cert['serial']}")
        c.drawCentredString(w / 2, 90, f"Issued: {cert['issued_at'][:10]}")
        c.setFont("DejaVuSans-Bold", 14)
        c.drawCentredString(w / 2, 55, "Igbo Mastery — igbomastery.com")
        c.showPage()
        c.save()
        buf.seek(0)
        from flask import Response
        return Response(buf.getvalue(), mimetype="application/pdf",
                        headers={"Content-Disposition":
                                 f"attachment; filename=igbo-certificate-{cert['serial']}.pdf"})
    except Exception as e:
        app.logger.warning("certificate pdf failed: %s", e)
        return jsonify({"error": "Certificate is ready, but the PDF could not be generated."}), 500


# ---- payments ----

@app.route("/api/paystack/initialize", methods=["POST"])
@auth_required
def paystack_initialize():
    data = request.get_json(silent=True) or {}
    tier = (data.get("tier") or "").strip()
    if tier not in ("survival", "fluency"):
        return jsonify({"error": "Please choose a course tier."}), 400
    if tier_rank(g.user["tier"]) >= tier_rank(tier):
        return jsonify({"error": "You already own this course. Thank you!"}), 400
    if not PAYSTACK_SECRET_KEY:
        return jsonify({"error": "Payments are not switched on yet."}), 503
    amount = TIERS[tier]["amount"]
    reference = f"IGB-{tier[:3].upper()}-{secrets.token_hex(6)}"
    execute(
        "INSERT INTO payments(user_id, reference, tier, amount, currency, status, created_at, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (g.user["id"], reference, tier, amount, "NGN", "pending", now_iso(), now_iso()))
    callback = (FRONTEND_ORIGIN if FRONTEND_ORIGIN != "*" else "") + "/#/payment-complete"
    try:
        r = requests.post(
            f"{PAYSTACK_BASE}/transaction/initialize",
            headers=paystack_headers(),
            json={
                "email": g.user["email"],
                "amount": amount,
                "reference": reference,
                "callback_url": callback or None,
                "metadata": {"user_id": g.user["id"], "tier": tier,
                             "reference": reference, "custom_fields": []},
            },
            timeout=20)
        payload = r.json()
        if r.status_code >= 300 or not payload.get("status"):
            return jsonify({"error": "We could not start the payment. Please try again."}), 502
        d = payload["data"]
        # Always hand back OUR reference: it is the one stored in our database.
        return jsonify({"authorization_url": d["authorization_url"],
                        "access_code": d["access_code"], "reference": reference})
    except Exception as e:
        app.logger.warning("paystack initialize failed: %s", e)
        return jsonify({"error": "We could not reach the payment provider. Please try again."}), 502


@app.route("/api/paystack/verify", methods=["GET"])
@auth_required
def paystack_verify():
    reference = (request.args.get("reference") or "").strip()
    payment = get_payment_by_reference(reference)
    if not payment:
        return jsonify({"error": "We could not find this payment."}), 404
    # 403 if someone claims another account's payment
    if payment["user_id"] != g.user["id"]:
        return jsonify({"error": "This payment belongs to a different account."}), 403
    if payment["status"] == "success":
        user = get_user_by_id(g.user["id"])
        return jsonify({"status": "success", "outcome": "already",
                        "tier": user["tier"], "user": public_user(user)})
    status, amount = verify_with_paystack(reference)
    if status is None:
        return jsonify({"status": "pending", "message":
                        "We are still confirming your payment. Check your account page in a minute."})
    outcome = fulfil(payment, status, amount, "verified")
    fresh = get_payment_by_reference(reference)
    user = get_user_by_id(g.user["id"])
    return jsonify({"status": fresh["status"], "outcome": outcome,
                    "tier": user["tier"], "user": public_user(user)})


@app.route("/api/paystack/reconcile", methods=["GET"])
@auth_required
def paystack_reconcile():
    outcomes = reconcile_user(g.user["id"])
    user = get_user_by_id(g.user["id"])
    return jsonify({"checked": len(outcomes), "outcomes": outcomes, "user": public_user(user)})


@app.route("/api/paystack/webhook", methods=["POST"])
def paystack_webhook():
    if not PAYSTACK_SECRET_KEY:
        return jsonify({"ok": True})  # nothing we can verify against
    signature = request.headers.get("x-paystack-signature", "")
    body = request.get_data()
    computed = hmac.new(PAYSTACK_SECRET_KEY.encode(), body, hashlib.sha512).hexdigest()
    if not signature or not hmac.compare_digest(signature, computed):
        return jsonify({"error": "Invalid signature."}), 401
    try:
        event = json.loads(body.decode("utf-8"))
    except Exception:
        return jsonify({"error": "Bad payload."}), 400
    if event.get("event") == "charge.success":
        data = event.get("data") or {}
        reference = data.get("reference")
        payment = get_payment_by_reference(reference)
        if payment:
            fulfil(payment, data.get("status"), data.get("amount"), "webhook")
    return jsonify({"ok": True})


# ----------------------------------------------------------------------------
# Frontend serving (Netlify serves the site in production; this is a fallback
# and keeps local dev simple). Backend, database and config files 404.
# ----------------------------------------------------------------------------
ALLOWED_STATIC_EXT = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg",
                      ".svg", ".ico", ".txt", ".webmanifest", ".woff", ".woff2"}
BLOCKED_NAMES = {"backend.py", ".env", "render.yaml", "requirements.txt",
                 "igbo_mastery.db", ".git", "config.py"}
BLOCKED_EXT = {".py", ".db", ".sqlite", ".sqlite3", ".env", ".yaml", ".yml",
               ".toml", ".cfg", ".ini", ".log", ".key", ".pem", ".sh"}


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if not os.path.isdir(FRONTEND_DIR):
        return jsonify({"error": "Frontend not found."}), 404
    name = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()
    if path in BLOCKED_NAMES or name in BLOCKED_NAMES or ext in BLOCKED_EXT:
        abort(404)
    if path == "":
        return send_from_directory(FRONTEND_DIR, "index.html")
    if name.startswith("."):
        abort(404)
    # path traversal protection
    safe = os.path.realpath(os.path.join(FRONTEND_DIR, path))
    if not safe.startswith(os.path.realpath(FRONTEND_DIR)):
        abort(404)
    if os.path.isfile(safe) and ext in ALLOWED_STATIC_EXT:
        return send_from_directory(FRONTEND_DIR, path)
    abort(404)


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    return jsonify({"error": "Not found."}), 404


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
