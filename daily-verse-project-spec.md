# Daily Verse — Project Spec

A working spec for a static website that, once a day, scrapes the day's news, identifies a unifying theme, and pairs it with a Bible verse and short reflection. Built to run hands-off on a free tier with a daily cron job.

> Status: brainstorming / pre-implementation. Recommendations are marked as such; open questions are listed at the end.

---

## 1. Vision

Every morning, a quiet page updates with one verse, one reflection, and a brief note on the day's news that prompted it. The tone is contemplative rather than reactive — closer to a daily devotional than a hot take. Visitors can read today's entry or browse the archive.

The whole thing should run itself: a scheduled job pulls news, calls an LLM, writes a file, and the site rebuilds. No manual intervention needed for normal operation.

## 2. Goals & non-goals

**Goals**
- Publish one new entry per day, automatically, indefinitely.
- Keep editorial tone thoughtful and non-partisan (see §7).
- Stay on free hosting tiers; LLM costs under $5/month.
- Make the archive readable and searchable over time.

**Non-goals (at least for v1)**
- User accounts, comments, or community features.
- Real-time updates or breaking-news pairings.
- Theological argument or commentary beyond a short reflection.
- Multiple verses per day, multiple translations, or per-topic feeds.

## 3. Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│  RSS feeds /    │────▶│ Daily script │────▶│ entries/       │
│  news API       │     │ (Python)     │     │ YYYY-MM-DD.md  │
└─────────────────┘     └──────┬───────┘     └────────┬───────┘
                               │                      │
                               ▼                      ▼
                        ┌──────────────┐     ┌────────────────┐
                        │ Claude API   │     │ Astro site     │
                        │ (verse pick) │     │ (rebuild)      │
                        └──────────────┘     └────────┬───────┘
                                                      │
                                                      ▼
                                             ┌────────────────┐
                                             │ Cloudflare /   │
                                             │ Netlify Pages  │
                                             └────────────────┘
```

The daily script and the site rebuild both run inside a single GitHub Actions workflow. The script writes a markdown file with frontmatter into the `entries/` directory; the site treats those files as content and rebuilds; the host auto-deploys on push.

## 4. Recommended tech stack

| Concern | Recommendation | Why |
|---|---|---|
| Site framework | **Astro** | Static-first, content collections fit markdown entries naturally, fast builds. |
| Hosting | **Cloudflare Pages** (or Netlify) | Free tier, auto-deploy from GitHub, generous bandwidth. |
| Scheduler | **GitHub Actions cron** | Free for public repos, runs the script + commits + triggers redeploy. |
| Daily script language | **Python** | Best ecosystem for RSS parsing and LLM calls; easy to read later. |
| News ingestion | **`feedparser`** over RSS | No API keys, no scraping fragility, generous rate limits. |
| LLM | **Claude (Sonnet or Haiku)** | Good at the task; Haiku is cheaper if quality holds up. |
| Bible text | Bundled JSON of a public-domain translation (WEB or KJV) | No external dependency at runtime; no rate limits. |
| Optional later | Vector store (sqlite + sqlite-vec) for embedding-based verse search | Only needed if v1's quality drifts. |

## 5. Daily pipeline, in detail

### 5.1 News ingestion
Pull RSS feeds from a small curated list of outlets — aim for roughly 4–8 sources spanning international, national, and feature coverage. Take the top 5–10 headlines from each (title + summary + link), dedupe on title similarity, and trim to a final shortlist of 15–25 stories.

Store the raw shortlist in the daily entry's frontmatter so it's auditable later — you can always tell what the AI was looking at when it picked the verse.

### 5.2 Theme extraction
Send the shortlist to Claude with a prompt asking it to identify 2–3 dominant *themes* across the day's news, expressed as biblical/moral concepts (e.g., "displacement and exile," "civic discord," "the cost of pride," "hope amid uncertainty"). This intermediate step keeps the verse selection from being mechanically tied to a single headline.

### 5.3 Verse selection + reflection
A second prompt (or same call, structured output) asks Claude to:
- Pick **one** verse appropriate to the dominant theme.
- Provide the full citation: book, chapter:verse, translation.
- Write a **2–4 sentence reflection** connecting the verse to the day's theme without naming specific people, parties, or events in a partisan way.

To minimize fabrication risk, the prompt should require Claude to choose from a curated list of verses you ship with the project — say 1,500–3,000 well-known passages — rather than generate any verse it remembers. The script then validates the chosen verse exists in the bundled Bible JSON before committing.

### 5.4 Output
The script writes `entries/YYYY-MM-DD.md` with frontmatter:

```yaml
---
date: 2026-04-30
verse_ref: "Isaiah 40:31"
verse_text: "But those who wait for Yahweh will renew their strength..."
translation: "WEB"
themes: ["weariness", "endurance", "hope"]
news_summary: "Across today's coverage, themes of exhaustion and..."
sources:
  - title: "..."
    url: "..."
    outlet: "Reuters"
---

[The reflection goes here as the body.]
```

Astro reads these as a content collection. Today's page shows the latest; `/archive` lists all entries by date.

### 5.5 Scheduling
A GitHub Actions workflow runs daily (e.g., 6:00 AM in your timezone). It:
1. Sets up Python, installs dependencies.
2. Runs the daily script, which writes the new markdown file.
3. Commits the file with a date-stamped message.
4. Pushes to `main`.
5. Cloudflare Pages picks up the push and rebuilds.

If the script fails (LLM timeout, RSS down), the workflow exits non-zero and you get an email. The site stays on the previous day's entry.

## 6. Bible text handling

Use a public-domain translation so there's no licensing concern. **World English Bible (WEB)** is a modern, readable choice; **KJV** is the traditional alternative. Both are available as JSON or USFM dumps from sources like ebible.org and bible-databases on GitHub.

Ship the chosen translation as a single JSON file (`data/bible-web.json`, ~5 MB). Index it as `{book: {chapter: {verse: text}}}` so the script can validate any reference in O(1).

If you want to use a copyrighted translation later (NIV, ESV, NRSV) you'd need to use API.Bible with proper attribution and respect their caching/usage rules.

## 7. Editorial guidelines

This is the most important and most easily underestimated part of the project. The AI will do whatever you tell it; you have to tell it the right things.

**Default tone.** Contemplative, not declarative. The reflection should *invite* a reading, not deliver a verdict. A reader of any political stripe should be able to read it without feeling preached at.

**Themes to lean toward.** Mercy, lament, wisdom, humility, patience, hope, the long view of history, care for the vulnerable.

**Themes to handle carefully.** Judgment passages, prophetic literature read as current-events prediction, anything that could be heard as condoning violence, prosperity-gospel framings, supersessionist readings, end-times speculation triggered by news.

**Hard rules to encode in the prompt.**
- Do not pair a verse about judgment, wickedness, or destruction with a story about an identifiable group of people.
- Do not interpret current events as fulfillment of prophecy.
- If the day's news is dominated by a tragedy with active victims, prefer verses of lament or comfort over verses about justice or consequence.

**Translation consistency.** Pick one translation and stick with it. Mixing translations across days makes the archive feel sloppy.

**Length discipline.** Reflection: 2–4 sentences. Hard cap. Anything longer drifts toward sermon.

Write these guidelines as an `EDITORIAL.md` in the repo and paste relevant excerpts into the system prompt.

## 8. Repo structure

```
daily-verse/
├── .github/workflows/
│   └── daily.yml              # cron + commit
├── data/
│   ├── bible-web.json         # bundled translation
│   └── verse-shortlist.json   # ~2000 curated verses for selection
├── scripts/
│   ├── daily.py               # the main pipeline
│   ├── prompts/
│   │   ├── theme.txt
│   │   └── verse.txt
│   └── feeds.yaml             # list of RSS sources
├── site/                      # Astro project
│   ├── src/
│   │   ├── content/
│   │   │   └── entries/       # markdown files written by daily.py
│   │   ├── pages/
│   │   │   ├── index.astro    # today's entry
│   │   │   └── archive.astro  # list of all entries
│   │   └── layouts/
│   └── astro.config.mjs
├── EDITORIAL.md
└── README.md
```

## 9. Cost estimate

| Item | Monthly cost |
|---|---|
| GitHub Actions (public repo) | $0 |
| Cloudflare Pages | $0 |
| Claude API (Haiku, ~3k tokens/day) | ~$0.30 |
| Claude API (Sonnet, ~3k tokens/day) | ~$1.50 |
| Domain (optional) | ~$1 (annualized) |
| **Total** | **under $3/month** |

## 10. MVP scope (first ship)

The smallest version worth deploying:
- 5 hard-coded RSS feeds.
- One Claude call per day that does theme + verse + reflection in one structured response.
- Verse must be validated against the bundled Bible JSON; if invalid, retry once, then fall back to a default verse for the day's themes.
- Astro site with two pages: today, and a date-sorted archive.
- GitHub Actions cron, manual trigger button enabled for testing.
- Basic typography, no fancy design.

Skip in MVP: subscriptions, RSS output, search, sharing buttons, multiple translations, embeddings.

## 11. Phase 2 ideas

- RSS feed for the site so people can subscribe in their reader.
- Email digest (weekly or daily) via a service like Buttondown.
- Embedding-based verse selection: pre-embed all verses, embed the daily theme, retrieve top 30, let the LLM choose. Better fidelity to scripture, costs a bit more setup.
- "On this day in past years" sidebar showing previous entries on the same date.
- Liturgical calendar awareness (Advent, Lent, etc.) influencing verse selection.
- Multiple translations toggle.
- Per-day permalink with Open Graph image generated from the verse.

## 12. Questions

1. **Translation.** Let's use KJV.
2. **News scope.** International news with a US focus, also include culture/sports, etc.
3. **Outlet selection.** Which 4–8 RSS sources? Up to you.
4. **Verse pool size.** The entire bible.
5. **Time zone for the cron.** What "day" does the entry represent? Use EST.
6. **Failure mode.** If the script fails, leave yesterday's entry visible, or show a fallback "no entry today"? up to you.
7. **Project naming and tone.** Devotional? Civic? Literary? The name sets reader expectations. Up to you.

## 13. Risks

- **Verse fabrication.** The LLM might invent or misquote a verse. *Mitigation: validation against bundled Bible JSON.*
- **Editorial drift.** Over time, the LLM's pairings might trend in a direction you don't intend. *Mitigation: review the archive monthly; refine the system prompt.*
- **News source bias.** Whatever feeds you pick will color the themes. *Mitigation: deliberate, balanced source selection; document the choices in EDITORIAL.md.*
- **Burnout / boredom.** Daily content sites have a high mortality rate. *Mitigation: full automation from day one; you should never have to babysit it.*
- **Sensitive-day failures.** A mass-casualty news day could produce a verse pairing that lands very wrong. *Mitigation: a "high-sensitivity" detector that, when triggered, defaults to a small allowlist of comfort/lament verses and skips the more interpretive logic.*

---

## Suggested next steps

1. Decide on the 7 open questions in §12.
2. Stand up an empty repo with the structure in §8.
3. Write `EDITORIAL.md` first, before any code.
4. Build the daily script end-to-end with hard-coded inputs, then wire up GitHub Actions.
5. Build the Astro site last — by then you'll have a week of real entries to design against.
