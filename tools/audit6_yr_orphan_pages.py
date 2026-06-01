#!/usr/bin/env python3
"""Check if year-folder orphaned images correspond to pages that exist (perhaps not linking the images)."""
import re
import subprocess
from pathlib import Path
from collections import defaultdict

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

srcs_normalized = set(s.lstrip('/') for s in all_srcs)
srcs_by_filename = {Path(s).name for s in srcs_normalized}

# Orphaned year images
img_exts = re.compile(r'\.(jpg|jpeg|gif|png|svg|JPG|GIF|PNG)$', re.IGNORECASE)

year_orphaned = []
for year in range(1996, 2005):
    year_images = ROOT / str(year) / 'images'
    if year_images.exists():
        for f in year_images.iterdir():
            if img_exts.search(f.name):
                rel = str(f.relative_to(ROOT))
                if rel not in srcs_normalized and f.name not in srcs_by_filename:
                    year_orphaned.append((f, rel))

print(f"Year-folder orphaned images: {len(year_orphaned)}")

# Group by year and image-name-prefix
groups = defaultdict(list)
for img, rel in year_orphaned:
    year = rel.split('/')[0]
    # Get the base page slug from image name
    stem = img.stem
    base = re.sub(r'-\d+$', '', stem)
    groups[(year, base)].append(img.name)

# For each group, check if an HTML page with that name exists
print("\nChecking if corresponding HTML pages exist:")
missing_page_imgs = []
page_exists_imgs = []
unclear_imgs = []

for (year, base), imgs in sorted(groups.items()):
    # Look for a page matching the base slug in that year or elsewhere
    result = subprocess.run(
        ['find', str(ROOT), '-name', f'{base}.html', '-not', '-path', '*/.git/*'],
        capture_output=True, text=True
    )
    found = [f for f in result.stdout.strip().split('\n') if f]

    # Also try without trailing digits
    base2 = re.sub(r'\d+$', '', base)
    result2 = subprocess.run(
        ['find', str(ROOT), '-name', f'{base2}.html', '-not', '-path', '*/.git/*'],
        capture_output=True, text=True
    )
    found2 = [f for f in result2.stdout.strip().split('\n') if f]

    all_found = list(set(found + found2))

    if all_found:
        page_exists_imgs.append(((year, base), imgs, all_found))
    else:
        missing_page_imgs.append(((year, base), imgs))

print(f"\nImages whose page EXISTS (page not linking them): {sum(len(i) for _, i, _ in page_exists_imgs)}")
for (year, base), imgs, pages in sorted(page_exists_imgs):
    page_rels = [str(Path(p).relative_to(ROOT)) for p in pages]
    print(f"  {year}/images/{base}-*.* ({len(imgs)} imgs) -> page: {', '.join(page_rels)}")

print(f"\nImages with NO corresponding page: {sum(len(i) for _, i in missing_page_imgs)}")
for (year, base), imgs in sorted(missing_page_imgs):
    print(f"  {year}/images/{base}-*.* ({len(imgs)} imgs) - no {base}.html found")

# Final summary of root orphaned images categories
print("\n\n--- Root images/ orphaned categories ---")
root_orphaned = []
images_dir = ROOT / 'images'
for f in images_dir.iterdir():
    if img_exts.search(f.name):
        rel = f'images/{f.name}'
        if rel not in srcs_normalized and f.name not in srcs_by_filename:
            root_orphaned.append(f)

# Old-site navigation/UI images
ui_images = []
review_images = []
feature_images = []
misc_images = []
for f in root_orphaned:
    name = f.name.lower()
    if any(x in name for x in ['archive', 'banner', 'bullet', 'empty', 'email', 'nav',
                                 'bg', 'boom', 'amzn', 'dell', 'eastcoast', 'paypal',
                                 'amazon', '1x1', 'high', 'no-', 'node', 'pointer',
                                 'store', 'nominate', 'logo', 'ie.', 'iec', 'imdb',
                                 'slogan', 'ksa', 'latest', 'links', 'henry', 'dan.',
                                 'elias', 'emma', 'joe.', 'lyall', 'sam.', 'lya',
                                 'carrie', 'eddie', 'gianni']):
        ui_images.append(f)
    elif name.startswith('r'):
        review_images.append(f)
    elif name.startswith('f'):
        feature_images.append(f)
    else:
        misc_images.append(f)

print(f"  Old UI/nav/misc images: {len(ui_images)}")
print(f"  Review images (r...): {len(review_images)}")
print(f"    (These are old design review thumbnails no longer used)")
print(f"  Feature article images (f...): {len(feature_images)}")
print(f"    (These are old design feature thumbnails no longer used)")
print(f"  Misc: {len(misc_images)}")
for f in misc_images:
    print(f"    images/{f.name}")
