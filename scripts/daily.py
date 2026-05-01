#!/usr/bin/env python3
"""Daily Verse pipeline: fetch news → extract theme → select verse → write entry."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import anthropic
import feedparser
import yaml

BASE_DIR = Path(__file__).parent.parent
BIBLE_PATH = BASE_DIR / "data" / "bible-kjv.json"
ENTRIES_DIR = BASE_DIR / "site" / "src" / "content" / "entries"
FEEDS_PATH = Path(__file__).parent / "feeds.yaml"
SYSTEM_PROMPT_PATH = Path(__file__).parent / "prompts" / "system.txt"

# KJV book name aliases Claude might use → canonical names in our JSON
BOOK_ALIASES = {
    "Psalm": "Psalms",
    "Song of Songs": "Song of Solomon",
    "Song of Song": "Song of Solomon",
    "Revelations": "Revelation",
    "1st Samuel": "1 Samuel",
    "2nd Samuel": "2 Samuel",
    "1st Kings": "1 Kings",
    "2nd Kings": "2 Kings",
    "1st Chronicles": "1 Chronicles",
    "2nd Chronicles": "2 Chronicles",
    "1st Corinthians": "1 Corinthians",
    "2nd Corinthians": "2 Corinthians",
    "1st Thessalonians": "1 Thessalonians",
    "2nd Thessalonians": "2 Thessalonians",
    "1st Timothy": "1 Timothy",
    "2nd Timothy": "2 Timothy",
    "1st Peter": "1 Peter",
    "2nd Peter": "2 Peter",
    "1st John": "1 John",
    "2nd John": "2 John",
    "3rd John": "3 John",
}


def load_feeds():
    with open(FEEDS_PATH) as f:
        return yaml.safe_load(f)["feeds"]


def fetch_stories(feeds):
    stories = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:8]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                link = entry.get("link", "")
                if title:
                    stories.append({
                        "title": title,
                        "summary": summary,
                        "url": link,
                        "outlet": feed["name"],
                    })
        except Exception as exc:
            print(f"Warning: failed to fetch {feed['name']}: {exc}", file=sys.stderr)

    # Dedupe by lowercased title prefix
    seen = set()
    deduped = []
    for s in stories:
        key = s["title"].lower()[:60]
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return deduped[:20]


def load_bible():
    if not BIBLE_PATH.exists():
        print(
            f"Bible JSON not found at {BIBLE_PATH}. Run: python scripts/download_bible.py",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(BIBLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize_book(name):
    return BOOK_ALIASES.get(name, name)


def validate_verse(bible, ref):
    """Return (ref, text) using the authoritative bundled text, or None if invalid."""
    match = re.match(r"^(.+?)\s+(\d+):(\d+)$", ref.strip())
    if not match:
        return None
    book = normalize_book(match.group(1).strip())
    chapter = match.group(2)
    verse = match.group(3)
    try:
        text = bible[book][chapter][verse]
        canonical_ref = f"{book} {chapter}:{verse}"
        return canonical_ref, text
    except KeyError:
        return None


def call_claude(stories, today_str):
    client = anthropic.Anthropic()
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

    news_lines = []
    for i, s in enumerate(stories, 1):
        news_lines.append(f"{i}. [{s['outlet']}] {s['title']}")
        if s["summary"]:
            news_lines.append(f"   {s['summary'][:200]}")

    user_message = (
        f"Today is {today_str}. Here are today's top news headlines:\n\n"
        + "\n".join(news_lines)
        + "\n\nRespond with only the JSON object described in your instructions."
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError(f"No JSON in Claude response: {text[:300]}")
    return json.loads(json_match.group())


def escape_yaml(s):
    """Escape a string for a YAML double-quoted scalar."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_entry(today, stories, result, verse_ref, verse_text):
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    date_str = today.isoformat()
    output_path = ENTRIES_DIR / f"{date_str}.md"

    themes_json = json.dumps(result["themes"])

    sources_lines = []
    for s in stories[:10]:
        sources_lines.append(
            f'  - title: "{escape_yaml(s["title"])}"\n'
            f'    url: "{escape_yaml(s["url"])}"\n'
            f'    outlet: "{escape_yaml(s["outlet"])}"'
        )
    sources_block = "\n".join(sources_lines)

    content = (
        f'---\n'
        f'date: "{date_str}"\n'
        f'verse_ref: "{escape_yaml(verse_ref)}"\n'
        f'verse_text: "{escape_yaml(verse_text)}"\n'
        f'translation: "KJV"\n'
        f'themes: {themes_json}\n'
        f'news_summary: "{escape_yaml(result["news_summary"])}"\n'
        f'sources:\n{sources_block}\n'
        f'---\n\n'
        f'{result["reflection"].strip()}\n'
    )

    output_path.write_text(content, encoding="utf-8")
    print(f"Written: {output_path}")
    return output_path


def main():
    today = datetime.now(ZoneInfo("America/New_York")).date()
    today_str = today.isoformat()
    output_path = ENTRIES_DIR / f"{today_str}.md"

    if output_path.exists():
        print(f"Entry for {today_str} already exists, skipping.")
        return

    print(f"Generating entry for {today_str} ...")

    feeds = load_feeds()
    print(f"Fetching from {len(feeds)} feeds ...")
    stories = fetch_stories(feeds)
    print(f"Got {len(stories)} unique stories")

    if len(stories) < 3:
        print("Too few stories fetched — check RSS feeds.", file=sys.stderr)
        sys.exit(1)

    bible = load_bible()

    print("Calling Claude API ...")
    result = call_claude(stories, today_str)

    verse_ref = result.get("verse_ref", "").strip()
    verse_text = result.get("verse_text", "").strip()
    print(f"Claude suggested: {verse_ref!r}")

    # Prefer the authoritative bundled text if the ref is found; otherwise trust Claude
    bundled = validate_verse(bible, verse_ref)
    if bundled:
        verse_ref, verse_text = bundled
        print("Using bundled Bible text.")
    else:
        print(f"Ref not found in Bible JSON — using Claude's text for {verse_ref!r}")
    write_entry(today, stories, result, verse_ref, verse_text)
    print("Done.")


if __name__ == "__main__":
    main()
