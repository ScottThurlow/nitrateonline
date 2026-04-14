#!/usr/bin/env python3
"""
tools/crosslink.py
Cross-link reviews and features/interviews about the same film.

For each film that has both review(s) and feature(s)/interview(s), inject a
"Related" sidebar widget into each page linking to the counterpart(s).

Usage:
  python3 tools/crosslink.py
  python3 tools/crosslink.py --dry-run
"""

import re, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']

DRY_RUN = '--dry-run' in sys.argv

# ─────────────────────────────────────────────────────────────────
# EXTRACTION
# ─────────────────────────────────────────────────────────────────

FILM_CARD_TITLE_RE = re.compile(
    r'<h2 class="film-card-title"><em>(.*?)</em>\s*\((\d{4})\)</h2>'
)

ARTICLE_TITLE_RE = re.compile(
    r'<h1 class="article-title">(?:<em>)?(.*?)(?:</em>)?</h1>'
)

BYLINE_RE = re.compile(
    r'<span class="meta-byline">(.*?)</span>', re.DOTALL
)


def extract_info(path: Path):
    """Extract film-card title, article title, and byline from an HTML file."""
    text = path.read_text(encoding='utf-8', errors='replace')

    film_match = FILM_CARD_TITLE_RE.search(text)
    if not film_match:
        return None

    film_title = film_match.group(1).strip()
    film_year = film_match.group(2)

    article_match = ARTICLE_TITLE_RE.search(text)
    article_title = article_match.group(1).strip() if article_match else path.stem

    byline_match = BYLINE_RE.search(text)
    byline = ''
    if byline_match:
        # Strip HTML tags from byline
        byline = re.sub(r'<[^>]+>', '', byline_match.group(1)).strip()

    return {
        'path': path,
        'film_title': film_title,
        'film_year': film_year,
        'film_key': f'{film_title}||{film_year}',
        'article_title': article_title,
        'byline': byline,
        'is_review': path.name.startswith('r'),
        'is_feature': path.name.startswith('f'),
    }


# ─────────────────────────────────────────────────────────────────
# WIDGET HTML GENERATION
# ─────────────────────────────────────────────────────────────────

WIDGET_MARKER = '<!-- crosslink-widget -->'


def make_crosslink_widget(current_path: Path, related_pages: list) -> str:
    """Build a sidebar widget linking to related reviews/features for the same film."""
    lines = [WIDGET_MARKER]
    lines.append('<div class="sidebar-widget">')
    lines.append('  <div class="widget-header"><h3 class="widget-title">Related</h3></div>')
    lines.append('  <div class="widget-body">')
    lines.append('    <ul class="related-list">')

    for page in related_pages:
        # Build relative URL
        if page['path'].parent == current_path.parent:
            href = page['path'].name
        else:
            # Cross-year link
            year = page['path'].parent.name
            href = f'/{year}/{page["path"].name}'

        tag = 'Review' if page['is_review'] else 'Feature'
        title = page['article_title']
        byline = page['byline']

        lines.append(f'      <li><a href="{href}">')
        lines.append(f'        <span class="related-dir">{tag}</span>')
        lines.append(f'        {title}')
        if byline:
            lines.append(f'        <span class="related-dir">{byline}</span>')
        lines.append(f'      </a></li>')

    lines.append('    </ul>')
    lines.append('  </div>')
    lines.append('</div>')

    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────
# INJECTION
# ─────────────────────────────────────────────────────────────────

def inject_widget(html: str, widget_html: str) -> str:
    """
    Insert the crosslink widget into the sidebar, right after the film-card div.
    If a crosslink widget already exists, replace it.
    """
    # Remove existing crosslink widget if present
    if WIDGET_MARKER in html:
        # Remove widget and normalize surrounding whitespace
        html = re.sub(
            r'\s*<!-- crosslink-widget -->\n<div class="sidebar-widget">\n'
            r'  <div class="widget-header">.*?</div>\n'
            r'  <div class="widget-body">\n'
            r'.*?'
            r'  </div>\n'
            r'</div>\s*',
            '\n\n      ',
            html,
            flags=re.DOTALL
        )

    # Find the film-card div, then insert before the first sidebar-widget after it
    card_idx = html.find('<div class="film-card">')
    if card_idx == -1:
        return html

    # Find the first <div class="sidebar-widget"> after the film-card
    widget_pattern = re.compile(r'(\n+\s*)(<div class="sidebar-widget">)')
    match = widget_pattern.search(html, card_idx)
    if match:
        indent = '      '
        return (html[:match.start()]
                + '\n\n' + indent + widget_html
                + '\n\n' + indent + match.group(2)
                + html[match.end():])

    return html


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    # Phase 1: Collect all pages with film cards
    all_pages = []
    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue
        for fp in sorted(yr_dir.glob('*.html')):
            if fp.name == 'index.html':
                continue
            if not (fp.name.startswith('r') or fp.name.startswith('f')):
                continue
            info = extract_info(fp)
            if info:
                all_pages.append(info)

    # Phase 2: Group by film
    film_groups = defaultdict(list)
    for page in all_pages:
        film_groups[page['film_key']].append(page)

    # Phase 3: Find films with both reviews and features
    crosslink_films = {}
    for key, pages in film_groups.items():
        has_review = any(p['is_review'] for p in pages)
        has_feature = any(p['is_feature'] for p in pages)
        if has_review and has_feature:
            crosslink_films[key] = pages

    if not crosslink_films:
        print('No films found with both reviews and features.')
        return

    print(f'Found {len(crosslink_films)} film(s) with both reviews and features:\n')
    for key, pages in sorted(crosslink_films.items()):
        reviews = [p for p in pages if p['is_review']]
        features = [p for p in pages if p['is_feature']]
        title = pages[0]['film_title']
        year = pages[0]['film_year']
        print(f'  {title} ({year})')
        for r in reviews:
            print(f'    Review:  {r["path"].parent.name}/{r["path"].name}  — {r["article_title"]}')
        for f in features:
            print(f'    Feature: {f["path"].parent.name}/{f["path"].name}  — {f["article_title"]}')
    print()

    # Phase 4: Remove stale crosslink widgets from pages no longer in any group
    crosslinked_paths = set()
    for pages in crosslink_films.values():
        for p in pages:
            crosslinked_paths.add(p['path'])

    cleaned = 0
    for page in all_pages:
        if page['path'] in crosslinked_paths:
            continue
        html = page['path'].read_text(encoding='utf-8', errors='replace')
        if WIDGET_MARKER not in html:
            continue
        # Remove the stale widget
        updated = re.sub(
            r'\s*<!-- crosslink-widget -->\n<div class="sidebar-widget">\n'
            r'  <div class="widget-header">.*?</div>\n'
            r'  <div class="widget-body">\n'
            r'.*?'
            r'  </div>\n'
            r'</div>\s*',
            '\n\n      ',
            html,
            flags=re.DOTALL
        )
        if updated != html:
            cleaned += 1
            if DRY_RUN:
                print(f'  [DRY] would clean stale widget: {page["path"].parent.name}/{page["path"].name}')
            else:
                page['path'].write_text(updated, encoding='utf-8')
                print(f'  Cleaned stale widget: {page["path"].parent.name}/{page["path"].name}')

    # Phase 5: Inject crosslink widgets
    modified = 0
    for key, pages in crosslink_films.items():
        for page in pages:
            # Related pages = all other pages for this film
            related = [p for p in pages if p['path'] != page['path']]
            if not related:
                continue

            widget_html = make_crosslink_widget(page['path'], related)
            original = page['path'].read_text(encoding='utf-8', errors='replace')
            updated = inject_widget(original, widget_html)

            if updated != original:
                modified += 1
                if DRY_RUN:
                    print(f'  [DRY] would modify: {page["path"].parent.name}/{page["path"].name}')
                else:
                    page['path'].write_text(updated, encoding='utf-8')
                    print(f'  Modified: {page["path"].parent.name}/{page["path"].name}')

    print(f'\nCleaned {cleaned} stale widget(s), modified {modified} file(s).')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
