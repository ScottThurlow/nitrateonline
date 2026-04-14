#!/usr/bin/env python3
"""
tools/fix_film_cards.py
Fix film cards that were matched to the wrong TMDB entry.

For each entry in FIXES, searches TMDB for the correct film, fetches metadata
and credits, and replaces the film card in the HTML page.

Usage:
  python3 tools/fix_film_cards.py --dry-run
  python3 tools/fix_film_cards.py
"""

import html as htmlmod
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent.parent
DRY_RUN = '--dry-run' in sys.argv
TMDB_API_KEY = 'c8e59cc33b2d165da0088537431aa66e'

# ─────────────────────────────────────────────────────────────────
# PAGES TO FIX: (file_path, search_title, release_year_hint)
# release_year_hint helps disambiguate; use None if unsure
# ─────────────────────────────────────────────────────────────────
FIXES = [
    # 1997
    ('1997/rhorse.html', 'Year of the Horse', 1997),
    ('1997/rscarlet.html', 'The Scarlet Letter', 1995),
    # 1998
    ('1998/renemy.html', 'Enemy of the State', 1998),
    ('1998/rgwtw.html', 'Gone with the Wind', 1939),
    ('1998/rwrong.html', 'Wrongfully Accused', 1998),
    # 1999
    ('1999/fbestman.html', 'The Best Man', 1999),
    ('1999/ranalyze.html', 'Analyze This', 1999),
    ('1999/rbones.html', 'The Bone Collector', 1999),
    ('1999/rcradle.html', 'Cradle Will Rock', 1999),
    ('1999/rdead.html', 'Bringing Out the Dead', 1999),
    ('1999/rdeepend.html', 'The Deep End of the Ocean', 1999),
    ('1999/rrunaway.html', 'Runaway Bride', 1999),
    ('1999/rsunday.html', 'Any Given Sunday', 1999),
    # 2000
    ('2000/fmansfield.html', 'Mansfield Park', 1999),
    ('2000/ralice.html', 'Alice and Martin', 1998),
    ('2000/rcharlie.html', "Charlie's Angels", 2000),
    ('2000/rdancer.html', 'Dancer in the Dark', 2000),
    ('2000/rdeath.html', 'Mr. Death: The Rise and Fall of Fred A. Leuchter, Jr.', 1999),
    ('2000/rfriday.html', 'Next Friday', 2000),
    ('2000/rgirl.html', 'Girl on the Bridge', 1999),
    ('2000/rhuman.html', 'Human Traffic', 1999),
    ('2000/rmars.html', 'Mission to Mars', 2000),
    ('2000/rme.html', 'Me Myself I', 1999),
    ('2000/rwaking.html', 'Waking the Dead', 2000),
    ('2000/rwomen.html', 'What Women Want', 2000),
    # 2001
    ('2001/fdish.html', 'The Dish', 2000),
    ('2001/fharry.html', 'With a Friend Like Harry', 2000),
    ('2001/ranimal.html', 'The Animal', 2001),
    ('2001/rcold.html', 'Out Cold', 2001),
    ('2001/rfast.html', 'The Fast and the Furious', 2001),
    ('2001/rglass.html', 'The Glass House', 2001),
    ('2001/rking.html', 'The King Is Alive', 2000),
    ('2001/rpearl.html', 'Pearl Harbor', 2001),
    ('2001/rresort.html', 'Last Resort', 2000),
    ('2001/rresort2.html', 'Last Resort', 2000),
    ('2001/rsand.html', 'Under the Sand', 2000),
    ('2001/rsugar.html', 'Sugar & Spice', 2001),
    ('2001/rtime.html', 'Time and Tide', 2000),
    ('2001/rwedding.html', 'The Wedding Planner', 2001),
    # 2002
    ('2002/fagitator.html', 'Agitator', 2001),
    ('2002/rfriday.html', 'Friday After Next', 2002),
    ('2002/rhollywood.html', 'Hollywood Ending', 2002),
    ('2002/rleaving.html', 'Partir, revenir', 1985),
    ('2002/rliberty.html', 'Liberty Stands Still', 2002),
    ('2002/rphoto.html', 'War Photographer', 2001),
    ('2002/rsunshine.html', 'Sunshine State', 2002),
    ('2002/rtime.html', 'The Time Machine', 2002),
    # 2003
    ('2003/r13.html', 'Thirteen', 2003),
    ('2003/reye.html', 'The Eye', 2002),
    ('2003/rheart.html', 'The Heart of Me', 2002),
    ('2003/rman.html', 'Man on the Train', 2002),
    # 2003/rproof.html — "The Naked Proof" not on TMDB, skip
    # 2003/fdevil.html — "Devil Talk" short film, not on TMDB, skip
    # 2003/rdominoes.html — indie Seattle film "Dominoes" by Cole Drumb, not on TMDB, skip
    ('2003/rworld.html', 'In This World', 2002),
    # 2004
    ('2004/rbaby.html', "My Baby's Daddy", 2004),
    # 2004/rfight.html — "Fight Circle" ultra-low-budget online film, not on TMDB, skip
]


# ─────────────────────────────────────────────────────────────────
# TMDB API
# ─────────────────────────────────────────────────────────────────

def tmdb_search(title, year=None):
    """Search TMDB for a movie by title and optional year."""
    params = {'api_key': TMDB_API_KEY, 'query': title}
    if year:
        params['year'] = year
    url = 'https://api.themoviedb.org/3/search/movie?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            if data.get('results'):
                return data['results'][0]
    except Exception as e:
        print(f'  [ERROR] TMDB search for "{title}": {e}')
    return None


def tmdb_details(movie_id):
    """Fetch full movie details including credits."""
    url = f'https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits'
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f'  [ERROR] TMDB details for {movie_id}: {e}')
    return None


# ─────────────────────────────────────────────────────────────────
# FILM CARD BUILDING
# ─────────────────────────────────────────────────────────────────

def build_credit_html(label, value):
    escaped = htmlmod.escape(value)
    return (f'            <div class="film-credit">\n'
            f'              <dt class="credit-label">{label}</dt>\n'
            f'              <dd class="credit-value">{escaped}</dd>\n'
            f'            </div>')


def build_film_card(details, existing_poster_src=None):
    """Build the film-card HTML from TMDB details."""
    title = htmlmod.escape(details.get('title', ''))
    year = details.get('release_date', '')[:4] if details.get('release_date') else ''

    # Poster
    if existing_poster_src:
        poster_html = (
            f'        <div class="film-card-poster">\n'
            f'          <img loading="lazy" src="{existing_poster_src}" alt="{title} poster" '
            f'style="width:100%;display:block;">\n'
            f'        </div>')
    else:
        poster_html = (
            f'        <div class="film-card-poster">\n'
            f'          <div class="film-card-poster-placeholder">\n'
            f'            <img src="/favicon.svg" alt="" aria-hidden="true">\n'
            f'          </div>\n'
            f'        </div>')

    # Credits
    credits = []
    creds = details.get('credits', {})

    # Director
    directors = [c['name'] for c in creds.get('crew', []) if c.get('job') == 'Director']
    if directors:
        credits.append(build_credit_html('Director', ', '.join(directors[:3])))

    # Writers
    writers = [c['name'] for c in creds.get('crew', [])
               if c.get('department') == 'Writing']
    if writers:
        seen = []
        for w in writers:
            if w not in seen:
                seen.append(w)
        credits.append(build_credit_html('Writer' + ('s' if len(seen) > 1 else ''),
                                         ', '.join(seen[:4])))

    # Cast
    cast = creds.get('cast', [])[:6]
    if cast:
        credits.append(build_credit_html('Starring', ', '.join(c['name'] for c in cast)))

    # Studio
    studios = details.get('production_companies', [])[:3]
    if studios:
        credits.append(build_credit_html('Studio', ' / '.join(s['name'] for s in studios)))

    # Runtime
    runtime = details.get('runtime')
    if runtime:
        credits.append(build_credit_html('Runtime', f'{runtime} min'))

    # Genre
    genres = [g['name'] for g in details.get('genres', [])][:4]
    if genres:
        credits.append(build_credit_html('Genre', ', '.join(genres)))

    credits_html = '\n'.join(credits)

    # External links
    links = []
    imdb_id = details.get('imdb_id', '')
    tmdb_id = details.get('id', '')
    if imdb_id:
        links.append(
            f'            <a href="https://www.imdb.com/title/{imdb_id}/" '
            f'class="film-link" rel="noopener" target="_blank">IMDB (Full Credits)</a>')
    if tmdb_id:
        links.append(
            f'            <a href="https://www.themoviedb.org/movie/{tmdb_id}" '
            f'class="film-link" rel="noopener" target="_blank">TMDB</a>')

    links_html = ''
    if links:
        links_html = (
            f'          <div class="film-card-links">\n'
            + '\n'.join(links) + '\n'
            f'          </div>')

    year_display = f' ({year})' if year else ''
    card = (
        f'      <div class="film-card">\n'
        f'{poster_html}\n'
        f'        <div class="film-card-body">\n'
        f'          <h2 class="film-card-title"><em>{title}</em>{year_display}</h2>\n'
        f'          <dl class="film-credits">\n'
        f'{credits_html}\n'
        f'          </dl>\n'
        f'{links_html}\n'
        f'        </div>\n'
        f'      </div>')

    return card


# ─────────────────────────────────────────────────────────────────
# FILM CARD REPLACEMENT
# ─────────────────────────────────────────────────────────────────

def extract_film_card(content):
    """Extract the full film-card div from content."""
    start = content.find('<div class="film-card">')
    if start == -1:
        return None, None, None
    depth = 0
    i = start
    while i < len(content):
        if content[i:i+4] == '<div':
            depth += 1
            i += 4
        elif content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                end = i + 6
                return content[start:end], start, end
            i += 6
        else:
            i += 1
    return None, None, None


def extract_existing_poster(content):
    """Get the existing poster src if any."""
    m = re.search(r'<div class="film-card-poster">\s*<img[^>]+src="([^"]+)"', content, re.DOTALL)
    if m:
        return m.group(1)
    return None


def update_schema(content, details):
    """Update JSON-LD Movie schema if present."""
    year = details.get('release_date', '')[:4] if details.get('release_date') else ''
    title = details.get('title', '')
    imdb_id = details.get('imdb_id', '')

    creds = details.get('credits', {})
    directors = [c['name'] for c in creds.get('crew', []) if c.get('job') == 'Director']
    cast = [c['name'] for c in creds.get('cast', [])[:6]]

    # Try to find and replace Movie schema
    movie_pattern = re.compile(
        r'(\{[^}]*"@type"\s*:\s*"Movie"[^}]*\})',
        re.DOTALL
    )

    def replace_movie(m):
        try:
            old = json.loads(m.group(1))
        except json.JSONDecodeError:
            return m.group(0)

        old['name'] = title
        if year:
            old['dateCreated'] = year
        if directors:
            old['director'] = [{'@type': 'Person', 'name': d} for d in directors]
        if cast:
            old['actor'] = [{'@type': 'Person', 'name': c} for c in cast]
        if imdb_id:
            old['sameAs'] = f'https://www.imdb.com/title/{imdb_id}/'
        return json.dumps(old, ensure_ascii=False)

    content = movie_pattern.sub(replace_movie, content)
    return content


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    fixed = 0
    failed = 0

    for rel_path, search_title, year_hint in FIXES:
        filepath = ROOT / rel_path
        if not filepath.exists():
            print(f'  [SKIP] {rel_path} — file not found')
            continue

        print(f'  {rel_path}: searching for "{search_title}" ({year_hint or "any year"})...')

        # Search TMDB
        result = tmdb_search(search_title, year_hint)
        if not result:
            # Try without year
            if year_hint:
                result = tmdb_search(search_title)
            if not result:
                print(f'    [FAIL] No TMDB result')
                failed += 1
                continue

        movie_id = result['id']
        found_title = result.get('title', '?')
        found_year = result.get('release_date', '')[:4]
        print(f'    Found: {found_title} ({found_year}) [TMDB {movie_id}]')

        # Fetch full details
        details = tmdb_details(movie_id)
        if not details:
            print(f'    [FAIL] Could not fetch details')
            failed += 1
            continue

        # Read current file
        content = filepath.read_text(encoding='utf-8', errors='replace')

        # Get existing poster
        poster_src = extract_existing_poster(content)

        # Build new card
        new_card = build_film_card(details, poster_src)

        # Replace card
        old_card, start, end = extract_film_card(content)
        if old_card is None:
            print(f'    [FAIL] No film-card found in HTML')
            failed += 1
            continue

        content = content[:start] + new_card + content[end:]

        # Update schema
        content = update_schema(content, details)

        if DRY_RUN:
            print(f'    [DRY] Would replace card')
        else:
            filepath.write_text(content, encoding='utf-8')
            print(f'    [OK] Card replaced')

        fixed += 1
        time.sleep(0.25)  # Rate limit

    print(f'\nFixed {fixed}, failed {failed}.')
    if DRY_RUN:
        print('(dry run — no files written)')


if __name__ == '__main__':
    main()
