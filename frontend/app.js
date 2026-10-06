/* Igbo Mastery - single-page app, no build step.
 *
 * API_BASE: when this file is served by the Flask backend itself (local
 * testing) calls go to the same origin. When the site is hosted on Netlify,
 * replace the address below with your Render backend address, e.g.
 *   const API_BASE = "https://igbo-mastery-api.onrender.com";
 */
const API_BASE = (location.hostname === "localhost" || location.hostname === "127.0.0.1" ||
                  location.hostname.endsWith(".e2b.app"))
  ? ""
  : "https://igbo-mastery-api.onrender.com";

const TOKEN_KEY = "igbo_mastery_token";
const USER_KEY = "igbo_mastery_user";

const state = {
  user: null,
  content: null,
  progress: null,       // {completed:[], quizzes:{}, tier:""}
  quizPicks: {},        // quizId -> [optionIndex,...]
  quizResults: {},      // quizId -> result
  fcQueue: [],
  fcIndex: 0,
  fcFlipped: false,
  fluencyTab: "dialogues",
};

/* ---------------- helpers ---------------- */
const $app = document.getElementById("app");

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function token() { return localStorage.getItem(TOKEN_KEY); }

async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (opts.body) headers["Content-Type"] = "application/json";
  if (token()) headers["Authorization"] = "Bearer " + token();
  const res = await fetch(API_BASE + path, {
    method: opts.method || "GET",
    headers,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* non-JSON */ }
  return { ok: res.ok, status: res.status, data };
}

function saveSession(t, user) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  state.user = user || state.user;
  renderHeaderActions();
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  state.user = null;
  state.progress = null;
  renderHeaderActions();
  location.hash = "#/";
  render();
}

let toastTimer = null;
function toast(msg, ms = 4200) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

const TIER_RANK = { free: 0, survival: 1, fluency: 2 };
function userTier() { return state.user ? state.user.tier : "free"; }
function hasTier(t) { return TIER_RANK[userTier()] >= TIER_RANK[t]; }

function fmtNaira(kobo) { return "₦" + (kobo / 100).toLocaleString("en-NG"); }

function setActiveNav() {
  const route = location.hash.split("?")[0] || "#/";
  document.querySelectorAll(".main-nav a").forEach(a => {
    const target = a.getAttribute("href").split("?")[0];
    a.classList.toggle("active", route === target ||
      (target !== "#/" && route.startsWith(target)));
  });
}

/* ---------------- header ---------------- */
function renderHeaderActions() {
  const el = document.getElementById("header-actions");
  if (state.user) {
    el.innerHTML =
      `<a class="btn btn-ghost" href="#/account">${esc(state.user.name || state.user.email)}</a>` +
      `<button class="btn btn-primary btn-small" id="logout-btn">Sign out</button>`;
    const b = document.getElementById("logout-btn");
    if (b) b.addEventListener("click", logout);
  } else {
    el.innerHTML =
      `<a class="btn btn-ghost" href="#/account">Sign in</a>` +
      `<a class="btn btn-primary btn-small" href="#/account?mode=register">Start free</a>`;
  }
}

/* ---------------- shared bits ---------------- */
function gateCard(need, what) {
  const label = need === "fluency" ? "Igbo Fluency Kit" : "Survival Igbo";
  const price = need === "fluency" ? "₦2,000 one time" : "₦500 one time";
  return `<div class="alert alert-gate">
    <strong>${esc(what)}</strong> is part of the ${esc(label)}.
    <div class="mt-16"><a class="btn btn-primary" href="#/pricing">See pricing — ${esc(price)}</a></div>
  </div>`;
}

function progressStats() {
  if (!state.content || !state.progress) return null;
  const lessons = state.content.lessons;
  const quizzes = state.content.quizzes;
  const doneLessons = lessons.filter(l => state.progress.completed.includes(l.id)).length;
  const passedQuizzes = Object.values(state.progress.quizzes || {})
    .filter(q => q.total > 0 && q.score * 100 >= q.total * 70).length;
  const total = lessons.length + quizzes.length;
  const done = doneLessons + passedQuizzes;
  return { done, total, doneLessons, passedQuizzes,
           lessons: lessons.length, quizzes: quizzes.length,
           pct: total ? Math.round(done * 100 / total) : 0 };
}

function progressBarHTML() {
  const s = progressStats();
  if (!s) return "";
  return `<div class="progress-track"><div class="progress-fill" style="width:${s.pct}%"></div></div>
    <div class="progress-label">${s.done} of ${s.total} steps complete (${s.pct}%) — ${s.doneLessons} lessons, ${s.passedQuizzes} quizzes passed</div>`;
}

/* ---------------- pages ---------------- */
function pageHome() {
  return `
  <section class="hero">
    <div class="wrap">
      <span class="pill">Free foundation course</span>
      <h1>Speak Igbo.<br>Connect with home.</h1>
      <p class="lead">Igbo is a tonal language — the pitch of your voice is part of every word.
      Learn the tones, the 36-letter alphabet and the dotted letters ị ọ ụ ṅ, then move on to
      survival Igbo you can use with family from day one.</p>
      <div class="cta-row">
        <a class="btn btn-gold" href="#/learn">Start the free foundation</a>
        <a class="btn btn-outline" style="color:#fff;border-color:rgba(255,255,255,.5);background:transparent" href="#/pricing">See pricing</a>
      </div>
      <div class="igbo-flash">
        <span><small>Hello</small>Ndeewo</span>
        <span><small>Thank you</small>Daalụ</span>
        <span><small>Mother</small>nne</span>
        <span><small>Market</small>ahịa</span>
        <span><small>Water</small>mmiri</span>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div class="eyebrow">Why tone comes first</div>
      <h2>One word. Four meanings.</h2>
      <p class="muted">Written without tone marks, <strong>akwa</strong> is a single word. Spoken four ways,
      it is four different words — the same trick that makes Mandarin tones matter.</p>
    </div>
    <div class="tone-demo">
      <div class="tone-card"><div class="word tone-high">ákwá</div><div class="meaning">cry</div></div>
      <div class="tone-card"><div class="word tone-low">àkwá</div><div class="meaning">egg</div></div>
      <div class="tone-card"><div class="word tone-high">ákwà</div><div class="meaning">cloth</div></div>
      <div class="tone-card"><div class="word tone-low">àkwà</div><div class="meaning">bed</div></div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div class="eyebrow">What you get</div>
      <h2>A real course, built for diaspora families</h2>
    </div>
    <div class="grid grid-3">
      <div class="card"><div class="feature-icon">ị</div>
        <h3>Written properly</h3>
        <p class="muted">Every lesson teaches the dotted letters ị ọ ụ ṅ and correct spelling,
        so you read Igbo the way Igbo people write it.</p></div>
      <div class="card"><div class="feature-icon">◎</div>
        <h3>Built around tone</h3>
        <p class="muted">Tone is taught first and reinforced everywhere — because in Igbo,
        pitch is meaning.</p></div>
      <div class="card"><div class="feature-icon">↻</div>
        <h3>It sticks</h3>
        <p class="muted">Quizzes after every module, spaced-repetition flashcards and a
        progress bar keep you moving.</p></div>
      <div class="card"><div class="feature-icon">⌂</div>
        <h3>Family vocabulary</h3>
        <p class="muted">Greetings, numbers, family, food, the market and daily life —
        the words you actually use at home.</p></div>
      <div class="card"><div class="feature-icon">❝</div>
        <h3>Proverbs (ilu)</h3>
        <p class="muted">Igbo wisdom in the Fluency Kit: twelve classic proverbs with
        meanings, ready to use.</p></div>
      <div class="card"><div class="feature-icon">★</div>
        <h3>A certificate</h3>
        <p class="muted">Finish the Fluency Kit and earn a downloadable certificate of
        completion with your name on it.</p></div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div class="eyebrow">Pricing</div>
      <h2>Start free. Upgrade once, if you want.</h2>
      <p>No subscriptions. One-time payments in naira. International cards accepted.</p>
    </div>
    <div class="grid grid-3">
      <div class="card tier-card">
        <span class="badge">Free</span>
        <div class="tier-price">₦0</div>
        <p class="muted">Igbo Foundation</p>
        <ul class="tier-list">
          <li>The three tones, taught properly</li>
          <li>The 36-letter alphabet</li>
          <li>The dotted letters ị ọ ụ ṅ</li>
          <li>Your first 13 words</li>
          <li>2 quizzes + preview flashcards</li>
        </ul>
        <a class="btn btn-outline btn-block" href="#/learn">Start free</a>
      </div>
      <div class="card tier-card">
        <span class="badge gold">Survival</span>
        <div class="tier-price">₦500 <small>one time</small></div>
        <p class="muted">Survival Igbo</p>
        <ul class="tier-list">
          <li>Everything in the foundation</li>
          <li>Greetings &amp; introductions</li>
          <li>Numbers, time &amp; money</li>
          <li>Family, food, market, daily life</li>
          <li>6 modules + quizzes + full flashcard deck</li>
        </ul>
        <a class="btn btn-outline btn-block" href="#/pricing">Get Survival Igbo</a>
      </div>
      <div class="card tier-card featured">
        <span class="tier-badge">Most complete</span>
        <span class="badge gold">Fluency</span>
        <div class="tier-price">₦2,000 <small>one time</small></div>
        <p class="muted">Igbo Fluency Kit</p>
        <ul class="tier-list">
          <li>Everything in Survival Igbo</li>
          <li>Spaced-repetition flashcards (SRS)</li>
          <li>Writing practice with letter pad</li>
          <li>6 dialogue practice scenes</li>
          <li>12 proverbs (ilu) with meanings</li>
          <li>Certificate of completion</li>
        </ul>
        <a class="btn btn-primary btn-block" href="#/pricing">Get the Fluency Kit</a>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="section-head">
      <div class="eyebrow">Questions</div>
      <h2>Before you start</h2>
    </div>
    <div class="faq">
      <details><summary>Is the free course really free?</summary>
        <p>Yes. The Igbo Foundation teaches the tones, the full alphabet, the dotted letters and your first words — no card needed, no trial timer. It stays free.</p></details>
      <details><summary>I understand some Igbo but cannot speak it. Is this for me?</summary>
        <p>That is exactly who the Fluency Kit is for. Many heritage learners understand more than they can say — the flashcards, dialogues and writing practice are built to turn passive understanding into active speaking and writing.</p></details>
      <details><summary>Can my children use it?</summary>
        <p>Yes. Parents learn alongside their children in most families who use this course. The vocabulary modules (family, food, market) are the first words children pick up.</p></details>
      <details><summary>Do you accept cards from abroad?</summary>
        <p>Yes. Visa, Mastercard and Verve cards issued anywhere in the world are accepted. Your bank converts the charge to your local currency; you pay in naira.</p></details>
      <details><summary>How long does access last?</summary>
        <p>Forever. Both paid tiers are one-time purchases with no subscription and no renewal. Your progress is saved to your account.</p></details>
    </div>
  </section>`;
}

function pagePricing() {
  const owned = (t) => hasTier(t);
  const buyBtn = (tier, label, cls) => {
    if (owned(tier)) return `<button class="btn ${cls} btn-block" disabled>You own this</button>`;
    return `<button class="btn ${cls} btn-block" data-buy="${tier}">${label}</button>`;
  };
  return `
  <section class="section">
    <div class="section-head">
      <div class="eyebrow">Pricing</div>
      <h2>Three tiers. One-time payments.</h2>
      <p>Prices are in naira and include everything — no subscription, no hidden fees.
      International cards (Visa, Mastercard, Verve) are accepted; your bank handles the currency conversion.</p>
    </div>
    <div class="grid grid-3">
      <div class="card tier-card">
        <span class="badge">Tier 1</span>
        <div class="tier-price">₦0</div>
        <p class="muted">Free Foundation</p>
        <ul class="tier-list">
          <li>Igbo tones (high, low, downstep)</li>
          <li>The famous akwa minimal set: cry / egg / cloth / bed</li>
          <li>36-letter alphabet + 9 digraphs</li>
          <li>Dotted letters ị ọ ụ ṅ</li>
          <li>Vowel harmony explained simply</li>
          <li>13 first words</li>
          <li>2 quizzes</li>
          <li>Preview flashcards (letters &amp; tones)</li>
        </ul>
        <a class="btn btn-outline btn-block" href="#/learn">Start free</a>
      </div>
      <div class="card tier-card">
        <span class="badge gold">Tier 2</span>
        <div class="tier-price">₦500 <small>one time</small></div>
        <p class="muted">Survival Igbo</p>
        <ul class="tier-list">
          <li>Everything in Free Foundation</li>
          <li>Greetings &amp; introductions</li>
          <li>Numbers, time &amp; money</li>
          <li>Family &amp; people</li>
          <li>Food &amp; drink</li>
          <li>Market &amp; bargaining</li>
          <li>Daily life &amp; getting around</li>
          <li>6 quizzes + full flashcard deck (SRS)</li>
        </ul>
        ${buyBtn("survival", "Buy Survival Igbo — ₦500", "btn-outline")}
        <p class="price-note mt-8">One-time payment. Yours forever.</p>
      </div>
      <div class="card tier-card featured">
        <span class="tier-badge">Most complete</span>
        <span class="badge gold">Tier 3</span>
        <div class="tier-price">₦2,000 <small>one time</small></div>
        <p class="muted">Igbo Fluency Kit</p>
        <ul class="tier-list">
          <li>Everything in Survival Igbo</li>
          <li>Spaced-repetition flashcards, full deck</li>
          <li>Writing practice with dotted-letter pad</li>
          <li>6 dialogue scenes (meeting, market, family, table, directions, elders)</li>
          <li>12 proverbs (ilu) with meanings</li>
          <li>Certificate of completion (PDF)</li>
        </ul>
        ${buyBtn("fluency", "Buy the Fluency Kit — ₦2,000", "btn-primary")}
        <p class="price-note mt-8">One-time payment. Yours forever.</p>
      </div>
    </div>
    <div class="alert alert-info mt-24">
      <strong>Paying from abroad?</strong> Paystack accepts Visa, Mastercard and Verve cards issued in any
      country, plus American Express. The charge is taken in naira and your bank converts it at its own
      exchange rate. If a payment ever fails to complete, your account is checked and repaired automatically
      when you next sign in — you will never lose access you paid for.
    </div>
  </section>`;
}

async function pageLearn() {
  if (!state.content) await loadContent();
  if (!state.user) {
    return `<section class="section">
      <div class="alert alert-gate"><strong>Create your free account to save your progress.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account?mode=register">Create free account</a>
      <a class="btn btn-ghost" href="#/account">I already have one</a></div></div>
      ${lessonListHTML(true)}</section>`;
  }
  await refreshProgress();
  return `<section class="section">
    <div class="learn-layout">
      <aside class="lesson-side"><div class="card">
        <h3>Your progress</h3>
        ${progressBarHTML()}
        <div class="mt-16" id="lesson-list">${lessonListHTML(false)}</div>
      </div></aside>
      <div id="lesson-main"><div class="card"><h3>Pick a lesson to begin</h3>
        <p class="muted">Start with “What Igbo is — and why it sounds like music”. Everything you complete is saved automatically.</p></div></div>
    </div>
  </section>`;
}

function lessonListHTML(locked) {
  const groups = [
    { tier: "free", label: "Igbo Foundation — free" },
    { tier: "survival", label: "Survival Igbo — ₦500" },
  ];
  let html = "";
  for (const grp of groups) {
    const lessons = state.content.lessons.filter(l => l.tier === grp.tier);
    if (!lessons.length) continue;
    html += `<div class="eyebrow mt-16">${esc(grp.label)}</div>`;
    for (const l of lessons) {
      const done = state.progress && state.progress.completed.includes(l.id);
      const accessible = !locked && hasTier(l.tier);
      const icon = done ? '<span class="tick">✓</span>'
        : accessible ? '<span class="tick" style="color:#bcdccd">○</span>'
        : '<span class="lock">🔒</span>';
      html += accessible
        ? `<a class="lesson-item ${done ? "done" : ""}" href="#/lesson/${l.id}">${icon}<span>${esc(l.title)}</span></a>`
        : `<div class="lesson-item ${done ? "done" : ""}">${icon}<span>${esc(l.title)}</span></div>`;
    }
  }
  return html;
}

async function pageLesson(id) {
  if (!state.content) await loadContent();
  const lesson = state.content.lessons.find(l => l.id === id);
  if (!lesson) return `<section class="section"><div class="alert alert-warn">Lesson not found. <a href="#/learn">Back to lessons</a></div></section>`;
  if (!state.user && TIER_RANK[lesson.tier] > 0) {
    return `<section class="section">${gateCard(lesson.tier, "This lesson")}
      <a class="btn btn-ghost" href="#/learn">Back to lessons</a></section>`;
  }
  if (state.user && !hasTier(lesson.tier)) {
    return `<section class="section">${gateCard(lesson.tier, "This lesson")}
      <a class="btn btn-ghost" href="#/learn">Back to lessons</a></section>`;
  }
  if (state.user) await refreshProgress();
  const done = state.progress && state.progress.completed.includes(id);
  const quizzes = state.content.quizzes.filter(q => q.lesson === id);
  const idx = state.content.lessons.findIndex(l => l.id === id);
  const next = state.content.lessons[idx + 1];
  let html = `<section class="section">
    <a class="btn btn-ghost" href="#/learn">← All lessons</a>
    <div class="card mt-16">
      <span class="badge">${esc(lesson.tier === "free" ? "Igbo Foundation" : lesson.tier === "survival" ? "Survival Igbo" : "Igbo Fluency Kit")}</span>
      <h1 style="font-size:clamp(1.5rem,3.4vw,2.1rem);margin-top:10px">${esc(lesson.title)}</h1>
      <p class="muted">About ${lesson.minutes} minutes ${done ? "· completed ✓" : ""}</p>`;
  html += lesson.blocks.map(renderBlock).join("");
  if (quizzes.length) {
    html += `<div class="callout"><div class="callout-title">Quiz time</div>
      <p>Lock in what you just learned.</p>
      <a class="btn btn-primary" href="#/quiz/${quizzes[0].id}">Take the quiz</a></div>`;
  }
  html += `<div class="mt-24" style="display:flex;gap:10px;flex-wrap:wrap">
      ${done
        ? `<span class="btn btn-outline" disabled>Completed ✓</span>`
        : `<button class="btn btn-primary" id="mark-done" data-lesson="${id}">Mark lesson complete</button>`}
      ${next && hasTier(next.tier) ? `<a class="btn btn-outline" href="#/lesson/${next.id}">Next: ${esc(next.title)} →</a>` : ""}
      ${next && !hasTier(next.tier) ? `<a class="btn btn-gold" href="#/pricing">Next lesson needs ${next.tier === "survival" ? "Survival Igbo" : "the Fluency Kit"} →</a>` : ""}
    </div></div></section>`;
  return html;
}

function renderBlock(b) {
  switch (b.type) {
    case "p": return `<div class="lesson-block"><p>${esc(b.text)}</p></div>`;
    case "h3": return `<div class="lesson-block"><h3>${esc(b.text)}</h3></div>`;
    case "callout": return `<div class="callout"><div class="callout-title">${esc(b.title)}</div><p style="margin:0">${esc(b.text)}</p></div>`;
    case "letters": return `<div class="lesson-block"><div class="letters-grid">` +
      b.items.map(i => `<div class="letter-cell"><div class="ltr">${esc(i.letter)}</div><div class="guide">${esc(i.guide)}</div></div>`).join("") + `</div></div>`;
    case "digraphs": return `<div class="lesson-block"><table class="data-table"><tr><th>Letters</th><th>Sound</th><th>Example</th></tr>` +
      b.items.map(i => `<tr><td><strong>${esc(i.letters)}</strong></td><td>${esc(i.guide)}</td><td>${esc(i.example)}</td></tr>`).join("") + `</table></div>`;
    case "dotted": return `<div class="lesson-block">` + b.items.map(d =>
      `<div class="dotted-card"><div class="big">${esc(d.letter)}</div>
        <p class="muted" style="margin:6px 0 0">${esc(d.guide)}</p>
        <div class="words">${d.words.map(w => `<span class="chip">${esc(w.word)} — ${esc(w.meaning)}</span>`).join("")}</div></div>`).join("") + `</div>`;
    case "tones": return `<div class="lesson-block"><div class="tones-grid">` + b.items.map(t =>
      `<div class="tone-item"><div class="word">${esc(t.word)}</div><div class="pattern">${esc(t.pattern)}</div><div class="meaning">${esc(t.meaning)}</div></div>`).join("") + `</div></div>`;
    case "table": return `<div class="lesson-block"><table class="data-table"><tr>${b.head.map(h => `<th>${esc(h)}</th>`).join("")}</tr>` +
      b.rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("") + `</table></div>`;
    case "words": return `<div class="lesson-block"><div class="words-grid">` +
      b.items.map(w => `<div class="word-cell"><div class="w">${esc(w.word)}</div><div class="m">${esc(w.meaning)}</div></div>`).join("") + `</div></div>`;
    default: return "";
  }
}

async function pageQuiz(id) {
  if (!state.content) await loadContent();
  const meta = state.content.quizzes.find(q => q.id === id);
  if (!meta) return `<section class="section"><div class="alert alert-warn">Quiz not found. <a href="#/learn">Back to lessons</a></div></section>`;
  if (!state.user) {
    return `<section class="section"><div class="alert alert-gate"><strong>Create a free account to take quizzes and save your scores.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account?mode=register">Create free account</a></div></div>
      <a class="btn btn-ghost" href="#/learn">Back to lessons</a></section>`;
  }
  if (!hasTier(meta.tier)) {
    return `<section class="section">${gateCard(meta.tier, "This quiz")}
      <a class="btn btn-ghost" href="#/learn">Back to lessons</a></section>`;
  }
  const res = await api("/api/quiz/" + id);
  const quiz = res.data;
  const picks = state.quizPicks[id] || (state.quizPicks[id] = []);
  const result = state.quizResults[id];
  let html = `<section class="section">
    <a class="btn btn-ghost" href="#/lesson/${meta.lesson}">← Back to lesson</a>
    <div class="card mt-16">
      <span class="badge">${esc(meta.tier === "free" ? "Igbo Foundation" : "Survival Igbo")}</span>
      <h1 style="font-size:clamp(1.4rem,3vw,1.9rem);margin-top:10px">${esc(quiz.title)}</h1>`;
  if (result) {
    html += `<div class="score-banner ${result.passed ? "pass" : "fail"} mt-16">
      ${result.passed ? "Passed" : "Not passed"} — ${result.score} of ${result.total} correct
      ${result.passed ? "" : "(you need 70% to pass — try again, you're close)"}</div>`;
  }
  html += quiz.questions.map((q, i) => {
    const picked = picks[i];
    const rev = result && result.review[i];
    let opts = q.options.map((o, oi) => {
      let cls = "quiz-opt";
      let disabled = "";
      if (result) {
        disabled = " disabled";
        if (oi === rev.answer) cls += " correct";
        else if (oi === rev.given) cls += " wrong";
      } else if (picked === oi) cls += " picked";
      return `<button class="${cls}" data-q="${i}" data-o="${oi}"${disabled}>${esc(o)}</button>`;
    }).join("");
    const explain = rev ? `<div class="quiz-explain">${esc(rev.explain)}</div>` : "";
    return `<div class="quiz-q"><div class="q-text">${i + 1}. ${esc(q.q)}</div>${opts}${explain}</div>`;
  }).join("");
  html += result
    ? `<div style="display:flex;gap:10px;flex-wrap:wrap">
        <a class="btn btn-primary" href="#/lesson/${meta.lesson}">Back to the lesson</a>
        <button class="btn btn-outline" id="retake">Try again</button></div>`
    : `<button class="btn btn-primary" id="submit-quiz" ${picks.filter(p => p != null).length < quiz.questions.length ? "disabled" : ""}>Submit answers</button>
       <p class="form-note">Answer every question to submit. You need 70% to pass.</p>`;
  html += `</div></section>`;
  return html;
}

async function pageFlashcards() {
  if (!state.user) {
    return `<section class="section"><div class="alert alert-gate"><strong>Create a free account to use the flashcards.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account?mode=register">Create free account</a></div></div></section>`;
  }
  const res = await api("/api/flashcards");
  state.fcQueue = res.data.cards || [];
  state.fcIndex = 0;
  state.fcFlipped = false;
  return `<section class="section">
    <div class="section-head"><div class="eyebrow">Spaced repetition</div>
      <h2>Flashcards</h2>
      <p>${hasTier("survival")
        ? "Your full deck. Cards you know come back less often; cards you miss come back sooner."
        : "Free preview: the letters and tone cards. The full deck unlocks with Survival Igbo."}</p>
    </div>
    <div class="fc-scene" id="fc-scene"></div>
  </section>`;
}

function renderFlashcard() {
  const el = document.getElementById("fc-scene");
  if (!el) return;
  const cards = state.fcQueue;
  if (!cards.length) {
    el.innerHTML = `<div class="card center"><h3>All done for now 🎉</h3>
      <p class="muted">No cards are due. Come back later — the schedule spaces your reviews so you remember more with less effort.</p>
      <a class="btn btn-outline" href="#/learn">Back to lessons</a></div>`;
    return;
  }
  const card = cards[state.fcIndex];
  const dueTotal = cards.length;
  const face = state.fcFlipped
    ? `<div class="back">${esc(card.back)}</div><div class="back-sub">${esc(card.front)}</div>`
    : `<div class="front">${esc(card.front)}</div><div class="hint">Tap or press Space to reveal</div>`;
  el.innerHTML = `
    <div class="fc-stats"><span>Card ${state.fcIndex + 1} of ${dueTotal} due</span><span>Box ${card.box}/4</span></div>
    <div class="fc-card" id="fc-card">
      <span class="group-chip">${esc(card.group)}</span>
      <span class="box-chip">${"★".repeat(card.box) || "new"}</span>
      ${face}
    </div>
    ${state.fcFlipped
      ? `<div class="fc-actions">
          <button class="btn btn-outline" id="fc-no">I didn't know it (2)</button>
          <button class="btn btn-primary" id="fc-yes">I knew it (1)</button>
        </div>`
      : `<div class="fc-actions"><button class="btn btn-primary" id="fc-flip">Show answer (Space)</button></div>`}
    <div class="key-hint">Keyboard: Space = reveal · 1 = knew it · 2 = didn't know it</div>`;
  const cardEl = document.getElementById("fc-card");
  cardEl.addEventListener("click", () => { if (!state.fcFlipped) { state.fcFlipped = true; renderFlashcard(); } });
  const flip = document.getElementById("fc-flip");
  if (flip) flip.addEventListener("click", () => { state.fcFlipped = true; renderFlashcard(); });
  const yes = document.getElementById("fc-yes");
  const no = document.getElementById("fc-no");
  if (yes) yes.addEventListener("click", () => reviewCard(card.id, true));
  if (no) no.addEventListener("click", () => reviewCard(card.id, false));
}

async function reviewCard(cardId, knew) {
  await api("/api/flashcards/review", { method: "POST", body: { card_id: cardId, knew } });
  state.fcFlipped = false;
  state.fcIndex += 1;
  if (state.fcIndex >= state.fcQueue.length) {
    // refresh the queue for the next round
    const res = await api("/api/flashcards");
    state.fcQueue = res.data.cards || [];
    state.fcIndex = 0;
  }
  renderFlashcard();
}

async function pageFluency() {
  if (!state.user) {
    return `<section class="section"><div class="alert alert-gate"><strong>Sign in to use the Fluency Kit tools.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account?mode=register">Create free account</a></div></div></section>`;
  }
  if (!hasTier("fluency")) {
    return `<section class="section">${gateCard("fluency", "The Fluency Kit tools")}
      <div class="grid grid-2 mt-16">
        <div class="card"><h3>What's inside</h3>
          <ul class="tier-list"><li>Full spaced-repetition flashcard deck</li>
          <li>Writing practice with a dotted-letter pad</li>
          <li>6 dialogue scenes</li><li>12 proverbs (ilu) with meanings</li>
          <li>Certificate of completion</li></ul></div>
        <div class="card"><h3>Who it's for</h3>
          <p class="muted">Heritage learners who understand some Igbo and want to speak and write it —
          and families who want to go past survival words into real conversation.</p></div>
      </div></section>`;
  }
  const tab = state.fluencyTab;
  let body = "";
  if (tab === "dialogues") {
    const res = await api("/api/dialogues");
    body = (res.data.dialogues || []).map(d => `
      <div class="card mt-16"><span class="badge">Dialogue</span>
        <h3 class="mt-8">${esc(d.title)}</h3>
        <p class="muted">${esc(d.scene)}</p>
        ${d.lines.map(l => `<div class="dlg-line"><div class="speaker">${esc(l.speaker)}</div>
          <div><div class="igbo">${esc(l.igbo)}</div><div class="english">${esc(l.english)}</div></div></div>`).join("")}
      </div>`).join("");
  } else if (tab === "proverbs") {
    const res = await api("/api/proverbs");
    body = (res.data.proverbs || []).map(p => `
      <div class="proverb-card"><div class="igbo">${esc(p.igbo)}</div>
        <div class="english">${esc(p.english)}</div>
        <div class="meaning">${esc(p.meaning)}</div></div>`).join("");
  } else {
    const res = await api("/api/writing-practice");
    body = `<div class="alert alert-info">Type the Igbo for each prompt. Use the letter pad for the dotted
      letters ị ọ ụ ṅ and tone marks. Both dotted and undotted spellings are accepted while you practise —
      the goal is the dotted one.</div>` +
      (res.data.items || []).map(w => `
      <div class="wp-item" data-wp="${w.id}">
        <div class="prompt">${esc(w.prompt)}</div>
        <input class="wp-input" type="text" placeholder="Type the Igbo here…" autocomplete="off" autocapitalize="off" spellcheck="false">
        <div class="letter-pad">
          ${["ị", "ọ", "ụ", "ṅ", "á", "à", "í", "ì", "ó", "ò", "ú", "ù"].map(ch =>
            `<button type="button" data-ch="${ch}">${ch}</button>`).join("")}
        </div>
        <button class="btn btn-primary btn-small wp-check">Check</button>
        <button class="btn btn-ghost btn-small wp-hint-btn">Hint</button>
        <div class="wp-hint" hidden>${esc(w.hint)}</div>
        <div class="wp-result" hidden></div>
      </div>`).join("");
  }
  return `<section class="section">
    <div class="section-head"><div class="eyebrow">Igbo Fluency Kit</div>
      <h2>Practice tools</h2></div>
    <div class="tabs">
      <button data-tab="dialogues" class="${tab === "dialogues" ? "active" : ""}">Dialogues</button>
      <button data-tab="proverbs" class="${tab === "proverbs" ? "active" : ""}">Proverbs (ilu)</button>
      <button data-tab="writing" class="${tab === "writing" ? "active" : ""}">Writing practice</button>
    </div>
    <div id="fluency-body">${body}</div>
  </section>`;
}

async function pageCertificate() {
  if (!state.user) {
    return `<section class="section"><div class="alert alert-gate"><strong>Sign in to see your certificate.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account?mode=register">Create free account</a></div></div></section>`;
  }
  const res = await api("/api/certificate");
  const d = res.data;
  if (!d.eligible) {
    return `<section class="section">
      <div class="section-head"><div class="eyebrow">Certificate</div>
        <h2>Your certificate is waiting</h2>
        <p>Finish the Igbo Fluency Kit and we will issue a downloadable certificate with your name on it.</p></div>
      <div class="alert alert-warn">${esc(d.reason || "Not eligible yet.")}</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <a class="btn btn-primary" href="#/learn">Go to lessons</a>
        ${hasTier("fluency") ? "" : `<a class="btn btn-gold" href="#/pricing">Get the Fluency Kit</a>`}
      </div></section>`;
  }
  return `<section class="section">
    <div class="section-head"><div class="eyebrow">Certificate</div>
      <h2>Congratulations!</h2></div>
    <div class="certificate">
      <div class="cert-title">Certificate of Completion</div>
      <div class="muted">Igbo Mastery — Igbo Fluency Kit</div>
      <div class="muted" style="margin-top:18px">This certifies that</div>
      <div class="cert-name">${esc(d.name || state.user.name)}</div>
      <div class="muted">has completed every lesson and passed every quiz of the Igbo Fluency Kit:
        tones, alphabet, dotted letters, survival Igbo, flashcards, writing practice, dialogues and proverbs (ilu).</div>
      <div class="cert-meta">Certificate number: ${esc(d.serial)}<br>Issued: ${esc((d.issued_at || "").slice(0, 10))}</div>
      <div class="mt-24"><button class="btn btn-primary" id="cert-download">Download certificate (PDF)</button></div>
    </div></section>`;
}

function pageAccount() {
  const mode = new URLSearchParams(location.hash.split("?")[1] || "").get("mode") || "login";
  if (state.user) {
    const s = progressStats();
    return `<section class="section">
      <div class="section-head"><div class="eyebrow">Your account</div><h2>Hello, ${esc(state.user.name || "friend")}</h2></div>
      <div class="grid grid-2">
        <div class="card">
          <h3>Your plan</h3>
          <p><span class="badge ${state.user.tier === "free" ? "" : "gold"}">${esc(state.user.tier_name)}</span></p>
          ${state.user.tier === "free"
            ? `<p class="muted">You are on the free foundation. Upgrade once to keep learning.</p>
               <a class="btn btn-primary" href="#/pricing">See pricing</a>`
            : `<p class="muted">Full access active. Thank you for learning with us.</p>
               <a class="btn btn-outline" href="#/learn">Continue learning</a>`}
        </div>
        <div class="card">
          <h3>Your progress</h3>
          ${s ? progressBarHTML() : `<p class="muted">Start a lesson to see your progress.</p>`}
          <div class="mt-16"><button class="btn btn-ghost" id="check-payments">Check for a payment I just made</button></div>
        </div>
      </div>
      <div class="mt-24"><button class="btn btn-ghost" id="logout-btn2">Sign out</button></div>
    </section>`;
  }
  const isReg = mode === "register";
  return `<section class="section">
    <div class="form-card card">
      <h1 style="font-size:1.6rem">${isReg ? "Create your free account" : "Sign in"}</h1>
      <p class="muted">${isReg
        ? "One account, free forever for the foundation course. Your progress is saved automatically."
        : "Welcome back. Your progress and purchases are waiting."}</p>
      <div class="form-error" id="auth-error" hidden></div>
      <form id="auth-form">
        ${isReg ? `<div class="field"><label for="f-name">Your name</label>
          <input id="f-name" type="text" autocomplete="name" required></div>` : ""}
        <div class="field"><label for="f-email">Email address</label>
          <input id="f-email" type="email" autocomplete="email" required></div>
        <div class="field"><label for="f-pass">Password</label>
          <input id="f-pass" type="password" autocomplete="${isReg ? "new-password" : "current-password"}" required minlength="8"></div>
        <button class="btn btn-primary btn-block" type="submit">${isReg ? "Create account" : "Sign in"}</button>
      </form>
      <p class="form-note">${isReg
        ? `Already have an account? <a href="#/account">Sign in</a>`
        : `New here? <a href="#/account?mode=register">Create a free account</a>`}</p>
    </div>
  </section>`;
}

function pagePaymentComplete() {
  const ref = new URLSearchParams(location.hash.split("?")[1] || "").get("reference");
  if (!state.user) {
    return `<section class="section"><div class="alert alert-gate"><strong>Sign in to confirm your payment.</strong>
      <div class="mt-16"><a class="btn btn-primary" href="#/account">Sign in</a></div></div></section>`;
  }
  return `<section class="section">
    <div class="card center" style="max-width:560px;margin:0 auto">
      <h2>Confirming your payment…</h2>
      <p class="muted" id="pay-status">One moment please.</p>
    </div>
  </section>`;
}

async function confirmPayment() {
  const ref = new URLSearchParams(location.hash.split("?")[1] || "").get("reference");
  const statusEl = document.getElementById("pay-status");
  if (!ref) { statusEl.textContent = "No payment reference found."; return; }
  const res = await api("/api/paystack/verify?reference=" + encodeURIComponent(ref));
  const d = res.data || {};
  if (d.status === "success") {
    saveSession(token(), d.user);
    await refreshProgress();
    statusEl.innerHTML = `<strong style="color:var(--green-dark)">Payment confirmed — thank you!</strong><br>
      Your access is active. <a class="btn btn-primary mt-16" href="#/learn">Start learning</a>`;
    toast("Payment confirmed. Your course is unlocked.");
  } else if (d.status === "pending") {
    statusEl.innerHTML = `We are still confirming your payment with the bank.<br>
      You can safely close this page — your account is checked automatically every time you sign in,
      and access appears the moment the payment clears.
      <div class="mt-16"><a class="btn btn-outline" href="#/account">Go to my account</a></div>`;
  } else {
    statusEl.innerHTML = `We could not confirm this payment (${esc(d.error || "please contact us")}).<br>
      If money left your account, email <a href="mailto:hello@igbomastery.com">hello@igbomastery.com</a>
      with your reference: <code>${esc(ref)}</code> and we will fix it manually.
      <div class="mt-16"><a class="btn btn-outline" href="#/account">Go to my account</a></div>`;
  }
}

/* ---------------- legal ---------------- */
function pageTerms() {
  return `<section class="section legal"><div class="legal-card">
    <h1>Terms of Service</h1>
    <p class="updated">Last updated: 26 September 2026</p>
    <h2>1. What this is</h2>
    <p>Igbo Mastery is an online course that teaches the Igbo language. When you create an account, you agree to these terms. If you do not agree, please do not use the site.</p>
    <h2>2. Your account</h2>
    <p>You are responsible for keeping your password private and for what happens under your account. Please tell us straight away if you think someone else has used your account.</p>
    <h2>3. The free course</h2>
    <p>The Igbo Foundation course is free to use. It teaches the tones, the alphabet, the dotted letters and your first words. We may improve or add to it over time.</p>
    <h2>4. Paid courses and payments</h2>
    <ul>
      <li>Survival Igbo costs ₦500 and the Igbo Fluency Kit costs ₦2,000. Both are one-time payments.</li>
      <li>There is no subscription. You pay once and keep access.</li>
      <li>Payments are processed by Paystack. We never see or store your full card details.</li>
      <li>International cards (Visa, Mastercard, Verve, and American Express where offered) are accepted. Your bank converts the charge to your own currency at its own rate.</li>
    </ul>
    <h2>5. If a payment goes wrong</h2>
    <p>If your bank takes the money but your access does not appear, email us at <a href="mailto:hello@igbomastery.com">hello@igbomastery.com</a> with the reference from your payment page. We check every payment record and will restore your access. We will never ask you for your card number or PIN.</p>
    <h2>6. Refunds</h2>
    <p>If something is genuinely wrong with what you bought — for example access fails to activate after payment — we will refund you or fix it, your choice. Because the course content is available immediately after purchase, we cannot offer “changed my mind” refunds, but we will always help if something breaks.</p>
    <h2>7. Using the content fairly</h2>
    <p>The lessons, quizzes, flashcards, dialogues, proverbs and certificate are for your personal learning. Please do not copy and resell them. Sharing what you learn — and encouraging others to learn Igbo — is always welcome.</p>
    <h2>8. The certificate</h2>
    <p>The certificate is issued when you complete every lesson and pass every quiz in the Igbo Fluency Kit. It records your achievement in this course. It is not a school, university or government qualification.</p>
    <h2>9. Changes</h2>
    <p>We may update these terms as the service grows. If we make an important change, we will post the new version here with a new date.</p>
    <h2>10. Contact</h2>
    <p>Questions about these terms? Email <a href="mailto:hello@igbomastery.com">hello@igbomastery.com</a>.</p>
  </div></section>`;
}

function pagePrivacy() {
  return `<section class="section legal"><div class="legal-card">
    <h1>Privacy Policy</h1>
    <p class="updated">Last updated: 26 September 2026</p>
    <h2>What we collect</h2>
    <ul>
      <li><strong>Your account details:</strong> the name and email address you give us when you sign up.</li>
      <li><strong>Your learning progress:</strong> which lessons and quizzes you have completed, and your flashcard review history.</li>
      <li><strong>Payment records:</strong> when you buy a course, our payment provider (Paystack) records the transaction. We keep a record of the amount, date and a reference number — not your card details.</li>
    </ul>
    <h2>Why we collect it</h2>
    <ul>
      <li>To create and protect your account.</li>
      <li>To save your progress so you can continue where you left off.</li>
      <li>To unlock the course you paid for, and to fix any payment that fails to go through.</li>
      <li>To send you important emails about your account or your purchases (for example a receipt, or your certificate).</li>
    </ul>
    <h2>What we do not do</h2>
    <ul>
      <li>We do not sell your personal information.</li>
      <li>We do not use your learning data to train AI models.</li>
      <li>We do not send you marketing emails unless you ask for them.</li>
    </ul>
    <h2>Who else sees your data</h2>
    <p>We use a small number of trusted services to run the site: a payment processor (Paystack) to take payments, an email service (Brevo) to send account emails, and a hosting provider to keep the site online. They only see what they need to do their job.</p>
    <h2>Cookies</h2>
    <p>We use your browser's local storage to keep you signed in and to remember your progress. We do not use advertising cookies.</p>
    <h2>How long we keep it</h2>
    <p>We keep your account and progress for as long as your account is open. Payment records are kept for as long as the law requires. You can ask us to delete your account at any time by emailing us.</p>
    <h2>Your choices</h2>
    <p>You can ask us what information we hold about you, correct it, or delete your account. Email <a href="mailto:hello@igbomastery.com">hello@igbomastery.com</a> and we will take care of it.</p>
    <h2>Children</h2>
    <p>The course is designed to be used by families together. Children should use it with a parent or guardian, who manages the account.</p>
    <h2>Contact</h2>
    <p>Any privacy question, big or small: <a href="mailto:hello@igbomastery.com">hello@igbomastery.com</a>.</p>
  </div></section>`;
}

/* ---------------- data loading ---------------- */
async function loadContent() {
  const res = await api("/api/content");
  state.content = res.data;
}

async function refreshProgress() {
  const res = await api("/api/progress/summary");
  if (res.ok) state.progress = res.data;
}

/* ---------------- payment ---------------- */
let paystackConfig = null;
async function getPaystackKey() {
  if (paystackConfig) return paystackConfig.paystack_public_key;
  const res = await api("/api/config");
  paystackConfig = res.data;
  return paystackConfig.paystack_public_key;
}

async function buy(tier) {
  if (!state.user) { location.hash = "#/account?mode=register"; toast("Create your free account first, then choose your course."); return; }
  if (hasTier(tier)) { toast("You already own this course."); return; }
  const key = await getPaystackKey();
  if (!key) { toast("Payments are being set up. Please check back soon."); return; }
  let init;
  try {
    const res = await api("/api/paystack/initialize", { method: "POST", body: { tier } });
    init = res.data;
    if (!res.ok) { toast(init.error || "We could not start the payment. Please try again."); return; }
  } catch (e) { toast("We could not reach the payment provider. Please try again."); return; }
  if (typeof PaystackPop === "undefined") { toast("Payment window could not load. Please refresh and try again."); return; }
  const amounts = { survival: 50000, fluency: 200000 };
  const handler = PaystackPop.setup({
    key,
    email: state.user.email,
    amount: amounts[tier],
    currency: "NGN",
    ref: init.reference,
    metadata: { tier },
    callback: function (response) {
      location.hash = "#/payment-complete?reference=" + encodeURIComponent(response.reference);
    },
    onClose: function () {
      toast("Payment window closed. If you completed the payment, sign in again and your access appears automatically.");
      location.hash = "#/account";
    },
  });
  handler.openIframe();
}

async function checkPayments() {
  const btn = document.getElementById("check-payments");
  if (btn) { btn.disabled = true; btn.innerHTML = `<span class="spinner"></span> Checking…`; }
  const res = await api("/api/paystack/reconcile");
  const d = res.data || {};
  if (res.ok && d.user) {
    saveSession(token(), d.user);
    await refreshProgress();
    toast(d.user.tier !== "free" ? "Your account is up to date." : "No new payments found yet — if you just paid, give it a minute and check again.");
  } else {
    toast("We could not check right now. Please try again in a minute.");
  }
  if (btn) { btn.disabled = false; btn.textContent = "Check for a payment I just made"; }
}

/* ---------------- router ---------------- */
async function render() {
  const hash = location.hash || "#/";
  const [path, qs] = hash.slice(1).split("?");
  const parts = path.split("/").filter(Boolean);
  setActiveNav();
  let html = "";
  try {
    if (!parts.length) html = pageHome();
    else if (parts[0] === "pricing") html = pagePricing();
    else if (parts[0] === "learn") html = await pageLearn();
    else if (parts[0] === "lesson") html = await pageLesson(parts[1]);
    else if (parts[0] === "quiz") html = await pageQuiz(parts[1]);
    else if (parts[0] === "flashcards") html = await pageFlashcards();
    else if (parts[0] === "fluency") html = await pageFluency();
    else if (parts[0] === "certificate") html = await pageCertificate();
    else if (parts[0] === "account") html = pageAccount();
    else if (parts[0] === "terms") html = pageTerms();
    else if (parts[0] === "privacy") html = pagePrivacy();
    else if (parts[0] === "payment-complete") html = pagePaymentComplete();
    else html = `<section class="section"><div class="alert alert-warn">Page not found. <a href="#/">Go home</a></div></section>`;
  } catch (e) {
    console.error(e);
    html = `<section class="section"><div class="alert alert-warn">Something went wrong loading this page. Please <a href="#/">go home</a> and try again.</div></section>`;
  }
  $app.innerHTML = html;
  window.scrollTo(0, 0);
  afterRender(parts, qs);
}

function afterRender(parts, qs) {
  // buy buttons
  document.querySelectorAll("[data-buy]").forEach(b =>
    b.addEventListener("click", () => buy(b.getAttribute("data-buy"))));
  // mark lesson done
  const md = document.getElementById("mark-done");
  if (md) md.addEventListener("click", async () => {
    md.disabled = true;
    const res = await api("/api/progress/complete", { method: "POST", body: { item_id: md.getAttribute("data-lesson"), item_type: "lesson" } });
    if (res.ok) {
      await refreshProgress();
      toast("Lesson completed. Progress saved.");
      render();
    } else {
      md.disabled = false;
      toast(res.data && res.data.error ? res.data.error : "Could not save. Please try again.");
    }
  });
  // quiz options
  const quizMatch = parts[0] === "quiz";
  if (quizMatch) {
    const quizId = parts[1];
    document.querySelectorAll(".quiz-opt[data-q]").forEach(btn =>
      btn.addEventListener("click", () => {
        if (state.quizResults[quizId]) return;
        const q = +btn.getAttribute("data-q"), o = +btn.getAttribute("data-o");
        const picks = state.quizPicks[quizId] || (state.quizPicks[quizId] = []);
        picks[q] = o;
        document.querySelectorAll(`.quiz-opt[data-q="${q}"]`).forEach(x => x.classList.remove("picked"));
        btn.classList.add("picked");
        const submit = document.getElementById("submit-quiz");
        const total = document.querySelectorAll(".quiz-q").length;
        if (submit) submit.disabled = picks.filter(p => p != null).length < total;
      }));
    const submit = document.getElementById("submit-quiz");
    if (submit) submit.addEventListener("click", () => submitQuiz(quizId));
    const retake = document.getElementById("retake");
    if (retake) retake.addEventListener("click", () => {
      delete state.quizPicks[quizId];
      delete state.quizResults[quizId];
      render();
    });
  }
  // flashcards
  if (parts[0] === "flashcards") renderFlashcard();
  // keyboard for flashcards
  document.onkeydown = (e) => {
    if (parts[0] !== "flashcards") return;
    if (e.code === "Space") {
      e.preventDefault();
      if (!state.fcFlipped) { state.fcFlipped = true; renderFlashcard(); }
    } else if (e.key === "1" && state.fcFlipped) {
      const card = state.fcQueue[state.fcIndex];
      if (card) reviewCard(card.id, true);
    } else if (e.key === "2" && state.fcFlipped) {
      const card = state.fcQueue[state.fcIndex];
      if (card) reviewCard(card.id, false);
    }
  };
  // fluency tabs
  if (parts[0] === "fluency") {
    document.querySelectorAll(".tabs button").forEach(b =>
      b.addEventListener("click", () => { state.fluencyTab = b.getAttribute("data-tab"); render(); }));
    // letter pad
    document.querySelectorAll(".letter-pad button").forEach(b =>
      b.addEventListener("click", () => {
        const input = b.closest(".wp-item").querySelector(".wp-input");
        const ch = b.getAttribute("data-ch");
        const pos = input.selectionStart || input.value.length;
        input.value = input.value.slice(0, pos) + ch + input.value.slice(pos);
        input.focus();
        input.selectionStart = input.selectionEnd = pos + ch.length;
      }));
    // check / hint buttons
    document.querySelectorAll(".wp-item").forEach(item => {
      const id = item.getAttribute("data-wp");
      const input = item.querySelector(".wp-input");
      const result = item.querySelector(".wp-result");
      const hint = item.querySelector(".wp-hint");
      item.querySelector(".wp-check").addEventListener("click", async () => {
        if (!input.value.trim()) { input.focus(); return; }
        const res = await api("/api/writing-practice/check", { method: "POST", body: { id, answer: input.value } });
        const d = res.data || {};
        result.hidden = false;
        if (d.correct && d.dotted) { result.className = "wp-result ok"; result.textContent = "Correct! Ọ dị mma."; }
        else if (d.correct && !d.dotted) { result.className = "wp-result ok"; result.textContent = d.note || "Correct — remember the dotted letter."; }
        else { result.className = "wp-result bad"; result.textContent = "Not quite. The answer is: " + (d.answer || "—"); }
      });
      item.querySelector(".wp-hint-btn").addEventListener("click", () => { hint.hidden = !hint.hidden; });
    });
  }
  // auth form
  const form = document.getElementById("auth-form");
  if (form) {
    const errEl = document.getElementById("auth-error");
    const isReg = !!document.getElementById("f-name");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errEl.hidden = true;
      const email = document.getElementById("f-email").value.trim();
      const password = document.getElementById("f-pass").value;
      const name = isReg ? document.getElementById("f-name").value.trim() : undefined;
      const res = await api(isReg ? "/api/auth/register" : "/api/auth/login",
        { method: "POST", body: isReg ? { email, password, name } : { email, password } });
      if (res.ok) {
        saveSession(res.data.token, res.data.user);
        await refreshProgress();
        toast(isReg ? "Welcome to Igbo Mastery! Your free foundation is ready." : "Welcome back!");
        location.hash = "#/learn";
        render();
      } else {
        errEl.textContent = (res.data && res.data.error) || "Something went wrong. Please try again.";
        errEl.hidden = false;
      }
    });
  }
  // account extras
  const cp = document.getElementById("check-payments");
  if (cp) cp.addEventListener("click", checkPayments);
  const lo = document.getElementById("logout-btn2");
  if (lo) lo.addEventListener("click", logout);
  // certificate download (authenticated fetch -> blob)
  const cd = document.getElementById("cert-download");
  if (cd) cd.addEventListener("click", async () => {
    cd.disabled = true; cd.textContent = "Preparing…";
    try {
      const res = await fetch(API_BASE + "/api/certificate/pdf", {
        headers: { "Authorization": "Bearer " + token() },
      });
      if (!res.ok) { toast("The certificate could not be downloaded. Please try again."); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "igbo-mastery-certificate.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast("Certificate downloaded.");
    } catch (e) {
      toast("The certificate could not be downloaded. Please try again.");
    } finally {
      cd.disabled = false; cd.textContent = "Download certificate (PDF)";
    }
  });
  // payment complete page
  if (parts[0] === "payment-complete") confirmPayment();
  // mobile nav
  const toggle = document.getElementById("nav-toggle");
  if (toggle) toggle.addEventListener("click", () => document.getElementById("main-nav").classList.toggle("open"));
}

async function submitQuiz(quizId) {
  const picks = state.quizPicks[quizId] || [];
  const res = await api("/api/quiz/submit", { method: "POST", body: { quiz_id: quizId, answers: picks } });
  const d = res.data || {};
  if (res.ok) {
    state.quizResults[quizId] = d;
    await refreshProgress();
    render();
    toast(d.passed ? `Passed — ${d.score}/${d.total}. Ọ dị mma!` : `${d.score}/${d.total} — review the lesson and try again.`);
  } else {
    toast(d.error || "Could not submit. Please try again.");
  }
}

/* ---------------- boot ---------------- */
document.getElementById("year").textContent = new Date().getFullYear();
try {
  const savedUser = localStorage.getItem(USER_KEY);
  if (savedUser && token()) {
    state.user = JSON.parse(savedUser);
    // confirm with the server (also reconciles any pending payment)
    api("/api/auth/me").then(res => {
      if (res.ok) {
        const before = state.user && state.user.tier;
        state.user = res.data.user;
        localStorage.setItem(USER_KEY, JSON.stringify(state.user));
        if (before && before !== "free" && state.user.tier !== before) {
          toast("Your access has been updated.");
        }
      } else {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        state.user = null;
      }
      renderHeaderActions();
      render();
    });
  } else {
    renderHeaderActions();
    render();
  }
} catch (e) {
  renderHeaderActions();
  render();
}
window.addEventListener("hashchange", render);
