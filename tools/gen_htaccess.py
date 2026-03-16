#!/usr/bin/env python3
"""
tools/gen_htaccess.py
Generate .htaccess with 301 redirects for:
  - default.htm → /
  - Moved r*/f* files (root → year/file)
  - Deleted store/subscribe/ads pages → /
  - Old archive year listing pages → year folders
  - Old asp pages → /

Usage: python3 tools/gen_htaccess.py > .htaccess
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']

lines = []

# ── Apache options ──
lines += [
    'Options -Indexes',
    'DirectoryIndex index.html',
    '',
    '<IfModule mod_rewrite.c>',
    '  RewriteEngine On',
    '',
]

# ── Home page: default.htm and old variations ──
home_redirects = [
    'default.htm',
    'default.html',
    'index.htm',
]
lines.append('  # Home page')
for old in home_redirects:
    lines.append(f'  RewriteRule ^{old}$ / [R=301,L]')
lines.append('')

# ── Old archive year listing pages → year folders ──
lines.append('  # Old archive year listing pages')
archive_map = {
    'archive96.html': '1996/',
    'archive97.html': '1997/',
    'archive98.html': '1998/',
    'archive99.html': '1999/',
    'archive00.html': '2000/',
    'archive01.html': '2001/',
    'archive02.html': '2002/',
    'archive03.html': '2003/',
}
for old, new in archive_map.items():
    lines.append(f'  RewriteRule ^{old}$ /{new} [R=301,L]')
lines.append('')

# ── Deleted pages → home ──
deleted_to_home = [
    'store.html', 'store0199.html', 'store1098.html', 'store1198.html',
    'store1298.html', 'storearch.html', 'posterstore.html', 'storeitm.asp',
    'shop.asp', 'subscribe.html', 'nitratesub.html', 'nitrateunsub.html',
    'postinfo.html', 'schedule.html', 'pointcast_jump.htm',
    'repub.html', 'press.html', 'nitratelist.html', 'masterarchive.html',
    'cinemaparallel.html', 'issmenu.html',
]
lines.append('  # Deleted pages → home')
for old in deleted_to_home:
    # Escape dots for regex
    pattern = old.replace('.', r'\.')
    lines.append(f'  RewriteRule ^{pattern}$ / [R=301,L]')
lines.append('')

# ── Moved r*/f* review/feature files ──
# Build map: filename → year/filename by scanning year folders
moved = {}  # basename → year/basename
for yr in YEAR_DIRS:
    yr_dir = ROOT / yr
    if not yr_dir.is_dir():
        continue
    for fp in yr_dir.glob('r*.html'):
        moved[fp.name] = f'{yr}/{fp.name}'
    for fp in yr_dir.glob('r*.htm'):
        moved[fp.name] = f'{yr}/{fp.name}'
    for fp in yr_dir.glob('f*.html'):
        moved[fp.name] = f'{yr}/{fp.name}'
    for fp in yr_dir.glob('f*.htm'):
        moved[fp.name] = f'{yr}/{fp.name}'

lines.append(f'  # Moved review/feature files ({len(moved)} files, r* and f*)')
for old_name in sorted(moved):
    new_path = moved[old_name]
    pattern = old_name.replace('.', r'\.')
    lines.append(f'  RewriteRule ^{pattern}$ /{new_path} [R=301,L]')
lines.append('')

# ── storeitm paths ──
lines.append('  # Store item paths')
lines.append(r'  RewriteRule ^storeitm/.*$ / [R=301,L]')
lines.append('')

lines.append('</IfModule>')
lines.append('')

# ── Error pages ──
lines += [
    '# Custom error pages',
    'ErrorDocument 404 /index.html',
    '',
]

print('\n'.join(lines))
