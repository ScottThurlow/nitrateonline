#!/usr/bin/env python3
"""
tools/fix_bylines.py
Find HTML files with empty bylines and attempt to fix them by
searching the article body for known author names.

Usage: python3 tools/fix_bylines.py [--dry-run]
"""

import re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']
DRY_RUN = '--dry-run' in sys.argv

# Known authors and their bio page filenames
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

# MISSING: pattern to match in footer meta
EMPTY_FEATURE = re.compile(r'Feature by  &nbsp;\;·&nbsp;')
EMPTY_REVIEW  = re.compile(r'Review by  &nbsp;\;·&nbsp;')

# Generic empty byline
EMPTY_BYLINE = re.compile(r'((?:Feature|Review|Essay|Report|Dispatch|Preview|Book Review) by)\s{2,}(&nbsp;·&nbsp;)')

def find_author_in_body(html: str):
    """Search the HTML body for any known author name."""
    for name in AUTHOR_PAGES:
        if name in html:
            return name
    return None

def fix_byline(html: str, author: str, article_type: str, year: str) -> str:
    page = AUTHOR_PAGES[author]
    link = f'<a href="../{page}.html">{author}</a>'

    # Fix footer meta line: "Feature by  &nbsp;·&nbsp; Nitrate Online"
    html = re.sub(
        r'(' + re.escape(article_type) + r' by)\s{2,}(&nbsp;·&nbsp; Nitrate Online)',
        r'\1 ' + link + r' \2',
        html
    )

    # Fix article-meta byline in header if present and empty
    html = re.sub(
        r'(<span class="meta-byline">' + re.escape(article_type) + r' by\s*)(\s*</span>)',
        r'\1' + link + r'\2',
        html
    )

    # Also fix if article-meta section is completely missing the byline (two blank lines in header)
    # If there's no article-meta at all, add one after the h1
    if f'class="meta-byline"' not in html:
        html = re.sub(
            r'(<h1 class="article-title">.*?</h1>\s*\n\s*\n\s*\n)',
            r'\1      <p class="article-meta"><span class="meta-byline">' + article_type + ' by ' + link + r'</span></p>\n',
            html,
            flags=re.DOTALL
        )

    return html


def main():
    fixed = 0
    unfixed = []

    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue

        for fp in sorted(yr_dir.glob('*.html')):
            try:
                original = fp.read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                print(f'  [ERROR] {fp}: {e}')
                continue

            # Check for empty byline
            m = re.search(r'<p>(Feature|Review|Essay|Report|Dispatch|Preview|Book Review) by  &nbsp;·&nbsp; Nitrate Online</p>', original)
            if not m:
                continue

            article_type = m.group(1)

            # Try to find author in body
            author = find_author_in_body(original)

            if not author:
                unfixed.append(f'{yr}/{fp.name}')
                continue

            modified = fix_byline(original, author, article_type, yr)

            if modified != original:
                fixed += 1
                if not DRY_RUN:
                    fp.write_text(modified, encoding='utf-8')
                    print(f'  [FIXED] {yr}/{fp.name} → {author}')
                else:
                    print(f'  [DRY]   {yr}/{fp.name} → {author}')
            else:
                unfixed.append(f'{yr}/{fp.name} (author found: {author}, but pattern not matched)')

    print(f'\nFixed: {fixed}')
    if unfixed:
        print(f'Could not fix ({len(unfixed)}):')
        for u in unfixed:
            print(f'  {u}')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
