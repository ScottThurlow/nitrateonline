#!/usr/bin/env python3
"""
Consolidate duplicate review files across year directories.

Identifies true duplicates (same review content in multiple years),
determines the canonical year (film release year or earliest available),
deletes non-canonical copies, adds .htaccess redirects, and updates
canonical/og URLs on the kept pages.

Usage:
    python3 tools/consolidate_dupes.py --dry-run    # preview
    python3 tools/consolidate_dupes.py              # execute
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TMDB_DIR = os.path.join(ROOT, 'tmdb_data')
HTACCESS = os.path.join(ROOT, '.htaccess')


def load_manifest():
    path = os.path.join(TMDB_DIR, 'manifest.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def get_release_year(code, manifest):
    """Get film release year from TMDB data."""
    entry = manifest.get(code, {})
    rd = entry.get('release_date', '')
    if rd and rd[:4].isdigit():
        return rd[:4]
    meta_path = os.path.join(TMDB_DIR, 'metadata', f'{code}.json')
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        rd = meta.get('release_date', '')
        if rd and rd[:4].isdigit():
            return rd[:4]
    return None


def extract_body_fingerprint(filepath):
    """Extract a content fingerprint from the article body."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    m = re.search(r'class="article-body"[^>]*>(.*?)</article>', content, re.DOTALL)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1))
        return ' '.join(text.split()[:40])
    return ''


def find_duplicates():
    """Find all review codes that appear in multiple year directories."""
    reviews = defaultdict(list)
    for f in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', 'r*.html'))):
        code = os.path.basename(f).replace('.html', '')
        year = os.path.basename(os.path.dirname(f))
        reviews[code].append({'file': f, 'year': year})
    return {k: v for k, v in reviews.items() if len(v) > 1}


def identify_true_duplicates(dupes):
    """Filter to only true duplicates (same content, same review)."""
    true_dupes = {}
    for code, entries in dupes.items():
        fingerprints = []
        for e in entries:
            fp = extract_body_fingerprint(e['file'])
            fingerprints.append(fp[:100])
            e['fingerprint'] = fp

        # Same content if first 100 chars of body match
        if len(set(fingerprints)) == 1:
            true_dupes[code] = entries
    return true_dupes


def determine_canonical(code, entries, manifest):
    """Determine which year directory should be canonical."""
    years = [e['year'] for e in entries]
    release_year = get_release_year(code, manifest)

    # If release year is one of the available years, use it
    if release_year and release_year in years:
        return release_year

    # If release year predates all copies (e.g., 1995 film in 1996+), use earliest
    if release_year and all(int(release_year) < int(y) for y in years):
        return min(years)

    # If release year is after all copies (wrong TMDB match), use earliest
    if release_year and all(int(release_year) > int(y) for y in years):
        return min(years)

    # Default: earliest year
    return min(years)


def build_consolidation_map(true_dupes, manifest):
    """Build the full map of what to keep and what to remove."""
    result = {}
    for code, entries in sorted(true_dupes.items()):
        years = [e['year'] for e in entries]
        keep_year = determine_canonical(code, entries, manifest)
        remove_years = [y for y in years if y != keep_year]

        # Get title
        with open(entries[0]['file'], 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        m = re.search(r'og:title.*?content="([^"]*)"', content)
        title = m.group(1) if m else code

        release_year = get_release_year(code, manifest)

        result[code] = {
            'title': title,
            'release_year': release_year,
            'keep_year': keep_year,
            'keep_file': f'{keep_year}/{code}.html',
            'remove_years': remove_years,
            'remove_files': [f'{y}/{code}.html' for y in remove_years],
        }
    return result


def add_redirects(consolidation_map, dry_run=False):
    """Add 301 redirects for removed files and fix wrong existing redirects."""
    with open(HTACCESS, 'r') as f:
        htaccess = f.read()

    new_redirects = []
    fixed_redirects = 0

    for code, info in sorted(consolidation_map.items()):
        keep = info['keep_file']

        for rm_file in info['remove_files']:
            redirect_line = f'Redirect 301 /{rm_file} /{keep}'

            # Check if redirect already exists
            if f'/{rm_file}' in htaccess:
                # Fix existing redirect if it points to wrong place
                old_pattern = rf'(Redirect\s+301\s+/{re.escape(rm_file)}\s+)\S+'
                m = re.search(old_pattern, htaccess)
                if m and f'/{keep}' not in m.group(0):
                    htaccess = re.sub(old_pattern, f'Redirect 301 /{rm_file} /{keep}', htaccess)
                    fixed_redirects += 1
            else:
                new_redirects.append(redirect_line)

        # Also fix root-level redirects (e.g., /rboogie.html -> /1998/rboogie.html)
        root_pattern = rf'(Redirect\s+301\s+/{re.escape(code)}\.html\s+)\S+'
        m = re.search(root_pattern, htaccess)
        if m and f'/{keep}' not in m.group(0):
            htaccess = re.sub(root_pattern, f'Redirect 301 /{code}.html /{keep}', htaccess)
            fixed_redirects += 1

    # Append new redirects before the last line
    if new_redirects:
        # Add after the existing redirect block
        redirect_block = '\n# Duplicate review consolidation redirects\n'
        redirect_block += '\n'.join(sorted(new_redirects))
        redirect_block += '\n'

        # Insert before the RewriteEngine section or at end
        if 'RewriteEngine' in htaccess:
            htaccess = htaccess.replace('RewriteEngine', redirect_block + '\nRewriteEngine', 1)
        else:
            htaccess += redirect_block

    if not dry_run:
        with open(HTACCESS, 'w') as f:
            f.write(htaccess)

    return len(new_redirects), fixed_redirects


def delete_duplicates(consolidation_map, dry_run=False):
    """Delete non-canonical duplicate files."""
    deleted = 0
    for code, info in consolidation_map.items():
        for rm_file in info['remove_files']:
            full_path = os.path.join(ROOT, rm_file)
            if os.path.exists(full_path):
                if not dry_run:
                    os.remove(full_path)
                deleted += 1
    return deleted


def update_canonical_urls(consolidation_map, dry_run=False):
    """Update canonical and og:url on kept pages to use correct year."""
    updated = 0
    for code, info in consolidation_map.items():
        keep_file = os.path.join(ROOT, info['keep_file'])
        if not os.path.exists(keep_file):
            continue

        with open(keep_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original = content
        keep_year = info['keep_year']
        canonical_url = f'https://nitrateonline.com/{keep_year}/{code}.html'

        # Fix canonical
        content = re.sub(
            r'<link rel="canonical" href="[^"]*">',
            f'<link rel="canonical" href="{canonical_url}">',
            content)

        # Fix og:url
        content = re.sub(
            r'<meta property="og:url" content="[^"]*">',
            f'<meta property="og:url" content="{canonical_url}">',
            content)

        # Fix JSON-LD url
        content = re.sub(
            r'"url":\s*"https://nitrateonline\.com/\d{4}/' + re.escape(code) + r'\.html"',
            f'"url": "{canonical_url}"',
            content)

        if content != original:
            if not dry_run:
                with open(keep_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            updated += 1
    return updated


def fix_release_years(consolidation_map, manifest, dry_run=False):
    """Update film card title year to show actual release year."""
    fixed = 0
    for code, info in consolidation_map.items():
        release_year = info.get('release_year')
        if not release_year:
            continue

        keep_file = os.path.join(ROOT, info['keep_file'])
        if not os.path.exists(keep_file):
            continue

        with open(keep_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original = content

        # Update film-card-title year display
        # Pattern: <em>Title</em> (YYYY)
        content = re.sub(
            r'(<h2 class="film-card-title"><em>[^<]*</em>\s*)\(\d{4}\)',
            rf'\g<1>({release_year})',
            content)

        if content != original:
            if not dry_run:
                with open(keep_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            fixed += 1
    return fixed


def check_internal_links(consolidation_map):
    """Check for internal links pointing to removed files."""
    removed_paths = set()
    for info in consolidation_map.values():
        for rm_file in info['remove_files']:
            removed_paths.add(f'/{rm_file}')

    broken = []
    for f in glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', '*.html')):
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
        for rm_path in removed_paths:
            if f'href="{rm_path}"' in content:
                broken.append((os.path.relpath(f, ROOT), rm_path))
    return broken


def fix_internal_links(consolidation_map, dry_run=False):
    """Fix internal links that point to removed duplicate files."""
    # Build redirect map: /1998/rboogie.html -> /1997/rboogie.html
    redirect_map = {}
    for code, info in consolidation_map.items():
        keep_path = f'/{info["keep_file"]}'
        for rm_file in info['remove_files']:
            redirect_map[f'/{rm_file}'] = keep_path

    fixed_files = 0
    fixed_links = 0
    for f in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', '*.html'))):
        with open(f, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()

        original = content
        for old_path, new_path in redirect_map.items():
            content = content.replace(f'href="{old_path}"', f'href="{new_path}"')

        if content != original:
            link_count = sum(1 for old in redirect_map if f'href="{old}"' in original)
            fixed_links += link_count
            fixed_files += 1
            if not dry_run:
                with open(f, 'w', encoding='utf-8') as fh:
                    fh.write(content)

    return fixed_files, fixed_links


def main():
    parser = argparse.ArgumentParser(description='Consolidate duplicate reviews')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    manifest = load_manifest()

    # Step 1: Find and classify duplicates
    dupes = find_duplicates()
    print(f"Review codes in multiple years: {len(dupes)}")

    true_dupes = identify_true_duplicates(dupes)
    print(f"True duplicates (same content): {len(true_dupes)}")

    # Step 2: Build consolidation map
    cmap = build_consolidation_map(true_dupes, manifest)

    if args.verbose or args.dry_run:
        print(f"\n{'Code':22s} {'Title':40s} {'Keep':5s} {'Remove':15s} {'Release':7s}")
        print('-' * 95)
        for code, info in sorted(cmap.items()):
            title = info['title'][:39]
            remove = ','.join(info['remove_years'])
            print(f"{code:22s} {title:40s} {info['keep_year']:5s} {remove:15s} {info.get('release_year') or '?':7s}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would:")
        print(f"  Delete {sum(len(i['remove_files']) for i in cmap.values())} duplicate files")
        print(f"  Add/fix redirects in .htaccess")
        print(f"  Update canonical URLs on {len(cmap)} kept pages")

        broken = check_internal_links(cmap)
        if broken:
            print(f"\n  WARNING: {len(broken)} internal links point to files being removed:")
            for page, link in broken[:20]:
                print(f"    {page} -> {link}")
        return

    # Step 3: Add/fix redirects
    new_redir, fixed_redir = add_redirects(cmap)
    print(f"Redirects: {new_redir} added, {fixed_redir} fixed")

    # Step 4: Delete duplicates
    deleted = delete_duplicates(cmap)
    print(f"Deleted: {deleted} duplicate files")

    # Step 5: Update canonical URLs
    updated = update_canonical_urls(cmap)
    print(f"Canonical URLs updated: {updated}")

    # Step 6: Fix release years
    fixed = fix_release_years(cmap, manifest)
    print(f"Release years fixed: {fixed}")

    # Step 7: Fix internal links
    fixed_files, fixed_links = fix_internal_links(cmap)
    print(f"Internal links fixed: {fixed_links} links in {fixed_files} files")

    # Step 8: Verify no broken links remain
    broken = check_internal_links(cmap)
    if broken:
        print(f"\nWARNING: {len(broken)} internal links still point to removed files:")
        for page, link in broken[:20]:
            print(f"  {page} -> {link}")
    else:
        print("No broken internal links remaining.")

    # Save consolidation map for reference
    map_path = os.path.join(ROOT, 'tools', 'consolidation_map.json')
    with open(map_path, 'w') as f:
        json.dump(cmap, f, indent=2, ensure_ascii=False)
    print(f"\nConsolidation map saved to: {map_path}")


if __name__ == '__main__':
    main()
