#!/usr/bin/env python3
"""Categorize the missing pages and understand the orphaned images better."""
import re
from pathlib import Path
from collections import Counter

ROOT = Path('/Users/scott/Code/nitrateonline')

# ============================================================
# Missing pages categorization
# ============================================================
MISSING_PAGES = [
    'archive00.html',
    'archive01.html',
    'archive03.html',
    'archive96.html',
    'archive97.html',
    'archive98.html',
    'archive99.html',
    'carriecv-old.html',
    'carriecv.html',
    'cinemaparallel.html',
    'default.htm',
    'google1a87e5c217b58a76.html',
    'issmenu.html',
    'masterarchive.html',
    'nitratelist.html',
    'nitratesub.html',
    'nitrateunsub.html',
    'pointcast_jump.htm',
    'posterstore.html',
    'postinfo.html',
    'schedule.html',
    'store.html',
    'store0199.html',
    'store1098.html',
    'store1198.html',
    'store1298.html',
    'storearch.html',
    'storeitm/storeitmnf.htm',
    'subscribe.html',
]

print("MISSING PAGES CATEGORIZATION:")
print("="*60)

infrastructure = []
old_content = []
archive_pages = []
store_pages = []

for p in sorted(MISSING_PAGES):
    name = Path(p).name
    if any(x in name for x in ['store', 'store']):
        store_pages.append(p)
    elif 'archive' in name.lower() or 'master' in name.lower():
        archive_pages.append(p)
    elif any(x in name for x in ['google', 'pointcast', 'issmenu', 'default', 'schedule', 'subscribe', 'nitratesub', 'nitrateunsub', 'nitratelist', 'postinfo']):
        infrastructure.append(p)
    else:
        old_content.append(p)

print(f"\nInfrastructure/utility pages (never meaningful content): {len(infrastructure)}")
for p in sorted(infrastructure):
    print(f"  {p}")

print(f"\nStore pages (old e-commerce, no longer relevant): {len(store_pages)}")
for p in sorted(store_pages):
    print(f"  {p}")

print(f"\nArchive index pages (consolidated into archive.html): {len(archive_pages)}")
for p in sorted(archive_pages):
    print(f"  {p}")

print(f"\nOther old content pages: {len(old_content)}")
for p in sorted(old_content):
    print(f"  {p}")

# ============================================================
# Broken links - which ones link to missing pages?
# ============================================================
print("\n\nBROKEN LINKS ANALYSIS:")
print("="*60)

BROKEN_LINKS = [
    ("1997/rkolya.html", "/1997/fberlin96-4.html#The Ride", "1997/fberlin96-4.html"),
    ("1998/foscar98-2.html", "/1998/fsiff97-2.html#The_Full_Monty", "1998/fsiff97-2.html"),
    ("1998/fsiff98-1.html", "/1998/ftiff97-3.html#Funny_Games", "1998/ftiff97-3.html"),
    ("1998/ftiff98-2.html", "/1998/fsiff96-5.html#Welcome-to-the-Dollhouse", "1998/fsiff96-5.html"),
    ("1998/rconair.html", "/1998/fsiff97-2.html#The_Van", "1998/fsiff97-2.html"),
    ("1998/redge.html", "/1998/ftiff97-1.html#The_Spanish_Prisoner", "1998/ftiff97-1.html"),
    ("1998/rhappiness.html", "/1998/fsiff96-5.html#Welcome-to-the-Dollhouse", "1998/fsiff96-5.html"),
    ("1998/rhiljack.html", "/1998/ftiff97-1.html#Welcome_to_Sarajevo", "1998/ftiff97-1.html"),
    ("1998/rmafia.html", "/1998/fsiff97-2.html#The_Full_Monty", "1998/fsiff97-2.html"),
    ("1998/rsliding.html", "/1998/ftiff97-3.html#Office_Killer", "1998/ftiff97-3.html"),
    ("1998/ryfriends.html", "/1998/fsiff97-3.html#Company_of_Men", "1998/fsiff97-3.html"),
    ("rhappiness.html", "/fsiff96-5.html#Welcome-to-the-Dollhouse", "fsiff96-5.html"),
    ("rhappiness.html", "/ftiff98-2.html#Happiness", "ftiff98-2.html"),
    ("rmafia.html", "/fsiff97-2.html#The_Full_Monty", "fsiff97-2.html"),
    ("rpsycho.html", "/store1098.html#The_Texas_Chainsaw_Massacre", "store1098.html"),
    ("rronin.html", "/fberlin98-5.html#Good-Will-Hunting", "fberlin98-5.html"),
]

# Categorize broken links by target
missing_targets = Counter()
for src, link, target in BROKEN_LINKS:
    missing_targets[target] += 1

print("\nBroken links grouped by missing target:")
for target, count in sorted(missing_targets.items()):
    print(f"  {target} (linked from {count} page(s))")
    for src, link, t in BROKEN_LINKS:
        if t == target:
            print(f"    <- {src}")

# Check if those targets exist in year folders (wrong year prefix?)
print("\nChecking if targets exist with different year prefix...")
targets_to_check = [
    '1997/fberlin96-4.html',
    '1998/fsiff97-2.html',
    '1998/ftiff97-3.html',
    '1998/fsiff96-5.html',
    '1998/ftiff97-1.html',
    '1998/fsiff97-3.html',
    'fsiff96-5.html',
    'ftiff98-2.html',
    'fsiff97-2.html',
    'store1098.html',
    'fberlin98-5.html',
]

import subprocess
for target in sorted(set(targets_to_check)):
    fname = Path(target).name
    result = subprocess.run(
        ['find', str(ROOT), '-name', fname, '-not', '-path', '*/.git/*'],
        capture_output=True, text=True
    )
    found = [f for f in result.stdout.strip().split('\n') if f]
    if found:
        locs = [str(Path(f).relative_to(ROOT)) for f in found]
        print(f"  {target} -> EXISTS at: {', '.join(locs)}")
    else:
        print(f"  {target} -> NOT FOUND ANYWHERE")
