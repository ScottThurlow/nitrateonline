#!/usr/bin/env python3
"""
Fetch movie posters from The Movie Database (TMDB) for Nitrate Online reviews.

Usage:
    # Dry run — show what would be fetched, download nothing
    python3 tools/fetch_posters.py --dry-run

    # Fetch only missing posters (reviews that have no -1.jpg image)
    python3 tools/fetch_posters.py

    # Re-fetch all posters (overwrite existing)
    python3 tools/fetch_posters.py --all

    # Fetch for a single file
    python3 tools/fetch_posters.py --file 1997/rgattaca.html

    # Verbose output
    python3 tools/fetch_posters.py -v

    # Limit to N downloads (useful for testing)
    python3 tools/fetch_posters.py --limit 10

Requires:
    - TMDB API key set as environment variable: TMDB_API_KEY
    - Or create a .tmdb_api_key file in the project root
    - Get a free API key at https://www.themoviedb.org/settings/api

Outputs:
    - Poster images saved to /images/{reviewcode}-poster.jpg
    - A JSON manifest at /tools/poster_manifest.json tracking all matches
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
IMAGES_DIR = os.path.join(ROOT, 'images')
MANIFEST_PATH = os.path.join(ROOT, 'tools', 'poster_manifest.json')

# TMDB API configuration
TMDB_API_BASE = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'
POSTER_SIZE = 'w500'  # w92, w154, w185, w342, w500, w780, original

# Rate limiting: TMDB allows ~40 requests per 10 seconds
REQUEST_DELAY = 0.25  # seconds between API calls


def get_api_key():
    """Get TMDB API key from environment or file."""
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
    print("Set the TMDB_API_KEY environment variable or create a .tmdb_api_key file.")
    print("Get a free API key at https://www.themoviedb.org/settings/api")
    sys.exit(1)


def tmdb_get(endpoint, params, api_key):
    """Make a GET request to the TMDB API."""
    params['api_key'] = api_key
    url = f'{TMDB_API_BASE}{endpoint}?{urllib.parse.urlencode(params)}'

    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited — wait and retry
            retry_after = int(e.headers.get('Retry-After', '5'))
            print(f"  Rate limited, waiting {retry_after}s...")
            time.sleep(retry_after)
            return tmdb_get(endpoint, params, api_key)
        raise
    except urllib.error.URLError as e:
        print(f"  Network error: {e}")
        return None


def download_image(url, dest_path):
    """Download an image from a URL to a local path."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'NitrateOnline-PosterFetcher/1.0'
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(dest_path, 'wb') as f:
                f.write(resp.read())
        return True
    except (urllib.error.URLError, OSError) as e:
        print(f"  Download failed: {e}")
        return False


def find_review_files(single_file=None):
    """Find all review HTML files."""
    if single_file:
        path = os.path.join(ROOT, single_file)
        if os.path.exists(path):
            return [path]
        print(f"ERROR: File not found: {single_file}")
        sys.exit(1)

    files = []
    for year_dir in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]'))):
        for f in sorted(glob.glob(os.path.join(year_dir, 'r*.html'))):
            files.append(f)
    return files


def extract_metadata(filepath):
    """Extract film title, year, and director from a review HTML file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    meta = {}

    # Title from og:title (cleanest source)
    m = re.search(r'<meta property="og:title" content="([^"]*)"', content)
    if m:
        meta['title'] = m.group(1).strip()

    # Year from directory name
    year_match = re.search(r'/(\d{4})/', filepath)
    if year_match:
        meta['year'] = int(year_match.group(1))

    # Also try to get the film's release year from eyebrow (may differ from review year)
    m = re.search(r'class="article-eyebrow"[^>]*>.*?(\d{4})', content, re.DOTALL)
    if m:
        meta['review_year'] = int(m.group(1))

    # Director from article-subtitle
    m = re.search(r'class="article-subtitle"[^>]*>\s*Directed by\s+([^<]+)', content)
    if m:
        meta['director'] = ' '.join(m.group(1).split()).strip()

    # Also try credit-value next to "Director" label
    if 'director' not in meta:
        m = re.search(
            r'class="credit-label"[^>]*>\s*Director\s*</.*?class="credit-value"[^>]*>([^<]+)',
            content, re.DOTALL
        )
        if m:
            meta['director'] = ' '.join(m.group(1).split()).strip()

    # Review code (filename without extension)
    meta['code'] = os.path.basename(filepath).replace('.html', '')

    # Existing poster image path
    meta['existing_image'] = os.path.join(IMAGES_DIR, f"{meta['code']}-1.jpg")
    meta['has_existing_image'] = os.path.exists(meta['existing_image'])

    # Poster output path
    meta['poster_path'] = os.path.join(IMAGES_DIR, f"{meta['code']}-poster.jpg")

    return meta


def clean_title(title):
    """Clean a film title for better TMDB search matching."""
    if not title:
        return ''

    # Remove common suffixes added by the site
    title = re.sub(r'\s*[-–—]\s*Nitrate Online\s*$', '', title, flags=re.I)

    # Remove parenthetical year references
    title = re.sub(r'\s*\(\d{4}\)\s*', ' ', title)

    # Remove "A Film by..." or "Directed by..." suffixes
    title = re.sub(r'\s*[-–—:]\s*(?:A Film|Directed)\s+by.*$', '', title, flags=re.I)

    return title.strip()


def search_tmdb(title, year, director, api_key):
    """
    Search TMDB for a film. Returns the best match or None.

    Strategy:
      1. Search by title + year (most precise)
      2. If no results, search by title only
      3. If multiple results, prefer the one matching the director
    """
    cleaned = clean_title(title)
    if not cleaned:
        return None

    # First try: title + year
    params = {'query': cleaned, 'language': 'en-US', 'include_adult': 'false'}
    if year:
        params['year'] = year
        # Also set primary_release_year for better matching
        params['primary_release_year'] = year

    data = tmdb_get('/search/movie', params, api_key)
    if not data:
        return None

    results = data.get('results', [])

    # Second try: without year constraint if no results
    if not results and year:
        params.pop('year', None)
        params.pop('primary_release_year', None)
        data = tmdb_get('/search/movie', params, api_key)
        if data:
            results = data.get('results', [])
        time.sleep(REQUEST_DELAY)

    if not results:
        return None

    # If only one result, use it
    if len(results) == 1:
        return results[0]

    # Multiple results — try to match by director
    if director:
        for result in results[:5]:  # Check top 5
            tmdb_id = result.get('id')
            if tmdb_id:
                credits = tmdb_get(f'/movie/{tmdb_id}/credits', {}, api_key)
                time.sleep(REQUEST_DELAY)
                if credits:
                    crew = credits.get('crew', [])
                    directors = [
                        c.get('name', '') for c in crew
                        if c.get('job', '').lower() == 'director'
                    ]
                    if any(director.lower() in d.lower() or d.lower() in director.lower()
                           for d in directors):
                        return result

    # Fall back to first result (highest popularity)
    return results[0]


def get_poster_url(movie_data):
    """Get the poster image URL from TMDB movie data."""
    poster_path = movie_data.get('poster_path')
    if not poster_path:
        return None
    return f'{TMDB_IMAGE_BASE}/{POSTER_SIZE}{poster_path}'


def load_manifest():
    """Load the existing poster manifest."""
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    """Save the poster manifest."""
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Fetch movie posters from TMDB')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be fetched without downloading')
    parser.add_argument('--all', action='store_true',
                        help='Re-fetch all posters, including those already downloaded')
    parser.add_argument('--file', type=str,
                        help='Process a single review file (relative path)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limit number of downloads (0 = unlimited)')
    args = parser.parse_args()

    if not args.dry_run:
        api_key = get_api_key()
    else:
        api_key = os.environ.get('TMDB_API_KEY', 'dry-run')

    # Find review files
    files = find_review_files(args.file)
    print(f"Found {len(files)} review files")

    # Load existing manifest
    manifest = load_manifest()

    # Extract metadata from all files
    reviews = []
    for filepath in files:
        meta = extract_metadata(filepath)
        if not meta.get('title'):
            if args.verbose:
                print(f"  Skipping {meta['code']}: no title found")
            continue
        reviews.append(meta)

    print(f"Extracted metadata for {len(reviews)} reviews")

    # Filter to those needing posters
    if not args.all:
        reviews = [
            r for r in reviews
            if not os.path.exists(r['poster_path'])
        ]
        print(f"{len(reviews)} reviews need poster images")

    if args.limit > 0:
        reviews = reviews[:args.limit]
        print(f"Limited to {len(reviews)} downloads")

    if args.dry_run:
        print("\n[DRY RUN] Would search TMDB for these films:\n")
        for r in reviews:
            year = r.get('year', '?')
            director = r.get('director', 'unknown')
            print(f"  {r['code']:30s}  {r['title']} ({year}) dir. {director}")
        print(f"\nTotal: {len(reviews)} films to look up")
        return

    # Process each review
    fetched = 0
    not_found = 0
    no_poster = 0
    errors = 0

    for i, review in enumerate(reviews, 1):
        code = review['code']
        title = review['title']
        year = review.get('year')
        director = review.get('director')

        print(f"[{i}/{len(reviews)}] {code}: {title} ({year or '?'})...", end=' ', flush=True)

        try:
            movie = search_tmdb(title, year, director, api_key)
            time.sleep(REQUEST_DELAY)

            if not movie:
                print("NOT FOUND")
                not_found += 1
                manifest[code] = {
                    'title': title,
                    'year': year,
                    'status': 'not_found'
                }
                continue

            poster_url = get_poster_url(movie)
            if not poster_url:
                print(f"no poster (TMDB id: {movie.get('id')})")
                no_poster += 1
                manifest[code] = {
                    'title': title,
                    'year': year,
                    'tmdb_id': movie.get('id'),
                    'tmdb_title': movie.get('title'),
                    'status': 'no_poster'
                }
                continue

            # Download the poster
            dest = review['poster_path']
            if download_image(poster_url, dest):
                print(f"OK -> {os.path.basename(dest)}")
                fetched += 1
                manifest[code] = {
                    'title': title,
                    'year': year,
                    'tmdb_id': movie.get('id'),
                    'tmdb_title': movie.get('title'),
                    'poster_path': movie.get('poster_path'),
                    'file': os.path.basename(dest),
                    'status': 'fetched'
                }
            else:
                print("DOWNLOAD FAILED")
                errors += 1

        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

        # Save manifest periodically (every 50 files)
        if i % 50 == 0:
            save_manifest(manifest)

    # Final save
    save_manifest(manifest)

    print(f"\nDone!")
    print(f"  Fetched:    {fetched}")
    print(f"  Not found:  {not_found}")
    print(f"  No poster:  {no_poster}")
    print(f"  Errors:     {errors}")
    print(f"  Manifest:   {MANIFEST_PATH}")


if __name__ == '__main__':
    main()
