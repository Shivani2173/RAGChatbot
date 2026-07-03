# 🚀 Deployment Guide — Streamlit Community Cloud

## Prerequisites
- GitHub account
- Groq API key (free at [console.groq.com](https://console.groq.com))

---

## Step 1 — Push the Repo to GitHub

```bash
# In your project folder
git init
git add .
git commit -m "Initial commit — Groww MF RAG Chatbot"
git remote add origin https://github.com/YOUR_USERNAME/RAGChatbot.git
git push -u origin main
```

> **Important**: The FAISS index (`vector_store/`), processed text (`data/processed/`),
> and chunks (`data/chunks/`) are **committed to the repo** so Streamlit Cloud
> can serve the chatbot immediately without running the ingestion pipeline.

---

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.
2. Click **"New app"**.
3. Fill in the form:

   | Field | Value |
   |---|---|
   | **Repository** | `YOUR_USERNAME/RAGChatbot` |
   | **Branch** | `main` |
   | **Main file path** | `src/ui/app.py` |
   | **App URL** | Choose a custom slug (e.g. `groww-mf-assistant`) |

4. Click **"Advanced settings"** and add the secret:

   ```toml
   GROQ_API_KEY = "gsk_your_actual_key_here"
   ```

5. Click **"Deploy!"** — the app will be live in ~2 minutes.

---

## Step 3 — Activate the Daily Refresh Scheduler

The GitHub Actions workflow (`.github/workflows/daily_refresh.yml`) runs every day
at **10:30 AM IST** and refreshes the FAISS index automatically.

To activate it:
1. Go to your GitHub repo → **Settings → Secrets and variables → Actions**
2. Click **"New repository secret"**:
   - Name: `GROQ_API_KEY`
   - Value: your Groq API key

The workflow will commit the refreshed index to the repo, and Streamlit Cloud will
pick it up automatically on the next app reload.

---

## Architecture on Deployment

```
GitHub Repo (main branch)
    ├── src/ui/app.py           ← Streamlit Cloud serves this
    ├── vector_store/           ← FAISS index (committed, refreshed by scheduler)
    ├── data/processed/         ← Parsed text (committed)
    └── .github/workflows/      ← Daily refresh cron

GitHub Actions (daily at 10:30 IST)
    └── Runs pipeline → commits refreshed index → Streamlit Cloud auto-updates
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| App shows "LLM not configured" | Add `GROQ_API_KEY` in App Settings → Secrets |
| App shows "I could not find this info" | Click **Reload Index** in the sidebar |
| Deployment fails on install | Check `requirements.txt` has all packages |
| GitHub Actions fails | Check `GROQ_API_KEY` secret is added in repo settings |
