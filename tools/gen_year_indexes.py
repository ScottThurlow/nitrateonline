#!/usr/bin/env python3
"""
tools/gen_year_indexes.py
Generate year archive index pages (index.html) for each year folder.
Usage: python3 tools/gen_year_indexes.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
YEAR_DIRS = ['1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004']


def get_title(fp: Path) -> str:
    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return fp.stem
    # article-title h1
    m = re.search(r'<h1 class="article-title">\s*(?:<em>)?(.*?)(?:</em>)?\s*</h1>', text, re.DOTALL)
    if m:
        t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if t:
            return t
    # <title>
    m = re.search(r'<title>(.*?)</title>', text)
    if m:
        t = re.sub(r'\s*[—–-]\s*Nitrate Online.*$', '', m.group(1)).strip()
        if t:
            return t
    return fp.stem


def get_eyebrow(fp: Path) -> str:
    try:
        text = fp.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''
    m = re.search(r'<p class="article-eyebrow">(.*?)</p>', text)
    if m:
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return ''


TEMPLATE = '''\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{year} Archive — Nitrate Online</title>
  <meta name="description" content="Nitrate Online {year}: {count} reviews and features.">
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=Raleway:wght@300;400;500;600;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../nitrate.css">
</head>
<body>

  <header class="masthead">
    <div class="masthead-inner">
      <a href="../index.html" class="site-logo" aria-label="Nitrate Online — Home">
        <img src="../logo.svg" alt="Nitrate Online" height="42">
      </a>
      <nav aria-label="Primary navigation">
        <ul class="primary-nav">
          <li><a href="../index.html">Home</a></li>
          <li><a href="../archive.html" class="active">Reviews</a></li>
          <li><a href="../archive.html">Features</a></li>
          <li><a href="../archive.html">Archive</a></li>
          <li><a href="../aboutus.html">About</a></li>
          <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                 class="nav-search" target="_blank" rel="noopener"
                 aria-label="Search via Bing">Search</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <div class="breadcrumb-inner">
      <a href="../index.html">Home</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <a href="../archive.html">Archive</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <span aria-current="page">{year}</span>
    </div>
  </nav>

  <div class="article-header">
    <div class="article-header-inner">
      <p class="article-eyebrow">Archive &nbsp;·&nbsp; {year}</p>
      <h1 class="article-title">{year}</h1>
      <p class="article-subtitle">{count} reviews and features</p>
    </div>
  </div>

  <div class="archive-listing">
    <div>
{sections}
    </div>

    <aside class="archive-sidebar">
      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Search the Archive</h3></div>
        <div class="widget-body">
          <form class="search-form" aria-label="Site search">
            <input class="search-input" type="text" placeholder="Film or director…" aria-label="Search">
            <button class="search-btn" type="submit">Go</button>
          </form>
        </div>
      </div>
      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Browse by Year</h3></div>
        <div class="widget-body">
          <ul style="list-style:none;font-family:var(--font-ui);font-size:.82rem;display:flex;flex-direction:column;gap:.3rem;">
{year_links}
          </ul>
        </div>
      </div>
    </aside>
  </div>

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
            <li><a href="../2004/">2004</a></li>
            <li><a href="../2003/">2003</a></li>
            <li><a href="../2002/">2002</a></li>
            <li><a href="../2001/">2001</a></li>
            <li><a href="../2000/">2000</a></li>
            <li><a href="../1999/">1999</a></li>
            <li><a href="../1998/">1998</a></li>
            <li><a href="../1997/">1997</a></li>
            <li><a href="../1996/">1996</a></li>
          </ul>
        </nav>
        <nav class="footer-nav-col" aria-label="Site navigation">
          <h4>Site</h4>
          <ul>
            <li><a href="../aboutus.html">About</a></li>
            <li><a href="../links.html">Links</a></li>
            <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                   target="_blank" rel="noopener">Search</a></li>
          </ul>
        </nav>
      </div>
      <div class="footer-bottom">
        <p class="footer-copy">
          Copyright &copy; 1996–2004 Nitrate Productions, Inc. &nbsp;·&nbsp; nitrateonline.com
        </p>
        <div class="footer-ornament">
          <div class="d-chev d-chev-l"></div>
          <span>Nitrate Online</span>
          <div class="d-chev d-chev-r"></div>
        </div>
      </div>
    </div>
  </footer>

  <script src="../nitrate.js"></script>
</body>
</html>
'''

SECTION_TMPL = '''\
      <p class="section-tag">{tag}</p>
      <h2 class="section-title">{heading}</h2>
      <hr class="deco-rule">
      <ul style="list-style:none;display:flex;flex-direction:column;gap:.45rem;margin-bottom:2.5rem;">
{items}
      </ul>'''

ITEM_TMPL = '        <li><a href="{href}" style="font-family:var(--font-ui);font-size:.82rem;">{title}</a></li>'


def make_sections(yr: str, files) -> str:
    reviews = []
    features = []
    other = []

    for fp in sorted(files, key=lambda f: f.name.lower()):
        title = get_title(fp)
        href = fp.name
        if fp.name.startswith('r'):
            reviews.append((title, href))
        elif fp.name.startswith('f'):
            features.append((title, href))
        else:
            other.append((title, href))

    parts = []
    if features:
        items = '\n'.join(ITEM_TMPL.format(href=h, title=t) for t, h in features)
        parts.append(SECTION_TMPL.format(tag='Features', heading='Features &amp; Essays', items=items))
    if reviews:
        items = '\n'.join(ITEM_TMPL.format(href=h, title=t) for t, h in reviews)
        parts.append(SECTION_TMPL.format(tag='Reviews', heading='Film Reviews', items=items))
    if other:
        items = '\n'.join(ITEM_TMPL.format(href=h, title=t) for t, h in other)
        parts.append(SECTION_TMPL.format(tag='Other', heading='Other', items=items))
    return '\n\n'.join(parts)


def make_year_links(current_yr: str) -> str:
    lines = []
    for yr in reversed(YEAR_DIRS):
        if yr == current_yr:
            lines.append(f'            <li style="color:var(--cream);font-weight:600;">{yr} (this year)</li>')
        else:
            lines.append(f'            <li><a href="../{yr}/">{yr}</a></li>')
    return '\n'.join(lines)


for yr in YEAR_DIRS:
    yr_dir = ROOT / yr
    files = [f for f in yr_dir.iterdir()
             if f.suffix in ('.html', '.htm') and f.name != 'index.html']

    sections = make_sections(yr, files)
    year_links = make_year_links(yr)
    count = len(files)

    html = TEMPLATE.format(
        year=yr,
        count=count,
        sections=sections,
        year_links=year_links,
    )

    out = yr_dir / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'  Written: {yr}/index.html ({count} articles)')

print(f'\nDone — {len(YEAR_DIRS)} year index pages generated.')
