#!/usr/bin/env python3
"""
tools/fix_bylines_git.py
For files where fetch failed, use git history to find original author.

Usage: python3 tools/fix_bylines_git.py [--dry-run]
"""

import re, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']
DRY_RUN = '--dry-run' in sys.argv

# The commit before our conversion (original FrontPage HTML)
ORIG_COMMIT = '73259c8'

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

# Also try initials/partial matches in old HTML
NAME_VARIANTS = {
    'Carrie Gorringe':  ['carrie', 'gorringe'],
    'Eddie Cockrell':   ['eddie', 'cockrell'],
    'Gregory Avery':    ['gregory', 'avery'],
    'Sean Axmaker':     ['sean', 'axmaker'],
    'Joe Barlow':       ['joe', 'barlow'],
    'Lyall Bush':       ['lyall', 'bush'],
    'KJ Doughton':      ['k.j.', 'kj', 'doughton'],
    'Emma French':      ['emma', 'french'],
    'Cynthia Fuchs':    ['cynthia', 'fuchs'],
    'Dave Luty':        ['dave', 'luty'],
    'Dan Lybarger':     ['dan', 'lybarger'],
    'Paula Nechak':     ['paula', 'nechak'],
    'Elias Savada':     ['elias', 'savada'],
    'Gianni Truzzi':    ['gianni', 'truzzi'],
    'Jerry White':      ['jerry', 'white'],
}


def git_show(path: str) -> str | None:
    try:
        result = subprocess.run(
            ['git', 'show', f'{ORIG_COMMIT}:{path}'],
            capture_output=True, cwd=ROOT
        )
        if result.returncode == 0:
            return result.stdout.decode('windows-1252', errors='replace')
    except Exception:
        pass
    return None


def find_author_in_html(html: str) -> str | None:
    # Direct name match
    for name in AUTHOR_PAGES:
        if name in html:
            return name
    # Case-insensitive last name match
    lower = html.lower()
    for name, variants in NAME_VARIANTS.items():
        for v in variants:
            if v in lower:
                # Confirm it's a byline context
                idx = lower.find(v)
                ctx = lower[max(0, idx-50):idx+50]
                if any(kw in ctx for kw in ['review', 'feature', 'by ', 'wrote', 'written']):
                    return name
    return None


def fix_file(fp: Path, author: str, article_type: str, yr: str) -> bool:
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
        modified = re.sub(
            r'(<span class="meta-byline">' + re.escape(article_type) + r' by\s*)(\s*</span>)',
            r'\1' + link + r'</span>',
            modified
        )
    else:
        modified = re.sub(
            r'(<h1 class="article-title">.*?</h1>)(\s*\n\s*\n\s*\n)',
            r'\1\n      <p class="article-meta"><span class="meta-byline">' + article_type + ' by ' + link + r'</span></p>\n\n',
            modified,
            flags=re.DOTALL
        )

    if modified != original:
        if not DRY_RUN:
            fp.write_text(modified, encoding='utf-8')
        return True
    return False


def main():
    missing = []
    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue
        for fp in sorted(list(yr_dir.glob('*.html')) + list(yr_dir.glob('*.htm'))):
            try:
                text = fp.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            m = re.search(r'<p>(Feature|Review|Essay|Report|Dispatch|Preview|Book Review) by  &nbsp;·&nbsp; Nitrate Online</p>', text)
            if m:
                missing.append((yr, fp, m.group(1)))

    print(f'Found {len(missing)} files still missing bylines. Checking git history ({ORIG_COMMIT})...\n')

    fixed = 0
    unfixed = []

    for yr, fp, article_type in missing:
        name = fp.name
        # Original file was at root (no year prefix)
        orig_html = git_show(name)
        if not orig_html:
            orig_html = git_show(f'{yr}/{name}')

        if not orig_html:
            unfixed.append(f'{yr}/{name} (not in git history)')
            continue

        author = find_author_in_html(orig_html)

        if not author:
            unfixed.append(f'{yr}/{name} (author not found in original)')
            continue

        result = fix_file(fp, author, article_type, yr)
        if result:
            fixed += 1
            action = '[DRY]' if DRY_RUN else '[FIXED]'
            print(f'  {action} {yr}/{name} → {author}')
        else:
            unfixed.append(f'{yr}/{name} (pattern not matched for {author})')

    print(f'\nFixed: {fixed} / {len(missing)}')
    if unfixed:
        print(f'Could not fix ({len(unfixed)}):')
        for u in unfixed:
            print(f'  {u}')
    if DRY_RUN:
        print('(dry run)')


if __name__ == '__main__':
    main()
