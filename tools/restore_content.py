#!/usr/bin/env python3
"""
restore_content.py
Bulk-restore missing review/article text from legacy branch into modern HTML files.

For each r*.html and f*.html file in year directories 1996-2004:
  1. Check if article body is empty
  2. If empty, get the legacy version from git
  3. Extract review paragraphs from legacy HTML
  4. Insert clean HTML into the modern file
"""

import os
import re
import subprocess
import sys

REPO_DIR = "/Users/scott/Code/nitrateonline"
YEARS = [str(y) for y in range(1996, 2005)]

# Windows-1252 control character replacements
WIN1252_MAP = {
    '\x91': '\u2018',  # left single quote
    '\x92': '\u2019',  # right single quote / apostrophe
    '\x93': '\u201c',  # left double quote
    '\x94': '\u201d',  # right double quote
    '\x95': '\u2022',  # bullet
    '\x96': '\u2013',  # en dash
    '\x97': '\u2014',  # em dash
    '\x85': '\u2026',  # ellipsis
    '\x80': '\u20ac',  # euro sign
}

# HTML numeric entity replacements
HTML_ENTITY_MAP = [
    (r'&#146;', '\u2019'),
    (r'&#147;', '\u201c'),
    (r'&#148;', '\u201d'),
    (r'&#150;', '\u2013'),
    (r'&#151;', '\u2014'),
    (r'&#133;', '\u2026'),
]


def fix_encoding(text):
    """Fix Windows-1252 characters and HTML entities."""
    for char, replacement in WIN1252_MAP.items():
        text = text.replace(char, replacement)
    for pattern, replacement in HTML_ENTITY_MAP:
        text = re.sub(pattern, replacement, text)
    return text


def get_legacy_content(year, filename):
    """
    Fetch the legacy file content via git show.
    Returns bytes or None if not found.

    For years 1996-1998: legacy files are at root (e.g. legacy:r101pups.html)
    For years 1999-2004: legacy files are in year subdirs (e.g. legacy:1999/ramelie.html)
    """
    if int(year) <= 1998:
        path = filename
    else:
        path = f"{year}/{filename}"

    result = subprocess.run(
        ["git", "-C", REPO_DIR, "show", f"legacy:{path}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def is_body_empty(modern_html):
    """
    Check if the article body is empty (no text between article-body and article-footer).
    Returns True if empty.
    """
    match = re.search(
        r'<article\s+class="article-body"[^>]*>(.*?)<div\s+class="article-footer"',
        modern_html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return False  # Can't find structure, skip
    body_content = match.group(1)
    # Consider empty if only whitespace/newlines
    return not body_content.strip()


def clean_tag(tag_text):
    """
    Clean up a single HTML tag string.
    - Remove font/span opening tags (keep content)
    - Convert b -> strong, i -> em
    - Fix anchor target attributes
    - Remove style/class/align from p tags
    """
    # We'll do this at the paragraph level instead
    return tag_text


def clean_paragraph_html(html):
    """
    Clean up the HTML content of a paragraph:
    - Remove <font ...> and </font> tags (keep inner content)
    - Remove <span ...> and </span> tags (keep inner content)
    - Convert <b> -> <strong>, </b> -> </strong>
    - Convert <i> -> <em>, </i> -> </em>
    - Fix <a> target attributes
    - Remove style, class, align from <p> tags
    """
    # Remove <font ...> opening tags
    html = re.sub(r'<font[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</font>', '', html, flags=re.IGNORECASE)

    # Remove <span ...> tags
    html = re.sub(r'<span[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</span>', '', html, flags=re.IGNORECASE)

    # Convert <b> -> <strong>
    html = re.sub(r'<b(\s[^>]*)?>', r'<strong>', html, flags=re.IGNORECASE)
    html = re.sub(r'</b>', '</strong>', html, flags=re.IGNORECASE)

    # Convert <i> -> <em>
    html = re.sub(r'<i(\s[^>]*)?>', r'<em>', html, flags=re.IGNORECASE)
    html = re.sub(r'</i>', '</em>', html, flags=re.IGNORECASE)

    # Fix anchor target="_top" -> rel="noopener" target="_blank"
    # Also handle anchors without target
    def fix_anchor(m):
        tag = m.group(0)
        # Remove existing target and rel attributes
        tag = re.sub(r'\s+target="[^"]*"', '', tag, flags=re.IGNORECASE)
        tag = re.sub(r"\s+target='[^']*'", '', tag, flags=re.IGNORECASE)
        tag = re.sub(r'\s+rel="[^"]*"', '', tag, flags=re.IGNORECASE)
        # Insert rel and target before closing >
        tag = tag.rstrip('>')
        tag = tag.rstrip()
        tag += ' rel="noopener" target="_blank">'
        return tag

    html = re.sub(r'<a\s[^>]*href[^>]*>', fix_anchor, html, flags=re.IGNORECASE)

    # Remove style, class, align attributes from <p> tags
    def clean_p_tag(m):
        attrs = m.group(1) or ''
        attrs = re.sub(r'\s+style="[^"]*"', '', attrs, flags=re.IGNORECASE)
        attrs = re.sub(r"\s+style='[^']*'", '', attrs, flags=re.IGNORECASE)
        attrs = re.sub(r'\s+class="[^"]*"', '', attrs, flags=re.IGNORECASE)
        attrs = re.sub(r"\s+class='[^']*'", '', attrs, flags=re.IGNORECASE)
        attrs = re.sub(r'\s+align="[^"]*"', '', attrs, flags=re.IGNORECASE)
        attrs = re.sub(r"\s+align='[^']*'", '', attrs, flags=re.IGNORECASE)
        attrs = attrs.strip()
        if attrs:
            return f'<p {attrs}>'
        return '<p>'

    html = re.sub(r'<p(\s[^>]*)?>', clean_p_tag, html, flags=re.IGNORECASE)

    # Collapse extra whitespace/newlines inside paragraph (but keep structure)
    html = re.sub(r'\n\s*\n', '\n', html)
    html = html.strip()

    return html


def extract_paragraphs_from_td(td_content):
    """
    Extract <p> paragraphs from a TD's content.
    Stop before <hr> or <ul> tags.
    Returns list of cleaned paragraph strings.
    """
    # Truncate at <hr> or <ul>
    hr_pos = re.search(r'<hr\b|<ul\b', td_content, re.IGNORECASE)
    if hr_pos:
        td_content = td_content[:hr_pos.start()]

    # Extract all <p>...</p> blocks (non-greedy)
    # Also handle <p> tags that aren't closed properly
    paragraphs = []

    # Split on <p> tags and process
    # Use a more robust approach: find all p...p blocks
    # Pattern: <p ...> content </p> OR <p ...> content (till next <p)
    # Try proper closed p tags first
    p_blocks = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', td_content, re.DOTALL | re.IGNORECASE)

    if not p_blocks:
        # Fall back: split on <p> openings
        parts = re.split(r'(?=<p(?:\s[^>]*)?>)', td_content, flags=re.IGNORECASE)
        p_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]

    for p in p_blocks:
        cleaned = clean_paragraph_html(p)
        # Skip empty paragraphs
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        if inner:
            paragraphs.append(cleaned)

    return paragraphs


def extract_paragraphs_from_body(body_content):
    """
    Extract <p> paragraphs directly from body (for files without table structure).
    Skip navigation/header paragraphs and stop before <hr>/<ul>.
    """
    # Remove header navigation section (before first <hr>)
    # Actually: find content after the first <hr> or after heading block
    # Truncate at <hr> near end (nav links) - find last significant <hr>
    # Strategy: extract all <p> blocks, skip those with images or navigation links
    # then stop at <ul> or <hr> that precedes navigation

    # Find stopping point
    stop_match = re.search(r'<ul\b', body_content, re.IGNORECASE)
    if stop_match:
        body_content = body_content[:stop_match.start()]

    # Find <hr> tags - skip everything before the last one that's near top
    # (after the nav bar)
    hr_matches = list(re.finditer(r'<hr\b[^>]*>', body_content, re.IGNORECASE))
    if hr_matches:
        # Skip content before first <hr> (which is the nav bar)
        body_content = body_content[hr_matches[0].end():]

    p_blocks = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', body_content, re.DOTALL | re.IGNORECASE)

    if not p_blocks:
        parts = re.split(r'(?=<p(?:\s[^>]*)?>)', body_content, flags=re.IGNORECASE)
        p_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]

    paragraphs = []
    for p in p_blocks:
        # Skip paragraphs that are just images or navigation links
        cleaned = clean_paragraph_html(p)
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        if inner:
            paragraphs.append(cleaned)

    return paragraphs


def extract_review_from_legacy(legacy_bytes):
    """
    Extract review paragraphs from legacy HTML bytes.
    Returns list of paragraph HTML strings, or empty list on failure.
    """
    try:
        content = legacy_bytes.decode('windows-1252', errors='replace')
    except Exception:
        content = legacy_bytes.decode('utf-8', errors='replace')

    content = fix_encoding(content)

    # Strategy 1: Find main content TD (not the narrow sidebar or spacer)
    # Look for all top-level TD blocks in the msnavigation table structure
    # The main content TD is typically: valign="top" without width="24" or width="165"

    # Find TDs with their attributes and content
    td_pattern = re.compile(r'<td([^>]*)>(.*?)</td>', re.DOTALL | re.IGNORECASE)

    # Collect all TDs with their content length
    tds = []
    for m in td_pattern.finditer(content):
        attrs = m.group(1)
        inner = m.group(2)

        # Skip the narrow spacer TD
        if re.search(r'width\s*=\s*["\']?\s*2[0-9]\b', attrs, re.IGNORECASE):
            continue
        # Skip the sidebar TD (width 165 or similar small widths)
        if re.search(r'width\s*=\s*["\']?\s*1[0-9]{2}\b', attrs, re.IGNORECASE):
            continue

        # Count actual text content (not just tags)
        text_content = re.sub(r'<[^>]+>', '', inner).strip()
        if len(text_content) > 100:  # Has substantial text content
            tds.append((attrs, inner))

    if tds:
        # Use the first substantial TD
        _, td_content = tds[0]

        # If TD contains a nested table, extract from the inner main TD
        inner_tds = td_pattern.findall(td_content)
        if inner_tds:
            # Find largest inner TD
            best_inner = None
            best_len = 0
            for attrs2, inner2 in inner_tds:
                text_len = len(re.sub(r'<[^>]+>', '', inner2).strip())
                if text_len > best_len:
                    best_len = text_len
                    best_inner = inner2
            if best_inner and best_len > 100:
                td_content = best_inner

        paragraphs = extract_paragraphs_from_td(td_content)
        if paragraphs:
            return paragraphs

    # Strategy 2: Body-level paragraphs (older files without table structure)
    body_match = re.search(r'<body[^>]*>(.*)', content, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_content = body_match.group(1)
        paragraphs = extract_paragraphs_from_body(body_content)
        if paragraphs:
            return paragraphs

    return []


def insert_content_into_modern(modern_html, paragraphs):
    """
    Insert extracted paragraphs into the modern HTML file's article body.
    Returns the updated HTML string.
    """
    content_html = '\n'.join(f'      {p}' for p in paragraphs)

    # Pattern: <article class="article-body" ...> followed by whitespace then <div class="article-footer"
    pattern = re.compile(
        r'(<article\s+class="article-body"[^>]*>)\s*(<div\s+class="article-footer")',
        re.DOTALL | re.IGNORECASE,
    )

    def replacer(m):
        return f'{m.group(1)}\n{content_html}\n\n      {m.group(2)}'

    new_html, count = pattern.subn(replacer, modern_html)
    if count == 0:
        return None  # Pattern not found
    return new_html


def process_file(year, filename):
    """
    Process a single file. Returns one of:
    'has_content', 'restored', 'no_legacy', 'failed'
    """
    filepath = os.path.join(REPO_DIR, year, filename)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            modern_html = f.read()
    except Exception as e:
        print(f"  ERROR reading {year}/{filename}: {e}")
        return 'failed'

    if not is_body_empty(modern_html):
        return 'has_content'

    # Get legacy content
    legacy_bytes = get_legacy_content(year, filename)
    if legacy_bytes is None:
        print(f"  NO LEGACY: {year}/{filename}")
        return 'no_legacy'

    # Extract paragraphs
    paragraphs = extract_review_from_legacy(legacy_bytes)
    if not paragraphs:
        print(f"  FAILED (no paragraphs extracted): {year}/{filename}")
        return 'failed'

    # Insert into modern file
    new_html = insert_content_into_modern(modern_html, paragraphs)
    if new_html is None:
        print(f"  FAILED (article-body pattern not found): {year}/{filename}")
        return 'failed'

    # Write back
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_html)
    except Exception as e:
        print(f"  ERROR writing {year}/{filename}: {e}")
        return 'failed'

    print(f"  RESTORED ({len(paragraphs)} paragraphs): {year}/{filename}")
    return 'restored'


def main():
    counts = {
        'total': 0,
        'has_content': 0,
        'restored': 0,
        'no_legacy': 0,
        'failed': 0,
    }

    for year in YEARS:
        year_dir = os.path.join(REPO_DIR, year)
        if not os.path.isdir(year_dir):
            continue

        # Get r*.html and f*.html files
        try:
            all_files = os.listdir(year_dir)
        except Exception as e:
            print(f"ERROR listing {year_dir}: {e}")
            continue

        target_files = sorted([
            f for f in all_files
            if (f.startswith('r') or f.startswith('f'))
            and f.endswith('.html')
        ])

        print(f"\n=== {year} ({len(target_files)} files) ===")

        for filename in target_files:
            counts['total'] += 1
            result = process_file(year, filename)
            counts[result] += 1

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total files checked:     {counts['total']}")
    print(f"  Already had content:     {counts['has_content']}")
    print(f"  Restored from legacy:    {counts['restored']}")
    print(f"  No legacy version found: {counts['no_legacy']}")
    print(f"  Failed (parse/write):    {counts['failed']}")
    print("=" * 60)


if __name__ == '__main__':
    main()
