#!/usr/bin/env python3
"""Comprehensive 6-point audit of the Nitrate Online static site."""

import os
import re
import subprocess
from pathlib import Path
from collections import defaultdict

ROOT = Path('/Users/scott/Code/nitrateonline')

def get_all_html_files():
    """Get all .html/.htm files in root and year folders."""
    html_files = []
    # Root level
    for f in ROOT.glob('*.html'):
        html_files.append(f)
    for f in ROOT.glob('*.htm'):
        html_files.append(f)
    # Year folders 1996-2004
    for year in range(1996, 2005):
        year_dir = ROOT / str(year)
        if year_dir.exists():
            for f in year_dir.glob('*.html'):
                html_files.append(f)
            for f in year_dir.glob('*.htm'):
                html_files.append(f)
    return sorted(html_files)

# ============================================================
# CHECK 1: All pages have new design
# ============================================================
def check1_new_design(html_files):
    print("\n" + "="*70)
    print("CHECK 1: All pages have new design")
    print("="*70)

    old_design_pages = []

    for fpath in html_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"  ERROR reading {fpath}: {e}")
            continue

        issues = []

        if 'Microsoft FrontPage' in content:
            issues.append('contains "Microsoft FrontPage"')

        if 'stylesrc=' in content:
            issues.append('contains "stylesrc="')

        # Check <body with link="# or bgcolor=
        body_tags = re.findall(r'<body[^>]*>', content, re.IGNORECASE)
        for body in body_tags:
            if re.search(r'link="#', body, re.IGNORECASE):
                issues.append(f'<body> has link="#..." attr')
            if re.search(r'bgcolor=', body, re.IGNORECASE):
                issues.append(f'<body> has bgcolor= attr')

        if 'nitrate.css' not in content:
            issues.append('does NOT contain nitrate.css')

        if issues:
            rel = fpath.relative_to(ROOT)
            old_design_pages.append((str(rel), issues))

    if not old_design_pages:
        print("  PASS - All pages use the new design")
    else:
        print(f"  FAIL - {len(old_design_pages)} pages NOT on new design:")
        for path, issues in sorted(old_design_pages):
            print(f"\n  FILE: {path}")
            for issue in issues:
                print(f"    - {issue}")

    return len(old_design_pages)

# ============================================================
# CHECK 2: No broken links (internal only)
# ============================================================
def check2_broken_links(html_files):
    print("\n" + "="*70)
    print("CHECK 2: No broken links")
    print("="*70)

    broken = []
    malformed_external = []

    for fpath in html_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            continue

        rel_file = fpath.relative_to(ROOT)

        # Find all href and src values
        links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', content, re.IGNORECASE)

        for link in links:
            # Strip fragment
            link_clean = link.split('#')[0]
            if not link_clean:
                continue

            # External links - check for obvious malformation
            if link_clean.startswith('http://') or link_clean.startswith('https://'):
                # Check for obviously malformed (e.g., double slashes in path, spaces)
                if ' ' in link_clean:
                    malformed_external.append((str(rel_file), link))
                continue

            # Skip mailto, data, //, #
            if link_clean.startswith('mailto:') or link_clean.startswith('//') or link_clean.startswith('data:'):
                continue

            # Root-relative links starting with /
            if link_clean.startswith('/'):
                # Resolve against root
                resolved = ROOT / link_clean.lstrip('/')
                if not resolved.exists():
                    broken.append((str(rel_file), link, str(resolved.relative_to(ROOT))))

    if not broken and not malformed_external:
        print("  PASS - No broken internal links found")
    else:
        if broken:
            print(f"\n  BROKEN INTERNAL LINKS ({len(broken)} issues):")
            for src, link, resolved in sorted(broken):
                print(f"    {src}: {link!r} -> missing: {resolved}")
        if malformed_external:
            print(f"\n  MALFORMED EXTERNAL LINKS ({len(malformed_external)} issues):")
            for src, link in malformed_external:
                print(f"    {src}: {link!r}")

    return len(broken) + len(malformed_external)

# ============================================================
# CHECK 3: All links are absolute paths
# ============================================================
def check3_relative_links(html_files):
    print("\n" + "="*70)
    print("CHECK 3: All links are absolute paths")
    print("="*70)

    relative_links = []

    ALLOWED_PREFIXES = ('/', 'http://', 'https://', 'mailto:', '//', '#', 'data:')

    for fpath in html_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            continue

        rel_file = fpath.relative_to(ROOT)

        links = re.findall(r'(?:href|src)=["\']([^"\']+)["\']', content, re.IGNORECASE)

        for link in links:
            if not link:
                continue
            if not any(link.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                relative_links.append((str(rel_file), link))

    if not relative_links:
        print("  PASS - All links use absolute paths")
    else:
        print(f"  FAIL - {len(relative_links)} relative links found:")
        for src, link in sorted(relative_links):
            print(f"    {src}: {link!r}")

    return len(relative_links)

# ============================================================
# CHECK 4: No missing pages from original (main branch)
# ============================================================
def check4_missing_pages():
    print("\n" + "="*70)
    print("CHECK 4: No missing pages from original (main branch)")
    print("="*70)

    # Get main branch HTML files
    result = subprocess.run(
        ['git', 'ls-tree', '-r', '--name-only', 'main'],
        cwd=ROOT, capture_output=True, text=True
    )
    main_files = result.stdout.strip().split('\n')

    # Filter to HTML/HTM files (exclude excluded files)
    EXCLUDE = {'robots.txt', 'BingSiteAuth.xml', '.DS_Store', 'README.md',
               'sitemap.xml', '.htaccess'}

    main_html = []
    for f in main_files:
        if f.endswith('.html') or f.endswith('.htm'):
            basename = os.path.basename(f)
            if basename not in EXCLUDE:
                main_html.append(f)

    print(f"  Main branch HTML files: {len(main_html)}")

    missing = []
    found_elsewhere = []

    for orig_path in main_html:
        full_path = ROOT / orig_path
        if full_path.exists():
            continue  # Found at original path

        # Not at original path - check if it exists anywhere
        filename = os.path.basename(orig_path)
        result2 = subprocess.run(
            ['find', str(ROOT), '-name', filename,
             '-not', '-path', '*/.git/*'],
            capture_output=True, text=True
        )
        found = [f for f in result2.stdout.strip().split('\n') if f]

        if found:
            found_elsewhere.append((orig_path, [str(Path(f).relative_to(ROOT)) for f in found]))
        else:
            missing.append(orig_path)

    if not missing and not found_elsewhere:
        print("  PASS - All original pages present on ModernDesign")
    else:
        if found_elsewhere:
            print(f"\n  MOVED (present elsewhere): {len(found_elsewhere)} pages")
            for orig, locations in sorted(found_elsewhere):
                print(f"    {orig} -> {', '.join(locations)}")
        if missing:
            print(f"\n  MISSING (not found anywhere): {len(missing)} pages")
            for path in sorted(missing):
                print(f"    {path}")

    return len(missing), len(found_elsewhere)

# ============================================================
# CHECK 5: No missing images from original
# ============================================================
def check5_missing_images():
    print("\n" + "="*70)
    print("CHECK 5: No missing images from original (main branch)")
    print("="*70)

    result = subprocess.run(
        ['git', 'ls-tree', '-r', '--name-only', 'main'],
        cwd=ROOT, capture_output=True, text=True
    )
    main_files = result.stdout.strip().split('\n')

    img_exts = re.compile(r'\.(jpg|jpeg|gif|png|svg|JPG|GIF|PNG)$')
    main_images = [f for f in main_files if img_exts.search(f)]

    print(f"  Main branch image files: {len(main_images)}")

    missing = []
    found_elsewhere = []

    for orig_path in main_images:
        full_path = ROOT / orig_path
        if full_path.exists():
            continue  # Found at original path

        filename = os.path.basename(orig_path)
        result2 = subprocess.run(
            ['find', str(ROOT), '-name', filename,
             '-not', '-path', '*/.git/*'],
            capture_output=True, text=True
        )
        found = [f for f in result2.stdout.strip().split('\n') if f]

        if found:
            found_elsewhere.append((orig_path, [str(Path(f).relative_to(ROOT)) for f in found]))
        else:
            missing.append(orig_path)

    if not missing and not found_elsewhere:
        print("  PASS - All original images present on ModernDesign")
    else:
        if found_elsewhere:
            print(f"\n  MOVED (present elsewhere): {len(found_elsewhere)} images")
            for orig, locations in sorted(found_elsewhere)[:20]:
                print(f"    {orig} -> {', '.join(locations)}")
            if len(found_elsewhere) > 20:
                print(f"    ... and {len(found_elsewhere)-20} more")
        if missing:
            print(f"\n  MISSING (not found anywhere): {len(missing)} images")
            for path in sorted(missing):
                print(f"    {path}")

    return len(missing), len(found_elsewhere)

# ============================================================
# CHECK 6: Orphaned pages and images
# ============================================================
def check6_orphaned(html_files):
    print("\n" + "="*70)
    print("CHECK 6: Orphaned pages and images")
    print("="*70)

    EXCLUDE_FROM_ORPHAN_CHECK = {
        'index.html', 'archive.html', 'aboutus.html', 'links.html',
        'search.html', 'carrie.html', 'eddie.html', 'cynthia.html',
        'dan.html', 'dave.html', 'elias.html', 'emma.html', 'gianni.html',
        'gregory.html', 'jerry.html', 'joe.html', 'kj.html', 'lyall.html',
        'paula.html', 'sean.html', 'press.html', 'eddiecv.html',
        'eddiephoto.html'
    }

    # Build set of all linked-to pages
    all_linked_hrefs = set()
    all_linked_srcs = set()

    for fpath in html_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue

        hrefs = re.findall(r'href=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for href in hrefs:
            # Normalize - strip fragment, keep path
            href_clean = href.split('#')[0].split('?')[0]
            if href_clean.startswith('/'):
                all_linked_hrefs.add(href_clean)
            elif href_clean.startswith('http') or href_clean.startswith('mailto'):
                pass
            else:
                all_linked_hrefs.add(href_clean)

        srcs = re.findall(r'src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for src in srcs:
            src_clean = src.split('?')[0]
            all_linked_srcs.add(src_clean)

    # Normalize hrefs to paths relative to root
    linked_paths = set()
    for href in all_linked_hrefs:
        if href.startswith('/'):
            linked_paths.add(href.lstrip('/'))
        elif href:
            linked_paths.add(href)

    # Check which HTML files are not linked to
    print("\n  --- Orphaned Pages ---")
    orphaned_pages = []
    for fpath in html_files:
        rel = str(fpath.relative_to(ROOT))
        basename = os.path.basename(rel)

        # Skip excluded
        if basename in EXCLUDE_FROM_ORPHAN_CHECK:
            continue
        # Skip year index files
        if re.match(r'^\d{4}/index\.html$', rel):
            continue

        # Check if this file is linked to
        if rel not in linked_paths and ('/' + rel) not in all_linked_hrefs:
            orphaned_pages.append(rel)

    if not orphaned_pages:
        print("  PASS - No orphaned pages")
    else:
        print(f"  {len(orphaned_pages)} potentially orphaned pages:")
        for p in sorted(orphaned_pages):
            print(f"    {p}")

    # Check orphaned images
    print("\n  --- Orphaned Images ---")

    # Normalize all src references
    linked_srcs_normalized = set()
    for src in all_linked_srcs:
        if src.startswith('/'):
            linked_srcs_normalized.add(src.lstrip('/'))
        elif src:
            linked_srcs_normalized.add(src)

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

    orphaned_images = []
    for img_path in all_images:
        rel = str(img_path.relative_to(ROOT))

        # Check if referenced
        if rel in linked_srcs_normalized:
            continue
        if '/' + rel in all_linked_srcs:
            continue
        # Also check by filename alone (in case paths differ)
        fname = img_path.name
        found = any(fname in src for src in all_linked_srcs)
        if not found:
            orphaned_images.append(rel)

    if not orphaned_images:
        print("  PASS - No orphaned images")
    else:
        print(f"  {len(orphaned_images)} potentially orphaned images:")
        for img in sorted(orphaned_images)[:30]:
            print(f"    {img}")
        if len(orphaned_images) > 30:
            print(f"    ... and {len(orphaned_images)-30} more")

    return len(orphaned_pages), len(orphaned_images)

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("NITRATE ONLINE SITE AUDIT")
    print("Branch: ModernDesign")
    print(f"Root: {ROOT}")

    html_files = get_all_html_files()
    print(f"\nTotal HTML files found: {len(html_files)}")

    c1 = check1_new_design(html_files)
    c2 = check2_broken_links(html_files)
    c3 = check3_relative_links(html_files)
    c4_missing, c4_moved = check4_missing_pages()
    c5_missing, c5_moved = check5_missing_images()
    c6_pages, c6_images = check6_orphaned(html_files)

    print("\n" + "="*70)
    print("SUMMARY TABLE")
    print("="*70)
    print(f"{'Check':<50} {'Result':<10}")
    print("-"*70)
    print(f"{'1. Pages on new design':<50} {'PASS' if c1==0 else f'FAIL ({c1} pages)':<10}")
    print(f"{'2. No broken links':<50} {'PASS' if c2==0 else f'FAIL ({c2} broken)':<10}")
    print(f"{'3. All links absolute':<50} {'PASS' if c3==0 else f'FAIL ({c3} relative)':<10}")
    print(f"{'4. No missing pages (main branch)':<50} {'PASS' if c4_missing==0 else f'FAIL ({c4_missing} missing)':<10}")
    print(f"{'   Pages moved to different location':<50} {c4_moved} pages")
    print(f"{'5. No missing images (main branch)':<50} {'PASS' if c5_missing==0 else f'FAIL ({c5_missing} missing)':<10}")
    print(f"{'   Images moved to different location':<50} {c5_moved} images")
    print(f"{'6. Orphaned pages':<50} {'PASS' if c6_pages==0 else f'{c6_pages} orphaned':<10}")
    print(f"{'6. Orphaned images':<50} {'PASS' if c6_images==0 else f'{c6_images} orphaned':<10}")
