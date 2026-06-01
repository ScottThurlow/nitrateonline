#!/usr/bin/env python3
"""
Add a filmography (list of reviews/features) to each author bio page.

Scans all review and feature HTML files, groups them by author based on
byline links, and injects a styled filmography section into each bio page.

Usage:
    python3 tools/add_author_filmography.py --dry-run   # preview counts
    python3 tools/add_author_filmography.py              # update bio pages
"""

import argparse
import glob
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Author bio pages: filename -> full name (auto-detected from <h1>)
BIO_PAGES = [
    'carrie', 'cynthia', 'dan', 'dave', 'eddie', 'elias', 'emma',
    'gianni', 'gregory', 'jerry', 'joe', 'kj', 'lyall', 'paula', 'sean',
]


def get_author_name(bio_file):
    """Extract the author's full name from their bio page <h1>."""
    path = os.path.join(ROOT, f'{bio_file}.html')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    m = re.search(r'<h1 class="article-title">([^<]+)</h1>', content)
    return m.group(1).strip() if m else bio_file.title()


def scan_articles():
    """
    Scan all review/feature HTML files and extract metadata.
    Returns a list of dicts with: path, year, code, title, type, date, author_page
    """
    articles = []
    for f in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', '*.html'))):
        basename = os.path.basename(f)
        # Skip index pages
        if basename == 'index.html':
            continue

        year = os.path.basename(os.path.dirname(f))
        code = basename.replace('.html', '')

        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        # Extract title from og:title
        m = re.search(r'og:title.*?content="([^"]*)"', content)
        title = html.unescape(m.group(1).strip()) if m else code

        # Extract type (Review or Feature) from eyebrow
        m = re.search(r'article-eyebrow">([^<]*)<', content)
        eyebrow = html.unescape(m.group(1).strip()) if m else ''
        # Clean up HTML entities in eyebrow
        eyebrow = re.sub(r'\s*[·]\s*\d{4}', '', eyebrow).strip()
        if not eyebrow:
            if code.startswith('f'):
                eyebrow = 'Feature'
            else:
                eyebrow = 'Review'

        # Extract published date
        m = re.search(r'Published\s+([^<]+)', content)
        date_str = m.group(1).strip() if m else ''

        # Extract author bio page links from byline (supports multiple authors)
        author_pages = re.findall(r'href="/([a-z]+)\.html">[A-Z][^<]+</a>', content)
        if not author_pages:
            author_pages = []

        # Create one entry per author so multi-author articles appear on each page
        if author_pages:
            for ap in author_pages:
                if ap in BIO_PAGES:
                    articles.append({
                        'path': f'/{year}/{basename}',
                        'year': year,
                        'code': code,
                        'title': title,
                        'type': eyebrow,
                        'date': date_str,
                        'author_page': ap,
                    })
        else:
            articles.append({
                'path': f'/{year}/{basename}',
                'year': year,
                'code': code,
                'title': title,
                'type': eyebrow,
                'date': date_str,
                'author_page': None,
            })

    return articles


def group_by_author(articles):
    """Group articles by author bio page name."""
    by_author = {}
    for art in articles:
        if art['author_page']:
            by_author.setdefault(art['author_page'], []).append(art)
    return by_author


def build_filmography_html(articles, author_name):
    """
    Build the filmography HTML section for an author.
    Groups by year, separates reviews and features.
    """
    # Sort by year (desc), then type, then title
    articles.sort(key=lambda a: (a['year'], a['title']))

    # Group by year
    by_year = {}
    for art in articles:
        by_year.setdefault(art['year'], []).append(art)

    review_count = sum(1 for a in articles if 'Review' in a['type'])
    feature_count = sum(1 for a in articles if 'Feature' in a['type'])

    lines = []
    lines.append('')
    lines.append('      <div class="author-filmography">')
    lines.append(f'        <h2>Articles by {html.escape(author_name)}</h2>')

    # Summary line
    parts = []
    if review_count:
        parts.append(f'{review_count} review{"s" if review_count != 1 else ""}')
    if feature_count:
        parts.append(f'{feature_count} feature{"s" if feature_count != 1 else ""}')
    other = len(articles) - review_count - feature_count
    if other:
        parts.append(f'{other} article{"s" if other != 1 else ""}')
    lines.append(f'        <p class="filmography-summary">{", ".join(parts)}</p>')

    # Year sections — reverse chronological
    for year in sorted(by_year.keys(), reverse=True):
        year_articles = by_year[year]
        lines.append(f'        <h3>{year}</h3>')
        lines.append('        <ul class="filmography-list">')
        for art in sorted(year_articles, key=lambda a: a['title']):
            title_escaped = html.escape(art['title'])
            type_label = art['type']
            # Clean up type for display
            if 'Review' in type_label:
                type_tag = 'Review'
            elif 'Feature' in type_label:
                type_tag = 'Feature'
            else:
                type_tag = type_label

            lines.append(
                f'          <li>'
                f'<a href="{html.escape(art["path"])}">'
                f'<em>{title_escaped}</em></a>'
                f' <span class="filmography-type">{html.escape(type_tag)}</span>'
                f'</li>'
            )
        lines.append('        </ul>')

    lines.append('      </div>')
    lines.append('')

    return '\n'.join(lines)


def build_filmography_css():
    """Return the inline CSS for the filmography section."""
    return """
      <style>
        .author-filmography { margin-top: 2.5rem; padding-top: 2rem; border-top: 1px solid #333; }
        .author-filmography h2 { font-family: 'Playfair Display', serif; font-size: 1.5rem; margin-bottom: 0.5rem; }
        .author-filmography h3 { font-family: 'Raleway', sans-serif; font-size: 1rem; font-weight: 600; color: var(--gold, #c8a84e); margin: 1.5rem 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }
        .filmography-summary { font-size: 0.9rem; opacity: 0.7; margin-bottom: 1rem; }
        .filmography-list { list-style: none; padding: 0; margin: 0; }
        .filmography-list li { padding: 0.35rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .filmography-list a { color: inherit; text-decoration: none; }
        .filmography-list a:hover { color: var(--gold, #c8a84e); }
        .filmography-list em { font-style: italic; }
        .filmography-type { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.5; margin-left: 0.5rem; }
      </style>"""


def inject_filmography(bio_file, filmography_html):
    """
    Inject the filmography section into a bio page.
    Places it after the bio text, before the closing </div> of info-body.
    Removes any existing filmography section first.
    """
    path = os.path.join(ROOT, f'{bio_file}.html')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Remove existing filmography if present
    content = re.sub(
        r'\n\s*<div class="author-filmography">.*?</div>\s*\n',
        '\n',
        content,
        flags=re.DOTALL,
    )

    # Remove existing filmography CSS if present
    content = re.sub(
        r'\n\s*<style>\s*\.author-filmography.*?</style>\s*',
        '',
        content,
        flags=re.DOTALL,
    )

    # Insert filmography before the clear:both div or end of info-body
    # The pattern is: <div style="clear:both;"></div> followed by </div> (info-body)
    insertion_point = '<div style="clear:both;"></div>'
    if insertion_point in content:
        css = build_filmography_css()
        content = content.replace(
            insertion_point,
            f'{insertion_point}\n{css}\n{filmography_html}',
        )
    else:
        # Fallback: insert before </div> of info-body
        content = content.replace(
            '    </div>\n  </div>\n\n  <footer>',
            f'{filmography_html}\n    </div>\n  </div>\n\n  <footer>',
        )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Add filmography to author bio pages')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without modifying files')
    args = parser.parse_args()

    print("Scanning articles...")
    articles = scan_articles()
    print(f"Found {len(articles)} articles")

    by_author = group_by_author(articles)
    print(f"Found articles for {len(by_author)} authors\n")

    # Get all author names
    author_names = {}
    for bio in BIO_PAGES:
        author_names[bio] = get_author_name(bio)

    for bio in BIO_PAGES:
        name = author_names[bio]
        author_articles = by_author.get(bio, [])

        if not author_articles:
            print(f"  {name}: no articles found, skipping")
            continue

        review_count = sum(1 for a in author_articles if 'Review' in a['type'])
        feature_count = sum(1 for a in author_articles if 'Feature' in a['type'])
        years = sorted(set(a['year'] for a in author_articles))
        year_range = f"{years[0]}–{years[-1]}" if len(years) > 1 else years[0]

        print(f"  {name}: {len(author_articles)} articles "
              f"({review_count} reviews, {feature_count} features) "
              f"— {year_range}")

        if args.dry_run:
            continue

        filmography_html = build_filmography_html(author_articles, name)
        inject_filmography(bio, filmography_html)
        print(f"    -> Updated {bio}.html")

    if args.dry_run:
        print("\n[DRY RUN] No files modified.")
    else:
        print(f"\nDone! Updated {sum(1 for b in BIO_PAGES if by_author.get(b))} bio pages.")


if __name__ == '__main__':
    main()
