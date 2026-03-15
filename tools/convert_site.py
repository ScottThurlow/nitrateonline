#!/usr/bin/env python3
"""
tools/convert_site.py
Convert nitrateonline.com review/feature pages from FrontPage HTML to new design.

Steps:
  1. Build year map for root r*/f* files
  2. Git mv root files to 1996/1997/1998 year directories
  3. Convert ALL year-folder HTML files (1996-2004) to new design template

Usage:
  python3 tools/convert_site.py              # full run
  python3 tools/convert_site.py --dry-run    # show year map, skip file ops
  python3 tools/convert_site.py --skip-mv    # skip git mv, just convert
  python3 tools/convert_site.py --file PATH  # convert one file only
"""

import os, re, sys, html as html_mod, subprocess
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']

FONTS_URL = (
    'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;'
    '0,700;0,900;1,400;1,700&family=Raleway:wght@300;400;500;600;700&family='
    'Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&display=swap'
)

# Nav images / store images to skip entirely
SKIP_SRCS = {'images/review.gif', 'images/feature.gif', 'images/imdb.gif',
             'images/storeimg.gif', 'images/nitlogo.gif', 'images/logo.gif',
             'images/button.gif', '../images/review.gif', '../images/feature.gif',
             '../images/imdb.gif'}

# ─────────────────────────────────────────────────────────────────
# YEAR MAPPING
# ─────────────────────────────────────────────────────────────────

def get_year(filepath: Path) -> str:
    """Determine 1996/1997/1998 year for a root-level r*/f* file."""
    name = filepath.stem
    try:
        content = filepath.read_text(errors='replace')
    except Exception:
        content = ''

    # 1. 4-digit year in filename
    m = re.search(r'(1996|1997|1998)', name)
    if m:
        return m.group(1)

    # 2. 2-digit suffix not inside a 4-digit year
    m = re.search(r'(?<!\d)(96|97|98)(?!\d)', name)
    if m:
        return '19' + m.group(1)

    # 3. IMDB URL year in content (cap at 1998)
    m = re.search(r'imdb\.com[^\'"<>]*?\((\d{4})\)', content)
    if m:
        yr = int(m.group(1))
        if 1996 <= yr <= 1998:
            return str(yr)

    # 4. Year in Posted date
    m = re.search(r'Posted\s+\d{1,2}\s+\w+\s+(1996|1997|1998)', content)
    if m:
        return m.group(1)

    # 5. Bare year in content
    for yr in ('1996', '1997', '1998'):
        if yr in content:
            return yr

    return '1998'


def build_root_year_map():
    """Return {Path: year_str} for all root r*/f* html files."""
    year_map = {}
    for pat in ('r*.html', 'r*.htm', 'f*.html', 'f*.htm'):
        for fp in sorted(ROOT.glob(pat)):
            year_map[fp] = get_year(fp)
    return year_map


# ─────────────────────────────────────────────────────────────────
# CONTENT EXTRACTION
# ─────────────────────────────────────────────────────────────────

def clean_ws(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def extract_meta(soup, filepath: Path) -> dict:
    """Extract title, type, reviewer, date, director, starring, screenplay."""
    is_review = filepath.name.startswith('r')
    result = dict(
        title='', article_type='Review' if is_review else 'Feature',
        reviewer='', date='', director='', starring='',
        screenplay='', description=''
    )

    # Title from <title> tag
    ttag = soup.find('title')
    if ttag:
        t = ttag.get_text(strip=True)
        t = re.sub(r'\s*[-–—]\s*Nitrate Online.*$', '', t).strip()
        result['title'] = t

    # Description from meta
    dmeta = soup.find('meta', attrs={'name': 'description'})
    if dmeta and dmeta.get('content'):
        result['description'] = dmeta['content'].strip()[:500]

    full_text = soup.get_text(' ', strip=True)

    # Reviewer — match 1-3 capitalized words, stop before "Posted"
    m = re.search(
        r'(?:Review|Feature|Book Review|Dispatch|Essay|Report|Preview)\s+by\s+'
        r'([A-Z][a-zA-Z\xe9\u2019\'-]+(?:\s+[A-Z][a-zA-Z\xe9\u2019\'-]+){0,2})'
        r'(?=\s*(?:Posted|\n|<|\Z|$))',
        full_text
    )
    if m:
        result['reviewer'] = m.group(1).strip()
    else:
        m = re.search(r'\bby\s+([A-Z][a-z]+ [A-Z][a-z]+)\b', full_text)
        if m:
            result['reviewer'] = m.group(1).strip()

    # Date
    m = re.search(r'Posted\s+(\d{1,2}\s+\w+\s+\d{4})', full_text)
    if not m:
        m = re.search(r'Posted\s+(\w+\s+\d{1,2},?\s+\d{4})', full_text)
    if m:
        result['date'] = m.group(1).strip()

    # Film credits from tables
    for td in soup.find_all('td'):
        td_text = td.get_text(' ', strip=True)
        if not result['director']:
            m = re.search(
                r'Directed\s+by\s+(.+?)(?:\s+Starring|\s+Screenplay|\s+Written|\Z)',
                td_text, re.DOTALL | re.I
            )
            if m:
                result['director'] = clean_ws(m.group(1))[:120]
        if not result['starring']:
            m = re.search(
                r'Starring\s+(.+?)(?:\s+Screenplay|\s+Written\s+by|\Z)',
                td_text, re.DOTALL | re.I
            )
            if m:
                result['starring'] = clean_ws(m.group(1))[:250]
        if not result['screenplay']:
            m = re.search(
                r'(?:Screenplay|Written)\s+by\s+(.+?)(?:\n|\Z)',
                td_text, re.I
            )
            if m:
                result['screenplay'] = clean_ws(m.group(1))[:120]

    return result


# Patterns that identify nav/boilerplate paragraphs to skip
_NAV_RE = re.compile(
    r'(Contents\s*\|.*(?:Features|Reviews|Archives))'
    r'|(Copyright.*Nitrate)'
    r'|(©.*Nitrate)'
    r'|(Nitrate Productions.*Rights Reserved)',
    re.IGNORECASE
)
_BYLINE_RE = re.compile(
    r'^(?:Review|Feature|Book Review|Dispatch|Essay|Report|Preview|feature)\s+by\s+',
    re.IGNORECASE
)
_POSTED_RE = re.compile(r'^Posted\s+\d', re.IGNORECASE)


def _is_skip(text: str) -> bool:
    if not text:
        return True
    if _NAV_RE.search(text):
        return True
    if _BYLINE_RE.match(text):
        return True
    if _POSTED_RE.match(text):
        return True
    return False


def _fix_src(src: str) -> str | None:
    """Return normalized ../images/X.jpg path, or None if should skip."""
    if not src:
        return None
    if src.startswith(('http://', 'https://', '//', 'data:')):
        return None
    # Normalise: strip leading slashes and ../
    s = src.lstrip('/')
    while s.startswith('../'):
        s = s[3:]
    if not s.startswith('images/'):
        return None
    basename = s[7:]  # strip 'images/'
    # skip nav gifs
    if basename.endswith('.gif'):
        return None
    return f'../images/{basename}'


def _node_to_html(node, depth=0) -> str:
    """Recursively convert a BS4 node to clean HTML, stripping FrontPage cruft."""
    if isinstance(node, NavigableString):
        text = str(node)
        # Fix Windows-1252 mojibake
        text = (text
                .replace('\x96', '–').replace('\x97', '—')
                .replace('\x91', '\u2018').replace('\x92', '\u2019')
                .replace('\x93', '\u201c').replace('\x94', '\u201d')
                .replace('&#150;', '–').replace('&#151;', '—')
                .replace('&#145;', '\u2018').replace('&#146;', '\u2019')
                .replace('&#147;', '\u201c').replace('&#148;', '\u201d'))
        return text

    name = node.name
    if not name:
        return ''

    # Tags to drop entirely
    if name in ('script', 'style', 'meta', 'link', 'head'):
        return ''

    # Tags to unwrap (keep children)
    if name in ('font', 'span', 'center', 'div', 'td', 'tr', 'tbody',
                'table', 'big', 'small'):
        return ''.join(_node_to_html(c, depth+1) for c in node.children)

    # Inline semantics
    if name in ('b', 'strong'):
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children).strip()
        return f'<strong>{inner}</strong>' if inner else ''
    if name in ('i', 'em'):
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children).strip()
        return f'<em>{inner}</em>' if inner else ''
    if name == 'sup':
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children)
        return f'<sup>{inner}</sup>'
    if name == 'sub':
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children)
        return f'<sub>{inner}</sub>'
    if name == 'br':
        return '<br>'
    if name == 'hr':
        return ''

    # Images
    if name == 'img':
        src = node.get('src', '')
        new_src = _fix_src(src)
        if not new_src:
            return ''
        alt = html_mod.escape(node.get('alt', ''))
        # Preserve float alignment
        align = node.get('align', '')
        style_parts = []
        if align == 'right':
            style_parts.append('float:right;margin:0 0 1rem 1.5rem;')
        elif align == 'left':
            style_parts.append('float:left;margin:0 1.5rem 1rem 0;')
        style = f' style="{style_parts[0]}"' if style_parts else ''
        return f'<img src="{new_src}" alt="{alt}"{style}>'

    # Anchors — keep internal links, skip nav/store targets
    if name == 'a':
        href = node.get('href', '')
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children)
        # Skip store/subscribe/asp links in body text
        if re.search(r'(store|storeitm|subscribe|default\.htm|\.asp)', href, re.I):
            return inner  # unwrap, keep text
        if href and inner:
            href_e = html_mod.escape(href)
            return f'<a href="{href_e}">{inner}</a>'
        return inner

    # Block elements we want to keep
    if name == 'p':
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children)
        inner = inner.strip()
        return f'<p>{inner}</p>' if inner else ''

    if name in ('h2', 'h3', 'h4'):
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children).strip()
        return f'<h2>{inner}</h2>' if inner else ''

    if name == 'blockquote':
        inner = ''.join(_node_to_html(c, depth+1) for c in node.children).strip()
        return f'<blockquote class="pull-quote"><p>{inner}</p></blockquote>' if inner else ''

    if name == 'ul':
        items = ''
        for li in node.find_all('li', recursive=False):
            li_inner = ''.join(_node_to_html(c, depth+1) for c in li.children).strip()
            items += f'<li>{li_inner}</li>\n'
        return f'<ul>{items}</ul>' if items else ''

    if name == 'ol':
        items = ''
        for li in node.find_all('li', recursive=False):
            li_inner = ''.join(_node_to_html(c, depth+1) for c in li.children).strip()
            items += f'<li>{li_inner}</li>\n'
        return f'<ol>{items}</ol>' if items else ''

    # Anything else: just recurse into children
    return ''.join(_node_to_html(c, depth+1) for c in node.children)


def extract_body(soup) -> str:
    """
    Extract article body HTML, skipping all nav/metadata boilerplate.
    Returns a clean HTML string ready to embed in <article class="article-body">.
    """
    body_tag = soup.find('body') or soup

    # Collect all <p>, <h2>, <h3>, <blockquote>, <ul>, <ol> NOT inside <table>
    elements = []
    for tag in body_tag.find_all(['p', 'h2', 'h3', 'h4', 'blockquote', 'ul', 'ol']):
        if tag.find_parent('table'):
            continue
        text = tag.get_text(' ', strip=True)

        # Skip navigation / boilerplate
        if _is_skip(text):
            continue

        # Skip title paragraph (big font, short text) — usually first visible <p>
        big = tag.find('font', attrs={'size': lambda x: x and str(x) in ('5', '6', '7')})
        if big and len(text) < 80 and not tag.find('img'):
            continue

        # Skip very short paragraphs that are just whitespace or punctuation
        if len(text) < 15 and not tag.find('img'):
            continue

        elements.append(tag)

    # Build output
    parts = []
    for elem in elements:
        h = _node_to_html(elem)
        h = h.strip()
        if h:
            parts.append(h)

    return '\n\n'.join(parts)


# ─────────────────────────────────────────────────────────────────
# HTML TEMPLATE RENDERING
# ─────────────────────────────────────────────────────────────────

MASTHEAD_TMPL = '''\
  <header class="masthead">
    <div class="masthead-inner">
      <a href="{root}index.html" class="site-logo" aria-label="Nitrate Online — Home">
        <img src="{root}logo.svg" alt="Nitrate Online" height="42">
      </a>
      <nav aria-label="Primary navigation">
        <ul class="primary-nav">
          <li><a href="{root}index.html">Home</a></li>
          <li><a href="{root}archive.html" class="active">Reviews</a></li>
          <li><a href="{root}archive.html">Features</a></li>
          <li><a href="{root}archive.html">Archive</a></li>
          <li><a href="{root}aboutus.html">About</a></li>
          <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                 class="nav-search" target="_blank" rel="noopener"
                 aria-label="Search via Bing">Search</a></li>
        </ul>
      </nav>
    </div>
  </header>'''

FOOTER_TMPL = '''\
  <footer>
    <div class="footer-inner">
      <div class="footer-top">
        <div>
          <p class="footer-wordmark">Nitrate Online</p>
          <p class="footer-tagline">In-depth film criticism and festival coverage, 1996–2004.</p>
        </div>
        <nav class="footer-nav-col" aria-label="Archive navigation">
          <h4>Archive</h4>
          <ul>
            <li><a href="{root}1999/">1999</a></li>
            <li><a href="{root}2000/">2000</a></li>
            <li><a href="{root}2001/">2001</a></li>
            <li><a href="{root}2002/">2002</a></li>
            <li><a href="{root}2003/">2003</a></li>
            <li><a href="{root}2004/">2004</a></li>
            <li><a href="{root}1998/">1998</a></li>
            <li><a href="{root}1997/">1997</a></li>
            <li><a href="{root}1996/">1996</a></li>
          </ul>
        </nav>
        <nav class="footer-nav-col" aria-label="Site navigation">
          <h4>Site</h4>
          <ul>
            <li><a href="{root}aboutus.html">About</a></li>
            <li><a href="{root}links.html">Links</a></li>
            <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                   target="_blank" rel="noopener">Search</a></li>
          </ul>
        </nav>
      </div>
      <div class="footer-bottom">
        <p class="footer-copy">
          Copyright &copy; 1996–2004
          <a href="{root}aboutus.html">Nitrate Productions, Inc.</a>
          &nbsp;·&nbsp; nitrateonline.com
        </p>
        <div class="footer-ornament">
          <div class="d-chev d-chev-l"></div>
          <span>Nitrate Online</span>
          <div class="d-chev d-chev-r"></div>
        </div>
      </div>
    </div>
  </footer>'''


def render_review_page(meta: dict, body_html: str, year: str, filename: str,
                        root: str = '../') -> str:
    """Generate full HTML for a review or feature page."""
    title_e = html_mod.escape(meta['title'])
    desc_e = html_mod.escape(meta['description'] or meta['title'])
    reviewer_e = html_mod.escape(meta['reviewer'])
    director_e = html_mod.escape(meta['director'])
    starring_e = html_mod.escape(meta['starring'])
    screenplay_e = html_mod.escape(meta['screenplay'])
    date_e = html_mod.escape(meta['date'])
    art_type = meta['article_type']

    # Breadcrumb middle link
    bc_section = 'Features' if art_type == 'Feature' else 'Reviews'

    # Archive year links for sidebar
    archive_tags = '\n'.join(
        f'            <a href="{root}{yr}/">{yr}</a>'
        for yr in ['2004','2003','2002','2001','2000','1999','1998','1997','1996']
    )

    # Film card credits
    credit_rows = ''
    if director_e:
        credit_rows += f'''
            <div class="film-credit">
              <dt class="credit-label">Director</dt>
              <dd class="credit-value">{director_e}</dd>
            </div>'''
    if starring_e:
        credit_rows += f'''
            <div class="film-credit">
              <dt class="credit-label">Starring</dt>
              <dd class="credit-value">{starring_e}</dd>
            </div>'''
    if screenplay_e:
        credit_rows += f'''
            <div class="film-credit">
              <dt class="credit-label">Screenplay</dt>
              <dd class="credit-value">{screenplay_e}</dd>
            </div>'''

    # Eyebrow text
    eyebrow_parts = [art_type]
    if year:
        eyebrow_parts.append(year)
    eyebrow = ' &nbsp;·&nbsp; '.join(eyebrow_parts)

    # Reviewer meta line
    meta_parts = []
    if reviewer_e:
        meta_parts.append(f'<span class="meta-byline">{art_type} by {reviewer_e}</span>')
    if date_e:
        meta_parts.append(f'<span>Published {date_e}</span>')

    meta_html = ''
    if meta_parts:
        meta_html = '<div class="article-meta">'
        meta_html += ('<span class="meta-sep" aria-hidden="true">◆</span>'.join(meta_parts))
        meta_html += '</div>'

    # Subtitle (director)
    subtitle_html = ''
    if director_e:
        subtitle_html = f'<p class="article-subtitle">Directed by {director_e}</p>'

    # Film card - use placeholder poster
    film_card_html = f'''\
      <div class="film-card">
        <div class="film-card-poster">
          <div class="film-card-poster-placeholder">▶</div>
        </div>
        <div class="film-card-body">
          <h2 class="film-card-title"><em>{title_e}</em> ({year})</h2>
          <dl class="film-credits">{credit_rows}
          </dl>
        </div>
      </div>'''

    masthead = MASTHEAD_TMPL.format(root=root)
    footer = FOOTER_TMPL.format(root=root)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_e} — Nitrate Online</title>
  <meta name="description" content="{desc_e}">
  <link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONTS_URL}" rel="stylesheet">
  <link rel="stylesheet" href="{root}nitrate.css">
</head>
<body>

{masthead}

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <div class="breadcrumb-inner">
      <a href="{root}index.html">Home</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <a href="{root}archive.html">{bc_section}</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <span aria-current="page">{title_e}</span>
    </div>
  </nav>

  <div class="article-header">
    <div class="article-header-inner">
      <p class="article-eyebrow">{eyebrow}</p>
      <h1 class="article-title"><em>{title_e}</em></h1>
      {subtitle_html}
      {meta_html}
    </div>
  </div>

  <div class="article-layout">

    <article class="article-body" aria-label="{art_type}">
{body_html}

      <div class="article-footer">
        <div class="article-footer-rule">
          <div class="footer-rule-line"></div>
          <div class="footer-diamond"></div>
          <div class="footer-rule-line"></div>
        </div>
        <div class="article-footer-meta">
          <p>{art_type} by {reviewer_e} &nbsp;·&nbsp; Nitrate Online</p>
        </div>
      </div>
    </article>

    <aside class="article-sidebar" aria-label="Film information and navigation">

{film_card_html}

      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Archive</h3></div>
        <div class="widget-body">
          <div class="archive-tags">
{archive_tags}
          </div>
        </div>
      </div>

      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Search</h3></div>
        <div class="widget-body">
          <form class="search-form" aria-label="Site search">
            <input class="search-input" type="text" placeholder="Film or director…" aria-label="Search">
            <button class="search-btn" type="submit">Go</button>
          </form>
        </div>
      </div>

    </aside>
  </div>

{footer}

  <script src="{root}nitrate.js"></script>
</body>
</html>
'''


# ─────────────────────────────────────────────────────────────────
# FILE CONVERSION
# ─────────────────────────────────────────────────────────────────

def convert_file(filepath: Path, year: str, dry_run: bool = False) -> bool:
    """Parse old FrontPage HTML and write new design HTML in-place."""
    try:
        raw = filepath.read_bytes()
        # Try UTF-8, fall back to latin-1 (FrontPage was often Windows-1252)
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('latin-1')

        soup = BeautifulSoup(text, 'lxml')

        meta = extract_meta(soup, filepath)
        body = extract_body(soup)

        if not meta['title']:
            print(f'  [WARN] no title: {filepath.name}')

        new_html = render_review_page(meta, body, year, filepath.name)

        if not dry_run:
            filepath.write_text(new_html, encoding='utf-8')
        return True

    except Exception as exc:
        print(f'  [ERROR] {filepath}: {exc}')
        return False


# ─────────────────────────────────────────────────────────────────
# GIT MV
# ─────────────────────────────────────────────────────────────────

def git_mv(src: Path, dst: Path, dry_run: bool = False) -> bool:
    if dry_run:
        print(f'  [DRY] git mv {src.name} → {dst}')
        return True
    try:
        result = subprocess.run(
            ['git', 'mv', str(src), str(dst)],
            cwd=str(ROOT), capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f'  [ERROR] git mv {src.name}: {result.stderr.strip()}')
            return False
        return True
    except Exception as exc:
        print(f'  [ERROR] git mv: {exc}')
        return False


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    dry_run = '--dry-run' in sys.argv
    skip_mv = '--skip-mv' in sys.argv
    single_file = None
    if '--file' in sys.argv:
        idx = sys.argv.index('--file')
        if idx + 1 < len(sys.argv):
            single_file = Path(sys.argv[idx + 1])

    if single_file:
        # Convert just one file (must already be in a year folder)
        year = single_file.parent.name
        if year not in YEAR_DIRS:
            year = '1998'
        print(f'Converting single file: {single_file} (year={year})')
        ok = convert_file(single_file, year, dry_run)
        print('Done.' if ok else 'Failed.')
        return

    # ── Step 1: Build year map for root r*/f* files ──
    print('Building year map...')
    year_map = build_root_year_map()

    counts = {}
    for fp, yr in year_map.items():
        counts[yr] = counts.get(yr, 0) + 1

    print(f'  Root files to move: {len(year_map)}')
    for yr in sorted(counts):
        print(f'    {yr}: {counts[yr]} files')

    if dry_run:
        print('\n[DRY RUN] Showing first 10 mappings:')
        for i, (fp, yr) in enumerate(list(year_map.items())[:10]):
            print(f'  {fp.name} → {yr}/')
        print('Exiting dry run.')
        return

    # ── Step 2: Create year directories ──
    for yr in ('1996', '1997', '1998'):
        yr_dir = ROOT / yr
        yr_dir.mkdir(exist_ok=True)
        # Create a minimal index placeholder if none exists
        idx_file = yr_dir / 'index.html'
        if not idx_file.exists():
            idx_file.write_text(
                f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
                f'<title>{yr} Archive — Nitrate Online</title></head>'
                f'<body><p>Archive {yr}</p></body></html>\n',
                encoding='utf-8'
            )

    # ── Step 3: Git mv root files to year folders ──
    if not skip_mv:
        print('\nMoving root files to year folders...')
        moved = 0
        for fp, yr in year_map.items():
            dst = ROOT / yr / fp.name
            if dst.exists():
                print(f'  [SKIP] already exists: {yr}/{fp.name}')
                continue
            if git_mv(fp, dst):
                moved += 1
        print(f'  Moved {moved} files.')
    else:
        print('\nSkipping git mv (--skip-mv).')

    # ── Step 4: Convert all year-folder HTML files ──
    print('\nConverting year-folder HTML files...')
    total = ok_count = 0

    for yr in YEAR_DIRS:
        yr_dir = ROOT / yr
        if not yr_dir.is_dir():
            continue
        files = sorted(
            fp for fp in yr_dir.glob('*.html')
            if fp.name not in ('index.html',)
        )
        # Also .htm files
        files += sorted(yr_dir.glob('*.htm'))

        print(f'  {yr}/: {len(files)} files')
        for fp in files:
            total += 1
            if convert_file(fp, yr, dry_run):
                ok_count += 1

    print(f'\nConverted {ok_count}/{total} files.')
    print('Done.')


if __name__ == '__main__':
    main()
