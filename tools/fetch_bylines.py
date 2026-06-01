#!/usr/bin/env python3
"""
tools/fetch_bylines.py
Fetch missing bylines from nitrateonline.com and fix local files.

Usage:
  python3 tools/fetch_bylines.py [--dry-run]
"""

import re, sys, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from html.parser import HTMLParser

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']
DRY_RUN = '--dry-run' in sys.argv
BASE_URL = 'https://nitrateonline.com'

AUTHOR_PAGES = {
    'Carrie Gorringe':  'carrie',
    'Eddie Cockrell':   'eddie',
    'Gregory Avery':    'gregory',
    'Sean Axmaker':     'sean',
    'Joe Barlow':       'joe',
    'Lyall Bush':       'lyall',
    'KJ Doughton':      'kj',
    'Emma French':      'emma',
    'Cynthia Fuchs':    'cynthia',
    'Dave Luty':        'dave',
    'Dan Lybarger':     'dan',
    'Paula Nechak':     'paula',
    'Elias Savada':     'elias',
    'Gianni Truzzi':    'gianni',
    'Jerry White':      'jerry',
}

UA = 'Mozilla/5.0 (compatible; NitrateArchiveBot/1.0)'

def fetch_url(url: str) -> str | None:
    try:
        req = Request(url, headers={'User-Agent': UA})
        with urlopen(req, timeout=10) as r:
            return r.read().decode('utf-8', errors='replace')
    except (HTTPError, URLError, Exception):
        return None

def find_author_in_page(html: str) -> str | None:
    """Search fetched HTML for any known author name."""
    for name in AUTHOR_PAGES:
        if name in html:
            return name
    # Also try common byline patterns
    m = re.search(r'(?:Review|Feature|Written|Reviewed|by)\s+(?:by\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+)+)', html)
    if m:
        cand = m.group(1).strip()
        if cand in AUTHOR_PAGES:
            return cand
    return None

def fix_file(fp: Path, author: str, article_type: str, year: str):
    original = fp.read_text(encoding='utf-8', errors='replace')
    page = AUTHOR_PAGES[author]
    link = f'<a href="../{page}.html">{author}</a>'

    # Fix footer meta
    modified = re.sub(
        r'(<p>)(' + re.escape(article_type) + r' by)(  &nbsp;·&nbsp; Nitrate Online</p>)',
        r'\1\2 ' + link + r' &nbsp;·&nbsp; Nitrate Online</p>',
        original
    )

    # Fix or add meta-byline in article header
    if 'class="meta-byline"' in modified:
        # Fix empty meta-byline
        modified = re.sub(
            r'(<span class="meta-byline">' + re.escape(article_type) + r' by\s*)(\s*</span>)',
            r'\1' + link + r'</span>',
            modified
        )
    else:
        # Add meta-byline after h1
        modified = re.sub(
            r'(<h1 class="article-title">.*?</h1>)(\s*\n\s*\n\s*\n)',
            r'\1\n      <p class="article-meta"><span class="meta-byline">' + article_type + ' by ' + link + r'</span></p>\n\n',
            modified,
            flags=re.DOTALL
        )

    return modified if modified != original else original


def main():
    # Collect files with missing bylines
    missing = []
    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue
        for fp in sorted(yr_dir.glob('*.html')) + sorted(yr_dir.glob('*.htm')):
            try:
                text = fp.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            m = re.search(r'<p>(Feature|Review|Essay|Report|Dispatch|Preview|Book Review) by  &nbsp;·&nbsp; Nitrate Online</p>', text)
            if m:
                missing.append((yr, fp, m.group(1)))

    print(f'Found {len(missing)} files with missing bylines. Fetching from {BASE_URL}...\n')

    fixed = 0
    unfixed = []

    for yr, fp, article_type in missing:
        name = fp.name

        # Try year subfolder first, then root
        html = None
        for url in [f'{BASE_URL}/{yr}/{name}', f'{BASE_URL}/{name}']:
            html = fetch_url(url)
            if html:
                break
            time.sleep(0.1)

        if not html:
            unfixed.append(f'{yr}/{name} (fetch failed)')
            continue

        author = find_author_in_page(html)
        if not author:
            unfixed.append(f'{yr}/{name} (author not found in fetched page)')
            continue

        if DRY_RUN:
            print(f'  [DRY] {yr}/{name} → {author}')
            fixed += 1
            continue

        modified = fix_file(fp, author, article_type, yr)
        if modified != fp.read_text(encoding='utf-8', errors='replace'):
            fp.write_text(modified, encoding='utf-8')
            print(f'  [FIXED] {yr}/{name} → {author}')
            fixed += 1
        else:
            unfixed.append(f'{yr}/{name} (pattern mismatch for {author})')

        time.sleep(0.15)  # polite crawl delay

    print(f'\nFixed: {fixed} / {len(missing)}')
    if unfixed:
        print(f'Could not fix ({len(unfixed)}):')
        for u in unfixed:
            print(f'  {u}')
    if DRY_RUN:
        print('(dry run)')


if __name__ == '__main__':
    main()
