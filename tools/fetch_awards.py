#!/usr/bin/env python3
"""
Fetch awards data from OMDb for all films that have TMDB metadata.

Reads tmdb_data/manifest.json to get IMDB IDs, then queries OMDb for each
film's awards summary and additional metadata (Rated, Awards, Metascore,
Rotten Tomatoes score).

Outputs:
  tmdb_data/awards/              — per-film JSON: {code}.json
  tmdb_data/manifest_awards.json — merged manifest with awards data

Usage:
    python3 tools/fetch_awards.py --dry-run
    python3 tools/fetch_awards.py --limit 10
    python3 tools/fetch_awards.py
    python3 tools/fetch_awards.py --all     # re-fetch already fetched

Requires:
    OMDb API key: git config --local omdb.apikey YOUR_KEY
    Or OMDB_API_KEY env var.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TMDB_DIR = os.path.join(ROOT, 'tmdb_data')
AWARDS_DIR = os.path.join(TMDB_DIR, 'awards')
MANIFEST_PATH = os.path.join(TMDB_DIR, 'manifest.json')
AWARDS_MANIFEST_PATH = os.path.join(TMDB_DIR, 'manifest_awards.json')

OMDB_API_BASE = 'https://www.omdbapi.com/'
REQUEST_DELAY = 0.1  # 100K/day ≈ ~1.15/sec, 0.1s is safe


def get_omdb_key():
    key = os.environ.get('OMDB_API_KEY', '').strip()
    if key:
        return key
    try:
        result = subprocess.run(
            ['git', 'config', '--local', 'omdb.apikey'],
            capture_output=True, text=True, cwd=ROOT)
        key = result.stdout.strip()
        if key:
            return key
    except Exception:
        pass
    print("ERROR: OMDb API key not found.")
    print("Set it with:  git config --local omdb.apikey YOUR_KEY")
    sys.exit(1)


def omdb_get(imdb_id, api_key):
    params = {'i': imdb_id, 'apikey': api_key, 'plot': 'full'}
    url = f'{OMDB_API_BASE}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if data.get('Response') == 'False':
            return None
        return data
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("\nERROR: OMDb API key is invalid or rate limit exceeded.")
            sys.exit(1)
        raise
    except urllib.error.URLError as e:
        print(f"  network error: {e}")
        return None


def extract_awards_data(omdb):
    """Extract all useful fields from an OMDb response."""
    imdb_id = omdb.get('imdbID', '')

    result = {
        'year': omdb.get('Year', 'N/A'),
        'awards': omdb.get('Awards', 'N/A'),
        'rated': omdb.get('Rated', 'N/A'),
        'released': omdb.get('Released', 'N/A'),
        'runtime': omdb.get('Runtime', 'N/A'),
        'genre': omdb.get('Genre', 'N/A'),
        'director': omdb.get('Director', 'N/A'),
        'writer': omdb.get('Writer', 'N/A'),
        'actors': omdb.get('Actors', 'N/A'),
        'plot': omdb.get('Plot', 'N/A'),
        'language': omdb.get('Language', 'N/A'),
        'country': omdb.get('Country', 'N/A'),
        'metascore': omdb.get('Metascore', 'N/A'),
        'imdb_rating': omdb.get('imdbRating', 'N/A'),
        'imdb_votes': omdb.get('imdbVotes', 'N/A'),
        'box_office': omdb.get('BoxOffice', 'N/A'),
        'dvd': omdb.get('DVD', 'N/A'),
        'ratings': [],
        # Constructed links
        'links': {
            'imdb': f'https://www.imdb.com/title/{imdb_id}/' if imdb_id else None,
            'imdb_fullcredits': f'https://www.imdb.com/title/{imdb_id}/fullcredits' if imdb_id else None,
        },
    }

    # Extract all rating sources (IMDB, Rotten Tomatoes, Metacritic)
    for r in omdb.get('Ratings', []):
        source = r.get('Source', '')
        value = r.get('Value', '')
        entry = {'source': source, 'value': value}

        # Add direct link for Rotten Tomatoes
        if source == 'Rotten Tomatoes':
            # Construct RT search URL from title (RT doesn't expose stable IDs via OMDb)
            rt_slug = omdb.get('Title', '').lower()
            rt_slug = re.sub(r'[^a-z0-9]+', '_', rt_slug).strip('_')
            entry['link'] = f'https://www.rottentomatoes.com/search?search={urllib.parse.quote_plus(omdb.get("Title", ""))}'

        if source == 'Metacritic':
            entry['link'] = f'https://www.metacritic.com/search/{urllib.parse.quote_plus(omdb.get("Title", ""))}/'

        result['ratings'].append(entry)

    return result


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    print("ERROR: No TMDB manifest found. Run fetch_tmdb.py first.")
    sys.exit(1)


def load_awards_manifest():
    if os.path.exists(AWARDS_MANIFEST_PATH):
        with open(AWARDS_MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def save_awards_manifest(manifest):
    with open(AWARDS_MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def save_awards(code, data):
    path = os.path.join(AWARDS_DIR, f'{code}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Fetch awards data from OMDb')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--all', action='store_true',
                        help='Re-fetch already fetched films')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    os.makedirs(AWARDS_DIR, exist_ok=True)

    if not args.dry_run:
        api_key = get_omdb_key()
    else:
        api_key = 'dry-run'

    tmdb_manifest = load_manifest()
    awards_manifest = load_awards_manifest()

    # Build list of films with IMDB IDs
    films = []
    for code, entry in tmdb_manifest.items():
        if entry.get('status') != 'ok':
            continue
        imdb_id = entry.get('imdb_id')
        if not imdb_id:
            # Try to get from per-film metadata
            meta_path = os.path.join(TMDB_DIR, 'metadata', f'{code}.json')
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                imdb_id = meta.get('imdb_id')
        if not imdb_id:
            if args.verbose:
                print(f"  skip {code}: no IMDB ID")
            continue
        films.append({'code': code, 'imdb_id': imdb_id,
                      'title': entry.get('title', ''), 'year': entry.get('year')})

    print(f"Found {len(films)} films with IMDB IDs")

    if not args.all:
        films = [f for f in films
                 if f['code'] not in awards_manifest
                 or awards_manifest[f['code']].get('status') != 'ok']
        print(f"{len(films)} need awards data")

    if args.limit > 0:
        films = films[:args.limit]
        print(f"Limited to {len(films)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch OMDb awards for {len(films)} films")
        for f in films[:20]:
            print(f"  {f['code']:30s}  {f['title']} ({f['year']})  {f['imdb_id']}")
        if len(films) > 20:
            print(f"  ... and {len(films) - 20} more")
        return

    ok = 0
    not_found = 0
    no_awards = 0
    errors = 0

    for i, film in enumerate(films, 1):
        code = film['code']
        imdb_id = film['imdb_id']
        title = film['title']

        print(f"[{i}/{len(films)}] {code}: {title} ({imdb_id})...",
              end=' ', flush=True)

        try:
            omdb = omdb_get(imdb_id, api_key)
            time.sleep(REQUEST_DELAY)

            if not omdb:
                print("NOT FOUND")
                not_found += 1
                awards_manifest[code] = {'imdb_id': imdb_id, 'status': 'not_found'}
                continue

            awards_data = extract_awards_data(omdb)
            save_awards(code, awards_data)

            awards_text = awards_data.get('awards', 'N/A')

            # Add TMDB link from the TMDB manifest
            tmdb_id = tmdb_manifest.get(code, {}).get('tmdb_id')
            links = awards_data.get('links', {})
            if tmdb_id:
                links['tmdb'] = f'https://www.themoviedb.org/movie/{tmdb_id}'
            awards_data['links'] = links

            # Re-save with links included
            save_awards(code, awards_data)

            awards_manifest[code] = {
                'imdb_id': imdb_id,
                'awards': awards_text,
                'rated': awards_data.get('rated', 'N/A'),
                'metascore': awards_data.get('metascore', 'N/A'),
                'ratings': awards_data.get('ratings', []),
                'links': links,
                'status': 'ok',
            }

            if awards_text and awards_text != 'N/A':
                print(f"OK — {awards_text}")
                ok += 1
            else:
                print("OK (no awards listed)")
                no_awards += 1

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        if i % 50 == 0:
            save_awards_manifest(awards_manifest)

    save_awards_manifest(awards_manifest)

    print(f"\nDone!")
    print(f"  With awards: {ok}")
    print(f"  No awards:   {no_awards}")
    print(f"  Not found:   {not_found}")
    print(f"  Errors:      {errors}")
    print(f"\nOutput:")
    print(f"  Awards JSON: {AWARDS_DIR}/")
    print(f"  Manifest:    {AWARDS_MANIFEST_PATH}")


if __name__ == '__main__':
    main()
