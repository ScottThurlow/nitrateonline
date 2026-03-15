#!/usr/bin/env python3
"""
tools/gen_sitemap.py
Generate sitemap.xml for nitrateonline.com

Usage: python3 tools/gen_sitemap.py > sitemap.xml
"""

from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent
BASE = 'https://nitrateonline.com'
TODAY = date.today().isoformat()
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']

urls = []

# ── Root site pages (high priority) ──
root_pages = [
    ('', 1.0, 'monthly'),
    ('index.html', 1.0, 'monthly'),
    ('archive.html', 0.9, 'monthly'),
    ('aboutus.html', 0.7, 'yearly'),
    ('links.html', 0.5, 'yearly'),
]
for page, priority, freq in root_pages:
    loc = f'{BASE}/{page}' if page else BASE + '/'
    urls.append((loc, TODAY, freq, priority))

# ── Bio pages ──
bio_pages = ['carrie', 'eddie', 'gregory', 'sean', 'joe', 'lyall',
             'kj', 'emma', 'cynthia', 'dave', 'dan', 'paula',
             'elias', 'gianni', 'jerry']
for bio in bio_pages:
    urls.append((f'{BASE}/{bio}.html', TODAY, 'yearly', 0.6))

# ── Year index pages ──
for yr in YEAR_DIRS:
    yr_dir = ROOT / yr
    if yr_dir.is_dir():
        urls.append((f'{BASE}/{yr}/', TODAY, 'yearly', 0.8))

# ── Individual review and feature pages ──
for yr in YEAR_DIRS:
    yr_dir = ROOT / yr
    if not yr_dir.is_dir():
        continue
    for fp in sorted(yr_dir.glob('*.html')) + sorted(yr_dir.glob('*.htm')):
        if fp.name == 'index.html':
            continue
        # Features get slightly higher priority
        priority = 0.6 if fp.name.startswith('f') else 0.5
        urls.append((f'{BASE}/{yr}/{fp.name}', TODAY, 'never', priority))

# ── Output XML ──
lines = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
         '']

for loc, lastmod, freq, priority in urls:
    lines += [
        '  <url>',
        f'    <loc>{loc}</loc>',
        f'    <lastmod>{lastmod}</lastmod>',
        f'    <changefreq>{freq}</changefreq>',
        f'    <priority>{priority}</priority>',
        '  </url>',
        '',
    ]

lines.append('</urlset>')
print('\n'.join(lines))
