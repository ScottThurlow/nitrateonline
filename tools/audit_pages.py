#!/usr/bin/env python3
"""
Comprehensive quality audit of converted HTML pages in Nitrate Online.
Compares modern pages against the legacy git branch.
"""

import os
import re
import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Configuration
PROJECT_ROOT = Path("/Users/scott/Code/nitrateonline")
IMAGES_DIR = PROJECT_ROOT / "images"
OUTPUT_CSV = PROJECT_ROOT / "data" / "audit_report.csv"
OUTPUT_SUMMARY = PROJECT_ROOT / "data" / "audit_summary.txt"
YEARS = list(range(1996, 2005))
LEGACY_ROOT_YEARS = {1996, 1997, 1998}  # files at legacy root (not in year subdirs)
MAX_WORKERS = 8


def get_modern_files():
    """Collect all r*.html and f*.html files in year dirs 1996–2004."""
    files = []
    for year in YEARS:
        year_dir = PROJECT_ROOT / str(year)
        if not year_dir.exists():
            continue
        for f in sorted(year_dir.glob("*.html")):
            if f.name.startswith(("r", "f")) and f.name != "index.html":
                files.append((year, f))
    return files


def get_legacy_content(year: int, filename: str) -> str | None:
    """Fetch legacy file content from git."""
    if year in LEGACY_ROOT_YEARS:
        legacy_path = filename
    else:
        legacy_path = f"{year}/{filename}"
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "show", f"legacy:{legacy_path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None


def extract_article_body(html: str) -> str:
    """Extract text between article-body open and article-footer open."""
    # Find article body start
    start_match = re.search(r'<article[^>]*class="[^"]*article-body[^"]*"[^>]*>', html)
    end_match = re.search(r'<div[^>]*class="[^"]*article-footer[^"]*"', html)
    if start_match and end_match and start_match.end() < end_match.start():
        return html[start_match.end():end_match.start()]
    return ""


def count_p_tags(html: str) -> int:
    return len(re.findall(r"<p[\s>]", html, re.IGNORECASE))


def check_reviewer(modern_html: str) -> str | None:
    """Return reviewer name from modern page, or None."""
    # Match meta-byline span — may contain plain text or anchor tags
    m = re.search(r'class="meta-byline"[^>]*>(.*?)</span>', modern_html, re.DOTALL)
    if m:
        # Strip any inner HTML tags to get text
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            return text
    # Check article footer
    m = re.search(r'<div[^>]*class="[^"]*article-footer-meta[^"]*"[^>]*>.*?<p>(.*?)</p>', modern_html, re.DOTALL)
    if m:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if text:
            return text
    return None


def check_legacy_reviewer(legacy_html: str) -> str | None:
    """Detect reviewer in legacy HTML."""
    if legacy_html is None:
        return None
    patterns = [
        r'[Rr]eview\s+by\s+<a[^>]*>([^<]+)</a>',
        r'[Rr]eview\s+by\s+([A-Z][a-z]+(?: [A-Z][a-z]+)?)',
        r'[Ww]ritten\s+by\s+([A-Z][a-z]+(?: [A-Z][a-z]+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, legacy_html)
        if m:
            return m.group(1).strip()
    return None


def check_film_card(modern_html: str) -> dict:
    """Check film-card presence and contents."""
    has_film_card = bool(re.search(r'class="film-card"', modern_html))
    has_director = bool(re.search(r'Director', modern_html)) if has_film_card else False
    has_imdb = bool(re.search(r'imdb\.com', modern_html, re.IGNORECASE)) if has_film_card else False
    return {
        "has_film_card": has_film_card,
        "has_director": has_director,
        "has_imdb": has_imdb,
    }


def extract_images(modern_html: str):
    """Return (poster_src, scene_srcs) from modern HTML."""
    poster_match = re.search(r'src="(/images/[^"]*-poster\.jpg)"', modern_html)
    poster_src = poster_match.group(1) if poster_match else None
    scene_srcs = re.findall(r'src="(/images/[rf][^"]+\.jpg)"', modern_html)
    # Exclude poster from scene list
    scene_srcs = [s for s in scene_srcs if not s.endswith("-poster.jpg")]
    return poster_src, scene_srcs


def check_og_image(modern_html: str) -> str | None:
    """Return og:image URL or None."""
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', modern_html)
    if not m:
        m = re.search(r'<meta\s+content="([^"]+)"\s+property="og:image"', modern_html)
    return m.group(1) if m else None


def url_to_local_path(url: str) -> Path | None:
    """Convert /images/foo.jpg URL to local filesystem path."""
    if url.startswith("/images/"):
        return IMAGES_DIR / url[len("/images/"):]
    elif url.startswith("https://nitrateonline.com/images/"):
        return IMAGES_DIR / url[len("https://nitrateonline.com/images/"):]
    return None


def audit_file(year: int, modern_path: Path) -> list[dict]:
    """Audit a single modern file. Returns list of issue dicts."""
    issues = []

    def add_issue(issue_type: str, details: str):
        issues.append({
            "file": str(modern_path.relative_to(PROJECT_ROOT)),
            "issue_type": issue_type,
            "details": details,
        })

    # Read modern file
    try:
        modern_html = modern_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        add_issue("empty_content", f"Could not read file: {e}")
        return issues

    # Get legacy content
    legacy_html = get_legacy_content(year, modern_path.name)

    # --- 1. Content completeness ---
    article_body = extract_article_body(modern_html)
    article_body_stripped = re.sub(r"\s+", " ", article_body).strip()

    if not article_body_stripped:
        add_issue("empty_content", "Article body is empty or missing")
    else:
        p_count = count_p_tags(article_body)
        if p_count < 2:
            add_issue("empty_content", f"Article body has only {p_count} <p> tag(s)")

        if legacy_html:
            # Compare lengths: strip HTML tags for text comparison
            modern_text = re.sub(r"<[^>]+>", "", article_body_stripped)
            legacy_text = re.sub(r"<[^>]+>", "", legacy_html)
            modern_len = len(modern_text.strip())
            legacy_len = len(legacy_text.strip())
            if legacy_len > 200 and modern_len < legacy_len * 0.5:
                pct = int(100 * modern_len / legacy_len) if legacy_len else 0
                add_issue("thin_content", f"Modern content is {pct}% of legacy length ({modern_len} vs {legacy_len} chars)")

    # --- 2. Reviewer attribution ---
    modern_reviewer = check_reviewer(modern_html)
    if not modern_reviewer:
        add_issue("missing_reviewer", "No reviewer byline found (meta-byline or article-footer-meta)")

    # --- 3. Film card / metadata ---
    fc = check_film_card(modern_html)
    if not fc["has_film_card"]:
        add_issue("missing_film_card", "No film-card div found")
    else:
        if not fc["has_director"]:
            add_issue("missing_director", "No Director listed in film-credits")
        if not fc["has_imdb"]:
            add_issue("missing_imdb_link", "No IMDB link in film card")

    # --- 4. Images ---
    poster_src, scene_srcs = extract_images(modern_html)

    if not poster_src:
        # Check if there's any poster reference at all
        if not re.search(r'-poster\.jpg', modern_html):
            add_issue("missing_poster_reference", "No poster image reference found")
    else:
        poster_path = url_to_local_path(poster_src)
        if poster_path and not poster_path.exists():
            add_issue("missing_poster_file", f"Poster image not found on disk: {poster_src}")

    for scene_src in scene_srcs:
        scene_path = url_to_local_path(scene_src)
        if scene_path and not scene_path.exists():
            add_issue("missing_scene_file", f"Scene image not found on disk: {scene_src}")

    # --- 5. og:image ---
    og_image = check_og_image(modern_html)
    if og_image:
        og_path = url_to_local_path(og_image)
        if og_path and not og_path.exists():
            add_issue("og_image_missing_file", f"og:image file not found: {og_image}")

    # --- 6. Structural issues ---
    has_article_layout = bool(re.search(r'class="[^"]*article-layout[^"]*"', modern_html))
    has_sidebar = bool(re.search(r'class="[^"]*article-sidebar[^"]*"', modern_html))
    if not has_article_layout or not has_sidebar:
        missing = []
        if not has_article_layout:
            missing.append("article-layout")
        if not has_sidebar:
            missing.append("article-sidebar")
        add_issue("missing_film_card", f"Missing structural elements: {', '.join(missing)}")

    return issues


def main():
    print("Collecting files to audit...")
    all_files = get_modern_files()
    total = len(all_files)
    print(f"Found {total} files to audit across years {YEARS[0]}–{YEARS[-1]}")

    all_issues = []
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(audit_file, year, path): (year, path)
            for year, path in all_files
        }
        for future in as_completed(futures):
            year, path = futures[future]
            try:
                issues = future.result()
                all_issues.extend(issues)
            except Exception as e:
                all_issues.append({
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "issue_type": "empty_content",
                    "details": f"Audit error: {e}",
                })
            processed += 1
            if processed % 100 == 0:
                print(f"  Progress: {processed}/{total} files processed...")

    print(f"  Done: {processed}/{total} files processed.")

    # Sort issues by file then issue_type
    all_issues.sort(key=lambda x: (x["file"], x["issue_type"]))

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "issue_type", "details"])
        writer.writeheader()
        writer.writerows(all_issues)
    print(f"\nWrote {len(all_issues)} issues to {OUTPUT_CSV}")

    # Tally by issue type
    from collections import Counter
    issue_counts = Counter(issue["issue_type"] for issue in all_issues)
    files_with_issues = len(set(issue["file"] for issue in all_issues))
    clean_files = total - files_with_issues

    # Write summary
    summary_lines = [
        "=" * 60,
        "NITRATE ONLINE PAGE QUALITY AUDIT SUMMARY",
        "=" * 60,
        f"Total files audited:       {total}",
        f"Files with issues:         {files_with_issues}",
        f"Files without issues:      {clean_files}",
        f"Total issues found:        {len(all_issues)}",
        "",
        "ISSUE COUNTS BY TYPE:",
        "-" * 40,
    ]
    for issue_type, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"  {issue_type:<30} {count:>5}")

    summary_lines += [
        "",
        "TOP 10 MOST COMMON ISSUES:",
        "-" * 40,
    ]
    for issue_type, count in issue_counts.most_common(10):
        summary_lines.append(f"  {issue_type:<30} {count:>5}")

    summary_lines += [
        "",
        f"Full details: {OUTPUT_CSV}",
        "=" * 60,
    ]

    summary_text = "\n".join(summary_lines)
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write(summary_text + "\n")
    print(f"Wrote summary to {OUTPUT_SUMMARY}")
    print()
    print(summary_text)


if __name__ == "__main__":
    main()
