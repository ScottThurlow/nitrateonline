#!/usr/bin/env python3
"""Corrected orphaned image check - src= references use leading slash."""
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
        all_srcs.add(s.split('?')[0])

# Normalize: strip leading slash for comparison
srcs_normalized = set()
for s in all_srcs:
    if s.startswith('/'):
        srcs_normalized.add(s.lstrip('/'))
    else:
        srcs_normalized.add(s)

# Build set of just filenames too (for fallback matching)
srcs_by_filename = set()
for s in srcs_normalized:
    srcs_by_filename.add(Path(s).name)

# Find all image files on ModernDesign
img_exts = re.compile(r'\.(jpg|jpeg|gif|png|svg|JPG|GIF|PNG)$', re.IGNORECASE)
all_images = []

# Root images dir
images_dir = ROOT / 'images'
if images_dir.exists():
    for f in images_dir.iterdir():
        if img_exts.search(f.name):
            all_images.append(f)

# Year folder images dirs
for year in range(1996, 2005):
    year_images = ROOT / str(year) / 'images'
    if year_images.exists():
        for f in year_images.iterdir():
            if img_exts.search(f.name):
                all_images.append(f)

print(f"Total image files found: {len(all_images)}")
print(f"Total normalized srcs: {len(srcs_normalized)}")

orphaned = []
referenced = []
for img_path in all_images:
    rel = str(img_path.relative_to(ROOT))  # e.g. "1999/images/foo.jpg"

    if rel in srcs_normalized:
        referenced.append(rel)
        continue
    # Filename-only fallback
    if img_path.name in srcs_by_filename:
        referenced.append(rel)
        continue

    orphaned.append(rel)

print(f"\nReferenced images: {len(referenced)}")
print(f"Orphaned images: {len(orphaned)}")

# Breakdown by directory
from collections import Counter
orphan_dirs = Counter()
for o in orphaned:
    orphan_dirs[str(Path(o).parent)] += 1

print("\nOrphaned by directory:")
for d, c in sorted(orphan_dirs.items()):
    print(f"  {d}: {c}")

# Sample of orphaned images
print("\nSample orphaned images (first 30):")
for o in sorted(orphaned)[:30]:
    print(f"  {o}")
if len(orphaned) > 30:
    print(f"  ... and {len(orphaned)-30} more")
