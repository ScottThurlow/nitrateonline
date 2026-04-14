#!/usr/bin/env python3
"""
Generate an IMDb external reviews harvest page for bulk submission.

Reads imdb_missing.csv and the HTML review files to produce:
  1. imdb-reviews.xml  — XML feed for IMDb's harvester
  2. imdb-reviews.html — Human-readable HTML page (also harvestable)

These pages list every Nitrate Online review that isn't yet in IMDb's
External Reviews, formatted so IMDb's automated system can ingest them.

Usage:
    python3 tools/gen_imdb_harvest.py              # generate both files
    python3 tools/gen_imdb_harvest.py --dry-run     # preview without writing
    python3 tools/gen_imdb_harvest.py --include-all  # include already-listed too

After generating, deploy the files and email IMDb's help desk:
    https://help.imdb.com/contact

Include:
  - Site name: Nitrate Online
  - Harvest URL: https://nitrateonline.com/imdb-reviews.xml
  - Format: XML
  - Preferred harvest day: any (Mon/Thu/Fri)
  - Multiple named reviewers (names included per review)
"""

import argparse
import csv
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
MISSING_CSV = DATA_DIR / 'imdb_missing.csv'
ALREADY_CSV = DATA_DIR / 'imdb_already.csv'


def load_reviews(csv_path):
    """Load reviews from a CSV file."""
    reviews = []
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            reviews.append(row)
    return reviews


def get_author(review_url):
    """Extract the author name from the review's HTML file."""
    parsed = urlparse(review_url)
    rel_path = parsed.path.lstrip('/')
    html_path = ROOT / rel_path

    if not html_path.exists():
        return None

    content = html_path.read_text(encoding='utf-8', errors='replace')

    # JSON-LD author
    m = re.search(r'"author"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', content)
    if m:
        return m.group(1).strip()

    # Byline with link
    m = re.search(
        r'meta-byline[^>]*>(?:Review|Feature)\s+by\s+<a[^>]*>([^<]+)', content)
    if m:
        return m.group(1).strip()

    # Byline without link
    m = re.search(
        r'(?:Review|Feature)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', content)
    if m:
        return m.group(1).strip()

    return None


def get_year(review_url):
    """Extract the year from the review URL."""
    m = re.search(r'/(\d{4})/', review_url)
    return m.group(1) if m else ''


def get_type(review_url):
    """Determine if this is a review or feature from the filename."""
    path = urlparse(review_url).path
    basename = os.path.basename(path)
    if basename.startswith('f'):
        return 'feature'
    return 'review'


def enrich_reviews(reviews):
    """Add author and metadata to each review dict."""
    for rev in reviews:
        rev['author'] = get_author(rev['review_url'])
        rev['year'] = get_year(rev['review_url'])
        rev['type'] = get_type(rev['review_url'])
    return reviews


def generate_xml(reviews, output_path, dry_run=False):
    """
    Generate an XML harvest page.

    Format based on IMDb's documented specification:
    - Each review has title, reviewer, and URL
    - IMDb IDs included as attributes for precise matching
    """
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<REVIEWS site="Nitrate Online" '
                 'url="https://nitrateonline.com/" '
                 f'generated="{datetime.now(timezone.utc).isoformat()}Z">')

    for rev in reviews:
        imdb_id = xml_escape(rev['imdb_id'])
        title = xml_escape(rev['title'])
        url = xml_escape(rev['review_url'])
        author = xml_escape(rev['author']) if rev['author'] else ''

        lines.append('  <REVIEW>')
        lines.append(f'    <IMDB>{imdb_id}</IMDB>')
        lines.append(f'    <TITLE>{title}</TITLE>')
        if author:
            lines.append(f'    <REVIEWER>{author}</REVIEWER>')
        lines.append(f'    <URL>{url}</URL>')
        lines.append('  </REVIEW>')

    lines.append('</REVIEWS>')

    content = '\n'.join(lines) + '\n'

    if dry_run:
        print(f"Would write {len(lines)} lines to {output_path}")
        print("First 20 lines:")
        for line in lines[:20]:
            print(f"  {line}")
        print("  ...")
    else:
        output_path.write_text(content, encoding='utf-8')
        print(f"Wrote {output_path} ({len(reviews)} reviews, {len(content)} bytes)")

    return content


def generate_html(reviews, output_path, dry_run=False):
    """
    Generate an HTML harvest page.

    Clean, parseable HTML table that IMDb can harvest and humans can read.
    Uses the site's own stylesheet for consistent branding.
    """
    rows = []
    for rev in reviews:
        author_display = html.escape(rev['author']) if rev['author'] else ''
        author_bracket = f' [{html.escape(rev["author"])}]' if rev['author'] else ''
        rows.append(
            f'      <tr>\n'
            f'        <td>{html.escape(rev["imdb_id"])}</td>\n'
            f'        <td>{html.escape(rev["title"])}</td>\n'
            f'        <td>{author_display}</td>\n'
            f'        <td><a href="{html.escape(rev["review_url"])}">'
            f'Nitrate Online{author_bracket}</a></td>\n'
            f'      </tr>'
        )

    # Count authors
    authors = {}
    for rev in reviews:
        name = rev['author'] or '(uncredited)'
        authors[name] = authors.get(name, 0) + 1
    author_list = sorted(authors.items(), key=lambda x: -x[1])

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>External Reviews for IMDb — Nitrate Online</title>
  <meta name="robots" content="noindex, nofollow">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Raleway:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/nitrate.css">
  <style>
    .harvest-table {{ width: 100%; border-collapse: collapse; margin: 2rem 0; font-size: 0.9rem; }}
    .harvest-table th, .harvest-table td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #333; }}
    .harvest-table th {{ color: var(--gold, #c8a84e); font-family: 'Raleway', sans-serif; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
    .harvest-table tr:hover td {{ background: rgba(200, 168, 78, 0.05); }}
    .harvest-table a {{ color: var(--gold, #c8a84e); }}
    .stats {{ display: flex; gap: 2rem; flex-wrap: wrap; margin: 1.5rem 0; }}
    .stat {{ text-align: center; }}
    .stat-num {{ font-size: 2rem; font-weight: 700; color: var(--gold, #c8a84e); font-family: 'Playfair Display', serif; }}
    .stat-label {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.7; }}
    .author-list {{ columns: 2; column-gap: 2rem; margin: 1rem 0; }}
    .author-list li {{ margin-bottom: 0.3rem; }}
    .xml-link {{ margin: 1rem 0; padding: 1rem; background: rgba(200, 168, 78, 0.08); border: 1px solid #333; border-radius: 4px; }}
    .xml-link code {{ color: var(--gold, #c8a84e); }}
  </style>
</head>
<body>
  <a href="#main" class="skip-link">Skip to content</a>

  <header class="masthead">
    <div class="masthead-inner">
      <a href="/index.html" class="site-logo" aria-label="Nitrate Online — Home">
        <img src="/logo.svg" alt="Nitrate Online" height="42">
      </a>
    </div>
  </header>

  <main id="main" class="site-main" style="max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem;">
    <h1 style="font-family: 'Playfair Display', serif;">External Reviews for IMDb</h1>

    <p>This page lists all <strong>Nitrate Online</strong> film reviews and features
    available for inclusion in IMDb's External Reviews. Each link points to a
    full critical review published between 1996 and 2004.</p>

    <div class="xml-link">
      Machine-readable version: <a href="/imdb-reviews.xml"><code>imdb-reviews.xml</code></a>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="stat-num">{len(reviews)}</div>
        <div class="stat-label">Reviews</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len([r for r in reviews if r['author']])}</div>
        <div class="stat-label">With Named Reviewer</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len(set(r['year'] for r in reviews))}</div>
        <div class="stat-label">Years (1996–2004)</div>
      </div>
      <div class="stat">
        <div class="stat-num">{len([a for a, _ in author_list if a != '(uncredited)'])}</div>
        <div class="stat-label">Reviewers</div>
      </div>
    </div>

    <h2 style="font-family: 'Playfair Display', serif;">Reviewers</h2>
    <ul class="author-list">
''' + '\n'.join(
        f'      <li><strong>{html.escape(name)}</strong> ({count})</li>'
        for name, count in author_list
    ) + '''
    </ul>

    <h2 style="font-family: 'Playfair Display', serif;">All Reviews</h2>

    <table class="harvest-table">
      <thead>
        <tr>
          <th>IMDb ID</th>
          <th>Title</th>
          <th>Reviewer</th>
          <th>Review Link</th>
        </tr>
      </thead>
      <tbody>
''' + '\n'.join(rows) + '''
      </tbody>
    </table>

    <p style="margin-top: 3rem; opacity: 0.5; font-size: 0.8rem;">
      Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} &mdash;
      <a href="https://nitrateonline.com/">nitrateonline.com</a>
    </p>
  </main>
</body>
</html>
'''

    if dry_run:
        print(f"Would write {len(page)} bytes to {output_path}")
        print(f"  {len(reviews)} reviews in table")
        print(f"  {len(author_list)} distinct authors")
    else:
        output_path.write_text(page, encoding='utf-8')
        print(f"Wrote {output_path} ({len(reviews)} reviews, {len(page)} bytes)")

    return page


def main():
    parser = argparse.ArgumentParser(
        description='Generate IMDb external reviews harvest page')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without writing files')
    parser.add_argument('--include-all', action='store_true',
                        help='Include reviews already listed on IMDb too')
    parser.add_argument('--output-dir', type=str, default=str(ROOT),
                        help='Output directory (default: repo root)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Load reviews
    reviews = load_reviews(MISSING_CSV)
    print(f"Loaded {len(reviews)} missing reviews from {MISSING_CSV}")

    if args.include_all and ALREADY_CSV.exists():
        already = load_reviews(ALREADY_CSV)
        print(f"Loaded {len(already)} already-listed reviews from {ALREADY_CSV}")
        reviews.extend(already)
        print(f"Total: {len(reviews)} reviews")

    # Enrich with author data
    print("Extracting authors from HTML files...")
    reviews = enrich_reviews(reviews)

    with_author = sum(1 for r in reviews if r['author'])
    without_author = len(reviews) - with_author
    print(f"  {with_author} with author, {without_author} without")

    # Sort by year then title for a clean listing
    reviews.sort(key=lambda r: (r.get('year', ''), r['title']))

    # Generate files
    print()
    generate_xml(reviews, output_dir / 'imdb-reviews.xml', dry_run=args.dry_run)
    generate_html(reviews, output_dir / 'imdb-reviews.html', dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nDone! Deploy these files and contact IMDb:")
        print(f"  https://help.imdb.com/contact")
        print()
        print(f"  Email should include:")
        print(f"    - Site name: Nitrate Online")
        print(f"    - Harvest URL: https://nitrateonline.com/imdb-reviews.xml")
        print(f"    - Also available: https://nitrateonline.com/imdb-reviews.html")
        print(f"    - Format: XML (with IMDb IDs for precise matching)")
        print(f"    - Preferred harvest day: any day (Mon/Thu/Fri)")
        print(f"    - Reviews by multiple named reviewers (names in each entry)")
        print(f"    - {len(reviews)} reviews covering 1996-2004")


if __name__ == '__main__':
    main()
