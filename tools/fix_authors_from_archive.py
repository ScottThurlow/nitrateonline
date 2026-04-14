#!/usr/bin/env python3
"""
Fix author attributions by cross-referencing the original archive.

The original site migration used the <a href> link target to assign authors,
but some archive pages have mismatched links (e.g. href="dan.html" but text
says "Cynthia Fuchs"). The displayed author name is authoritative.

This script:
  1. Extracts the correct author from each archive HTML file (displayed name)
  2. Compares against the current site author
  3. Updates JSON-LD, byline link, and byline text where they differ

Usage:
    python3 tools/fix_authors_from_archive.py --dry-run   # preview corrections
    python3 tools/fix_authors_from_archive.py              # apply fixes
"""

import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ARCHIVE = os.path.join(os.path.dirname(ROOT), 'nitrateonline_archive')

# Map author full names to their bio page filename (without .html)
AUTHOR_PAGES = {
    'Carrie Gorringe': 'carrie',
    'Cynthia Fuchs': 'cynthia',
    'Dan Lybarger': 'dan',
    'Dave Luty': 'dave',
    'David Luty': 'dave',
    'Eddie Cockrell': 'eddie',
    'Elias Savada': 'elias',
    'Emma French': 'emma',
    'Gianni Truzzi': 'gianni',
    'Gregory Avery': 'gregory',
    'Jerry White': 'jerry',
    'Joe Barlow': 'joe',
    'KJ Doughton': 'kj',
    'Lyall Bush': 'lyall',
    'Nicholas Schager': None,  # no bio page
    'Paula Nechak': 'paula',
    'Sean Axmaker': 'sean',
}

# Normalize display name (David -> Dave)
DISPLAY_NAMES = {
    'David Luty': 'Dave Luty',
}


def normalize(name):
    """Normalize an author name."""
    n = ' '.join(name.split()).strip().rstrip(',').rstrip('.')
    return DISPLAY_NAMES.get(n, n)


def extract_archive_author(filepath):
    """Extract the displayed author name from an archive HTML file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    m = re.search(
        r'(?:Review|Feature)\s+by\s*\n?\s*<a[^>]*>([^<]+)',
        content, re.IGNORECASE)
    if m:
        return normalize(m.group(1))
    m = re.search(
        r'(?:Review|Feature)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        content)
    if m:
        return normalize(m.group(1))
    return None


def extract_site_author(filepath):
    """Extract the current author from a site HTML file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()
    m = re.search(r'"author"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', content)
    if m:
        return normalize(m.group(1))
    m = re.search(
        r'meta-byline[^>]*>(?:Review|Feature)\s+by\s+<a[^>]*>([^<]+)',
        content)
    if m:
        return normalize(m.group(1))
    return None


def fix_author_in_file(filepath, correct_author):
    """
    Update the author in a site HTML file:
      - JSON-LD "author" name
      - Byline link href and text
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fh:
        content = fh.read()

    original = content
    bio_page = AUTHOR_PAGES.get(correct_author)

    # Fix JSON-LD author name
    def replace_jsonld_author(m):
        return f'"author": {{\n        "@type": "Person",\n        "name": "{correct_author}"\n    }}'

    content = re.sub(
        r'"author"\s*:\s*\{[^}]*"name"\s*:\s*"[^"]*"[^}]*\}',
        replace_jsonld_author,
        content,
    )

    # If there's no JSON-LD author block, add one before the closing </script>
    if '"author"' not in content and 'application/ld+json' in content:
        content = content.replace(
            '\n}\n  </script>',
            f',\n    "author": {{\n        "@type": "Person",\n        "name": "{correct_author}"\n    }}\n}}\n  </script>',
        )

    # Fix byline: <span class="meta-byline">Review by <a href="/name.html">Name</a></span>
    if bio_page:
        # Has a bio page — update both href and name
        content = re.sub(
            r'(meta-byline[^>]*>(?:Review|Feature)\s+by\s+)<a\s+href="[^"]*">([^<]+)</a>',
            lambda m: f'{m.group(1)}<a href="/{bio_page}.html">{correct_author}</a>',
            content,
        )
    else:
        # No bio page — just update the name text
        content = re.sub(
            r'(meta-byline[^>]*>(?:Review|Feature)\s+by\s+)<a\s+href="[^"]*">([^<]+)</a>',
            lambda m: f'{m.group(1)}<a href="/{AUTHOR_PAGES.get(correct_author, "aboutus")}.html">{correct_author}</a>',
            content,
        )

    # If there was no byline at all (the 6 missing cases), add one
    if 'meta-byline' not in content and bio_page:
        # Find the article-meta or article-eyebrow to insert after
        eyebrow_match = re.search(r'(<p class="article-eyebrow">[^<]*</p>)', content)
        if eyebrow_match:
            # Determine type from eyebrow
            art_type = 'Review'
            if 'Feature' in eyebrow_match.group(1):
                art_type = 'Feature'
            byline_html = f'\n      <p class="article-meta"><span class="meta-byline">{art_type} by <a href="/{bio_page}.html">{correct_author}</a></span></p>'
            # Insert after the <h1> title line
            content = re.sub(
                r'(</h1>\s*\n)',
                lambda m: m.group(1) + byline_html + '\n',
                content,
                count=1,
            )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write(content)
        return True
    return False


def build_corrections():
    """Build the list of corrections needed."""
    # Build archive author map keyed by (year, code) to handle duplicate
    # codes across years (e.g. rdead = "Bringing Out the Dead" in 1999
    # vs "Half Past Dead" in 2002).
    archive_authors = {}
    for pat in [
        os.path.join(ARCHIVE, '[rf]*.htm*'),
        os.path.join(ARCHIVE, '[12]*', '[rf]*.htm*'),
    ]:
        for f in glob.glob(pat):
            code = os.path.basename(f).split('.')[0]
            a = extract_archive_author(f)
            if not a:
                continue
            # Determine the year — root-level files are 1996-1998 era
            parent = os.path.basename(os.path.dirname(f))
            if parent.isdigit():
                archive_authors[(parent, code)] = a
            else:
                # Root-level: try all early years
                for yr in ('1996', '1997', '1998'):
                    archive_authors[(yr, code)] = a

    # Find corrections
    corrections = []
    for f in sorted(glob.glob(os.path.join(ROOT, '[12][0-9][0-9][0-9]', '[rf]*.html'))):
        code = os.path.basename(f).replace('.html', '')
        year = os.path.basename(os.path.dirname(f))
        site_author = extract_site_author(f)
        archive_author = archive_authors.get((year, code))

        if not archive_author:
            continue

        needs_fix = False
        if not site_author:
            needs_fix = True
        elif site_author.lower() != archive_author.lower():
            # Skip known non-person authors
            if site_author in ('Nitrate Productions',):
                needs_fix = True
            else:
                needs_fix = True

        if needs_fix:
            corrections.append({
                'code': code,
                'year': year,
                'file': os.path.join(ROOT, year, f'{code}.html'),
                'rel_path': f'{year}/{code}.html',
                'site_author': site_author or '(none)',
                'correct_author': archive_author,
            })

    return corrections


def main():
    parser = argparse.ArgumentParser(
        description='Fix author attributions from archive')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without modifying files')
    args = parser.parse_args()

    if not os.path.isdir(ARCHIVE):
        print(f"Error: Archive not found at {ARCHIVE}")
        sys.exit(1)

    print("Building corrections list...")
    corrections = build_corrections()
    print(f"Found {len(corrections)} corrections needed\n")

    if not corrections:
        print("All authors match the archive. Nothing to do.")
        return

    fixed = 0
    for c in corrections:
        print(f"  {c['rel_path']}: {c['site_author']} -> {c['correct_author']}")
        if not args.dry_run:
            if fix_author_in_file(c['file'], c['correct_author']):
                fixed += 1
            else:
                print(f"    (no changes made — check manually)")

    if args.dry_run:
        print(f"\n[DRY RUN] Would fix {len(corrections)} files.")
    else:
        print(f"\nFixed {fixed} / {len(corrections)} files.")
        print("Run tools/add_author_filmography.py to update bio pages.")


if __name__ == '__main__':
    main()
