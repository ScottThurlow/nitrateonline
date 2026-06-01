#!/usr/bin/env python3
"""
Revert pages with wrong TMDB matches back to basic film cards.
Removes wrong credits, posters, ratings, and links.
"""

import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
IMAGES_DIR = os.path.join(ROOT, 'images')

# Wrong TMDB matches identified by audit
BAD_CODES = {
    'r247', 'r5senses', 'radored', 'ragitator', 'ramistad', 'rapower', 'ratl',
    'rautumntale', 'rbdj', 'rbeautiful', 'rbeyondmat', 'rbiggie', 'rbrothers',
    'rcasino', 'rchaos', 'rcircle', 'rcompanyman', 'rcontact', 'rcorpses',
    'rdeath', 'rdiabol', 'rdiamonds', 'rdish', 'rdominoes', 'redge', 'relling',
    'remcowboy', 'renigma', 'reye', 'rfight', 'rfighter', 'rgift', 'rgodzilla2K',
    'rgreendr', 'rguru', 'rguys', 'rhappytimes', 'rheadon', 'rheart', 'rheat',
    'rhide', 'rhorse', 'rhours', 'rhumanite', 'riamsam', 'rimpostor', 'rinlaws',
    'rjackpot', 'rjustonetime', 'rkids', 'rlapromesse', 'rlastnight',
    'rlastorders', 'rleaving', 'rmadamesata', 'rmadcity', 'rmade', 'rman',
    'rmax', 'rmissing', 'rmood', 'rnaked', 'rphoto', 'rpokemon2k', 'rprincess',
    'rrain', 'rresort', 'rresort2', 'rrespiro', 'rrunningfree', 'rshowgrl',
    'rsister', 'rsummer', 'rswingers', 'rturidi', 'rvisit', 'rworld', 'rx2',
}


def extract_page_title(content):
    m = re.search(r'<meta property="og:title" content="([^"]*)"', content)
    return m.group(1).strip() if m else ''


def extract_page_year(filepath):
    m = re.search(r'/(\d{4})/', filepath)
    return m.group(1) if m else ''


def extract_film_card(content):
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
                return content[start:i+6], start, i+6
            i += 6
        else:
            i += 1
    return None, None, None


def build_basic_card(title, year):
    """Build a basic film card with just title, no wrong data."""
    escaped = html.escape(title)
    year_display = f' ({year})' if year else ''
    return (
        f'      <div class="film-card">\n'
        f'        <div class="film-card-poster">\n'
        f'          <div class="film-card-poster-placeholder">\n'
        f'            <img src="/favicon.svg" alt="" aria-hidden="true">\n'
        f'          </div>\n'
        f'        </div>\n'
        f'        <div class="film-card-body">\n'
        f'          <h2 class="film-card-title"><em>{escaped}</em>{year_display}</h2>\n'
        f'          <dl class="film-credits">\n'
        f'          </dl>\n'
        f'        </div>\n'
        f'      </div>')


def remove_inserted_image(content, code):
    """Remove the scene image that was incorrectly inserted into the body."""
    # The enrich script inserts: <img src="/images/{code}-poster.jpg"... after first </p>
    # Also may have inserted old image with "Scene from" alt text
    # Remove any img with the wrong poster
    content = re.sub(
        rf'\n*<img[^>]*src="/images/{re.escape(code)}-poster\.jpg"[^>]*>\n*',
        '\n', content)
    return content


def revert_og_image(content, code):
    """Revert OG image from wrong poster back to default or original."""
    # Check if there's an original -1.jpg
    if os.path.exists(os.path.join(IMAGES_DIR, f'{code}-1.jpg')):
        new_img = f'https://nitrateonline.com/images/{code}-1.jpg'
    else:
        new_img = 'https://nitrateonline.com/images/og-default.png'
    content = re.sub(
        r'<meta property="og:image" content="[^"]*">',
        f'<meta property="og:image" content="{new_img}">',
        content)
    return content


def remove_wrong_poster_file(code):
    """Remove the wrong poster image file."""
    poster = os.path.join(IMAGES_DIR, f'{code}-poster.jpg')
    if os.path.exists(poster):
        os.remove(poster)
        return True
    return False


def main():
    dry_run = '--dry-run' in sys.argv

    fixed = 0
    posters_removed = 0

    for code in sorted(BAD_CODES):
        # Find the HTML file
        matches = glob.glob(os.path.join(ROOT, f'*/{code}.html'))
        if not matches:
            print(f"  {code}: file not found, skipping")
            continue

        filepath = matches[0]
        relpath = os.path.relpath(filepath, ROOT)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        title = extract_page_title(content)
        year = extract_page_year(filepath)

        old_card, start, end = extract_film_card(content)
        if old_card is None:
            print(f"  {code}: no film card found, skipping")
            continue

        # Build basic card
        new_card = build_basic_card(title, year)

        # Replace card
        new_content = content[:start] + new_card + content[end:]

        # Revert OG image
        new_content = revert_og_image(new_content, code)

        # Remove any wrongly inserted body image
        new_content = remove_inserted_image(new_content, code)

        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)

            # Remove wrong poster file
            if remove_wrong_poster_file(code):
                posters_removed += 1

        print(f"  {relpath}: reverted ({title})")
        fixed += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fixed: {fixed}, Posters removed: {posters_removed}")


if __name__ == '__main__':
    main()
