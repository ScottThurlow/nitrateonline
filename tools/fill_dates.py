#!/usr/bin/env python3
"""
tools/fill_dates.py
Fill in missing publish dates from Wayback Machine first-seen dates.

For review/feature pages that lack a "Published" date in their article-meta,
look up the wayback first-seen date and inject it.

Usage:
  python3 tools/fill_dates.py --dry-run
  python3 tools/fill_dates.py
"""

import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']
DRY_RUN = '--dry-run' in sys.argv

WAYBACK_CSV = os.path.expanduser('~/code/wayback_first_seen.csv')

# Pattern to match the closing of article-meta without a date
# Handles both <div> and <p> wrappers, with or without trailing whitespace
META_CLOSE_RE = re.compile(
    r'(<span class="meta-byline">.*?</span>)(</(?:div|p)>)',
    re.DOTALL
)


def format_date(iso_date: str) -> str:
    """Convert 'YYYY-MM-DD' to 'D Month YYYY' format."""
    dt = datetime.strptime(iso_date, '%Y-%m-%d')
    return f'{dt.day} {dt.strftime("%B")} {dt.year}'


def main():
    # Load wayback data
    wayback = {}
    with open(WAYBACK_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = os.path.basename(row['file'])
            wayback[fname] = row['date_published']

    modified = 0
    skipped = 0

    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue

        for fp in sorted(yr_dir.glob('*.html')):
            if fp.name == 'index.html':
                continue
            if not (fp.name.startswith('r') or fp.name.startswith('f')):
                continue

            text = fp.read_text(encoding='utf-8', errors='replace')

            # Skip if already has a date
            if 'Published ' in text:
                continue

            # Look up wayback date
            wb_date = wayback.get(fp.name)
            if not wb_date:
                skipped += 1
                continue

            formatted = format_date(wb_date)
            date_insert = (
                f'<span class="meta-sep" aria-hidden="true">◆</span>'
                f'<span>Published {formatted}</span>'
            )

            # Find the meta-byline closing and insert before the wrapper close
            match = META_CLOSE_RE.search(text)
            if not match:
                print(f'  [SKIP] No article-meta pattern in {yr}/{fp.name}')
                skipped += 1
                continue

            # Check this match doesn't already have a date (safety)
            byline_end = match.end(1)
            wrapper_close = match.group(2)

            new_text = text[:byline_end] + date_insert + text[byline_end:]

            modified += 1
            if DRY_RUN:
                print(f'  [DRY] {yr}/{fp.name} ← {formatted}')
            else:
                fp.write_text(new_text, encoding='utf-8')
                print(f'  {yr}/{fp.name} ← {formatted}')

    print(f'\nFilled {modified} date(s), skipped {skipped}.')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
