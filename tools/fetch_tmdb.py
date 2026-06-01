#!/usr/bin/env python3
"""
Fetch movie posters and metadata from TMDB for all Nitrate Online reviews.

Outputs everything into a /tmdb_data/ folder:
  tmdb_data/
    manifest.json          — master index: review code → TMDB match + all metadata
    posters/               — poster JPEGs: {code}-poster.jpg
    metadata/              — per-film JSON: {code}.json (full TMDB detail + credits)

Each metadata JSON contains:
  - tmdb_id, title, original_title, release_date, runtime
  - overview, tagline, genres, spoken_languages
  - production_companies (studio)
  - director, writers, producers
  - cast (top 10 billed actors)
  - poster_path, backdrop_path
  - awards (sourced from TMDB keywords/collections where available)

Usage:
    python3 tools/fetch_tmdb.py --dry-run            # preview, no API calls
    python3 tools/fetch_tmdb.py --limit 10            # test with 10 films
    python3 tools/fetch_tmdb.py                       # fetch all missing
    python3 tools/fetch_tmdb.py --all                 # re-fetch everything
    python3 tools/fetch_tmdb.py --file 1997/rgattaca.html  # single file

Requires:
    TMDB_API_KEY env var or .tmdb_api_key file in project root.
    Free key: https://www.themoviedb.org/settings/api
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TMDB_DIR = os.path.join(ROOT, 'tmdb_data')
POSTERS_DIR = os.path.join(TMDB_DIR, 'posters')
METADATA_DIR = os.path.join(TMDB_DIR, 'metadata')
MANIFEST_PATH = os.path.join(TMDB_DIR, 'manifest.json')

TMDB_API_BASE = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'
POSTER_SIZE = 'w500'
REQUEST_DELAY = 0.25


# ── API helpers ──────────────────────────────────────────────

def get_api_key():
    # 1) Environment variable
    key = os.environ.get('TMDB_API_KEY', '').strip()
    if key:
        return key

    # 2) Git config (stored in .git/config, never pushed)
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'config', '--local', 'tmdb.apikey'],
            capture_output=True, text=True, cwd=ROOT)
        key = result.stdout.strip()
        if key:
            return key
    except Exception:
        pass

    # 3) Dotfile fallback
    keyfile = os.path.join(ROOT, '.tmdb_api_key')
    if os.path.exists(keyfile):
        with open(keyfile) as f:
            key = f.read().strip()
        if key:
            return key

    print("ERROR: TMDB API key not found.")
    print("Set it with:  git config --local tmdb.apikey YOUR_KEY")
    print("Or set TMDB_API_KEY env var, or create .tmdb_api_key file.")
    print("Free key: https://www.themoviedb.org/settings/api")
    sys.exit(1)


def tmdb_get(endpoint, params, api_key):
    params = dict(params)
    params['api_key'] = api_key
    url = f'{TMDB_API_BASE}{endpoint}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            retry = int(e.headers.get('Retry-After', '5'))
            print(f"  rate-limited, waiting {retry}s...", flush=True)
            time.sleep(retry)
            return tmdb_get(endpoint, params, api_key)
        if e.code == 404:
            return None
        raise
    except urllib.error.URLError as e:
        print(f"  network error: {e}")
        return None


def download_image(url, dest):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'NitrateOnline-Fetcher/1.0'
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(dest, 'wb') as f:
                f.write(resp.read())
        return True
    except (urllib.error.URLError, OSError) as e:
        print(f"  download failed: {e}")
        return False


# ── HTML metadata extraction ─────────────────────────────────

def find_review_files(single_file=None):
    if single_file:
        path = os.path.join(ROOT, single_file)
        if os.path.exists(path):
            return [path]
        print(f"ERROR: not found: {single_file}")
        sys.exit(1)
    files = []
    for year_dir in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]'))):
        files.extend(sorted(glob.glob(os.path.join(year_dir, 'r*.html'))))
    return files


def extract_html_metadata(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    meta = {}
    m = re.search(r'<meta property="og:title" content="([^"]*)"', content)
    if m:
        meta['title'] = m.group(1).strip()
    m = re.search(r'/(\d{4})/', filepath)
    if m:
        meta['year'] = int(m.group(1))
    m = re.search(r'class="article-subtitle"[^>]*>\s*Directed by\s+([^<]+)', content)
    if m:
        meta['director'] = ' '.join(m.group(1).split()).strip()
    if 'director' not in meta:
        m = re.search(
            r'class="credit-label"[^>]*>\s*Director\s*</.*?class="credit-value"[^>]*>([^<]+)',
            content, re.DOTALL)
        if m:
            meta['director'] = ' '.join(m.group(1).split()).strip()
    meta['code'] = os.path.basename(filepath).replace('.html', '')
    meta['filepath'] = filepath
    return meta


def clean_title(title):
    if not title:
        return ''
    title = re.sub(r'\s*[-–—]\s*Nitrate Online\s*$', '', title, flags=re.I)
    title = re.sub(r'\s*\(\d{4}\)\s*', ' ', title)
    title = re.sub(r'\s*[-–—:]\s*(?:A Film|Directed)\s+by.*$', '', title, flags=re.I)
    return title.strip()


# ── TMDB search & detail fetching ────────────────────────────

def search_tmdb(title, year, director, api_key):
    cleaned = clean_title(title)
    if not cleaned:
        return None

    params = {'query': cleaned, 'language': 'en-US', 'include_adult': 'false'}
    if year:
        params['year'] = year
        params['primary_release_year'] = year

    data = tmdb_get('/search/movie', params, api_key)
    if not data:
        return None
    results = data.get('results', [])

    # Retry without year if nothing found
    if not results and year:
        params.pop('year', None)
        params.pop('primary_release_year', None)
        data = tmdb_get('/search/movie', params, api_key)
        time.sleep(REQUEST_DELAY)
        if data:
            results = data.get('results', [])

    if not results:
        return None

    # Filter out documentaries about the film (common false match)
    non_doc = [r for r in results if 99 not in r.get('genre_ids', [])]
    if non_doc:
        results = non_doc

    if len(results) == 1:
        return results[0]

    # Disambiguate by director if we have one
    if director:
        for result in results[:5]:
            tmdb_id = result.get('id')
            if tmdb_id:
                credits = tmdb_get(f'/movie/{tmdb_id}/credits', {}, api_key)
                time.sleep(REQUEST_DELAY)
                if credits:
                    dirs = [c['name'] for c in credits.get('crew', [])
                            if c.get('job', '').lower() == 'director']
                    if any(director.lower() in d.lower() or d.lower() in director.lower()
                           for d in dirs):
                        return result

    # Fall back to most popular non-documentary result
    results.sort(key=lambda r: r.get('popularity', 0), reverse=True)
    return results[0]


def fetch_full_metadata(tmdb_id, api_key):
    """Fetch movie details + credits + release info in as few calls as possible."""
    # Use append_to_response to batch detail + credits
    detail = tmdb_get(f'/movie/{tmdb_id}', {
        'language': 'en-US',
        'append_to_response': 'credits,release_dates'
    }, api_key)
    if not detail:
        return None

    # Extract crew by role
    credits = detail.get('credits', {})
    crew = credits.get('crew', [])
    cast = credits.get('cast', [])

    directors = [c['name'] for c in crew if c.get('job') == 'Director']
    writers = []
    for c in crew:
        if c.get('department') == 'Writing':
            job = c.get('job', '')
            writers.append({'name': c['name'], 'job': job})
    producers = [{'name': c['name'], 'job': c.get('job', 'Producer')}
                 for c in crew if c.get('job') in
                 ('Producer', 'Executive Producer')]

    # Top-billed cast (up to 10)
    top_cast = []
    for c in cast[:10]:
        top_cast.append({
            'name': c.get('name', ''),
            'character': c.get('character', ''),
            'order': c.get('order', 99),
        })

    # Studios / production companies
    studios = [{'name': co['name'], 'country': co.get('origin_country', '')}
               for co in detail.get('production_companies', [])]

    # Awards: TMDB doesn't have a dedicated awards endpoint, but we can
    # extract US MPAA rating from release_dates and note certifications
    certifications = []
    for entry in detail.get('release_dates', {}).get('results', []):
        country = entry.get('iso_3166_1', '')
        for rd in entry.get('release_dates', []):
            cert = rd.get('certification', '').strip()
            if cert:
                certifications.append({'country': country, 'rating': cert})
                break

    result = {
        'tmdb_id': tmdb_id,
        'title': detail.get('title', ''),
        'original_title': detail.get('original_title', ''),
        'release_date': detail.get('release_date', ''),
        'runtime': detail.get('runtime'),
        'tagline': detail.get('tagline', ''),
        'overview': detail.get('overview', ''),
        'genres': [g['name'] for g in detail.get('genres', [])],
        'spoken_languages': [l.get('english_name', l.get('name', ''))
                             for l in detail.get('spoken_languages', [])],
        'production_companies': studios,
        'director': directors,
        'writers': writers,
        'producers': producers,
        'cast': top_cast,
        'poster_path': detail.get('poster_path'),
        'backdrop_path': detail.get('backdrop_path'),
        'budget': detail.get('budget'),
        'revenue': detail.get('revenue'),
        'vote_average': detail.get('vote_average'),
        'vote_count': detail.get('vote_count'),
        'imdb_id': detail.get('imdb_id'),
        'certifications': certifications,
        'status': detail.get('status', ''),
    }
    return result


# ── Manifest / persistence ───────────────────────────────────

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=False)


def save_metadata(code, data):
    path = os.path.join(METADATA_DIR, f'{code}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Fetch movie posters & metadata from TMDB')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without API calls')
    parser.add_argument('--all', action='store_true',
                        help='Re-fetch everything (overwrite existing)')
    parser.add_argument('--file', type=str,
                        help='Process a single review file')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit to N films (for testing)')
    args = parser.parse_args()

    # Ensure output directories exist
    os.makedirs(POSTERS_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)

    if not args.dry_run:
        api_key = get_api_key()
    else:
        api_key = 'dry-run'

    files = find_review_files(args.file)
    print(f"Found {len(files)} review files")

    reviews = []
    for fp in files:
        meta = extract_html_metadata(fp)
        if not meta.get('title'):
            if args.verbose:
                print(f"  skip (no title): {meta['code']}")
            continue
        reviews.append(meta)
    print(f"Extracted metadata for {len(reviews)} reviews")

    manifest = load_manifest()

    # Filter to those not yet fetched
    if not args.all:
        reviews = [
            r for r in reviews
            if r['code'] not in manifest or manifest[r['code']].get('status') != 'ok'
        ]
        print(f"{len(reviews)} reviews need TMDB data")

    if args.limit > 0:
        reviews = reviews[:args.limit]
        print(f"Limited to {len(reviews)}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would fetch TMDB data for {len(reviews)} films:\n")
        for r in reviews:
            yr = r.get('year', '?')
            d = r.get('director', 'unknown')
            print(f"  {r['code']:30s}  {r['title']} ({yr}) dir. {d}")
        return

    # Process
    ok = 0
    not_found = 0
    errors = 0

    for i, review in enumerate(reviews, 1):
        code = review['code']
        title = review['title']
        year = review.get('year')
        director = review.get('director')

        print(f"[{i}/{len(reviews)}] {code}: {title} ({year or '?'})...",
              end=' ', flush=True)

        try:
            # 1) Search
            movie = search_tmdb(title, year, director, api_key)
            time.sleep(REQUEST_DELAY)

            if not movie:
                print("NOT FOUND")
                not_found += 1
                manifest[code] = {
                    'title': title, 'year': year,
                    'status': 'not_found',
                }
                continue

            tmdb_id = movie['id']

            # 2) Fetch full details + credits (single batched call)
            full = fetch_full_metadata(tmdb_id, api_key)
            time.sleep(REQUEST_DELAY)

            if not full:
                print(f"detail fetch failed (id={tmdb_id})")
                errors += 1
                continue

            # 3) Save per-film metadata JSON
            save_metadata(code, full)

            # 4) Download poster
            poster_file = None
            if full.get('poster_path'):
                poster_url = f"{TMDB_IMAGE_BASE}/{POSTER_SIZE}{full['poster_path']}"
                poster_dest = os.path.join(POSTERS_DIR, f'{code}-poster.jpg')
                if download_image(poster_url, poster_dest):
                    poster_file = f'{code}-poster.jpg'

            # 5) Update manifest with summary
            manifest[code] = {
                'title': title,
                'year': year,
                'tmdb_id': tmdb_id,
                'tmdb_title': full.get('title', ''),
                'release_date': full.get('release_date', ''),
                'runtime': full.get('runtime'),
                'director': full.get('director', []),
                'writers': [w['name'] for w in full.get('writers', [])],
                'producers': [p['name'] for p in full.get('producers', [])],
                'cast': [c['name'] for c in full.get('cast', [])[:5]],
                'studios': [s['name'] for s in full.get('production_companies', [])],
                'genres': full.get('genres', []),
                'imdb_id': full.get('imdb_id'),
                'poster_file': poster_file,
                'status': 'ok',
            }

            status = "OK"
            if poster_file:
                status += f" + {poster_file}"
            print(status)
            ok += 1

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        if i % 25 == 0:
            save_manifest(manifest)

    save_manifest(manifest)

    print(f"\nDone!")
    print(f"  OK:         {ok}")
    print(f"  Not found:  {not_found}")
    print(f"  Errors:     {errors}")
    print(f"\nOutput:")
    print(f"  Manifest:   {MANIFEST_PATH}")
    print(f"  Metadata:   {METADATA_DIR}/")
    print(f"  Posters:    {POSTERS_DIR}/")


if __name__ == '__main__':
    main()
