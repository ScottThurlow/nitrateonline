#!/usr/bin/env python3
"""
Batch-enrich review and feature pages with TMDB/OMDb metadata.

For each page with matching data in tmdb_data/:
  1. Replace sidebar film card credits with full data (director, writers,
     producers, cast, studio, runtime, rated, genre, awards, box office)
  2. Add ratings badges (IMDB, RT, Metacritic)
  3. Add external links (IMDB, TMDB, Rotten Tomatoes)
  4. If a TMDB poster exists:
     - Use it in the sidebar
     - Move the old scene still into the review body (if not already there)
     - Update OG image to the poster
  5. If no poster but a placeholder exists, leave the placeholder

Usage:
    python3 tools/enrich_pages.py --dry-run
    python3 tools/enrich_pages.py --limit 10
    python3 tools/enrich_pages.py
    python3 tools/enrich_pages.py --file 1997/rgattaca.html

Safe to re-run: replaces the entire film-card block each time.
"""

import argparse
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TMDB_DIR = os.path.join(ROOT, 'tmdb_data')
IMAGES_DIR = os.path.join(ROOT, 'images')

# Skip Gattaca — already manually enriched
SKIP_CODES = {'rgattaca'}


def load_tmdb_data(code):
    """Load TMDB metadata for a review code."""
    path = os.path.join(TMDB_DIR, 'metadata', f'{code}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def load_awards_data(code):
    """Load OMDb awards data for a review code."""
    path = os.path.join(TMDB_DIR, 'awards', f'{code}.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def find_review_files(single_file=None):
    """Find all review and feature HTML files."""
    if single_file:
        path = os.path.join(ROOT, single_file)
        if os.path.exists(path):
            return [path]
        print(f"ERROR: not found: {single_file}")
        sys.exit(1)
    files = []
    for year_dir in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]'))):
        for f in sorted(glob.glob(os.path.join(year_dir, '[rf]*.html'))):
            files.append(f)
    return files


def has_poster(code):
    """Check if a TMDB poster was fetched for this code."""
    return os.path.exists(os.path.join(TMDB_DIR, 'posters', f'{code}-poster.jpg'))


def ensure_poster_in_images(code):
    """Copy poster from tmdb_data to images/ if not already there."""
    src = os.path.join(TMDB_DIR, 'posters', f'{code}-poster.jpg')
    dst = os.path.join(IMAGES_DIR, f'{code}-poster.jpg')
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
    return os.path.exists(dst)


def extract_current_sidebar_image(content):
    """Extract the current image src from the film-card-poster section."""
    m = re.search(
        r'<div class="film-card-poster">\s*<img[^>]+src="([^"]+)"',
        content, re.DOTALL)
    if m:
        return m.group(1)
    return None


def is_placeholder_poster(content):
    """Check if the film card uses a placeholder instead of a real image."""
    return 'film-card-poster-placeholder' in content


def image_already_in_body(content, img_src):
    """Check if an image src is already in the article body (not sidebar/head)."""
    basename = os.path.basename(img_src)
    # Look only within the <article class="article-body"> ... </article> section
    m = re.search(r'<article[^>]*class="article-body"[^>]*>(.*?)</article>', content, re.DOTALL)
    if m:
        return basename in m.group(1)
    return False


def build_credit_html(label, value):
    """Build a single film-credit div."""
    escaped = html.escape(value)
    return (f'            <div class="film-credit">\n'
            f'              <dt class="credit-label">{label}</dt>\n'
            f'              <dd class="credit-value">{escaped}</dd>\n'
            f'            </div>')


def build_film_card(code, tmdb, awards, poster_src):
    """Build the complete film-card HTML block."""
    title = html.escape(tmdb.get('title', ''))
    year = ''
    if tmdb.get('release_date'):
        year = tmdb['release_date'][:4]
    elif awards and awards.get('year') and awards['year'] != 'N/A':
        year = awards['year']

    # Poster section
    if poster_src:
        poster_html = (
            f'        <div class="film-card-poster">\n'
            f'          <img loading="lazy" src="{poster_src}" alt="{title} poster" '
            f'style="width:100%;display:block;">\n'
            f'        </div>')
    else:
        poster_html = (
            f'        <div class="film-card-poster">\n'
            f'          <div class="film-card-poster-placeholder">\n'
            f'            <img src="/favicon.svg" alt="" aria-hidden="true">\n'
            f'          </div>\n'
            f'        </div>')

    # Credits
    credits = []

    # Director
    directors = tmdb.get('director', [])
    if directors:
        credits.append(build_credit_html('Director', ', '.join(directors)))

    # Writers
    writers = tmdb.get('writers', [])
    if writers:
        writer_names = []
        seen = set()
        for w in writers:
            name = w['name'] if isinstance(w, dict) else w
            if name not in seen:
                writer_names.append(name)
                seen.add(name)
        if writer_names:
            credits.append(build_credit_html('Writer' + ('s' if len(writer_names) > 1 else ''),
                                             ', '.join(writer_names[:4])))

    # Producers (top 3)
    producers = tmdb.get('producers', [])
    if producers:
        prod_names = []
        seen = set()
        for p in producers:
            name = p['name'] if isinstance(p, dict) else p
            if name not in seen:
                prod_names.append(name)
                seen.add(name)
        if prod_names:
            credits.append(build_credit_html('Producer' + ('s' if len(prod_names) > 1 else ''),
                                             ', '.join(prod_names[:3])))

    # Cast (top 6)
    cast = tmdb.get('cast', [])
    if cast:
        cast_names = [c['name'] if isinstance(c, dict) else c for c in cast[:6]]
        credits.append(build_credit_html('Starring', ', '.join(cast_names)))

    # Studio
    studios = tmdb.get('production_companies', [])
    if studios:
        studio_names = [s['name'] if isinstance(s, dict) else s for s in studios[:3]]
        credits.append(build_credit_html('Studio', ' / '.join(studio_names)))

    # Runtime
    runtime = tmdb.get('runtime')
    if runtime:
        credits.append(build_credit_html('Runtime', f'{runtime} min'))

    # Rated (from OMDb)
    if awards and awards.get('rated') and awards['rated'] != 'N/A':
        credits.append(build_credit_html('Rated', awards['rated']))

    # Genre
    genres = tmdb.get('genres', [])
    if genres:
        credits.append(build_credit_html('Genre', ', '.join(genres[:4])))

    # Awards (from OMDb)
    if awards and awards.get('awards') and awards['awards'] != 'N/A':
        credits.append(build_credit_html('Awards', awards['awards']))

    # Box office (from OMDb)
    if awards and awards.get('box_office') and awards['box_office'] != 'N/A':
        credits.append(build_credit_html('Box Office', awards['box_office']))

    credits_html = '\n'.join(credits)

    # Ratings badges
    ratings_html = ''
    if awards:
        badges = []
        imdb = awards.get('imdb_rating')
        if imdb and imdb != 'N/A':
            badges.append(f'            <span class="film-rating" title="IMDB">IMDB {imdb}</span>')
        for r in awards.get('ratings', []):
            if r.get('source') == 'Rotten Tomatoes':
                badges.append(f'            <span class="film-rating" title="Rotten Tomatoes">RT {r["value"]}</span>')
            elif r.get('source') == 'Metacritic':
                mc = r['value'].replace('/100', '')
                badges.append(f'            <span class="film-rating" title="Metacritic">MC {mc}</span>')
        if badges:
            ratings_html = (
                f'          <div class="film-card-ratings">\n'
                + '\n'.join(badges) + '\n'
                f'          </div>')

    # External links
    links = []
    imdb_id = tmdb.get('imdb_id', '')
    tmdb_id = tmdb.get('tmdb_id', '')
    if imdb_id:
        links.append(
            f'            <a href="https://www.imdb.com/title/{imdb_id}/" '
            f'class="film-link" rel="noopener" target="_blank">IMDB (Full Credits)</a>')
    if tmdb_id:
        links.append(
            f'            <a href="https://www.themoviedb.org/movie/{tmdb_id}" '
            f'class="film-link" rel="noopener" target="_blank">TMDB</a>')
    # RT link from awards
    if awards:
        for r in awards.get('ratings', []):
            if r.get('source') == 'Rotten Tomatoes' and r.get('link'):
                links.append(
                    f'            <a href="{html.escape(r["link"])}" '
                    f'class="film-link" rel="noopener" target="_blank">Rotten Tomatoes</a>')
                break

    links_html = ''
    if links:
        links_html = (
            f'          <div class="film-card-links">\n'
            + '\n'.join(links) + '\n'
            f'          </div>')

    # Assemble
    year_display = f' ({year})' if year else ''
    card = (
        f'      <div class="film-card">\n'
        f'{poster_html}\n'
        f'        <div class="film-card-body">\n'
        f'          <h2 class="film-card-title"><em>{title}</em>{year_display}</h2>\n'
        f'          <dl class="film-credits">\n'
        f'{credits_html}\n'
        f'          </dl>\n'
        f'{ratings_html}\n'
        f'{links_html}\n'
        f'        </div>\n'
        f'      </div>')

    return card


def insert_image_in_body(content, img_src, alt_text):
    """Insert an image into the article body after the first paragraph."""
    # Find the end of the first <p>...</p> in the article body
    body_start = content.find('class="article-body"')
    if body_start == -1:
        return content

    # Find the first </p> after article-body
    first_p_end = content.find('</p>', body_start)
    if first_p_end == -1:
        return content

    insert_pos = first_p_end + len('</p>')
    img_tag = (f'\n\n<img src="{img_src}" alt="{html.escape(alt_text)}" '
               f'style="float:right;margin:0 0 1rem 1.5rem;">')

    return content[:insert_pos] + img_tag + content[insert_pos:]


def update_og_image(content, poster_src, code):
    """Update the og:image meta tag to use the poster."""
    if not poster_src or not poster_src.startswith('/'):
        return content
    new_url = f'https://nitrateonline.com{poster_src}'
    content = re.sub(
        r'<meta property="og:image" content="[^"]*">',
        f'<meta property="og:image" content="{new_url}">',
        content)
    return content


def extract_film_card(content):
    """Extract the full film-card div from the content."""
    start = content.find('<div class="film-card">')
    if start == -1:
        return None, None, None

    # Find matching closing div - count nesting
    depth = 0
    i = start
    while i < len(content):
        if content[i:i+4] == '<div':
            depth += 1
            i += 4
        elif content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                end = i + 6
                return content[start:end], start, end
            i += 6
        else:
            i += 1
    return None, None, None


def process_file(filepath, dry_run=False, verbose=False):
    """Process a single review/feature page."""
    code = os.path.basename(filepath).replace('.html', '')

    tmdb = load_tmdb_data(code)
    if not tmdb:
        return 'no_data'

    awards = load_awards_data(code)

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Must have a film-card to update
    old_card, card_start, card_end = extract_film_card(content)
    if old_card is None:
        return 'no_card'

    # Determine poster situation
    current_img = extract_current_sidebar_image(content)
    has_placeholder = is_placeholder_poster(content)
    poster_available = has_poster(code)

    poster_src = None
    move_old_image = False

    if poster_available:
        if not dry_run:
            ensure_poster_in_images(code)
        poster_src = f'/images/{code}-poster.jpg'

        # If there was a real image (not placeholder), move it to the body
        if current_img and not has_placeholder:
            # Check it's not already in the body
            if not image_already_in_body(content, current_img):
                move_old_image = True
    elif current_img and not has_placeholder:
        # No TMDB poster, keep the existing image
        poster_src = current_img
    # else: no poster at all, will use placeholder

    # Build new film card
    new_card = build_film_card(code, tmdb, awards, poster_src)

    # Replace the film card
    new_content = content[:card_start] + new_card + content[card_end:]

    # Move old image into body if needed
    if move_old_image and current_img:
        title = tmdb.get('title', code)
        if not image_already_in_body(new_content, current_img):
            new_content = insert_image_in_body(
                new_content, current_img, f'Scene from {title}')

    # Update OG image if we have a poster
    if poster_available:
        new_content = update_og_image(new_content, poster_src, code)

    if new_content != content:
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
        return 'updated'
    return 'unchanged'


def main():
    parser = argparse.ArgumentParser(
        description='Batch-enrich pages with TMDB/OMDb data')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--file', type=str)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    files = find_review_files(args.file)
    print(f"Found {len(files)} review/feature files")

    # Filter to those with TMDB data
    eligible = []
    for f in files:
        code = os.path.basename(f).replace('.html', '')
        if code in SKIP_CODES:
            continue
        if load_tmdb_data(code):
            eligible.append(f)

    print(f"{len(eligible)} have TMDB metadata")

    if args.limit > 0:
        eligible = eligible[:args.limit]
        print(f"Limited to {len(eligible)}")

    if args.dry_run:
        updated = no_card = unchanged = 0
        for f in eligible:
            result = process_file(f, dry_run=True, verbose=args.verbose)
            if result == 'updated':
                updated += 1
            elif result == 'no_card':
                no_card += 1
            else:
                unchanged += 1
        print(f"\n[DRY RUN] Would update: {updated}, No card: {no_card}, Unchanged: {unchanged}")
        return

    updated = 0
    no_card = 0
    no_data = 0
    unchanged = 0
    errors = 0

    for i, filepath in enumerate(eligible, 1):
        code = os.path.basename(filepath).replace('.html', '')
        relpath = os.path.relpath(filepath, ROOT)

        try:
            result = process_file(filepath, verbose=args.verbose)
            if result == 'updated':
                updated += 1
                if args.verbose or i % 100 == 0:
                    print(f"[{i}/{len(eligible)}] {relpath}: updated")
            elif result == 'no_card':
                no_card += 1
                if args.verbose:
                    print(f"[{i}/{len(eligible)}] {relpath}: no film card found")
            elif result == 'no_data':
                no_data += 1
            else:
                unchanged += 1
        except Exception as e:
            errors += 1
            print(f"[{i}/{len(eligible)}] {relpath}: ERROR: {e}")

        if i % 200 == 0:
            print(f"  ... processed {i}/{len(eligible)}")

    print(f"\nDone!")
    print(f"  Updated:   {updated}")
    print(f"  No card:   {no_card}")
    print(f"  No data:   {no_data}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Errors:    {errors}")


if __name__ == '__main__':
    main()
