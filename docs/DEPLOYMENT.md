# CiteRight — Deployment Guide

Follow these steps in order. Each section is self-contained — do one, confirm it works, then move to the next.

---

## Step 1 — Test Supabase persistence locally

**1.1 Run the schema**
- Supabase dashboard → **SQL Editor** → **New query**
- Paste the full contents of `supabase/schema.sql`
- Click **Run**
- You should see "Success. No rows returned"

**1.2 Update your local `.env`**
Add this line (with your real password — the one you rotated after sharing it earlier):
```
SUPABASE_DB_URL=postgresql://postgres.lbbamoxmzvzlcuprwulb:yournewpassword@aws-1-ap-south-1.pooler.supabase.com:6543/postgres
```

**1.3 Install the new dependencies**
```bash
cd citeright
pip install -r requirements.txt
```

**1.4 Restart the backend**
```bash
uvicorn app.main:app --reload
```
Check the terminal — you should see:
```
[document_manager] SUPABASE_DB_URL set — using persistent Supabase pgvector store.
```
If you instead see the "using in-memory store" message, your `.env` isn't being picked up — double check the variable name and that there's no typo.

**1.5 The actual persistence test**
- Upload a document in the UI, note the `document_id` shown ("ready — xxxxxxxx")
- Generate a draft, confirm it works
- **Stop the uvicorn server (Ctrl+C) and restart it**
- Try generating again using the same document (don't re-upload)
- ✅ If it still works — persistence is confirmed
- ❌ If you get a "document not found" error — something's wrong, come back and tell me what happened

**1.6 Check Supabase directly (optional but satisfying)**
- Supabase dashboard → **Table Editor** → `documents` and `chunks` tables
- You should see rows there matching what you uploaded

---

## Step 2 — Push the updated code to GitHub

Once Step 1 passes, commit and push the changes:
```bash
git add .
git status   # double-check .env is NOT listed — it should be gitignored
git commit -m "Add Supabase pgvector persistence layer"
git push
```

---

## Step 3 — Deploy the backend to Render

**3.1 Create account & new service**
- Go to **render.com** → sign up (GitHub login recommended)
- Dashboard → **New** → **Web Service**
- Connect your GitHub account if prompted, select your `citeright` repo

**3.2 Configure the service**
| Setting | Value |
|---|---|
| Name | `citeright-api` (or anything) |
| Region | closest to you |
| Branch | `main` |
| Root Directory | *(leave blank — backend is at repo root)* |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

**3.3 Add environment variables**
In the same setup screen (or Settings → Environment after creating), add:
| Key | Value |
|---|---|
| `GROQ_API_KEY` | your real Groq key |
| `SUPABASE_DB_URL` | your real Supabase connection string |

**3.4 Deploy**
- Click **Create Web Service**
- Watch the build logs — first deploy takes a few minutes (installing `sentence-transformers`/`torch` is the slow part)
- Once live, Render gives you a URL like `https://citeright-api.onrender.com`

**3.5 Test it**
Visit `https://citeright-api.onrender.com/health` in your browser — should return `{"status":"ok"}`.
Visit `https://citeright-api.onrender.com/docs` — should show the interactive API docs.

**Note on free tier:** Render's free web services spin down after ~15 minutes of inactivity and take ~30-60 seconds to wake up on the next request. This is normal — just means the first request after idle time will be slow. Worth mentioning if you demo this live to someone.

---

## Step 4 — Deploy the frontend to Vercel

**4.1 Import the project**
- Go to **vercel.com** → sign up (GitHub login recommended)
- **Add New** → **Project** → import your `citeright` repo

**4.2 Configure the build**
| Setting | Value |
|---|---|
| Framework Preset | Vite (should auto-detect) |
| Root Directory | `frontend` — **important, click "Edit" and set this** |
| Build Command | `npm run build` (default, leave as-is) |
| Output Directory | `dist` (default, leave as-is) |

**4.3 Add environment variable**
| Key | Value |
|---|---|
| `VITE_API_BASE` | your Render URL from Step 3, e.g. `https://citeright-api.onrender.com` (no trailing slash) |

**4.4 Deploy**
- Click **Deploy**
- Takes ~1-2 minutes
- Vercel gives you a URL like `https://citeright.vercel.app`

**4.5 Test it**
Open the Vercel URL. Upload a document, pick a mode, generate a draft — this is now the fully live, deployed version.

---

## Step 5 — Tighten CORS (optional but recommended)

Right now the backend allows requests from any origin (`allow_origins=["*"]`) — fine for getting things working, but worth locking down once you know your real Vercel URL. In `app/main.py`, change:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```
to:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://citeright.vercel.app"],  # your actual Vercel URL
    ...
)
```
Commit, push — Render auto-redeploys on every push to `main`.

---

## Step 6 — Final checklist

- [ ] Backend `/health` returns OK on the live Render URL
- [ ] Frontend loads on the live Vercel URL
- [ ] Upload → generate works end-to-end on the live site (not localhost)
- [ ] Trust score, citation stamps, source drawer all work on the live site
- [ ] Restarting/redeploying the backend doesn't lose previously uploaded documents (Supabase persistence working)
- [ ] `.env` files are NOT in the GitHub repo (spot-check on github.com)
- [ ] README's live demo link (add this once deployed) points to the real Vercel URL

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Render build fails on `sentence-transformers` install | Free tier can be slow/memory-limited for the torch install — check build logs for the actual error, may need to retry |
| Frontend loads but upload fails with a network/CORS error | `VITE_API_BASE` env var wrong, or CORS `allow_origins` doesn't include your Vercel URL |
| "Document not found" after Render redeploys | Check Render logs for the `[document_manager]` startup message — confirms whether `SUPABASE_DB_URL` was actually picked up |
| Generation always returns `mock` backend | `GROQ_API_KEY` env var missing/wrong on Render — double check under Render → Settings → Environment |
| First request after idle is very slow | Normal — Render free tier cold start, not a bug |

---

Whenever you hit a step that doesn't work as described, come back with the exact error message or screenshot and we'll debug it together.
