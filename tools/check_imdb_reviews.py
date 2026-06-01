#!/usr/bin/env python3
"""
Check which Nitrate Online reviews are missing from IMDB's External Reviews.

For each review with an IMDB ID, fetches the IMDB external reviews page
and checks if nitrateonline.com is listed.

Usage:
    python3 tools/check_imdb_reviews.py --dry-run     # preview count
    python3 tools/check_imdb_reviews.py --limit 10    # test with 10
    python3 tools/check_imdb_reviews.py               # check all
    python3 tools/check_imdb_reviews.py --output imdb_missing.csv

Outputs:
    imdb_missing.csv — reviews not yet listed on IMDB
    imdb_already.csv — reviews already listed on IMDB
"""

import argparse
import csv
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

# Be polite to IMDB
REQUEST_DELAY = 3.0  # 3 seconds between requests
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


def get_reviews_with_imdb():
    """Get all reviews that have IMDB IDs."""
    reviews = []
    manifest = {}
    manifest_path = os.path.join(TMDB_DIR, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)

    for f in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', 'r*.html'))):
        code = os.path.basename(f).replace('.html', '')
        year = os.path.basename(os.path.dirname(f))

        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        # Get IMDB ID from the page
        m = re.search(r'imdb\.com/title/(tt\d+)', content)
        if not m:
            # Try manifest
            entry = manifest.get(code, {})
            imdb_id = entry.get('imdb_id')
            if not imdb_id:
                continue
        else:
            imdb_id = m.group(1)

        m = re.search(r'og:title.*?content="([^"]*)"', content)
        title = m.group(1) if m else code

        reviews.append({
            'code': code,
            'year': year,
            'imdb_id': imdb_id,
            'title': title,
            'url': f'https://nitrateonline.com/{year}/{code}.html',
        })

    return reviews


def check_imdb_external_reviews(imdb_id):
    """Check if nitrateonline.com is listed in IMDB's external reviews."""
    url = f'https://www.imdb.com/title/{imdb_id}/externalreviews/'
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'text/html',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')

        # Check if nitrateonline.com appears anywhere on the page
        if 'nitrateonline' in html.lower() or 'nitrate online' in html.lower():
            return 'listed'
        return 'missing'

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 'no_page'
        if e.code == 403:
            return 'blocked'
        if e.code == 429:
            time.sleep(10)
            return check_imdb_external_reviews(imdb_id)
        return f'error_{e.code}'
    except urllib.error.URLError as e:
        return f'error_{e}'
    except Exception as e:
        return f'error_{e}'


def main():
    parser = argparse.ArgumentParser(
        description='Check which reviews are missing from IMDB')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--output', type=str, default='imdb_missing.csv')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    reviews = get_reviews_with_imdb()
    print(f"Found {len(reviews)} reviews with IMDB IDs")

    if args.dry_run:
        print(f"[DRY RUN] Would check {len(reviews)} IMDB external review pages")
        return

    if args.limit > 0:
        reviews = reviews[:args.limit]
        print(f"Limited to {len(reviews)}")

    missing = []
    listed = []
    errors = []

    for i, rev in enumerate(reviews, 1):
        print(f"[{i}/{len(reviews)}] {rev['code']}: {rev['title']} ({rev['imdb_id']})...",
              end=' ', flush=True)

        status = check_imdb_external_reviews(rev['imdb_id'])
        time.sleep(REQUEST_DELAY)

        if status == 'missing':
            print("NOT ON IMDB")
            missing.append(rev)
        elif status == 'listed':
            print("already listed")
            listed.append(rev)
        else:
            print(f"({status})")
            errors.append((rev, status))

        # Save progress periodically
        if i % 50 == 0:
            _save_csv(os.path.join(ROOT, args.output), missing)
            print(f"  ... progress: {len(missing)} missing, {len(listed)} listed, {len(errors)} errors")

    # Save final results
    missing_path = os.path.join(ROOT, args.output)
    _save_csv(missing_path, missing)

    already_path = os.path.join(ROOT, args.output.replace('missing', 'already'))
    _save_csv(already_path, listed)

    print(f"\nDone!")
    print(f"  Missing from IMDB: {len(missing)}")
    print(f"  Already listed:    {len(listed)}")
    print(f"  Errors:            {len(errors)}")
    print(f"\nOutput:")
    print(f"  {missing_path}")
    print(f"  {already_path}")

    if errors:
        print(f"\nErrors:")
        for rev, status in errors[:10]:
            print(f"  {rev['imdb_id']}: {status}")


def _save_csv(path, reviews):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['imdb_id', 'title', 'review_url', 'label'])
        for rev in reviews:
            w.writerow([rev['imdb_id'], rev['title'], rev['url'], 'Nitrate Online'])


if __name__ == '__main__':
    main()
