"""Run the full verification suite for Igbo Mastery.
Usage:  python3 run_tests.py        (safe to run any time; uses a temporary database)"""
import os, sys, json, hmac, hashlib

os.environ.setdefault("PAYSTACK_SECRET_KEY", "sk_test_secret_key")
os.environ.setdefault("PAYSTACK_PUBLIC_KEY", "pk_test_public_key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-verification-only")
os.environ.pop("DATABASE_URL", None)
os.environ["BREVO_API_KEY"] = ""  # email disabled during tests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TEST_DB = "/tmp/igbo_mastery_test.db"
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

import backend
backend.SQLITE_PATH = TEST_DB  # keep the real database untouched
from unittest import mock

backend.init_db()
c = backend.app.test_client()
P = []
def check(name, cond, extra=""):
    P.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

r = c.get("/api/health"); check("health", r.status_code == 200 and r.get_json()["database"] == "sqlite")
r = c.get("/api/config"); check("config has public key", r.get_json()["paystack_public_key"] == "pk_test_public_key")

r = c.post("/api/auth/register", json={"email": "ada@example.com", "name": "Ada", "password": "password123"})
check("register 201", r.status_code == 201, r.data)
tok1 = r.get_json()["token"]
r = c.post("/api/auth/register", json={"email": "ada@example.com", "name": "Ada", "password": "password123"})
check("duplicate register 409", r.status_code == 409)
r = c.post("/api/auth/register", json={"email": "x@y.com", "name": "X", "password": "short"})
check("weak password 400", r.status_code == 400)
r = c.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong"})
check("bad login 401", r.status_code == 401)
r = c.post("/api/auth/login", json={"email": "ada@example.com", "password": "password123"})
tok1 = r.get_json()["token"]; H1 = {"Authorization": f"Bearer {tok1}"}
r = c.get("/api/auth/me", headers=H1)
check("me ok", r.status_code == 200 and r.get_json()["user"]["tier"] == "free")
r = c.get("/api/auth/me"); check("me without token 401", r.status_code == 401)
r = c.post("/api/auth/register", json={"email": "chi@example.com", "name": "Chi", "password": "password123"})
tok2 = r.get_json()["token"]; H2 = {"Authorization": f"Bearer {tok2}"}

r = c.get("/api/content"); j = r.get_json()
check("12 lessons", len(j["lessons"]) == 12)
check("8 quizzes", len(j["quizzes"]) == 8)
check("72 flashcards", j["flashcard_count"] == 72)
check("6 dialogues + 12 proverbs", j["dialogue_count"] == 6 and j["proverb_count"] == 12)

r = c.post("/api/progress/complete", headers=H1, json={"item_id": "igbo-at-a-glance", "item_type": "lesson"})
check("complete free lesson", r.status_code == 200)
r = c.post("/api/progress/complete", headers=H1, json={"item_id": "greetings", "item_type": "lesson"})
check("paid lesson blocked 403", r.status_code == 403 and r.get_json().get("need") == "survival")
r = c.get("/api/quiz/quiz-foundation-tones")
check("quiz hides answers", len(r.get_json()["questions"]) == 5 and "answer" not in r.get_json()["questions"][0])
r = c.post("/api/quiz/submit", headers=H1, json={"quiz_id": "quiz-foundation-tones", "answers": [0,3,0,1,1]})
j = r.get_json(); check("quiz all correct", j.get("score") == 5 and j.get("passed") is True, j)
r = c.post("/api/quiz/submit", headers=H1, json={"quiz_id": "quiz-greetings", "answers": [0,3,0,1,1]})
check("paid quiz blocked 403", r.status_code == 403)

r = c.get("/api/flashcards", headers=H1)
cards = r.get_json()["cards"]
check("free gets preview cards only", all(x["group"] in ("Letters","Tones") for x in cards))
r = c.post("/api/flashcards/review", headers=H1, json={"card_id": cards[0]["id"], "knew": True})
check("review knew -> box 1", r.get_json()["box"] == 1)
r = c.post("/api/flashcards/review", headers=H1, json={"card_id": cards[0]["id"], "knew": False})
check("review forgot -> box 0", r.get_json()["box"] == 0)
for ep in ["/api/dialogues", "/api/proverbs", "/api/writing-practice"]:
    r = c.get(ep, headers=H1)
    check(f"{ep} blocked for free", r.status_code == 403 and r.get_json().get("need") == "fluency")
r = c.get("/api/certificate", headers=H1)
check("certificate blocked", r.get_json()["eligible"] is False)

def fake_init(*a, **k):
    class R:
        status_code = 200
        def json(self):
            return {"status": True, "data": {"authorization_url": "https://paystack.test/pay/abc",
                                             "access_code": "ac_1", "reference": "ref-1"}}
    return R()

with mock.patch("backend.requests.post", side_effect=fake_init):
    r = c.post("/api/paystack/initialize", headers=H1, json={"tier": "survival"})
check("initialize ok", r.status_code == 200 and r.get_json()["authorization_url"].startswith("https://"), r.data)
ref_surv = r.get_json()["reference"]
pay = backend.get_payment_by_reference(ref_surv)
check("payment pending row", pay["status"] == "pending" and pay["amount"] == 50000 and pay["tier"] == "survival")
r = c.get(f"/api/paystack/verify?reference={ref_surv}", headers=H2)
check("verify other user's payment 403", r.status_code == 403)
with mock.patch("backend.verify_with_paystack", return_value=("success", 40000)):
    r = c.get(f"/api/paystack/verify?reference={ref_surv}", headers=H1)
check("underpayment refused", r.get_json()["outcome"] == "underpayment", r.data)
check("tier still free after underpayment", backend.get_user_by_email("ada@example.com")["tier"] == "free")
with mock.patch("backend.verify_with_paystack", return_value=("success", 60000)):
    r = c.get(f"/api/paystack/verify?reference={ref_surv}", headers=H1)
check("amount mismatch refused", r.get_json()["outcome"] == "amount_mismatch", r.data)
check("tier still free after mismatch", backend.get_user_by_email("ada@example.com")["tier"] == "free")
with mock.patch("backend.verify_with_paystack", return_value=("success", 50000)):
    r = c.get(f"/api/paystack/verify?reference={ref_surv}", headers=H1)
j = r.get_json()
check("exact payment grants survival", j.get("outcome") == "granted" and j.get("tier") == "survival", j)
with mock.patch("backend.verify_with_paystack", return_value=("success", 50000)):
    r = c.get(f"/api/paystack/verify?reference={ref_surv}", headers=H1)
check("re-verify idempotent", r.get_json()["outcome"] == "already" and r.get_json()["tier"] == "survival", r.data)
r = c.post("/api/progress/complete", headers=H1, json={"item_id": "greetings", "item_type": "lesson"})
check("survival lesson now allowed", r.status_code == 200)
r = c.get("/api/flashcards", headers=H1)
check("full deck unlocked", len(r.get_json()["cards"]) > 60)
r = c.get("/api/dialogues", headers=H1)
check("dialogues still locked until fluency", r.status_code == 403)

with mock.patch("backend.requests.post", side_effect=fake_init):
    r = c.post("/api/paystack/initialize", headers=H2, json={"tier": "fluency"})
ref_flu = r.get_json()["reference"]
with mock.patch("backend.verify_with_paystack", return_value=("success", 200000)):
    r = c.get(f"/api/paystack/verify?reference={ref_flu}", headers=H2)
check("fluency granted to user2", r.get_json()["tier"] == "fluency")
u2 = backend.get_user_by_email("chi@example.com")
ref_s2 = "IGB-SUR-DOWNGRADETEST"
backend.execute("INSERT INTO payments(user_id,reference,tier,amount,currency,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (u2["id"], ref_s2, "survival", 50000, "NGN", "pending", backend.now_iso(), backend.now_iso()))
outcome = backend.fulfil(backend.get_payment_by_reference(ref_s2), "success", 50000, "test")
check("no downgrade on lower purchase", outcome == "no_downgrade" and backend.get_user_by_email("chi@example.com")["tier"] == "fluency", outcome)
with mock.patch("backend.requests.post", side_effect=fake_init):
    r = c.post("/api/paystack/initialize", headers=H2, json={"tier": "fluency"})
check("re-init owned tier 400", r.status_code == 400)

secret = b"sk_test_secret_key"
event = {"event": "charge.success", "data": {"reference": ref_surv, "status": "success", "amount": 50000}}
body = json.dumps(event).encode()
good_sig = hmac.new(secret, body, hashlib.sha512).hexdigest()
r = c.post("/api/paystack/webhook", data=body, headers={"x-paystack-signature": good_sig, "content-type": "application/json"})
check("webhook valid signature 200", r.status_code == 200)
r = c.post("/api/paystack/webhook", data=body, headers={"x-paystack-signature": "deadbeef", "content-type": "application/json"})
check("webhook bad signature 401", r.status_code == 401)

with mock.patch("backend.requests.post", side_effect=fake_init):
    r = c.post("/api/auth/register", json={"email": "nkechi@example.com", "name": "Nkechi", "password": "password123"})
tok3 = r.get_json()["token"]; H3 = {"Authorization": f"Bearer {tok3}"}
with mock.patch("backend.requests.post", side_effect=fake_init):
    r = c.post("/api/paystack/initialize", headers=H3, json={"tier": "fluency"})
ref_h = r.get_json()["reference"]
with mock.patch("backend.verify_with_paystack", return_value=("success", 200000)):
    r = c.get("/api/auth/me", headers=H3)
check("me self-heals pending payment", r.get_json()["user"]["tier"] == "fluency", r.data)
r = c.get("/api/paystack/reconcile", headers=H1)
check("reconcile endpoint works", r.status_code == 200 and "outcomes" in r.get_json())

uid = backend.get_user_by_email("nkechi@example.com")["id"]
for l in backend.LESSONS:
    backend.execute("INSERT OR IGNORE INTO progress(user_id,item_id,item_type,created_at) VALUES (?,?,?,?)",
                    (uid, l["id"], "lesson", backend.now_iso()))
for q in backend.QUIZZES:
    backend.execute("INSERT INTO quiz_results(user_id,quiz_id,score,total,created_at) VALUES (?,?,?,?,?)",
                    (uid, q["id"], len(q["questions"]), len(q["questions"]), backend.now_iso()))
r = c.get("/api/certificate", headers=H3)
j = r.get_json()
check("certificate eligible + serial", j.get("eligible") and j.get("serial", "").startswith("IGBO-FLUENCY-"), j)
r = c.get("/api/certificate/pdf", headers=H3)
check("certificate PDF generated", r.status_code == 200 and r.data[:4] == b"%PDF", r.status_code)
r = c.get("/api/certificate/pdf", headers=H1)
check("certificate PDF blocked for incomplete user", r.status_code == 403)
r = c.post("/api/writing-practice/check", headers=H3, json={"id": "wp-5", "answer": "ụlọ"})
check("writing check exact", r.get_json().get("correct") and r.get_json().get("dotted"), r.data)
r = c.post("/api/writing-practice/check", headers=H3, json={"id": "wp-5", "answer": "ulo"})
check("writing check accepts undotted", r.get_json().get("correct") and not r.get_json().get("dotted"), r.data)
r = c.post("/api/writing-practice/check", headers=H3, json={"id": "wp-5", "answer": "akpu"})
check("writing check rejects wrong", not r.get_json().get("correct"))

for p in ["/backend.py", "/.env", "/render.yaml", "/requirements.txt", "/.git/config", "/../backend.py"]:
    r = c.get(p)
    check(f"404 for {p}", r.status_code == 404, r.status_code)

print(f"\n=== {sum(1 for _, ok in P if ok)}/{len(P)} passed ===")
fails = [n for n, ok in P if not ok]
if fails:
    print("FAILED:", fails); sys.exit(1)
print("ALL CHECKS PASSED")
