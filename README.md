# Daily Verse

## Run locally

```bash
pip install -r requirements.txt
python scripts/download_bible.py
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/daily.py
cd site && npm install && npm run dev
```

## Deploy

1. Push repo to GitHub
2. Add `ANTHROPIC_API_KEY` as a repository secret (Settings → Secrets → Actions)
3. Connect repo to Cloudflare Pages with build command `cd site && npm install && npm run build` and output directory `site/dist`
4. Add custom domain in Cloudflare Pages → Custom domains
