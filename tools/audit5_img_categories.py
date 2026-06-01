#!/usr/bin/env python3
"""Categorize the 848 orphaned images."""
import re
from pathlib import Path
from collections import Counter

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
        all_srcs.add(s.split('?')[0])

# Normalize srcs
srcs_normalized = set()
for s in all_srcs:
    srcs_normalized.add(s.lstrip('/'))

# Build filename lookup
srcs_by_filename = {Path(s).name for s in srcs_normalized}

# Find all image files
img_exts = re.compile(r'\.(jpg|jpeg|gif|png|svg|JPG|GIF|PNG)$', re.IGNORECASE)
all_images = []
images_dir = ROOT / 'images'
if images_dir.exists():
    for f in images_dir.iterdir():
        if img_exts.search(f.name):
            all_images.append(f)
for year in range(1996, 2005):
    year_images = ROOT / str(year) / 'images'
    if year_images.exists():
        for f in year_images.iterdir():
            if img_exts.search(f.name):
                all_images.append(f)

orphaned = []
for img_path in all_images:
    rel = str(img_path.relative_to(ROOT))
    if rel in srcs_normalized:
        continue
    if img_path.name in srcs_by_filename:
        continue
    orphaned.append((img_path, rel))

print(f"Orphaned images: {len(orphaned)}")

# Categorize orphaned images from root images/
root_orphaned = [(img, rel) for img, rel in orphaned if str(img.parent) == str(ROOT / 'images')]
year_orphaned = [(img, rel) for img, rel in orphaned if str(img.parent) != str(ROOT / 'images')]

print(f"\nFrom root images/: {len(root_orphaned)}")
print(f"From year images/: {len(year_orphaned)}")

# Analyze root orphaned images
print("\n--- Root images/ orphaned ---")
prefix_counts = Counter()
for img, rel in root_orphaned:
    name = img.name
    for prefix in ['fberlin', 'ftiff', 'fsiff', 'fofcs', 'fcinefest', 'foscar',
                   'f', 'r', 'store', 'nav', 'bg']:
        if name.startswith(prefix):
            prefix_counts[prefix] += 1
            break
    else:
        prefix_counts['other'] += 1

for prefix, count in sorted(prefix_counts.items(), key=lambda x: -x[1]):
    print(f"  Prefix '{prefix}...': {count} images")

# Are these old design images (gifs from old site)?
gifs = sum(1 for img, _ in root_orphaned if img.suffix.lower() == '.gif')
jpgs = sum(1 for img, _ in root_orphaned if img.suffix.lower() in ('.jpg', '.jpeg'))
print(f"\n  By extension: {gifs} GIFs, {jpgs} JPGs")

# Sample root orphaned
print("\n  Sample root orphaned images:")
for img, rel in sorted(root_orphaned, key=lambda x: x[1])[:20]:
    print(f"    {rel}")

# Year orphaned analysis
print(f"\n--- Year images/ orphaned ({len(year_orphaned)} total) ---")
year_counts = Counter()
for img, rel in year_orphaned:
    year = rel.split('/')[0]
    year_counts[year] += 1
for year, count in sorted(year_counts.items()):
    print(f"  {year}/images/: {count} orphaned")

# Sample year orphaned
print("\n  Sample year orphaned images:")
for img, rel in sorted(year_orphaned, key=lambda x: x[1])[:20]:
    print(f"    {rel}")

# Check if year images that are orphaned correspond to missing HTML pages
# e.g., 1999/images/fhitch100-1.jpg might belong to a missing page
print("\n--- Looking for corresponding HTML pages for orphaned year images ---")
pages_for_orphan_imgs = set()
for img, rel in year_orphaned:
    # Extract base name (strip year number at end)
    stem = img.stem  # e.g., 'fhitch100-1'
    # Try base: remove trailing -N
    base = re.sub(r'-\d+$', '', stem)  # e.g. 'fhitch100'
    base = re.sub(r'\d+$', '', base)   # e.g. 'fhitch'
    pages_for_orphan_imgs.add(base)

print("  Image name bases (possible missing page slugs):")
for base in sorted(pages_for_orphan_imgs):
    print(f"    {base}")
