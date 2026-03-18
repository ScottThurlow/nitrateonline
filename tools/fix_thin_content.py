#!/usr/bin/env python3
"""
fix_thin_content.py
Fix empty_content and thin_content issues found in audit_report.csv.

For each affected file:
  1. Get the legacy version from git
  2. Extract review paragraphs using improved logic (handles ul-in-content and
     post-table review bodies found in 1998 files)
  3. Replace the current article body content (force replacement even if some content exists)
"""

import csv
import os
import re
import subprocess
import sys

REPO_DIR = "/Users/scott/Code/nitrateonline"
AUDIT_CSV = os.path.join(REPO_DIR, "data", "audit_report.csv")

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
    def fix_anchor(m):
        tag = m.group(0)
        tag = re.sub(r'\s+target="[^"]*"', '', tag, flags=re.IGNORECASE)
        tag = re.sub(r"\s+target='[^']*'", '', tag, flags=re.IGNORECASE)
        tag = re.sub(r'\s+rel="[^"]*"', '', tag, flags=re.IGNORECASE)
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

    # Collapse extra whitespace/newlines inside paragraph
    html = re.sub(r'\n\s*\n', '\n', html)
    html = html.strip()

    return html


def clean_block_html(html):
    """
    Clean a block of HTML (may include <p>, <ul>, <li>) similarly to clean_paragraph_html.
    """
    return clean_paragraph_html(html)


def count_text(html):
    """Return text length of an HTML string (tags stripped)."""
    return len(re.sub(r'<[^>]+>', '', html).replace('&nbsp;', ' ').strip())


def extract_paragraphs_from_td(td_content, allow_ul=False):
    """
    Extract <p> paragraphs (and optionally <ul>/<li> blocks) from a TD's content.

    If allow_ul=False: stop before <hr> or <ul> tags (original behavior for sidebar).
    If allow_ul=True: include <ul> content as review content, only stop before <hr>.

    If no <p> tags are found but the TD has substantial text (e.g. text in <font>/<b>
    wrappers with no <p> tags), returns the full TD text as a single block.

    Returns list of cleaned paragraph/block HTML strings.
    """
    if not allow_ul:
        # Original behavior: stop at <hr> or <ul>
        stop_pos = re.search(r'<hr\b|<ul\b', td_content, re.IGNORECASE)
        if stop_pos:
            td_content = td_content[:stop_pos.start()]

        p_blocks = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', td_content, re.DOTALL | re.IGNORECASE)
        if not p_blocks:
            parts = re.split(r'(?=<p(?:\s[^>]*)?>)', td_content, flags=re.IGNORECASE)
            p_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]
    else:
        # allow_ul=True: stop only at <hr>, include <ul> blocks as content
        hr_pos = re.search(r'<hr\b', td_content, re.IGNORECASE)
        if hr_pos:
            td_content = td_content[:hr_pos.start()]

        # Extract both <p> and <ul> blocks as content units
        # Split content by <p> and <ul> tags to get all blocks
        p_blocks = re.findall(
            r'(?:<p(?:\s[^>]*)?>.*?</p>|<ul\b.*?</ul>)',
            td_content,
            re.DOTALL | re.IGNORECASE
        )
        if not p_blocks:
            # Fall back: just p tags without proper close
            parts = re.split(r'(?=<p(?:\s[^>]*)?>)', td_content, flags=re.IGNORECASE)
            p_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]

    paragraphs = []
    for p in p_blocks:
        cleaned = clean_block_html(p)
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        if inner:
            paragraphs.append(cleaned)

    # If no paragraphs found but TD has substantial text (text in non-p wrappers),
    # wrap the TD content in a <p> and return it
    if not paragraphs:
        td_text = re.sub(r'<[^>]+>', '', td_content).replace('&nbsp;', ' ').strip()
        if len(td_text) > 50:
            # Wrap the cleaned TD content as a paragraph
            cleaned_td = clean_block_html(td_content.strip())
            if cleaned_td:
                paragraphs.append(f'<p>{cleaned_td}</p>')

    return paragraphs


def extract_paragraphs_from_body(body_content):
    """
    Extract <p> paragraphs directly from body (for files without table structure).
    Skips content before first <hr> (nav bar), stops at <ul> (nav list at bottom).
    """
    stop_match = re.search(r'<ul\b', body_content, re.IGNORECASE)
    if stop_match:
        body_content = body_content[:stop_match.start()]

    hr_matches = list(re.finditer(r'<hr\b[^>]*>', body_content, re.IGNORECASE))
    if hr_matches:
        body_content = body_content[hr_matches[0].end():]

    p_blocks = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', body_content, re.DOTALL | re.IGNORECASE)

    if not p_blocks:
        parts = re.split(r'(?=<p(?:\s[^>]*)?>)', body_content, flags=re.IGNORECASE)
        p_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]

    paragraphs = []
    for p in p_blocks:
        cleaned = clean_block_html(p)
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        if inner:
            paragraphs.append(cleaned)

    return paragraphs


def extract_all_body_paragraphs(content):
    """
    Extract ALL substantive <p> paragraphs from the full body, ignoring table structure.
    Used as a last-resort strategy for complex multi-table layouts (e.g. ftopten.html).
    Skips navigation-only paragraphs (those containing only links or images).
    """
    body_match = re.search(r'<body[^>]*>(.*)', content, re.DOTALL | re.IGNORECASE)
    if not body_match:
        return []
    body = body_match.group(1)

    # Remove obvious nav sections: content before first <hr>
    hr_matches = list(re.finditer(r'<hr\b[^>]*>', body, re.IGNORECASE))
    if hr_matches:
        body = body[hr_matches[0].end():]

    p_blocks = re.findall(r'<p(?:\s[^>]*)?>.*?</p>', body, re.DOTALL | re.IGNORECASE)

    paragraphs = []
    for p in p_blocks:
        cleaned = clean_block_html(p)
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        # Skip very short paragraphs (likely nav/spacer)
        if len(inner) > 20:
            paragraphs.append(cleaned)

    return paragraphs


def extract_paragraphs_after_last_table(content):
    """
    For 1998-style files: extract review content from the section after the last
    </table> tag. These files keep the review body outside the table structure.

    Extracts <p>, <h1>-<h6>, and <ul>/<ol> blocks (all may be review content).
    Stops only at the final nav section (identified by a <ul> containing "Contents").
    """
    tables = list(re.finditer(r'</table>', content, re.IGNORECASE))
    if not tables:
        return []

    after = content[tables[-1].end():]

    # Find the navigation <ul> at the very end (contains "Contents" nav links)
    # Stop before that final nav list
    nav_ul_matches = list(re.finditer(r'<ul\b[^>]*>.*?</ul>', after, re.DOTALL | re.IGNORECASE))
    if nav_ul_matches:
        # Check if last <ul> contains navigation text
        last_ul = nav_ul_matches[-1]
        last_ul_text = re.sub(r'<[^>]+>', '', last_ul.group(0)).strip()
        if 'Contents' in last_ul_text or 'Features' in last_ul_text:
            after = after[:last_ul.start()]

    # Extract <p>, <h1>-<h6>, <ul>, <ol> blocks as content
    content_blocks = re.findall(
        r'(?:<p(?:\s[^>]*)?>.*?</p>|<h[1-6](?:\s[^>]*)?>.*?</h[1-6]>|<ul\b.*?</ul>|<ol\b.*?</ol>)',
        after,
        re.DOTALL | re.IGNORECASE
    )

    if not content_blocks:
        # Fall back: just p tags without proper close
        parts = re.split(r'(?=<p(?:\s[^>]*)?>)', after, flags=re.IGNORECASE)
        content_blocks = [p for p in parts if re.match(r'<p', p, re.IGNORECASE)]

    paragraphs = []
    for block in content_blocks:
        cleaned = clean_block_html(block)
        inner = re.sub(r'<[^>]+>', '', cleaned)
        inner = inner.replace('&nbsp;', ' ').strip()
        if len(inner) > 5:  # Skip nearly empty blocks
            paragraphs.append(cleaned)

    return paragraphs


def extract_review_from_legacy(legacy_bytes):
    """
    Extract review paragraphs from legacy HTML bytes.
    Returns list of paragraph HTML strings, or empty list on failure.

    Tries multiple strategies and picks the one with the most text:
    1. Main content TD (with <ul> allowed) — for 1999-2004 files with <ul> in review
    2. Main content TD (without <ul> — original behavior)
    3. Content after last </table> — for 1998-style files with review outside tables
    4. All body paragraphs — for complex multi-table layouts (e.g. top-ten lists)
    5. Body-level paragraphs with <hr> start (oldest files without table structure)
    """
    try:
        content = legacy_bytes.decode('windows-1252', errors='replace')
    except Exception:
        content = legacy_bytes.decode('utf-8', errors='replace')

    content = fix_encoding(content)

    td_pattern = re.compile(r'<td([^>]*)>(.*?)</td>', re.DOTALL | re.IGNORECASE)

    # Collect candidate TDs (excluding spacer and sidebar columns)
    tds = []
    for m in td_pattern.finditer(content):
        attrs = m.group(1)
        inner = m.group(2)

        # Skip the narrow spacer TD (width="24" etc.)
        if re.search(r'width\s*=\s*["\']?\s*2[0-9]\b', attrs, re.IGNORECASE):
            continue
        # Skip the sidebar TD (width="165" or similar small widths)
        if re.search(r'width\s*=\s*["\']?\s*1[0-9]{2}\b', attrs, re.IGNORECASE):
            continue

        text_content = re.sub(r'<[^>]+>', '', inner).strip()
        if len(text_content) > 100:
            tds.append((attrs, inner))

    # Always run all strategies; pick the one with the most text
    paragraphs_with_ul = []
    paragraphs_no_ul = []

    if tds:
        _, td_content = tds[0]

        # If TD contains a nested table, drill into the largest inner TD
        inner_tds = td_pattern.findall(td_content)
        if inner_tds:
            best_inner = None
            best_len = 0
            for attrs2, inner2 in inner_tds:
                text_len = len(re.sub(r'<[^>]+>', '', inner2).strip())
                if text_len > best_len:
                    best_len = text_len
                    best_inner = inner2
            if best_inner and best_len > 100:
                td_content = best_inner

        # Strategy 1a: Try extraction allowing <ul> as review content
        paragraphs_with_ul = extract_paragraphs_from_td(td_content, allow_ul=True)

        # Strategy 1b: Try extraction stopping at <ul> (original behavior)
        paragraphs_no_ul = extract_paragraphs_from_td(td_content, allow_ul=False)

    # Strategy 2: Content after last </table> (1998-style files and awards pages)
    paragraphs_post_table = extract_paragraphs_after_last_table(content)

    # Strategy 3: All body paragraphs (for complex multi-table layouts)
    paragraphs_all_body = extract_all_body_paragraphs(content)

    # Strategy 4: Simple body-level paragraphs with <hr> nav skip
    body_match = re.search(r'<body[^>]*>(.*)', content, re.DOTALL | re.IGNORECASE)
    paragraphs_simple_body = []
    if body_match:
        paragraphs_simple_body = extract_paragraphs_from_body(body_match.group(1))

    # Choose the best result: most text content
    def total_text(ps):
        return sum(count_text(p) for p in ps)

    candidates = [
        (total_text(paragraphs_with_ul), paragraphs_with_ul),
        (total_text(paragraphs_no_ul), paragraphs_no_ul),
        (total_text(paragraphs_post_table), paragraphs_post_table),
        (total_text(paragraphs_all_body), paragraphs_all_body),
        (total_text(paragraphs_simple_body), paragraphs_simple_body),
    ]
    candidates.sort(key=lambda x: x[0], reverse=True)

    best_text_len, best_paragraphs = candidates[0]
    if best_paragraphs:
        return best_paragraphs

    return []


def replace_content_in_modern(modern_html, paragraphs):
    """
    Replace the article body content in the modern HTML file.
    This replaces everything between <article class="article-body"...> and
    <div class="article-footer" — whether there's existing content or not.
    Returns the updated HTML string, or None if pattern not found.
    """
    content_html = '\n'.join(f'      {p}' for p in paragraphs)

    # Pattern: <article class="article-body" ...> ... <div class="article-footer"
    # Replace whatever is between them with the new content
    pattern = re.compile(
        r'(<article\s+class="article-body"[^>]*>)(.*?)(<div\s+class="article-footer")',
        re.DOTALL | re.IGNORECASE,
    )

    def replacer(m):
        return f'{m.group(1)}\n{content_html}\n\n      {m.group(3)}'

    new_html, count = pattern.subn(replacer, modern_html)
    if count == 0:
        return None
    return new_html


def get_affected_files(csv_path):
    """
    Read audit_report.csv and return a set of file paths with empty_content or thin_content.
    Returns list of (year, filename) tuples.
    """
    affected = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['issue_type'] in ('empty_content', 'thin_content'):
                filepath = row['file']
                parts = filepath.split('/')
                if len(parts) == 2:
                    year, filename = parts
                    affected.add((year, filename))
    return sorted(affected)


def process_file(year, filename):
    """
    Process a single file. Returns one of:
    'restored', 'no_legacy', 'failed'
    """
    filepath = os.path.join(REPO_DIR, year, filename)

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            modern_html = f.read()
    except Exception as e:
        print(f"  ERROR reading {year}/{filename}: {e}")
        return 'failed'

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

    # Replace content in modern file (force replacement)
    new_html = replace_content_in_modern(modern_html, paragraphs)
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

    text_chars = sum(count_text(p) for p in paragraphs)
    print(f"  RESTORED ({len(paragraphs)} para, {text_chars} chars): {year}/{filename}")
    return 'restored'


def main():
    affected_files = get_affected_files(AUDIT_CSV)
    print(f"Found {len(affected_files)} unique files with empty_content or thin_content issues\n")

    counts = {
        'restored': 0,
        'no_legacy': 0,
        'failed': 0,
    }
    no_legacy_files = []
    failed_files = []

    for year, filename in affected_files:
        result = process_file(year, filename)
        counts[result] += 1
        if result == 'no_legacy':
            no_legacy_files.append(f"{year}/{filename}")
        elif result == 'failed':
            failed_files.append(f"{year}/{filename}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total files processed:   {len(affected_files)}")
    print(f"  Restored from legacy:    {counts['restored']}")
    print(f"  No legacy version found: {counts['no_legacy']}")
    print(f"  Failed (parse/write):    {counts['failed']}")

    if no_legacy_files:
        print("\nFiles with no legacy version:")
        for f in no_legacy_files:
            print(f"  {f}")

    if failed_files:
        print("\nFiles that failed:")
        for f in failed_files:
            print(f"  {f}")

    print("=" * 60)


if __name__ == '__main__':
    main()
