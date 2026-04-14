#!/usr/bin/env python3
"""
Add Schema.org Movie structured data to review/feature pages.

Extracts film metadata from the sidebar film card and generates a
JSON-LD Movie object alongside the existing Article object. This gives
search engines rich movie metadata (director, cast, ratings, etc.)
in addition to the article/review metadata.

Usage:
    python3 tools/add_movie_schema.py --dry-run    # preview changes
    python3 tools/add_movie_schema.py --limit 5     # test on 5 pages
    python3 tools/add_movie_schema.py               # update all pages
"""

import argparse
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def extract_film_card(content):
    """Extract all metadata from the film card sidebar."""
    data = {}

    # Title and year from film-card-title
    m = re.search(
        r'film-card-title"><em>([^<]+)</em>\s*\((\d{4})\)', content)
    if m:
        data['title'] = html.unescape(m.group(1).strip())
        data['year'] = m.group(2)
    else:
        return None  # No film card

    # Poster image
    m = re.search(r'film-card-poster">\s*<img[^>]*src="([^"]+)"', content)
    if m:
        data['poster'] = m.group(1)

    # Credits from <dt>/<dd> pairs
    for m in re.finditer(
        r'credit-label">([^<]+)</dt>\s*<dd class="credit-value">([^<]+)',
        content):
        label = m.group(1).strip()
        value = html.unescape(m.group(2).strip())

        if label == 'Director':
            data['directors'] = [n.strip() for n in value.split(',')]
        elif label == 'Writers':
            data['writers'] = [n.strip() for n in value.split(',')]
        elif label == 'Producers':
            data['producers'] = [n.strip() for n in value.split(',')]
        elif label == 'Starring':
            data['actors'] = [n.strip() for n in value.split(',')]
        elif label == 'Studio':
            data['studios'] = [n.strip() for n in value.split('/')]
        elif label == 'Runtime':
            data['runtime'] = value  # e.g. "129 min"
        elif label == 'Rated':
            data['rated'] = value  # e.g. "R", "PG-13"
        elif label == 'Genre':
            data['genres'] = [g.strip() for g in value.split(',')]
        elif label == 'Awards':
            data['awards'] = value
        elif label == 'Box Office':
            data['box_office'] = value

    # Ratings
    for m in re.finditer(
        r'film-rating"[^>]*>(\w+)\s+([\d.]+%?)', content):
        source = m.group(1)
        val = m.group(2)
        if source == 'IMDB':
            data['imdb_rating'] = val
        elif source == 'RT':
            data['rt_rating'] = val
        elif source == 'MC':
            data['mc_rating'] = val

    # IMDB URL
    m = re.search(r'href="(https://www\.imdb\.com/title/tt\d+/)"', content)
    if m:
        data['imdb_url'] = m.group(1)

    return data


def runtime_to_iso(runtime_str):
    """Convert '129 min' to ISO 8601 duration 'PT129M'."""
    m = re.search(r'(\d+)\s*min', runtime_str)
    if m:
        return f'PT{m.group(1)}M'
    return None


def build_movie_jsonld(data, page_url):
    """Build a Schema.org Movie JSON-LD object from extracted data."""
    movie = {
        '@type': 'Movie',
        'name': data['title'],
    }

    if 'year' in data:
        movie['dateCreated'] = data['year']

    if 'poster' in data:
        if data['poster'].startswith('/'):
            movie['image'] = f'https://nitrateonline.com{data["poster"]}'
        else:
            movie['image'] = data['poster']

    if 'directors' in data:
        if len(data['directors']) == 1:
            movie['director'] = {
                '@type': 'Person',
                'name': data['directors'][0],
            }
        else:
            movie['director'] = [
                {'@type': 'Person', 'name': n}
                for n in data['directors']
            ]

    if 'actors' in data:
        movie['actor'] = [
            {'@type': 'Person', 'name': n}
            for n in data['actors']
        ]

    if 'studios' in data:
        if len(data['studios']) == 1:
            movie['productionCompany'] = {
                '@type': 'Organization',
                'name': data['studios'][0],
            }
        else:
            movie['productionCompany'] = [
                {'@type': 'Organization', 'name': n.strip()}
                for n in data['studios']
            ]

    if 'runtime' in data:
        iso = runtime_to_iso(data['runtime'])
        if iso:
            movie['duration'] = iso

    if 'rated' in data:
        movie['contentRating'] = data['rated']

    if 'genres' in data:
        movie['genre'] = data['genres']

    if 'awards' in data:
        movie['award'] = data['awards']

    if 'imdb_url' in data:
        movie['sameAs'] = data['imdb_url']

    # Aggregate ratings — use IMDB as the primary since it has a numeric scale
    if 'imdb_rating' in data:
        movie['aggregateRating'] = {
            '@type': 'AggregateRating',
            'ratingValue': data['imdb_rating'],
            'bestRating': '10',
            'worstRating': '1',
            'ratingSource': 'IMDb',
        }

    return movie


def build_review_jsonld(data, article_data):
    """
    Build a Schema.org Review JSON-LD referencing the Movie as itemReviewed.
    Enhances the existing Article data into a proper Review.
    """
    review = {
        '@type': 'Review',
        'itemReviewed': build_movie_jsonld(data, None),
    }

    # Carry over article fields
    if 'headline' in article_data:
        review['name'] = article_data['headline']
    if 'description' in article_data:
        review['description'] = article_data['description']
    if 'url' in article_data:
        review['url'] = article_data['url']
    if 'image' in article_data:
        review['image'] = article_data['image']
    if 'datePublished' in article_data:
        review['datePublished'] = article_data['datePublished']
    if 'publisher' in article_data:
        review['publisher'] = article_data['publisher']
    if 'author' in article_data:
        review['author'] = article_data['author']

    return review


def extract_existing_jsonld(content):
    """Extract the existing JSON-LD Article data."""
    m = re.search(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            # Some pages have newlines inside JSON string values — fix them
            cleaned = re.sub(
                r'(?<=": ")(.*?)(?=")',
                lambda m: re.sub(r'[\n\r\t]+', ' ', m.group(0)),
                m.group(1), flags=re.DOTALL)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None
    return None


def inject_movie_schema(filepath, dry_run=False):
    """
    Add Movie schema to a page. For reviews, converts the Article to a
    Review with itemReviewed=Movie. For features, adds a separate Movie
    block alongside the Article.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Skip if already has Movie schema
    if '"@type": "Movie"' in content or '"@type":"Movie"' in content:
        return False, 'already_has_movie_schema'

    # Extract film card data
    film_data = extract_film_card(content)
    if not film_data:
        return False, 'no_film_card'

    # Extract existing JSON-LD
    existing = extract_existing_jsonld(content)
    if not existing:
        return False, 'no_existing_jsonld'

    # Determine if this is a review (r*.html) or feature (f*.html)
    basename = os.path.basename(filepath)
    is_review = basename.startswith('r')

    if is_review:
        # Build a Review with itemReviewed = Movie
        new_jsonld = {
            '@context': 'https://schema.org',
            '@type': 'Review',
            'itemReviewed': build_movie_jsonld(film_data, None),
        }
        # Copy existing article fields into the Review
        for key in ('headline', 'description', 'publisher', 'url',
                    'image', 'author', 'datePublished'):
            if key in existing:
                new_jsonld[key] = existing[key]
        # Map headline -> name for Review
        if 'headline' in existing:
            new_jsonld['name'] = existing['headline']
    else:
        # Feature: use @graph with both Article and Movie
        movie = build_movie_jsonld(film_data, None)
        # Keep existing article, add Movie alongside
        new_jsonld = {
            '@context': 'https://schema.org',
            '@graph': [
                existing,
                movie,
            ],
        }
        # Remove @context from the nested Article since it's at the top level
        if '@context' in new_jsonld['@graph'][0]:
            del new_jsonld['@graph'][0]['@context']

    # Format the JSON-LD
    formatted = json.dumps(new_jsonld, indent=4, ensure_ascii=False)

    # Replace the existing JSON-LD block
    new_script = f'<script type="application/ld+json">\n  {formatted}\n  </script>'

    content = re.sub(
        r'<script type="application/ld\+json">\s*\{.*?\}\s*</script>',
        new_script,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return True, 'review' if is_review else 'feature'


def main():
    parser = argparse.ArgumentParser(
        description='Add Schema.org Movie structured data')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without modifying files')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of files to process')
    parser.add_argument('--file', type=str,
                        help='Process a single file')
    args = parser.parse_args()

    if args.file:
        files = [args.file]
    else:
        files = sorted(glob.glob(
            os.path.join(ROOT, '[12][0-9][0-9][0-9]', '[rf]*.html')))

    if args.limit > 0:
        files = files[:args.limit]

    print(f'Processing {len(files)} files...')

    updated = 0
    skipped_no_card = 0
    skipped_existing = 0
    skipped_no_jsonld = 0
    reviews = 0
    features = 0

    for f in files:
        rel = os.path.relpath(f, ROOT)
        success, detail = inject_movie_schema(f, dry_run=args.dry_run)

        if success:
            updated += 1
            if detail == 'review':
                reviews += 1
            else:
                features += 1
            if args.dry_run or args.limit:
                print(f'  {rel}: {detail}')
        else:
            if detail == 'no_film_card':
                skipped_no_card += 1
            elif detail == 'already_has_movie_schema':
                skipped_existing += 1
            elif detail == 'no_existing_jsonld':
                skipped_no_jsonld += 1

    action = 'Would update' if args.dry_run else 'Updated'
    print(f'\n{action} {updated} pages ({reviews} reviews, {features} features)')
    print(f'Skipped: {skipped_no_card} no film card, '
          f'{skipped_existing} already has Movie schema, '
          f'{skipped_no_jsonld} no existing JSON-LD')


if __name__ == '__main__':
    main()
