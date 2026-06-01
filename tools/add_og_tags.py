#!/usr/bin/env python3
"""Add Open Graph meta tags to all HTML pages in nitrateonline."""

import os
import re
import sys

REPO_ROOT = "/Users/scott/Code/nitrateonline"
SKIP_DIRS = {"tools", "designs", "mediabar", "cgi-bin", ".git"}
SKIP_FILES = {"google1a87e5c217b58a76.html"}
YEAR_DIRS = {"1996", "1997", "1998", "1999", "2000", "2001", "2002", "2003", "2004"}

def get_og_files():
    """Get all HTML files to process, organized by batch."""
    batches = {}

    # Root level files
    root_files = []
    for f in os.listdir(REPO_ROOT):
        if f.endswith(".html") and f not in SKIP_FILES:
            full = os.path.join(REPO_ROOT, f)
            if os.path.isfile(full):
                root_files.append(full)
    batches["root"] = sorted(root_files)

    # Year directories
    for year in sorted(YEAR_DIRS):
        year_dir = os.path.join(REPO_ROOT, year)
        if os.path.isdir(year_dir):
            year_files = []
            for f in os.listdir(year_dir):
                if f.endswith(".html"):
                    year_files.append(os.path.join(year_dir, f))
            batches[year] = sorted(year_files)

    return batches


def extract_title(content):
    """Extract title from <title> tag, stripping ' — Nitrate Online' suffix."""
    m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    title = m.group(1).strip()
    # Strip common suffixes
    for suffix in [" — Nitrate Online", " - Nitrate Online", " – Nitrate Online"]:
        if title.endswith(suffix):
            title = title[:-len(suffix)]
            break
    return title


def extract_description(content):
    """Extract content from <meta name="description">."""
    m = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        content, re.IGNORECASE | re.DOTALL
    )
    if not m:
        # Try alternate attribute order
        m = re.search(
            r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
            content, re.IGNORECASE | re.DOTALL
        )
    if m:
        return m.group(1).strip()
    return None


def has_og_tags(content):
    """Check if file already has any og: meta tags."""
    return bool(re.search(r'property=["\']og:', content, re.IGNORECASE))


def make_og_url(file_path):
    """Derive the og:url from the file path."""
    rel = os.path.relpath(file_path, REPO_ROOT)
    # Normalize path separators
    rel = rel.replace(os.sep, "/")
    if rel == "index.html":
        return "https://nitrateonline.com/"
    return f"https://nitrateonline.com/{rel}"


def make_og_type(file_path):
    """Determine og:type: 'article' for year subdirs, 'website' otherwise."""
    rel = os.path.relpath(file_path, REPO_ROOT)
    parts = rel.split(os.sep)
    if len(parts) > 1 and parts[0] in YEAR_DIRS:
        return "article"
    return "website"


def build_og_block(url, og_type, title, description):
    """Build the OG meta tags block."""
    lines = [
        f'  <meta property="og:site_name" content="Nitrate Online">',
        f'  <meta property="og:type" content="{og_type}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:title" content="{title}">',
        f'  <meta property="og:description" content="{description}">',
    ]
    return "\n".join(lines) + "\n"


def process_file(file_path):
    """
    Process a single HTML file.
    Returns: 'updated', 'skipped_og_exists', 'skipped_no_title', 'skipped_no_desc', 'error'
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR reading {file_path}: {e}")
        return "error"

    if has_og_tags(content):
        return "skipped_og_exists"

    title = extract_title(content)
    if not title:
        print(f"  WARN: no <title> found in {file_path}")
        return "skipped_no_title"

    description = extract_description(content)
    if not description:
        print(f"  WARN: no <meta name=description> found in {file_path}")
        return "skipped_no_desc"

    url = make_og_url(file_path)
    og_type = make_og_type(file_path)
    og_block = build_og_block(url, og_type, title, description)

    # Insert OG tags immediately before </head>
    if "</head>" not in content and "</HEAD>" not in content:
        print(f"  WARN: no </head> found in {file_path}")
        return "error"

    # Use regex to preserve casing
    new_content = re.sub(
        r'(</head>)',
        og_block + r'\1',
        content,
        count=1,
        flags=re.IGNORECASE
    )

    if new_content == content:
        print(f"  WARN: replacement had no effect in {file_path}")
        return "error"

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        print(f"  ERROR writing {file_path}: {e}")
        return "error"

    return "updated"


def main():
    batches = get_og_files()

    total_updated = 0
    total_skipped_og = 0
    total_skipped_no_title = 0
    total_skipped_no_desc = 0
    total_errors = 0

    for batch_name, files in batches.items():
        print(f"\n=== Batch: {batch_name} ({len(files)} files) ===")
        batch_updated = 0
        for file_path in files:
            result = process_file(file_path)
            if result == "updated":
                batch_updated += 1
                total_updated += 1
            elif result == "skipped_og_exists":
                total_skipped_og += 1
            elif result == "skipped_no_title":
                total_skipped_no_title += 1
            elif result == "skipped_no_desc":
                total_skipped_no_desc += 1
            else:
                total_errors += 1
        print(f"  Updated {batch_updated}/{len(files)} files in {batch_name}")

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"  Updated:              {total_updated}")
    print(f"  Skipped (og exists):  {total_skipped_og}")
    print(f"  Skipped (no title):   {total_skipped_no_title}")
    print(f"  Skipped (no desc):    {total_skipped_no_desc}")
    print(f"  Errors:               {total_errors}")
    print(f"  Total processed:      {total_updated + total_skipped_og + total_skipped_no_title + total_skipped_no_desc + total_errors}")


if __name__ == "__main__":
    main()
