# Daily Verse

A static website that scrapes the day's news, identifies a unifying theme, and pairs it with a Bible verse and short reflection. Publishes automatically once a day via GitHub Actions.

## How it works

1. A GitHub Actions cron job runs daily at 6 AM EST.
2. `scripts/daily.py` fetches RSS headlines, calls the Claude API, validates the verse against the bundled KJV Bible, and writes a markdown entry to `site/src/content/entries/`.
3. The entry is committed and pushed to `main`.
4. Cloudflare Pages (or Netlify) picks up the push and rebuilds the Astro site.

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Download the Bible JSON

The KJV Bible (~5 MB) is downloaded at runtime to keep the repo lean:

```bash
python scripts/download_bible.py
```

This writes `data/bible-kjv.json`.

### 3. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run the daily script manually

```bash
python scripts/daily.py
```

This writes today's entry to `site/src/content/entries/YYYY-MM-DD.md`.

### 5. Run the Astro site locally

```bash
cd site
npm install
npm run dev
```

## Deployment

### GitHub Actions

Add `ANTHROPIC_API_KEY` as a repository secret in **Settings → Secrets → Actions**.

The workflow (`.github/workflows/daily.yml`) runs automatically at 6 AM EST and on manual trigger (`workflow_dispatch`).

### Cloudflare Pages

1. Connect the GitHub repo.
2. Set build command: `cd site && npm install && npm run build`
3. Set publish directory: `site/dist`

## Repo structure

```
daily-verse/
├── .github/workflows/daily.yml   # cron + commit workflow
├── data/
│   └── bible-kjv.json            # KJV (downloaded, not committed)
├── scripts/
│   ├── daily.py                  # main pipeline
│   ├── download_bible.py         # one-time Bible download
│   ├── prompts/
│   │   └── system.txt            # Claude system prompt
│   └── feeds.yaml                # RSS sources
├── site/                         # Astro project
│   └── src/
│       ├── content/entries/      # markdown entries (written by daily.py)
│       ├── pages/                # index, archive, [date]
│       └── layouts/
├── EDITORIAL.md                  # editorial principles
└── README.md
```

## Cost

| Item | Monthly |
|---|---|
| GitHub Actions (public repo) | $0 |
| Cloudflare Pages | $0 |
| Claude Haiku (~3k tokens/day) | ~$0.30 |
| **Total** | **< $1/month** |

## Editorial principles

See [EDITORIAL.md](EDITORIAL.md). The short version: contemplative, non-partisan, 2–4 sentence reflections. The verse is validated against the bundled Bible JSON to prevent fabrication.
