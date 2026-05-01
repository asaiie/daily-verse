#!/usr/bin/env python3
"""Download and convert the KJV Bible JSON from a public source.

Source: https://github.com/thiagobodruk/bible (public domain)
Converts the array format to a nested dict: {book: {chapter: {verse: text}}}
"""

import json
import sys
from pathlib import Path

import requests

SOURCE_URL = "https://raw.githubusercontent.com/thiagobodruk/bible/master/json/en_kjv.json"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "bible-kjv.json"


def download_and_convert():
    print(f"Downloading KJV Bible from {SOURCE_URL} ...")
    response = requests.get(SOURCE_URL, timeout=60)
    response.raise_for_status()
    raw = json.loads(response.content.decode("utf-8-sig"))

    print(f"Converting {len(raw)} books ...")
    bible = {}
    for book_data in raw:
        book_name = book_data["name"]
        bible[book_name] = {}
        for chapter_idx, chapter_verses in enumerate(book_data["chapters"]):
            chapter_num = str(chapter_idx + 1)
            bible[book_name][chapter_num] = {}
            for verse_idx, verse_text in enumerate(chapter_verses):
                verse_num = str(verse_idx + 1)
                bible[book_name][chapter_num][verse_num] = verse_text

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(bible, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = OUTPUT_PATH.stat().st_size / 1_000_000
    total_verses = sum(
        len(verses)
        for book in bible.values()
        for verses in book.values()
    )
    print(f"Saved to {OUTPUT_PATH} ({size_mb:.1f} MB, {total_verses:,} verses)")


if __name__ == "__main__":
    if OUTPUT_PATH.exists():
        print(f"{OUTPUT_PATH} already exists. Delete it to re-download.")
        sys.exit(0)
    download_and_convert()
