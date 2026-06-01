#!/usr/bin/env python3
"""Verify image orphan detection logic."""
import re
from pathlib import Path

ROOT = Path('/Users/scott/Code/nitrateonline')

# Collect all src= references from all HTML files
all_srcs = set()
html_files = list(ROOT.glob('*.html')) + list(ROOT.glob('*.htm'))
for year in range(1996, 2005):
    html_files += list((ROOT / str(year)).glob('*.html'))
    html_files += list((ROOT / str(year)).glob('*.htm'))

for fpath in html_files:
    content = fpath.read_text(encoding='utf-8', errors='replace')
    srcs = re.findall(r'src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    for s in srcs:
        all_srcs.add(s)

# Sample some src references that contain 'images'
img_srcs = [s for s in all_srcs if 'images' in s.lower()]
print('Sample src references with images:')
for s in sorted(img_srcs)[:30]:
    print(f'  {s!r}')
print(f'\nTotal srcs with images: {len(img_srcs)}')
print(f'Total unique srcs: {len(all_srcs)}')

# Now check a specific image from the orphaned list
test_img = '1999/images/fhitch100-1.jpg'
fname = 'fhitch100-1.jpg'
print(f'\nLooking for {test_img} in srcs:')
print(f'  Direct path match: {test_img in all_srcs}')
print(f'  /path match: {"/" + test_img in all_srcs}')
found_by_name = [s for s in all_srcs if fname in s]
print(f'  By filename: {found_by_name}')

# Check what types of srcs are in all_srcs
print('\nSample of all srcs (first 20 non-http):')
count = 0
for s in sorted(all_srcs):
    if not s.startswith('http'):
        print(f'  {s!r}')
        count += 1
        if count >= 30:
            break
