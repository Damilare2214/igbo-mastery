# Igbo Mastery — Final Report
### What was built, what was verified, and where everything lives.

---

## 1. The audience model (researched from scratch)

The Mandarin "traders importing from China" model was discarded — nobody learns
Igbo for trade. The research found a completely different buyer:

1. **Diaspora parents (US, UK, Canada, Germany, Ireland, Australia)** — the primary
   customer. They want their children to speak Igbo, to talk with grandparents, to
   keep their identity. Comparable services charge $49–$149/month; our one-time
   ₦500/₦2,000 pricing is deliberately far below that.
2. **Heritage adults** who understand some Igbo but cannot speak it — the second
   primary customer ("Igbo by blood" reclamation).
3. **Culture-curious learners** — Nollywood fans, people with Igbo partners,
   travellers to the East: a reason to learn more than a separate segment.
4. **Igbo studies / academics** — a credibility and content angle, not revenue.
5. **Language-data buyers (AI companies)** — real money flows here (Lacuna Fund's
   NaijaVoice project, the Igbo API, IgboSpeech) but through grants and
   partnerships, not course sales. Flagged honestly as a future partnership angle.

The marketing speaks to identity and family ("your child will greet their
grandmother in Igbo"), not to utility.

## 2. The product — three tiers, as approved

| Tier | Price | Contents |
|---|---|---|
| **Free Foundation** | ₦0 | 6 lessons: what Igbo is, the 36-letter alphabet, the dotted letters ị ọ ụ ṅ, the tones (the ákwá quartet: cry/egg/cloth/bed, plus eze = king or teeth), vowel harmony, first 13 words. 2 quizzes + preview flashcards. Genuinely free. |
| **Survival Igbo** | ₦500 once | 6 modules: greetings & introductions, numbers & money, family & people, food & drink, market & bargaining, daily life. Quiz per module. Full 72-card flashcard deck. |
| **Igbo Fluency Kit** | ₦2,000 once | Everything above + spaced-repetition flashcards, writing practice with dotted-letter pad, 6 dialogue scenes, 12 proverbs (ilu) with meanings, downloadable PDF certificate. |

Content correctness: tone-marked examples were checked against Wikipedia's Igbo
phonology notes and Wiktionary headwords (ọ́kụ́ = fire, ḿmírí = water, the ákwá/àkwá
minimal quartet). Tone marks appear only where verified; everyday vocabulary is
presented without tone marks, matching standard practice.

## 3. The website

- **backend.py** — the entire backend in one file: Flask, JWT auth, dual SQLite/Postgres
  drivers, course content, progress, quizzes, SRS (Leitner boxes), certificate PDF
  generation, Brevo HTTPS-API email, Paystack integration.
- **frontend/** — single-page app (index.html, styles.css, app.js), no build step,
  hash routing, works on phones first. Pages: Home, Pricing, Learn, Lessons, Quizzes,
  Flashcards, Fluency tools, Certificate, Account, Terms, Privacy.
- **Payment safety net** — all five requirements built and individually tested:
  Paystack webhook with HMAC-SHA512 verification using `hmac.compare_digest`;
  reconciliation on every `/api/auth/me`; `GET /api/paystack/reconcile`; an idempotent
  fulfil function that never grants twice, refuses amount mismatches and underpayment,
  and never downgrades a higher tier; `/api/paystack/verify` returns 403 if someone
  claims another account's payment.
- **Security** — backend files, database files and config files all return 404
  (tested); passwords hashed; CORS locked to your Netlify address in production.

## 4. Verification performed

- **54/54 automated backend tests pass**, covering: registration/login/token
  handling, tier gating, quiz scoring, SRS box progression, certificate eligibility
  and PDF generation, every payment-safety rule, webhook signature validation,
  self-healing reconciliation, and all 404 guards.
- **Fonts**: DejaVu Sans visually verified to render ị ọ ụ ṅ, precomposed tone-marked
  vowels, and combining marks — no empty boxes in the site, posters, videos or
  certificate PDF.
- **Videos**: all 20 verified at exactly 1080×1920, 30fps, H.264 video + AAC audio,
  with frame-level visual checks of tone marks and dotted letters.
- **Posters**: all 8 verified at exact target sizes (1080×1920 ×4, 1080×1080 ×4).
- **Live preview**: end-to-end user flow (register → lesson → quiz → progress)
  exercised against the running server.

## 5. The voice decision (checked first, as instructed)

Tested before any video design: **no Igbo voice and no Nigerian-accent English voice
exist in the text-to-speech system** — both requests failed outright. You chose
reading-focused videos, so every video teaches reading: big Igbo text with tone
marks colour-coded gold, English translations, word-by-word animated captions,
AI-generated dark backgrounds with a Ken Burns zoom and gradient scrim. No audio
needed — and no voice dependency to break later.

## 6. International payments (checked before building checkout)

Paystack accepts Visa, Mastercard and Verve cards issued anywhere in the world
(plus American Express for Nigerian businesses), but "Accept international
payments" is off by default and needs dashboard activation with CAC documents.
Per your decision, the checkout is built for **naira pricing with international
payments enabled** — the customer's bank handles currency conversion.
`DEPLOY-STEPS.md` Step 8 gives the exact clicks, including keeping
"pass transaction fees to customer" OFF.

## 7. Marketing kit (₦0 budget)

- **STRATEGY-PLAYBOOK.md** — audience, messaging, channel priorities (WhatsApp
  first), a 30-day launch plan, conversion engine, group etiquette, partnerships.
- **VIDEO-SCRIPTS.md** — all 20 scripts with exact on-screen timing.
- **WHATSAPP-MESSAGES.md** — 15 ready-to-send messages for groups, parents,
  associations and churches.
- **SOCIAL-POSTS.md** — 10 Facebook posts, 6 Instagram captions, story/poll ideas.
- **PROFILE-BIOS.md** — bios for every platform.
- **HASHTAG-SETS.md** — hashtag blocks by audience.
- **CHEAT-SHEET.pdf** — printable one-page starter sheet (A4) + shareable PNG.

## 8. Where everything is

```
igbo-mastery/
├── backend.py                 the whole backend (single file)
├── requirements.txt           everything Render needs to install
├── render.yaml                Render deploy configuration
├── .env.example               every setting, explained
├── frontend/                  index.html · styles.css · app.js (no build step)
├── marketing/
│   ├── STRATEGY-PLAYBOOK.md
│   ├── VIDEO-SCRIPTS.md
│   ├── WHATSAPP-MESSAGES.md
│   ├── SOCIAL-POSTS.md
│   ├── PROFILE-BIOS.md
│   ├── HASHTAG-SETS.md
│   └── CHEAT-SHEET.pdf        printable one-page starter sheet
├── build_videos.py            rebuilds any video when you supply backgrounds
├── make_posters.py            rebuilds any poster when you supply backgrounds
├── make_cheatsheet.py         rebuilds the cheat sheet
└── run_tests.py               re-run all 55 verification checks any time
├── DEPLOY-STEPS.md            plain numbered steps, one action at a time
└── FINAL-REPORT.md            this file
```

## 9. Videos and posters — your choice of method

The 20 videos and 8 posters were built and fully verified (1080×1920, 30fps,
H.264+AAC; exact poster sizes), then deleted at your request to free storage —
you are producing them with your own method. Everything needed to rebuild them
is kept:

- `build_videos.py` — drop any background image into `assets/bg/` and it builds
  the video (Ken Burns zoom, scrim, animated captions, correct codecs).
- `make_posters.py` — same for the posters.
- `VIDEO-SCRIPTS.md` — all 20 scripts with exact on-screen text and timing, so
  whatever tool you use can follow them.

## 10. The one thing left for you

Open **DEPLOY-STEPS.md** and do Step 1 (create your free Neon database). That is
the only action needed before the site can go live — everything else is one click
each, in order, with nothing to figure out.
