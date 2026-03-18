#!/usr/bin/env python3
"""
fix_legacy_artifacts.py

Fixes two legacy HTML artifacts in r*.html and f*.html files for years 1996-2004:

Fix 1: Remove bold wrapping from opening paragraph
  - Strips <strong>...</strong> when the entire first article <p> is wrapped.
  - Drop-cap style (<p><strong>W</strong>ord...) is left alone.
  - Credit lines (Directed by, Starring, etc.) are left to Fix 2.

Fix 2: Remove redundant title/byline paragraphs from article body start
  - Closed byline: <p><em><strong>Review by...</strong></em></p>
  - Unclosed byline: <p>Title<br><em>review by...</em><p> (no closing </p>)
  - Credit blocks: <p><strong><em>Directed by...</em>...</strong></p> etc.
  - Short plain deck-heads immediately after a removed byline paragraph.

Only operates on the first ~1200 chars of the article body to be conservative.
"""

import re
import glob
import os
import sys

YEARS = list(range(1996, 2005))
BASE_DIR = "/Users/scott/Code/nitrateonline"

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

ARTICLE_BODY_RE = re.compile(
    r'(<article class="article-body"[^>]*>)(.*?)(\s*<div class="article-footer")',
    re.DOTALL
)


def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html)


# ─────────────────────────────────────────────────────────────────────────────
# Fix 1: strip whole-paragraph bold from the first real article paragraph
# ─────────────────────────────────────────────────────────────────────────────

# Matches a <p> whose first and only inline-level child is <strong>...</strong>
# (possibly with whitespace around it).  We require </strong> immediately before </p>.
WHOLE_BOLD_PARA_RE = re.compile(
    r'(<p>)\s*(<strong>)(.*?)(</strong>)\s*(</p>)',
    re.DOTALL
)


def fix1_whole_bold(body):
    """
    Strip <strong>...</strong> wrapping from the first real article paragraph
    if and only if:
      - <strong> is the IMMEDIATE first child of <p> (no leading text)
      - </strong> is the last element before </p>
      - The inner content is substantial (not a single drop-cap letter)
      - The content is NOT a credit line (Directed by, Starring, etc.)

    Returns (new_body, fixed: bool).
    """
    # Find the first PLAIN <p> tag (no attributes) in the body.
    # We skip styled <p style=...> tags (those are inside widget/nav blocks).
    first_p = re.search(r'<p>', body)
    if not first_p:
        return body, False

    m = WHOLE_BOLD_PARA_RE.match(body, first_p.start())
    if not m:
        return body, False

    inner = m.group(3)
    inner_text = strip_tags(inner).strip()

    # Reject single-character drop caps
    if len(inner_text) < 5:
        return body, False

    # Reject credit lines — those should be handled by Fix 2
    if re.match(
        r'\s*(?:<[^>]+>\s*)*(?:Directed by|Written by|Written and Directed by|'
        r'Starring|Produced by|Screenplay by|Screen Story|Adapted by|Adapted from|'
        r'Freely adapted|Photography by|Music by|Cinematography by)\b',
        inner,
        re.IGNORECASE
    ):
        return body, False

    # Build replacement: keep the <p>...</p> but drop the <strong> wrapping
    old_span = m.group(0)
    new_span = f'<p>{inner}</p>'
    new_body = body[:m.start()] + new_span + body[m.end():]
    return new_body, True


# ─────────────────────────────────────────────────────────────────────────────
# Fix 2: remove byline / title / credit-block paragraphs near article start
# ─────────────────────────────────────────────────────────────────────────────

BYLINE_KEYWORDS_RE = re.compile(
    r'\b(?:review|feature|interview)\s+by\b',
    re.IGNORECASE
)

CREDIT_KEYWORDS_RE = re.compile(
    r'\b(?:Directed by|Written by|Written and Directed by|Starring|'
    r'Screenplay by|Screen Story|Screen story and Screenplay|'
    r'Produced by|Photography by|Music by|Cinematography by|'
    r'Adapted by|Adapted from|Freely adapted)\b',
    re.IGNORECASE
)


def text_len(html):
    return len(strip_tags(html).strip())


def is_byline_para(para_html):
    """
    Short paragraph (< 300 chars of text) that contains a byline keyword.
    """
    if text_len(para_html) > 300:
        return False
    return bool(BYLINE_KEYWORDS_RE.search(para_html))


CREDIT_AT_START_RE = re.compile(
    r'^\s*[\"\u201c]?'  # optional opening quotation mark
    r'(?:Directed by|Written by|Written and Directed by|Starring|'
    r'Screenplay by|Screen Story|Screen story and Screenplay|'
    r'Produced by|Photography by|Music by|Cinematography by|'
    r'Adapted by|Adapted from|Freely adapted)',
    # No \b at the end — handles malformed "byName" (missing space after keyword)
    re.IGNORECASE
)


def is_credit_block_para(para_html):
    """
    Paragraph that contains ONLY credit information (Directed by, Starring,
    Screenplay by, etc.) and is wrapped in <strong>.  The credit keyword must
    appear at or near the START of the paragraph's text content (not buried
    in review prose).  No hard length cap — cast lists can be long.
    Handles both explicitly-closed (<p>...</p>) and unclosed (<p>...<p>) paragraphs.
    """
    tlen = text_len(para_html)
    if tlen == 0:
        return False
    # Hard cap: if text is very long (> 600 chars) it's probably review prose
    if tlen > 600:
        return False
    stripped = para_html.strip()
    # Must start with <p><strong> or <p><br>...<strong>
    if not (re.match(r'^<p>\s*<strong>', stripped) or
            re.match(r'^<p>\s*<br[^>]*>\s*<strong>', stripped)):
        return False
    # The text content (with tags stripped) must START with a credit keyword
    inner_text = strip_tags(para_html).strip()
    return bool(CREDIT_AT_START_RE.match(inner_text))


def is_standalone_subtitle(para_html):
    """
    Very short (< 60 chars of text, ≤ 8 words) deck-head paragraph with no links
    and no text-level markup (em/strong wrapping the text itself).
    Only remove if the text content comes BEFORE any markup (i.e., text is plain).
    """
    text = strip_tags(para_html).strip()
    tlen = len(text)
    if tlen == 0 or tlen > 60:
        return False
    if len(text.split()) > 8:
        return False
    if '<a ' in para_html:
        return False
    # Reject if the <p> starts with <em> or <strong> — text is styled (epigraph/quote)
    para_inner = re.match(r'<p>\s*(.*)', para_html.strip(), re.DOTALL)
    if para_inner:
        inner_start = para_inner.group(1).lstrip()
        if inner_start.startswith('<em>') or inner_start.startswith('<strong>'):
            return False
    return True


def _remove_para(body, start, end):
    """Remove the substring body[start:end] and strip leading whitespace before next token."""
    after = body[end:]
    # Strip leading whitespace/newlines after the removed element
    after = after.lstrip(' \t\n\r')
    return body[:start] + after


def fix2_byline(body):
    """
    Remove redundant byline/title/credit paragraphs from the start of the article body.

    Handles:
    A. CLOSED byline paragraphs: <p>...(review by)...</p>
       (including em+strong-wrapped variants)
    B. UNCLOSED byline paragraphs: <p>...(review by)...<p>  [no </p>]
    C. Credit-block paragraphs: <p><strong><em>Directed by...</em>...</strong></p>
       These are removed even if preceded by <img> tags (within first 1200 chars).
    D. Short plain deck-head paragraphs immediately after a removed byline.

    Returns (new_body, count_removed: int).
    """
    removed_count = 0
    MAX_OFFSET = 1200
    MAX_PASSES = 8

    result = body

    for _pass in range(MAX_PASSES):
        # Take a snapshot of the working area (first MAX_OFFSET chars)
        work = result[:MAX_OFFSET]
        original_result = result
        made_change = False

        # ── Strategy A/B: look for a byline paragraph ──────────────────────
        # Pattern A: closed <p>...</p> containing byline keyword
        # Pattern B: unclosed <p>...<p> (implicit close) containing byline keyword

        # We try to find the FIRST byline-containing paragraph, whether open or closed.
        # For unclosed: match from <p> to the next <p> (not through </p>)
        # Regex: <p>(no </p>)*(byline keyword)(no </p>)* followed by <p>
        closed_byline = re.search(
            r'<p>((?:[^<]|<(?!/?p>))*?)'         # open <p>, content with no </p>
            r'(?:review|feature|interview)\s+by\b'  # byline keyword
            r'((?:[^<]|<(?!/?p>))*?)'             # more content with no </p>
            r'</p>',                               # EXPLICIT close
            work, re.IGNORECASE | re.DOTALL
        )
        unclosed_byline = re.search(
            r'<p>((?:[^<]|<(?!/?p>))*?)'         # open <p>, content with no </p>
            r'(?:review|feature|interview)\s+by\b'  # byline keyword
            r'((?:[^<]|<(?!/?p>))*?)'             # more content with no </p>
            r'(?=<p>)',                            # lookahead: followed by <p> (no </p> before it)
            work, re.IGNORECASE | re.DOTALL
        )

        # Choose whichever appears first
        byline_match = None
        byline_is_unclosed = False

        if closed_byline and unclosed_byline:
            if unclosed_byline.start() <= closed_byline.start():
                byline_match = unclosed_byline
                byline_is_unclosed = True
            else:
                byline_match = closed_byline
        elif closed_byline:
            byline_match = closed_byline
        elif unclosed_byline:
            byline_match = unclosed_byline
            byline_is_unclosed = True

        if byline_match:
            para_text_len = text_len(byline_match.group(0))
            if para_text_len <= 300:
                result = _remove_para(result, byline_match.start(), byline_match.end())
                removed_count += 1
                made_change = True
                continue  # re-evaluate from the top

        # ── Strategy C: look for credit-block paragraphs in first 1200 chars ──
        # These may come after <img> tags, title paragraphs, or after a byline removal.
        # We check both closed (<p>...</p>) and unclosed (<p>...<p>) credit blocks.
        # We scan ALL <p><strong> candidates in the work area and remove the first
        # one that passes is_credit_block_para(), skipping non-credit <p><strong> paras.
        found_credit = False
        for credit_match in re.finditer(r'<p>\s*(?:<br[^>]*>\s*)?<strong>', work, re.IGNORECASE):
            # Try to find the full paragraph (closed or unclosed)
            full_closed = re.search(
                r'<p>\s*(?:<br[^>]*>\s*)?<strong>.*?</p>',
                work[credit_match.start():],
                re.DOTALL
            )
            full_unclosed = re.search(
                r'<p>\s*(?:<br[^>]*>\s*)?<strong>(?:[^<]|<(?!/?p>))*?(?=<p>)',
                work[credit_match.start():],
                re.DOTALL
            )
            # Pick whichever ends first (shorter paragraph)
            full_para = None
            if full_closed and full_unclosed:
                if full_unclosed.end() < full_closed.end():
                    full_para = full_unclosed
                else:
                    full_para = full_closed
            elif full_closed:
                full_para = full_closed
            elif full_unclosed:
                full_para = full_unclosed

            if full_para and is_credit_block_para(full_para.group(0)):
                abs_start = credit_match.start()
                abs_end = abs_start + full_para.end()
                result = _remove_para(result, abs_start, abs_end)
                removed_count += 1
                made_change = True
                found_credit = True
                break  # restart the outer loop to re-evaluate

        if found_credit:
            continue

        # ── Strategy D: look for a plain deck-head after removed content ──
        # Only if we already removed at least something (removed_count > 0)
        # and the body still starts with (or near the start has) a short plain para.
        if removed_count > 0:
            # Find first plain <p>...</p> near the start
            first_para = re.search(r'<p>(.*?)</p>', work, re.DOTALL)
            if first_para:
                para_html = first_para.group(0)
                if is_standalone_subtitle(para_html):
                    result = _remove_para(result, first_para.start(), first_para.end())
                    removed_count += 1
                    made_change = True
                    continue

        if not made_change:
            break

    # ── Final cleanup: remove empty <p> tags at body start ─────────────────────
    # When an unclosed byline (<p>byline<p><p>nextpara) is removed, one or more
    # dangling empty paragraphs may remain at the start.
    # Remove all consecutive leading empty <p> tags (whitespace-only content).
    if removed_count > 0:
        while True:
            stripped_result = result.lstrip()
            empty_p = re.match(r'<p>\s*(?=<p>)', stripped_result)
            if not empty_p:
                break
            leading_ws = result[:len(result) - len(stripped_result)]
            result = leading_ws + stripped_result[empty_p.end()]
            result = leading_ws + stripped_result[empty_p.end():]

    return result, removed_count


# ─────────────────────────────────────────────────────────────────────────────
# Per-file processing
# ─────────────────────────────────────────────────────────────────────────────

def process_file(filepath):
    """
    Returns (bold_fixed: bool, bylines_removed: int, error: str|None).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception as exc:
        return False, 0, f"read error: {exc}"

    m = ARTICLE_BODY_RE.search(content)
    if not m:
        return False, 0, None  # no article body — skip

    body_open_tag = m.group(1)
    body = m.group(2)
    body_close_prefix = m.group(3)

    original_body = body

    # Fix 2 first (byline removal), then Fix 1 (bold stripping on what is now the
    # true first paragraph).
    body, bylines_removed = fix2_byline(body)
    body, bold_fixed = fix1_whole_bold(body)

    if body == original_body:
        return False, 0, None

    new_content = (
        content[:m.start()]
        + body_open_tag
        + body
        + body_close_prefix
        + content[m.end():]
    )

    try:
        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
    except Exception as exc:
        return False, 0, f"write error: {exc}"

    return bold_fixed, bylines_removed, None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    files_checked = 0
    bold_fixes = 0
    byline_fixes = 0
    errors = []

    all_files = []
    for year in YEARS:
        year_dir = os.path.join(BASE_DIR, str(year))
        all_files += glob.glob(os.path.join(year_dir, 'r*.html'))
        all_files += glob.glob(os.path.join(year_dir, 'f*.html'))
    all_files.sort()

    total = len(all_files)
    print(f"Processing {total} files across years {YEARS[0]}–{YEARS[-1]}...")

    for filepath in all_files:
        files_checked += 1
        bold_fixed, byline_count, error = process_file(filepath)

        if error:
            errors.append(f"{filepath}: {error}")
            print(f"  ERROR: {filepath}: {error}", file=sys.stderr)
            continue

        if bold_fixed:
            bold_fixes += 1
        if byline_count > 0:
            byline_fixes += byline_count

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Files checked:        {files_checked}")
    print(f"  Bold fixes applied:   {bold_fixes}")
    print(f"  Byline paras removed: {byline_fixes}")
    print(f"  Errors:               {len(errors)}")
    if errors:
        print()
        print("Errors:")
        for e in errors:
            print(f"  {e}")
    print("=" * 60)


if __name__ == '__main__':
    main()
