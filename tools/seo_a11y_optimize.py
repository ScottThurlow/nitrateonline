#!/usr/bin/env python3
"""
Batch SEO, accessibility, and mobile optimization for all HTML pages.

Adds:
  1. <meta name="theme-color"> tag
  2. Skip-to-content link after <body>
  3. id="main" on the main content landmark
  4. loading="lazy" on below-fold <img> tags
  5. Article structured data (JSON-LD) on article pages

Safe to re-run: checks for existing modifications before applying.
"""

import os
import re
import json
import html
import glob
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Pages to skip (already handled manually or special cases)
# Use paths relative to ROOT
SKIP_RELPATHS = {'index.html'}


def find_html_files():
    """Find all HTML files in the project, excluding tools/ and cgi-bin/."""
    files = []
    for pattern in ['*.html', '*/*.html']:
        files.extend(glob.glob(os.path.join(ROOT, pattern)))
    # Filter out tool files, cgi-bin, google verification, etc.
    files = [
        f for f in files
        if '/tools/' not in f
        and '/cgi-bin/' not in f
        and 'google' not in os.path.basename(f).lower()
        and os.path.relpath(f, ROOT) not in SKIP_RELPATHS
    ]
    return sorted(files)


def add_theme_color(content):
    """Add theme-color meta tag if missing."""
    if 'theme-color' in content:
        return content
    # Insert before </head>
    return content.replace('</head>', '  <meta name="theme-color" content="#111111">\n</head>', 1)


def add_skip_link(content):
    """Add skip-to-content link after <body> if missing."""
    if 'skip-link' in content:
        return content
    return content.replace('<body>', '<body>\n  <a href="#main" class="skip-link">Skip to content</a>', 1)


def add_main_id(content):
    """Add id="main" to the primary content landmark."""
    if 'id="main"' in content:
        return content

    # Article pages: target article-layout or article-body
    # The main content starts at article-header or article-layout
    # Best target: the first <div class="article-layout"> or <div class="info-layout">
    # or <main> tag

    # If there's a <main> tag, add id to it
    if '<main>' in content:
        return content.replace('<main>', '<main id="main">', 1)
    if '<main ' in content and 'id="main"' not in content:
        return re.sub(r'<main\b', '<main id="main"', content, count=1)

    # For article pages, add id to article-layout div
    if 'class="article-layout"' in content:
        return content.replace('class="article-layout"', 'id="main" class="article-layout"', 1)

    # For info pages, add id to info-layout div
    if 'class="info-layout"' in content:
        return content.replace('class="info-layout"', 'id="main" class="info-layout"', 1)

    # For archive listing pages
    if 'class="archive-listing"' in content:
        return content.replace('class="archive-listing"', 'id="main" class="archive-listing"', 1)

    # Fallback: add id to first element after breadcrumb or header
    return content


def add_lazy_loading(content):
    """Add loading="lazy" to images that are below the fold."""
    if 'loading="lazy"' in content and content.count('loading="lazy"') >= content.count('<img') - 2:
        return content  # Already has lazy loading on most images

    # Don't add lazy to the logo (in masthead) or the first article image
    # Strategy: add lazy to all <img> tags that aren't the logo
    lines = content.split('\n')
    result = []
    img_count = 0
    in_masthead = False

    for line in lines:
        if 'class="masthead"' in line:
            in_masthead = True
        if in_masthead and '</header>' in line:
            in_masthead = False

        if '<img' in line and 'loading=' not in line:
            if in_masthead or 'logo.svg' in line:
                # Don't lazy load the logo
                result.append(line)
            elif img_count == 0 and ('card-large' in content or 'film-card-poster' in content):
                # Don't lazy the first content image on pages with featured cards
                img_count += 1
                result.append(line)
            else:
                # Add lazy loading
                line = line.replace('<img ', '<img loading="lazy" ')
                img_count += 1
                result.append(line)
        else:
            if '<img' in line:
                img_count += 1
            result.append(line)

    return '\n'.join(result)


def extract_article_metadata(content, filepath):
    """Extract metadata from an article page for structured data."""
    meta = {}

    # Title from og:title
    m = re.search(r'<meta property="og:title" content="([^"]*)"', content)
    if m:
        meta['title'] = html.unescape(m.group(1))

    # Description from og:description
    m = re.search(r'<meta property="og:description" content="([^"]*)"', content)
    if m:
        meta['description'] = html.unescape(m.group(1))[:300]

    # URL from canonical
    m = re.search(r'<link rel="canonical" href="([^"]*)"', content)
    if m:
        meta['url'] = m.group(1)

    # Image from og:image
    m = re.search(r'<meta property="og:image" content="([^"]*)"', content)
    if m:
        meta['image'] = m.group(1)

    # Author from meta-byline
    m = re.search(r'class="meta-byline"[^>]*>(?:Review by |by |By )?([^<]+)', content, re.DOTALL)
    if m:
        meta['author'] = ' '.join(m.group(1).split()).strip()

    # Date published
    m = re.search(r'Published\s+(\d{1,2}\s+\w+\s+\d{4})', content)
    if m:
        meta['datePublished'] = m.group(1)

    # Type from og:type
    m = re.search(r'<meta property="og:type" content="([^"]*)"', content)
    if m:
        meta['og_type'] = m.group(1)

    return meta


def build_article_jsonld(meta):
    """Build Article JSON-LD structured data."""
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta.get('title', ''),
        "description": meta.get('description', ''),
        "publisher": {
            "@type": "Organization",
            "name": "Nitrate Online",
            "url": "https://nitrateonline.com/"
        }
    }
    if 'url' in meta:
        ld['url'] = meta['url']
    if 'image' in meta:
        ld['image'] = meta['image']
    if 'author' in meta:
        ld['author'] = {"@type": "Person", "name": meta['author']}
    if 'datePublished' in meta:
        ld['datePublished'] = meta['datePublished']
    return ld


def add_structured_data(content, filepath):
    """Add JSON-LD structured data to article pages."""
    if 'application/ld+json' in content:
        return content

    # Only add to article pages (those with og:type article)
    if '"article"' not in content and "'article'" not in content:
        return content

    meta = extract_article_metadata(content, filepath)
    if not meta.get('title'):
        return content

    ld = build_article_jsonld(meta)
    ld_json = json.dumps(ld, indent=4, ensure_ascii=False)

    script_tag = f'  <script type="application/ld+json">\n  {ld_json}\n  </script>\n'
    return content.replace('</head>', script_tag + '</head>', 1)


def process_file(filepath, dry_run=False):
    """Apply all optimizations to a single file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        original = f.read()

    content = original
    content = add_theme_color(content)
    content = add_skip_link(content)
    content = add_main_id(content)
    content = add_lazy_loading(content)
    content = add_structured_data(content, filepath)

    if content != original:
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        return True
    return False


def main():
    dry_run = '--dry-run' in sys.argv
    verbose = '--verbose' in sys.argv or '-v' in sys.argv

    files = find_html_files()
    modified = 0
    skipped = 0

    print(f"{'[DRY RUN] ' if dry_run else ''}Processing {len(files)} HTML files...")

    for filepath in files:
        relpath = os.path.relpath(filepath, ROOT)
        try:
            changed = process_file(filepath, dry_run=dry_run)
            if changed:
                modified += 1
                if verbose:
                    print(f"  Modified: {relpath}")
            else:
                skipped += 1
                if verbose:
                    print(f"  Skipped (no changes): {relpath}")
        except Exception as e:
            print(f"  ERROR: {relpath}: {e}")

    print(f"\nDone. Modified: {modified}, Unchanged: {skipped}, Total: {len(files)}")
    if dry_run:
        print("(No files were written — dry run mode)")


if __name__ == '__main__':
    main()
