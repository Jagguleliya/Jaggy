# YouTube Shorts Bot — Setup Guide 🚀

Complete step-by-step guide. Total setup time: ~15-20 minutes.

## Prerequisites
- **Windows 10/11** with Python 3.10+ installed
- **Google account** with a YouTube channel
- **Internet connection**

---

## Step 1: Install the Bot (2 minutes)

Double-click **`install.bat`** OR run manually:
```bash
cd C:\Users\HPP\.gemini\antigravity\scratch\youtube-shorts-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2: Get API Keys (10 minutes)

### 2a. Google Gemini API Key (FREE)
1. Go to https://aistudio.google.com
2. Click **"Get API Key"** → **"Create API key"**
3. Paste in `config/config.yaml` → `api_keys.gemini`

### 2b. Pexels API Key (FREE)
1. Go to https://www.pexels.com/api/
2. Create account → Copy API key
3. Paste in `config/config.yaml` → `api_keys.pexels`

### 2c. Reddit API (FREE)
1. Go to https://www.reddit.com/prefs/apps
2. Click **"Create another app..."**
3. Name: `youtube-shorts-bot`, Type: **script**, Redirect: `http://localhost:8080`
4. Copy Client ID + Secret → Paste in config under `api_keys.reddit_client_id` and `api_keys.reddit_client_secret`

### 2d. YouTube OAuth (FREE — one-time setup)
1. Go to https://console.cloud.google.com → Create new project
2. Enable **YouTube Data API v3** and **YouTube Analytics API**
3. Go to **OAuth consent screen** → External → Add your email as test user
4. Go to **Credentials** → Create **OAuth client ID** → Desktop app
5. Download JSON → Save as `config/credentials.json`
6. Run:
```bash
venv\Scripts\activate
python setup_oauth.py
```
7. Browser opens → Sign in → Grant permissions → Token saved automatically

### 2e. X (Twitter) API (FREE — Optional)
1. Go to https://developer.x.com → Free access
2. Generate API Key, Secret, Access Token, Access Token Secret
3. Paste in config under `platforms.x_twitter`

### 2f. Facebook Page (FREE — Optional)
1. Create a Facebook Page → Go to https://developers.facebook.com
2. Create app → Add Pages API → Generate Page Access Token
3. Paste in config under `platforms.facebook`

---

## Step 3: Record Your 2 Clips (5 minutes)

No face needed! Record with your phone in **portrait/vertical mode**:

**Clip 1 — "Desk Shot" (15-20 seconds):**
Hand at desk: pointing at screen, scrolling phone, writing

**Clip 2 — "Reaction Gestures" (15-20 seconds):**
Hand gestures: thumbs up, mind-blown, clapping, OK sign

Save as:
- `user_clips/clip_1_desk.mp4`
- `user_clips/clip_2_reaction.mp4`

---

## Step 4: Download Free Music (5 minutes)

Get 5-10 royalty-free tracks from:
- **YouTube Audio Library** (YouTube Studio → Audio Library)
- **Pixabay Music** — https://pixabay.com/music/
- **Free Music Archive** — https://freemusicarchive.org

Organize in `data/music/` by mood: upbeat, mysterious, dramatic, chill, inspiring

---

## Step 5: Test (2 minutes)

```bash
venv\Scripts\activate

# Test without uploading
python main.py --dry-run

# Test with upload
python main.py
```

---

## Step 6: Automate Daily (3 minutes)

1. Press **Win+R** → `taskschd.msc` → Enter
2. **Create Basic Task** → Name: `YouTube Shorts Bot`
3. Trigger: **Daily** → Set time (e.g., 10:00 AM)
4. Action: **Start a program**
   - Program: `C:\Users\HPP\.gemini\antigravity\scratch\youtube-shorts-bot\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\Users\HPP\.gemini\antigravity\scratch\youtube-shorts-bot`
5. Check "Run whether user is logged on or not"

Optional: Add second task for engagement at 6:00 PM with args: `main.py --engage-only`

---

## Commands Reference

| Command | What it does |
|---|---|
| `python main.py` | Full pipeline (generate + upload + engage) |
| `python main.py --dry-run` | Generate video without uploading |
| `python main.py --mode clips` | Force clip curation mode |
| `python main.py --mode original` | Force original content mode |
| `python main.py --engage-only` | Reply to comments only |
| `python main.py --report` | Show weekly performance report |
| `python main.py --analytics-only` | Collect analytics data only |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| ModuleNotFoundError | Run `venv\Scripts\activate` first |
| OAuth token expired | Run `python setup_oauth.py` again |
| No music files found | Download tracks to `data/music/` folders |
| YouTube upload failed | Run `python setup_oauth.py --verify` |
| Video looks wrong | Run `--dry-run` and check output folder |
