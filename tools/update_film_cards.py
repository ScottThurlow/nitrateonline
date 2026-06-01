#!/usr/bin/env python3
"""
Update film cards in HTML pages with poster images and credits from TMDB.

Reads poster_manifest.json to find TMDB IDs, then fetches credits
and updates the HTML film-card sidebar.

Usage:
    python3 tools/update_film_cards.py --dry-run
    python3 tools/update_film_cards.py
    python3 tools/update_film_cards.py --file 2004/fkillbill.html
"""

import argparse
import glob
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
IMAGES_DIR = os.path.join(ROOT, 'images')
MANIFEST_PATH = os.path.join(ROOT, 'tools', 'poster_manifest.json')

TMDB_API_BASE = 'https://api.themoviedb.org/3'
REQUEST_DELAY = 0.25


def get_api_key():
    key = os.environ.get('TMDB_API_KEY', '').strip()
    if key:
        return key
    keyfile = os.path.join(ROOT, '.tmdb_api_key')
    if os.path.exists(keyfile):
        with open(keyfile) as f:
            key = f.read().strip()
        if key:
            return key
    print("ERROR: TMDB API key not found.")
    sys.exit(1)


def tmdb_get(endpoint, params, api_key):
    params['api_key'] = api_key
    url = f'{TMDB_API_BASE}{endpoint}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry_after = int(e.headers.get('Retry-After', '5'))
            time.sleep(retry_after)
            return tmdb_get(endpoint, params, api_key)
        return None
    except urllib.error.URLError:
        return None


def fetch_movie_details(tmdb_id, api_key):
    """Fetch movie details and credits from TMDB."""
    details = tmdb_get(f'/movie/{tmdb_id}', {'language': 'en-US'}, api_key)
    time.sleep(REQUEST_DELAY)
    credits = tmdb_get(f'/movie/{tmdb_id}/credits', {'language': 'en-US'}, api_key)
    time.sleep(REQUEST_DELAY)

    if not details:
        return None

    info = {
        'title': details.get('title', ''),
        'year': (details.get('release_date') or '')[:4],
        'runtime': details.get('runtime', 0),
        'tmdb_id': tmdb_id,
        'imdb_id': details.get('imdb_id', ''),
        'genres': [g['name'] for g in details.get('genres', [])],
    }

    if credits:
        crew = credits.get('crew', [])
        cast = credits.get('cast', [])

        directors = [c['name'] for c in crew if c.get('job') == 'Director']
        writers = [c['name'] for c in crew if c.get('job') in ('Writer', 'Screenplay')]
        producers = [c['name'] for c in crew if c.get('job') == 'Producer']

        info['directors'] = directors[:3]
        info['writers'] = writers[:4]
        info['producers'] = producers[:3]
        info['cast'] = [c['name'] for c in cast[:5]]

    # Studio from production companies
    companies = details.get('production_companies', [])
    if companies:
        info['studio'] = companies[0].get('name', '')

    return info


def build_film_card_html(info, poster_file):
    """Build the film card HTML from movie info."""
    title_escaped = info['title'].replace("'", "&#x27;").replace('"', '&quot;')
    year = info.get('year', '')

    parts = []

    # Poster
    if poster_file:
        parts.append(f'        <div class="film-card-poster">')
        parts.append(f'          <img loading="lazy" src="/images/{poster_file}" alt="{title_escaped} poster" style="width:100%;display:block;">')
        parts.append(f'        </div>')
    else:
        parts.append(f'        <div class="film-card-poster">')
        parts.append(f'          <div class="film-card-poster-placeholder"><img src="/favicon.svg" alt="" aria-hidden="true"></div>')
        parts.append(f'        </div>')

    parts.append(f'        <div class="film-card-body">')
    parts.append(f'          <h2 class="film-card-title"><em>{title_escaped}</em> ({year})</h2>')
    parts.append(f'          <dl class="film-credits">')

    # Credits
    if info.get('directors'):
        label = 'Director' if len(info['directors']) == 1 else 'Directors'
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">{label}</dt>')
        parts.append(f'              <dd class="credit-value">{", ".join(info["directors"])}</dd>')
        parts.append(f'            </div>')

    if info.get('writers'):
        label = 'Writer' if len(info['writers']) == 1 else 'Writers'
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">{label}</dt>')
        parts.append(f'              <dd class="credit-value">{", ".join(info["writers"])}</dd>')
        parts.append(f'            </div>')

    if info.get('cast'):
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">Starring</dt>')
        parts.append(f'              <dd class="credit-value">{", ".join(info["cast"])}</dd>')
        parts.append(f'            </div>')

    if info.get('studio'):
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">Studio</dt>')
        parts.append(f'              <dd class="credit-value">{info["studio"]}</dd>')
        parts.append(f'            </div>')

    if info.get('runtime'):
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">Runtime</dt>')
        parts.append(f'              <dd class="credit-value">{info["runtime"]} min</dd>')
        parts.append(f'            </div>')

    if info.get('genres'):
        parts.append(f'            <div class="film-credit">')
        parts.append(f'              <dt class="credit-label">Genre</dt>')
        parts.append(f'              <dd class="credit-value">{", ".join(info["genres"])}</dd>')
        parts.append(f'            </div>')

    parts.append(f'          </dl>')
    parts.append(f'')

    # Links
    imdb_id = info.get('imdb_id', '')
    tmdb_id = info.get('tmdb_id', '')
    if imdb_id or tmdb_id:
        parts.append(f'          <div class="film-card-links">')
        if imdb_id:
            parts.append(f'            <a href="https://www.imdb.com/title/{imdb_id}/" class="film-link" rel="noopener" target="_blank">IMDB (Full Credits)</a>')
        if tmdb_id:
            parts.append(f'            <a href="https://www.themoviedb.org/movie/{tmdb_id}" class="film-link" rel="noopener" target="_blank">TMDB</a>')
        parts.append(f'          </div>')

    parts.append(f'        </div>')

    return '\n'.join(parts)


def update_html_file(filepath, info, poster_file, dry_run=False):
    """Update the film card in an HTML file."""
    with open(filepath) as f:
        content = f.read()

    # Find the film-card div and replace its contents
    pattern = re.compile(
        r'(<div class="film-card">\s*)'
        r'<div class="film-card-poster">.*?</div>\s*'
        r'<div class="film-card-body">.*?</div>\s*'
        r'(</div>)',
        re.DOTALL
    )

    m = pattern.search(content)
    if not m:
        return False

    new_card = build_film_card_html(info, poster_file)
    new_content = content[:m.start(1)] + '      <div class="film-card">\n' + new_card + '\n      ' + m.group(2) + content[m.end():]

    # Also update og:image if it's the default
    if poster_file:
        new_content = new_content.replace(
            'content="https://nitrateonline.com/images/og-default.png"',
            f'content="https://nitrateonline.com/images/{poster_file}"',
            1
        )
        new_content = new_content.replace(
            '"image": "https://nitrateonline.com/images/og-default.png"',
            f'"image": "https://nitrateonline.com/images/{poster_file}"',
            1
        )

    if new_content != content:
        if not dry_run:
            with open(filepath, 'w') as f:
                f.write(new_content)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Update film cards with TMDB data')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--file', type=str)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    api_key = get_api_key()

    # Load manifest
    if not os.path.exists(MANIFEST_PATH):
        print("ERROR: No poster manifest found. Run fetch_posters.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    # Find files to process
    if args.file:
        files = [os.path.join(ROOT, args.file)]
    else:
        files = []
        for year_dir in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]'))):
            for f in sorted(glob.glob(os.path.join(year_dir, '[rf]*.html'))):
                if not f.endswith('index.html'):
                    files.append(f)

    # Filter to files that need updating (have placeholder or empty credits)
    to_update = []
    for filepath in files:
        with open(filepath) as f:
            content = f.read()

        has_placeholder = 'film-card-poster-placeholder' in content
        has_empty_credits = bool(re.search(r'<dl class="film-credits">\s*</dl>', content))

        if has_placeholder or has_empty_credits:
            code = os.path.basename(filepath).replace('.html', '')
            entry = manifest.get(code, {})
            tmdb_id = entry.get('tmdb_id')
            poster_file = entry.get('file')

            if tmdb_id:
                to_update.append((filepath, code, tmdb_id, poster_file))

    print(f"Found {len(to_update)} files to update with TMDB data")

    if args.limit > 0:
        to_update = to_update[:args.limit]

    updated = 0
    errors = 0

    for i, (filepath, code, tmdb_id, poster_file) in enumerate(to_update, 1):
        relpath = os.path.relpath(filepath, ROOT)
        print(f"[{i}/{len(to_update)}] {relpath}...", end=' ', flush=True)

        try:
            info = fetch_movie_details(tmdb_id, api_key)
            if not info:
                print("TMDB ERROR")
                errors += 1
                continue

            if update_html_file(filepath, info, poster_file, dry_run=args.dry_run):
                print(f"{'WOULD UPDATE' if args.dry_run else 'UPDATED'} ({info['title']})")
                updated += 1
            else:
                print("NO CHANGE")

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

    action = 'Would update' if args.dry_run else 'Updated'
    print(f"\n{action}: {updated} files")
    if errors:
        print(f"Errors: {errors}")


if __name__ == '__main__':
    main()
