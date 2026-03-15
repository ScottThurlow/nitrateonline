import re
from pathlib import Path

ROOT = Path('/Users/scott/Code/nitrateonline')

# Check a 1999 review page
sample = ROOT / '1999/rmatrix.html'
content = sample.read_text()
srcs = re.findall(r'src=["\']([^"\']+)["\']', content, re.IGNORECASE)
print('1999/rmatrix.html srcs:')
for s in srcs:
    print(f'  {s!r}')

# Check archive.html to see if year archive pages are linked
sample2 = ROOT / 'archive.html'
content2 = sample2.read_text()
hrefs = re.findall(r'href=["\']([^"\']+)["\']', content2, re.IGNORECASE)
archive_hrefs = [h for h in hrefs if 'archive' in h.lower()]
print('\narchive.html archive-related hrefs:')
for h in archive_hrefs[:20]:
    print(f'  {h!r}')
