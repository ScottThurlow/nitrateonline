#!/usr/bin/env python3
"""
tools/postprocess.py
Post-conversion fixups for nitrateonline.com:
  1. Multi-page feature cross-linking (TOC ↔ sub-pages, prev/next nav)
  2. Author name → bio page hyperlinks in article meta

Usage:
  python3 tools/postprocess.py
  python3 tools/postprocess.py --dry-run
"""

import re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']

DRY_RUN = '--dry-run' in sys.argv

# ─────────────────────────────────────────────────────────────────
# AUTHOR → BIO PAGE MAP
# (first/last name → root-relative filename, no extension)
# ─────────────────────────────────────────────────────────────────
AUTHOR_PAGES = {
    'Carrie Gorringe':  'carrie',
    'Eddie Cockrell':   'eddie',
    'Gregory Avery':    'gregory',
    'Sean Axmaker':     'sean',
    'Joe Barlow':       'joe',
    'Lyall Bush':       'lyall',
    'KJ Doughton':      'kj',
    'Emma French':      'emma',
    'Cynthia Fuchs':    'cynthia',
    'Dave Luty':        'dave',
    'Dan Lybarger':     'dan',
    'Paula Nechak':     'paula',
    'Elias Savada':     'elias',
    'Gianni Truzzi':    'gianni',
    'Jerry White':      'jerry',
}


def add_author_links(html: str) -> str:
    """
    In the article-meta section, replace 'Review/Feature by NAME' with a hyperlink.
    Only replaces inside <span class="meta-byline"> to avoid touching body text.
    """
    for name, page in AUTHOR_PAGES.items():
        # Match the byline span content: "Review by NAME" or "Feature by NAME" etc.
        # We look for the name NOT already inside an <a> tag
        pattern = re.compile(
            r'(<span class="meta-byline">[^<]*by\s+)(' + re.escape(name) + r')(</span>)',
            re.IGNORECASE
        )
        replacement = r'\1<a href="../' + page + r'.html">' + name + r'</a>\3'
        html = pattern.sub(replacement, html)

        # Also fix article-footer-meta
        footer_pat = re.compile(
            r'(' + re.escape('by') + r'\s+)(' + re.escape(name) + r')(\s+&nbsp;)',
            re.IGNORECASE
        )
        footer_repl = r'\1<a href="../' + page + r'.html">' + name + r'</a>\3'
        html = footer_pat.sub(footer_repl, html)

    return html


# ─────────────────────────────────────────────────────────────────
# MULTI-PAGE FEATURE DETECTION
# ─────────────────────────────────────────────────────────────────

def get_title_from_html(path: Path) -> str:
    """Extract the H1 article-title text from a converted HTML file."""
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'<h1 class="article-title"><em>(.*?)</em></h1>', text)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()
        m = re.search(r'<h1 class="article-title">(.*?)</h1>', text)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()
        # Fall back to <title>
        m = re.search(r'<title>(.*?)</title>', text)
        if m:
            t = m.group(1)
            t = re.sub(r'\s*—\s*Nitrate Online.*$', '', t).strip()
            return t
    except Exception:
        pass
    return path.stem


def find_feature_groups(year_dir: Path):
    """
    Find groups of multi-page features in a year directory.
    Returns list of (toc_file, [sub_file_1, sub_file_2, ...]) tuples.
    toc_file may be None if no TOC page exists.
    """
    # Collect all f*-N.html files
    sub_files = sorted(year_dir.glob('f*-[0-9].html'))
    # Also f*-[0-9][0-9].html for >9 sub-pages
    sub_files += sorted(year_dir.glob('f*-[0-9][0-9].html'))

    # Group by base name (strip trailing -N)
    groups = {}
    for sf in sub_files:
        m = re.match(r'^(f.+?)-(\d+)\.html$', sf.name)
        if m:
            base = m.group(1)
            num = int(m.group(2))
            if base not in groups:
                groups[base] = []
            groups[base].append((num, sf))

    result = []
    for base, pages in groups.items():
        pages.sort(key=lambda x: x[0])
        sub_files_sorted = [p for _, p in pages]
        toc_file = year_dir / f'{base}.html'
        toc = toc_file if toc_file.exists() else None
        result.append((base, toc, sub_files_sorted))

    return result


# ─────────────────────────────────────────────────────────────────
# MULTI-PAGE NAVIGATION INJECTION
# ─────────────────────────────────────────────────────────────────

def make_parts_nav(toc_path, sub_paths, current_path):
    """
    Build an HTML navigation block for multi-page features.
    current_path: the file being edited (to determine relative links).
    """
    # Build list of (title, relative_href) for each sub-page
    parts = []
    for sp in sub_paths:
        title = get_title_from_html(sp)
        href = sp.name  # same directory
        parts.append((title, href))

    # TOC link
    toc_href = toc_path.name if toc_path else None

    # Which part index is this? (0-indexed)
    current_name = current_path.name
    current_idx = None
    for i, sp in enumerate(sub_paths):
        if sp.name == current_name:
            current_idx = i
            break

    # Build HTML
    lines = ['<nav class="feature-parts-nav" aria-label="Feature parts" style="'
             'background:var(--dark);border:1px solid var(--gold-dim);'
             'margin-bottom:2rem;padding:1rem 1.1rem;">']
    lines.append('<p style="font-family:var(--font-ui);font-size:.56rem;'
                 'letter-spacing:.22em;text-transform:uppercase;color:var(--teal-light);'
                 'margin-bottom:.7rem;">This Feature</p>')

    if toc_href and current_name != toc_href:
        lines.append(f'<p style="margin-bottom:.6rem;font-family:var(--font-ui);'
                     f'font-size:.7rem;"><a href="{toc_href}" style="color:var(--gold);">'
                     f'← Series Overview</a></p>')

    lines.append('<ol style="list-style:decimal;margin-left:1.2rem;'
                 'font-family:var(--font-ui);font-size:.7rem;'
                 'display:flex;flex-direction:column;gap:.3rem;">')
    for i, (title, href) in enumerate(parts):
        if current_idx is not None and i == current_idx:
            lines.append(f'<li style="color:var(--cream);">{title}</li>')
        else:
            lines.append(f'<li><a href="{href}" style="color:var(--text-muted);">'
                         f'{title}</a></li>')
    lines.append('</ol>')

    # Prev / Next links
    if current_idx is not None:
        nav_links = []
        if current_idx > 0:
            prev_href = sub_paths[current_idx - 1].name
            nav_links.append(f'<a href="{prev_href}" style="color:var(--gold);">← Previous</a>')
        if current_idx < len(sub_paths) - 1:
            next_href = sub_paths[current_idx + 1].name
            nav_links.append(f'<a href="{next_href}" style="color:var(--gold);">Next →</a>')
        if nav_links:
            lines.append('<p style="margin-top:.8rem;font-family:var(--font-ui);'
                         'font-size:.7rem;display:flex;gap:1.5rem;">'
                         + ' '.join(nav_links) + '</p>')

    lines.append('</nav>')
    return '\n'.join(lines)


def make_toc_parts_list(sub_paths):
    """
    Build the sub-page index HTML to inject into a TOC page's article body.
    """
    lines = ['<nav class="feature-parts-nav" aria-label="Feature parts" style="'
             'background:var(--dark);border:1px solid var(--gold-dim);'
             'margin:1.5rem 0;padding:1rem 1.1rem;">']
    lines.append('<p style="font-family:var(--font-ui);font-size:.56rem;'
                 'letter-spacing:.22em;text-transform:uppercase;color:var(--teal-light);'
                 'margin-bottom:.7rem;">Parts</p>')
    lines.append('<ol style="list-style:decimal;margin-left:1.2rem;'
                 'font-family:var(--font-ui);font-size:.78rem;'
                 'display:flex;flex-direction:column;gap:.4rem;">')
    for sp in sub_paths:
        title = get_title_from_html(sp)
        lines.append(f'<li><a href="{sp.name}">{title}</a></li>')
    lines.append('</ol>')
    lines.append('</nav>')
    return '\n'.join(lines)


ARTICLE_BODY_OPEN = '<article class="article-body" aria-label="'


def inject_into_body_start(html: str, inject_html: str) -> str:
    """Inject HTML right after the opening <article class="article-body"> tag."""
    idx = html.find(ARTICLE_BODY_OPEN)
    if idx == -1:
        return html
    # Find end of the opening tag
    close_idx = html.index('>', idx) + 1
    return html[:close_idx] + '\n' + inject_html + '\n' + html[close_idx:]


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    total_files = 0
    modified_files = 0

    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue

        # Gather all HTML files to process for author links
        html_files = list(yr_dir.glob('*.html')) + list(yr_dir.glob('*.htm'))

        # Find multi-page feature groups
        groups = find_feature_groups(yr_dir)

        # Build set of files that are TOC or sub-pages
        toc_files = set()
        sub_file_map = {}  # sub_path → (base, toc_path, all_sub_paths)

        for base, toc, subs in groups:
            if toc:
                toc_files.add(toc)
            for sp in subs:
                sub_file_map[sp] = (base, toc, subs)

        # Process each HTML file
        for fp in sorted(html_files):
            if fp.name == 'index.html':
                continue

            try:
                original = fp.read_text(encoding='utf-8', errors='replace')
            except Exception as e:
                print(f'  [ERROR] read {fp}: {e}')
                continue

            modified = original

            # 1. Author bio links
            modified = add_author_links(modified)

            # 2. Multi-page navigation
            if fp in toc_files:
                # Find which group this TOC belongs to
                for base, toc, subs in groups:
                    if toc and toc == fp:
                        parts_html = make_toc_parts_list(subs)
                        # Only inject if not already present
                        if 'feature-parts-nav' not in modified:
                            modified = inject_into_body_start(modified, parts_html)
                        break

            elif fp in sub_file_map:
                base, toc, subs = sub_file_map[fp]
                nav_html = make_parts_nav(toc, subs, fp)
                if 'feature-parts-nav' not in modified:
                    modified = inject_into_body_start(modified, nav_html)

            total_files += 1
            if modified != original:
                modified_files += 1
                if not DRY_RUN:
                    fp.write_text(modified, encoding='utf-8')
                else:
                    print(f'  [DRY] would modify: {yr}/{fp.name}')

    print(f'\nProcessed {total_files} files, modified {modified_files}.')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
