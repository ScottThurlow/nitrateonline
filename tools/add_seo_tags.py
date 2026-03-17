#!/usr/bin/env python3
"""Add og:image, Twitter Card tags, and canonical URLs to all HTML pages."""

import os
import re
import glob

SITE_URL = "https://nitrateonline.com"
DEFAULT_OG_IMAGE = f"{SITE_URL}/images/og-default.svg"

def get_poster_image(html):
    """Extract poster image from film-card-poster if it has a real image (not placeholder)."""
    m = re.search(r'<div class="film-card-poster">\s*<img\s+src="([^"]+)"', html)
    if m:
        return m.group(1)
    return None

def get_og_url(html):
    """Extract og:url value."""
    m = re.search(r'<meta property="og:url" content="([^"]+)"', html)
    return m.group(1) if m else None

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()

    # Skip if already has twitter:card (already processed)
    if 'twitter:card' in html:
        return False

    # Skip if no og:url (not a standard page)
    og_url = get_og_url(html)
    if not og_url:
        return False

    # Determine og:image
    poster = get_poster_image(html)
    if poster:
        # Convert relative path to absolute URL
        if poster.startswith('/'):
            og_image = SITE_URL + poster
        else:
            og_image = SITE_URL + '/' + poster
    else:
        og_image = DEFAULT_OG_IMAGE

    # Build new tags to insert
    new_tags = []

    # Canonical URL
    if '<link rel="canonical"' not in html:
        new_tags.append(f'  <link rel="canonical" href="{og_url}">')

    # og:image
    if 'og:image' not in html:
        new_tags.append(f'  <meta property="og:image" content="{og_image}">')

    # Twitter Card tags
    new_tags.append('  <meta name="twitter:card" content="summary_large_image">')

    if not new_tags:
        return False

    # Insert before </head>
    insertion = '\n'.join(new_tags)
    html = html.replace('</head>', insertion + '\n</head>')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return True

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html_files = glob.glob(os.path.join(root, '**/*.html'), recursive=True)

    updated = 0
    skipped = 0
    with_poster = 0

    for filepath in sorted(html_files):
        # Skip tools directory and sample files
        rel = os.path.relpath(filepath, root)
        if rel.startswith('tools/') or rel.startswith('sample-'):
            continue

        poster = None
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            poster = get_poster_image(content)

        if process_file(filepath):
            updated += 1
            if poster:
                with_poster += 1
        else:
            skipped += 1

    print(f"Updated: {updated} files")
    print(f"  With poster image: {with_poster}")
    print(f"  With default image: {updated - with_poster}")
    print(f"Skipped: {skipped} files")

if __name__ == '__main__':
    main()
