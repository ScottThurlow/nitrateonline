#!/usr/bin/env python3
"""Deep dive into orphaned images - understand root images folder."""
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

# What is in root images/ directory?
images_dir = ROOT / 'images'
all_root_images = sorted([f for f in images_dir.iterdir() if f.is_file()])
print(f"Root images/ total files: {len(all_root_images)}")

# What types/patterns?
extensions = Counter(f.suffix.lower() for f in all_root_images)
print(f"\nExtensions in root images/:")
for ext, cnt in sorted(extensions.items(), key=lambda x: -x[1]):
    print(f"  {ext}: {cnt}")

# What prefixes do root image filenames have?
prefixes = Counter()
for f in all_root_images:
    name = f.name
    if name.startswith('r'):
        prefixes['r... (review)'] += 1
    elif name.startswith('f'):
        prefixes['f... (feature)'] += 1
    elif name.startswith('store'):
        prefixes['store...'] += 1
    elif name.startswith('nav'):
        prefixes['nav...'] += 1
    elif name.startswith('bg'):
        prefixes['bg...'] += 1
    else:
        prefixes[f'other ({name[:3]})'] += 1

print(f"\nFilename prefix breakdown:")
for p, c in sorted(prefixes.items(), key=lambda x: -x[1]):
    print(f"  {p}: {c}")

# Normalize srcs
srcs_normalized = set()
for s in all_srcs:
    if s.startswith('/'):
        srcs_normalized.add(s.lstrip('/'))
    else:
        srcs_normalized.add(s)

# Which root images ARE referenced?
referenced_root = []
orphaned_root = []
for f in all_root_images:
    rel = f'images/{f.name}'
    if rel in srcs_normalized or f.name in srcs_normalized:
        referenced_root.append(f.name)
    else:
        orphaned_root.append(f.name)

print(f"\nRoot images referenced: {len(referenced_root)}")
print(f"Root images orphaned: {len(orphaned_root)}")

# Sample referenced root images
print("\nSample referenced root images:")
for img in sorted(referenced_root)[:15]:
    print(f"  images/{img}")

# Sample orphaned root images
print("\nSample orphaned root images (30):")
for img in sorted(orphaned_root)[:30]:
    print(f"  images/{img}")

# Check if these orphaned images are actually referenced with just the filename
print("\nChecking if orphaned images are referenced by other means (checking all content)...")
count_found = 0
still_orphaned = []
for fname in orphaned_root:
    found = any(fname in s for s in all_srcs)
    if found:
        count_found += 1
    else:
        still_orphaned.append(fname)
print(f"  Found via filename substring: {count_found}")
print(f"  Truly orphaned: {len(still_orphaned)}")
