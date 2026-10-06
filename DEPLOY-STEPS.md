# Deploying Igbo Mastery — plain steps, one at a time
Follow these in order. Each step is one action. Nothing here needs code.

---

## Step 1 — Create your database (Neon, free)

1. Go to https://neon.com and click **Sign up** (use your Google account if easier).
2. Click **Create project**. Name it `igbo-mastery`. Choose any region close to you.
3. When the project opens, find **Connection string** and click **Copy**.
   It looks like: `postgresql://user:password@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`
4. Paste it into a note on your phone. You will need it in Step 3.

## Step 2 — Create your Paystack keys

1. Go to https://dashboard.paystack.com and sign in.
2. Click **Settings** (the gear icon) → **API Keys & Webhooks**.
3. Copy your **Test Secret Key** (starts with `sk_test_`) and **Test Public Key**
   (starts with `pk_test_`) into your note.
4. Stay on this page — you will add the webhook address in Step 8.

## Step 3 — Create your email key (Brevo, free)

1. Go to https://www.brevo.com and click **Sign up free** (no card needed).
2. In the dashboard, click your name (top right) → **SMTP & API** → **API keys**.
3. Click **Generate a new API key**. Copy it into your note.
4. Click **Senders, Domains & Dedicated IPs** → **Add a sender**. Use your name and
   an email you can receive mail at. Confirm it from your inbox.
5. Write down the sender email you just confirmed.

## Step 4 — Put the project online (GitHub)

1. Go to https://github.com and sign up if you do not have an account.
2. Click **New repository**. Name it `igbo-mastery`. Set it **Private**. Click **Create**.
3. On your computer, open the project folder `igbo-mastery`.
4. Delete the file `igbo_mastery.db` if you see it (it is only a local test file).
5. Upload all the files: click **uploading an existing file** on the repository page,
   then drag the whole `igbo-mastery` folder contents in. Click **Commit changes**.

## Step 5 — Deploy the backend (Render, free)

1. Go to https://render.com and sign up with your GitHub account.
2. Click **New +** → **Web Service**. Choose your `igbo-mastery` repository.
3. Fill in:
   - **Name:** `igbo-mastery-api`
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn backend:app --bind 0.0.0.0:$PORT`
   - **Instance type:** Free
4. Before clicking deploy, scroll to **Environment Variables** and add these
   **one by one** (this matters — service-level variables are the ones that count):
   - `DATABASE_URL` = your Neon connection string from Step 1
   - `JWT_SECRET` = any long random text, e.g. `igbo-mastery-jwt-9f27c1d4e8b3a56`
   - `PAYSTACK_SECRET_KEY` = your `sk_test_...` key from Step 2
   - `PAYSTACK_PUBLIC_KEY` = your `pk_test_...` key from Step 2
   - `BREVO_API_KEY` = your Brevo key from Step 3
   - `BREVO_SENDER_EMAIL` = the sender email you confirmed in Step 3
   - `BREVO_SENDER_NAME` = `Igbo Mastery`
   - `FRONTEND_ORIGIN` = leave empty for now (you will fill it in Step 7)
5. Click **Create Web Service** and wait for "Live" to appear (2–4 minutes).
6. Copy your service address, e.g. `https://igbo-mastery-api.onrender.com`.

## Step 6 — Point the frontend at the backend

1. Open `frontend/app.js` in any text editor (Notepad is fine).
2. Find the line that says `const API_BASE = "https://igbo-mastery-api.onrender.com";`
3. Replace the address with your real Render address from Step 5.6.
4. Save the file. Commit the change to GitHub (upload the changed file again).

## Step 7 — Deploy the website (Netlify, free)

1. Go to https://netlify.com and sign up with GitHub.
2. Click **Add new site** → **Deploy manually**.
3. Drag the **frontend** folder onto the page. Wait for the deploy to finish.
4. Click **Site settings** → **Change site name** and choose something clean like
   `igbo-mastery`. Your site address is now `https://igbo-mastery.netlify.app`.
5. Go back to Render → your service → **Environment** → edit `FRONTEND_ORIGIN`
   to your Netlify address (no trailing slash) → **Save changes**. Render will
   restart automatically.
6. In Netlify, click **Deploys** → **Trigger deploy** → **Deploy site** once more.

> ⚠️ Netlify gives every deploy a temporary address like
> `6789abc-igbo-mastery.netlify.app` that search engines are told to ignore.
> **Only ever share the clean name you chose in step 7.4.**

## Step 8 — Connect Paystack properly

1. In Paystack dashboard → **Settings** → **API Keys & Webhooks**:
   - **Webhook URL:** `https://igbo-mastery-api.onrender.com/api/paystack/webhook`
     (use your real Render address). Click **Save**.
   - **Test mode:** keep the toggle ON while testing.
2. Click **Settings** → **Preferences** → find **Accept international payments**
   and tick it. If it asks for your CAC documents, submit them — approval takes
   a few working days. (Local Nigerian cards work either way.)
3. Check your **Settings → General**: make sure **"Pass transaction fees to
   customer"** is **OFF**. If it is on, customers are charged a different amount
   than your course price and their access will not unlock. Leave it off.

## Step 9 — Test everything (15 minutes, do not skip)

1. Open your Netlify address. You should see the homepage.
2. Click **Start the free foundation** → create an account with your real email.
   Check your inbox for the welcome email (look in spam too).
3. Complete lesson 1 and take the first quiz. Confirm the progress bar moves.
4. Click **Pricing** → **Buy Survival Igbo — ₦500**.
5. In the Paystack popup, use a test card: card number `4084 0840 8408 4081`,
   any future expiry, CVV `408`, and any OTP.
6. You should land on a "Payment confirmed" page. Go to **Learn** — the
   Survival Igbo lessons should now be unlocked.
7. Close the payment popup early on a second test to confirm the safety net:
   pay, close the popup, then sign out and back in — access should appear anyway.

## Step 10 — Go live with real money

1. In Paystack, complete your business verification (CAC/BVN as prompted).
2. When approved, toggle **Test mode** OFF.
3. Replace the test keys in Render (Step 5.4) with your **live** keys
   (`sk_live_...` and `pk_live_...`). Save. Render restarts.
4. Make one real ₦500 purchase yourself, then refund yourself from the Paystack
   dashboard (**Transactions** → find it → **Refund**).
5. You are live. Start posting the videos from the marketing folder.

---

## If something looks wrong

| What you see | What to do |
|---|---|
| Site shows "API error" or nothing loads | Check `API_BASE` in app.js matches your Render address exactly |
| "Payments are not switched on yet" | Your Paystack keys are missing in Render environment variables |
| Payment succeeded but content is locked | Sign out, sign back in (this re-checks payments). Still stuck? Email hello@igbomastery.com with the reference |
| No welcome email | Check Brevo API key and that your sender email is confirmed in Brevo |
| Render says "service unavailable" | Free services sleep after inactivity — open the site once and wait 30 seconds |

## The one habit that saves you

**Whenever you change an environment variable in Render, click Save changes and
wait for the automatic restart.** Restarting the service by hand does not reload
variables — this is the single most common deployment mistake.
