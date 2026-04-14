#!/usr/bin/env python3
"""Fix JSON-LD author name fields that contain 'Review by' or 'Feature by'
instead of the actual author name. Extracts the real name from the
meta-byline span in the HTML."""

import re
import glob
import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if this file has the problem
    author_match = re.search(r'"name":\s*"(Review by|Feature by)(.*?)"', content)
    if not author_match:
        return False

    # Extract author from meta-byline span
    # Patterns: "Review by <a href=...>Name</a>" or "Review by Name"
    # Use DOTALL because the name sometimes spans multiple lines
    byline_match = re.search(
        r'class="meta-byline">\s*(?:Review|Feature|Interview|Essay|Report|Column|Special) by\s+'
        r'(?:<a[^>]*>)?(.*?)(?:</a>)?\s*</span>',
        content, re.DOTALL
    )
    if not byline_match:
        print(f"  SKIP (no byline found): {filepath}")
        return False

    author_name = byline_match.group(1).strip()
    # Clean any remaining HTML tags and normalize whitespace
    author_name = re.sub(r'<[^>]+>', '', author_name)
    author_name = re.sub(r'\s+', ' ', author_name).strip()

    if not author_name:
        print(f"  SKIP (empty author): {filepath}")
        return False

    old_str = author_match.group(0)
    new_str = f'"name": "{author_name}"'

    if old_str == new_str:
        return False

    content = content.replace(old_str, new_str, 1)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  FIXED: {filepath}: {old_str} -> {new_str}")
    return True


def main():
    dry_run = '--dry-run' in sys.argv
    files = sorted(glob.glob('**/*.html', recursive=True))
    fixed = 0
    skipped = 0

    for f in files:
        if dry_run:
            # Just check
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
            if re.search(r'"name":\s*"(Review by|Feature by)', content):
                byline_match = re.search(
                    r'class="meta-byline">\s*(?:Review|Feature|Interview|Essay|Report|Column|Special) by\s+'
                    r'(?:<a[^>]*>)?(.*?)(?:</a>)?\s*</span>',
                    content, re.DOTALL
                )
                if byline_match:
                    author = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', byline_match.group(1))).strip()
                    print(f"  WOULD FIX: {f} -> {author}")
                    fixed += 1
                else:
                    print(f"  WOULD SKIP (no byline): {f}")
                    skipped += 1
        else:
            if fix_file(f):
                fixed += 1

    print(f"\n{'Would fix' if dry_run else 'Fixed'}: {fixed} files")
    if skipped:
        print(f"Skipped: {skipped} files")


if __name__ == '__main__':
    main()
