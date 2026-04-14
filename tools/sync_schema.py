#!/usr/bin/env python3
"""
tools/sync_schema.py
Sync JSON-LD Movie schema with sidebar film card data.

For each page with both a film card and a JSON-LD Movie schema, ensures
the schema name, dateCreated, director, actor, and sameAs fields match
the film card.

Usage:
  python3 tools/sync_schema.py --dry-run
  python3 tools/sync_schema.py
"""

import html as htmlmod
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']
DRY_RUN = '--dry-run' in sys.argv

# ─────────────────────────────────────────────────────────────────
# EXTRACTION
# ─────────────────────────────────────────────────────────────────

FILM_CARD_TITLE_RE = re.compile(
    r'<h2 class="film-card-title"><em>(.*?)</em>\s*\((\d{4})\)</h2>'
)

# Extract director from film card
DIRECTOR_RE = re.compile(
    r'<dt class="credit-label">Director</dt>\s*<dd class="credit-value">(.*?)</dd>',
    re.DOTALL
)

# Extract cast from film card
CAST_RE = re.compile(
    r'<dt class="credit-label">Starring</dt>\s*<dd class="credit-value">(.*?)</dd>',
    re.DOTALL
)

# Extract IMDB link
IMDB_RE = re.compile(
    r'href="(https://www\.imdb\.com/title/[^"]+)"'
)

# JSON-LD block
JSONLD_RE = re.compile(
    r'(<script type="application/ld\+json">\s*)(.*?)(</script>)',
    re.DOTALL
)


def extract_card_data(html):
    """Extract film metadata from the sidebar film card."""
    title_m = FILM_CARD_TITLE_RE.search(html)
    if not title_m:
        return None

    title = htmlmod.unescape(title_m.group(1).strip())
    year = title_m.group(2)

    director_m = DIRECTOR_RE.search(html)
    directors = []
    if director_m:
        directors = [d.strip() for d in htmlmod.unescape(director_m.group(1)).split(',')]

    cast_m = CAST_RE.search(html)
    cast = []
    if cast_m:
        cast = [c.strip() for c in htmlmod.unescape(cast_m.group(1)).split(',')]

    imdb_m = IMDB_RE.search(html)
    imdb_url = imdb_m.group(1) if imdb_m else None

    return {
        'title': title,
        'year': year,
        'directors': directors,
        'cast': cast,
        'imdb_url': imdb_url,
    }


def update_movie_in_schema(schema, card, publish_date=None):
    """Update the Movie object within the schema to match card data.
    Also adds datePublished to the Article/Review if provided."""
    changed = False

    # Add datePublished to the top-level Article/Review schema
    if publish_date and schema.get('@type') in ('Article', 'Review', 'NewsArticle'):
        if schema.get('datePublished') != publish_date:
            schema['datePublished'] = publish_date
            changed = True

    # Find the Movie object - it could be top-level or nested in "itemReviewed"
    movie = None
    if schema.get('@type') == 'Movie':
        movie = schema
    elif schema.get('itemReviewed', {}).get('@type') == 'Movie':
        movie = schema['itemReviewed']

    if not movie:
        return changed

    # Update name
    if movie.get('name') != card['title']:
        movie['name'] = card['title']
        changed = True

    # Update dateCreated
    if movie.get('dateCreated') != card['year']:
        movie['dateCreated'] = card['year']
        changed = True

    # Update director
    if card['directors']:
        new_directors = card['directors']
        old_director = movie.get('director')

        # Normalize old director to a list of names for comparison
        old_names = []
        if isinstance(old_director, dict):
            old_names = [old_director.get('name', '')]
        elif isinstance(old_director, list):
            old_names = [d.get('name', '') if isinstance(d, dict) else d for d in old_director]

        if old_names != new_directors:
            if len(new_directors) == 1:
                movie['director'] = {'@type': 'Person', 'name': new_directors[0]}
            else:
                movie['director'] = [{'@type': 'Person', 'name': d} for d in new_directors]
            changed = True

    # Update actors
    if card['cast']:
        old_actors = movie.get('actor', [])
        old_names = []
        if isinstance(old_actors, list):
            old_names = [a.get('name', '') if isinstance(a, dict) else a for a in old_actors]

        if old_names != card['cast']:
            movie['actor'] = [{'@type': 'Person', 'name': c} for c in card['cast']]
            changed = True

    # Update sameAs (IMDB URL)
    if card['imdb_url']:
        if movie.get('sameAs') != card['imdb_url']:
            movie['sameAs'] = card['imdb_url']
            changed = True

    return changed


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    modified = 0
    no_schema = 0
    no_card = 0
    already_correct = 0

    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue

        for fp in sorted(yr_dir.glob('*.html')):
            if fp.name == 'index.html':
                continue
            if not (fp.name.startswith('r') or fp.name.startswith('f')):
                continue

            html = fp.read_text(encoding='utf-8', errors='replace')

            # Extract card data
            card = extract_card_data(html)
            if not card:
                no_card += 1
                continue

            # Find JSON-LD block
            jsonld_match = JSONLD_RE.search(html)
            if not jsonld_match:
                no_schema += 1
                continue

            prefix = jsonld_match.group(1)
            json_text = jsonld_match.group(2).strip()
            suffix = jsonld_match.group(3)

            try:
                schema = json.loads(json_text)
            except json.JSONDecodeError:
                continue

            # Extract publish date from article-meta if present
            pub_match = re.search(r'Published (\d+) (\w+) (\d{4})', html)
            publish_date = None
            if pub_match:
                from datetime import datetime
                try:
                    dt = datetime.strptime(
                        f'{pub_match.group(1)} {pub_match.group(2)} {pub_match.group(3)}',
                        '%d %B %Y'
                    )
                    publish_date = dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass

            # Update the Movie in the schema
            changed = update_movie_in_schema(schema, card, publish_date)

            if not changed:
                already_correct += 1
                continue

            # Serialize back
            new_json = json.dumps(schema, indent=4, ensure_ascii=False)
            new_block = prefix + new_json + '\n  ' + suffix

            new_html = html[:jsonld_match.start()] + new_block + html[jsonld_match.end():]

            modified += 1
            rel = f'{yr}/{fp.name}'
            if DRY_RUN:
                print(f'  [DRY] {rel}: {card["title"]} ({card["year"]})')
            else:
                fp.write_text(new_html, encoding='utf-8')
                print(f'  {rel}: schema synced to "{card["title"]}" ({card["year"]})')

    print(f'\nSynced {modified} schema(s). '
          f'{already_correct} already correct, '
          f'{no_schema} without schema, '
          f'{no_card} without card.')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
