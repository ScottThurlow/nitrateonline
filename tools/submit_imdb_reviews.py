#!/usr/bin/env python3
"""
Submit Nitrate Online reviews to IMDb's External Reviews via browser automation.

Uses Playwright to fill out IMDb's contribution form one review at a time,
simulating human-like behavior with randomized timing and breaks.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python3 tools/submit_imdb_reviews.py                    # run a 4-hour session
    python3 tools/submit_imdb_reviews.py --hours 2          # run for 2 hours
    python3 tools/submit_imdb_reviews.py --dry-run          # preview what would be submitted
    python3 tools/submit_imdb_reviews.py --headed            # run with visible browser
    python3 tools/submit_imdb_reviews.py --resume            # resume from last session
    python3 tools/submit_imdb_reviews.py --check tt0114746  # check/submit one title

Session state is saved to data/imdb_submit_progress.json so you can resume
across multiple runs.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright is required. Install it with:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
PROGRESS_FILE = DATA_DIR / 'imdb_submit_progress.json'
MISSING_CSV = DATA_DIR / 'imdb_missing.csv'
SESSION_LOG = DATA_DIR / 'imdb_submit_log.csv'
AUTH_STATE = DATA_DIR / '.imdb_auth_state.json'

# ---------------------------------------------------------------------------
# Timing constants (seconds) — designed to look human
# ---------------------------------------------------------------------------
MIN_BETWEEN_SUBMISSIONS = 60      # 1 minute minimum between submissions
MAX_BETWEEN_SUBMISSIONS = 300     # 5 minutes maximum
MIN_BREAK_INTERVAL = 45 * 60     # take a break after at least 45 min of work
MAX_BREAK_INTERVAL = 90 * 60     # take a break before 90 min of work
MIN_BREAK_DURATION = 10 * 60     # breaks last at least 10 minutes
MAX_BREAK_DURATION = 30 * 60     # breaks last at most 30 minutes
DEFAULT_SESSION_HOURS = 4        # total work time per session (excluding breaks)

# Typing speed (seconds between keystrokes)
MIN_KEYSTROKE_DELAY = 0.04
MAX_KEYSTROKE_DELAY = 0.18

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('imdb_submit')


# ===================================================================
# Data helpers
# ===================================================================

def load_missing_reviews():
    """Load reviews from imdb_missing.csv."""
    reviews = []
    with open(MISSING_CSV, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviews.append({
                'imdb_id': row['imdb_id'],
                'title': row['title'],
                'review_url': row['review_url'],
                'label': row.get('label', 'Nitrate Online'),
            })
    return reviews


def get_author_for_review(review_url):
    """Extract the author name from the review's HTML file."""
    parsed = urlparse(review_url)
    rel_path = parsed.path.lstrip('/')
    html_path = ROOT / rel_path

    if not html_path.exists():
        return None

    content = html_path.read_text(encoding='utf-8', errors='replace')

    # Try JSON-LD author first
    m = re.search(r'"author"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', content)
    if m:
        return m.group(1)

    # Try byline
    m = re.search(r'meta-byline[^>]*>(?:Review|Feature)\s+by\s+<a[^>]*>([^<]+)', content)
    if m:
        return m.group(1)

    # Try plain byline text
    m = re.search(r'(?:Review|Feature)\s+by\s+([A-Z][a-z]+ [A-Z][a-z]+)', content)
    if m:
        return m.group(1)

    return None


def build_description(label, author):
    """
    Build the IMDb external review description.
    Format: "Nitrate Online [Author Name]"
    """
    if author:
        return f"{label} [{author}]"
    return label


def load_progress():
    """Load submission progress from disk."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {
        'submitted': [],      # list of imdb_ids successfully submitted
        'failed': [],         # list of {imdb_id, error, timestamp}
        'skipped': [],        # list of imdb_ids skipped (already present, etc.)
        'last_session': None,
        'total_submitted': 0,
    }


def save_progress(progress):
    """Save submission progress to disk."""
    progress['last_session'] = datetime.now().isoformat()
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))


def log_submission(imdb_id, title, review_url, status, detail=''):
    """Append a line to the session CSV log."""
    file_exists = SESSION_LOG.exists()
    with open(SESSION_LOG, 'a', newline='') as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(['timestamp', 'imdb_id', 'title', 'review_url', 'status', 'detail'])
        w.writerow([datetime.now().isoformat(), imdb_id, title, review_url, status, detail])


# ===================================================================
# Human-like behavior helpers
# ===================================================================

def human_delay(min_s=MIN_BETWEEN_SUBMISSIONS, max_s=MAX_BETWEEN_SUBMISSIONS):
    """Sleep a random duration, weighted toward the lower end."""
    # Use a triangular distribution so most waits are on the shorter side
    delay = random.triangular(min_s, max_s, min_s + (max_s - min_s) * 0.3)
    log.info(f"  Waiting {delay:.0f}s before next submission...")
    time.sleep(delay)


def human_type(page, selector, text):
    """Type text into a field with human-like keystroke timing."""
    page.click(selector)
    time.sleep(random.uniform(0.2, 0.5))
    for char in text:
        page.keyboard.type(char, delay=random.uniform(
            MIN_KEYSTROKE_DELAY * 1000, MAX_KEYSTROKE_DELAY * 1000))
    time.sleep(random.uniform(0.3, 0.8))


def human_click(page, selector):
    """Click with a small random delay before and after."""
    time.sleep(random.uniform(0.3, 1.0))
    page.click(selector)
    time.sleep(random.uniform(0.5, 1.5))


def take_break():
    """Simulate a human break — step away from the computer."""
    duration = random.uniform(MIN_BREAK_DURATION, MAX_BREAK_DURATION)
    mins = duration / 60
    log.info(f"☕ Taking a {mins:.0f}-minute break...")
    time.sleep(duration)
    log.info("  Back from break.")


def should_take_break(work_start_time):
    """Decide whether it's time for a break based on continuous work time."""
    elapsed = time.time() - work_start_time
    threshold = random.uniform(MIN_BREAK_INTERVAL, MAX_BREAK_INTERVAL)
    return elapsed >= threshold


# ===================================================================
# IMDb interaction
# ===================================================================

def ensure_logged_in(page, context):
    """
    Check if we're logged in to IMDb. If not, navigate to login
    and wait for the user to complete it manually.
    """
    page.goto('https://www.imdb.com/', wait_until='domcontentloaded', timeout=30000)
    time.sleep(2)

    # Check for sign-in indicators
    logged_in = page.locator('text=Watchlist').first
    try:
        logged_in.wait_for(timeout=5000)
        log.info("Already logged in to IMDb.")
        return True
    except PlaywrightTimeout:
        pass

    # If we have saved auth state, try loading it
    if AUTH_STATE.exists():
        log.info("Loading saved auth state...")
        context.clear_cookies()
        cookies = json.loads(AUTH_STATE.read_text())
        context.add_cookies(cookies)
        page.reload(wait_until='domcontentloaded')
        time.sleep(2)

        try:
            page.locator('text=Watchlist').first.wait_for(timeout=5000)
            log.info("Logged in via saved session.")
            return True
        except PlaywrightTimeout:
            log.info("Saved session expired.")

    # Manual login required
    log.info("=" * 60)
    log.info("Please log in to IMDb in the browser window.")
    log.info("The script will continue once you're logged in.")
    log.info("=" * 60)
    page.goto('https://www.imdb.com/registration/signin', wait_until='domcontentloaded')

    # Wait up to 5 minutes for manual login
    for _ in range(300):
        time.sleep(1)
        try:
            page.locator('text=Watchlist').first.wait_for(timeout=1000)
            log.info("Login detected! Saving session...")
            cookies = context.cookies()
            AUTH_STATE.write_text(json.dumps(cookies, indent=2))
            return True
        except PlaywrightTimeout:
            continue

    log.error("Login timed out after 5 minutes.")
    return False


def submit_one_review(page, imdb_id, review_url, description, dry_run=False):
    """
    Submit a single external review via IMDb's contribution form.

    The flow:
    1. Go to the title's edit page on contribute.imdb.com
    2. Find "External Reviews" under "Links to Other Sites"
    3. Add the URL and description
    4. Check and submit the update

    Returns: (success: bool, detail: str)
    """
    edit_url = f'https://contribute.imdb.com/updates?update={imdb_id}'

    if dry_run:
        log.info(f"  [DRY RUN] Would submit: {edit_url}")
        log.info(f"    URL: {review_url}")
        log.info(f"    Desc: {description}")
        return True, 'dry_run'

    try:
        # Step 1: Navigate to the edit page
        log.info(f"  Navigating to edit page for {imdb_id}...")
        page.goto(edit_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(random.uniform(2, 4))

        # Step 2: Find and expand "External Reviews" section
        # Look for the "External Sites" or "Links" section
        # The form structure varies, so we try multiple approaches

        # Try to find "External Reviews" link/section
        ext_review_link = None
        for selector in [
            'text=External Reviews',
            'text=External reviews',
            'a:has-text("External Reviews")',
            'text=Links to Other Sites',
            'text=Add external review',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=5000)
                ext_review_link = el
                break
            except PlaywrightTimeout:
                continue

        if not ext_review_link:
            # Maybe we need to scroll down or the page layout is different
            # Try looking for an "Add" button near external reviews
            page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
            time.sleep(1)

            for selector in [
                'text=External Reviews',
                '[data-testid*="external"]',
                'text=Add 1 Item',
            ]:
                try:
                    el = page.locator(selector).first
                    el.wait_for(timeout=3000)
                    ext_review_link = el
                    break
                except PlaywrightTimeout:
                    continue

        if not ext_review_link:
            return False, 'could_not_find_external_reviews_section'

        # Click to expand/navigate to the external reviews section
        ext_review_link.click()
        time.sleep(random.uniform(2, 4))

        # Step 3: Look for "Add 1 Item" or similar button
        add_btn = None
        for selector in [
            'text=Add 1 Item',
            'text=Add item',
            'button:has-text("Add")',
            'a:has-text("Add")',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=5000)
                add_btn = el
                break
            except PlaywrightTimeout:
                continue

        if add_btn:
            add_btn.click()
            time.sleep(random.uniform(2, 3))

        # Step 4: Fill in the URL field
        url_field = None
        for selector in [
            'input[name*="url" i]',
            'input[placeholder*="URL" i]',
            'input[placeholder*="http" i]',
            'input[type="url"]',
            'input[name*="link" i]',
            '#url',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=3000)
                url_field = el
                break
            except PlaywrightTimeout:
                continue

        if not url_field:
            # Take a screenshot for debugging
            screenshot_path = DATA_DIR / f'debug_{imdb_id}.png'
            page.screenshot(path=str(screenshot_path))
            return False, f'could_not_find_url_field (screenshot: {screenshot_path})'

        # Type the URL human-style
        url_field.click()
        time.sleep(random.uniform(0.3, 0.8))
        url_field.fill('')  # clear first
        for char in review_url:
            page.keyboard.type(char, delay=random.uniform(20, 60))
        time.sleep(random.uniform(0.5, 1.0))

        # Step 5: Fill in the description field
        desc_field = None
        for selector in [
            'input[name*="desc" i]',
            'input[name*="label" i]',
            'input[placeholder*="description" i]',
            'input[placeholder*="label" i]',
            'textarea[name*="desc" i]',
            '#description',
            '#label',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=3000)
                desc_field = el
                break
            except PlaywrightTimeout:
                continue

        if not desc_field:
            screenshot_path = DATA_DIR / f'debug_{imdb_id}.png'
            page.screenshot(path=str(screenshot_path))
            return False, f'could_not_find_description_field (screenshot: {screenshot_path})'

        desc_field.click()
        time.sleep(random.uniform(0.3, 0.8))
        desc_field.fill('')
        for char in description:
            page.keyboard.type(char, delay=random.uniform(25, 80))
        time.sleep(random.uniform(0.5, 1.5))

        # Step 6: Submit — first "Check these updates", then "Submit"
        check_btn = None
        for selector in [
            'text=Check these updates',
            'button:has-text("Check")',
            'input[value*="Check" i]',
            'button:has-text("Continue")',
            'text=Continue',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=5000)
                check_btn = el
                break
            except PlaywrightTimeout:
                continue

        if check_btn:
            time.sleep(random.uniform(1, 2))
            check_btn.click()
            time.sleep(random.uniform(3, 6))

        # Now click the final submit button
        submit_btn = None
        for selector in [
            'text=Submit these updates',
            'button:has-text("Submit")',
            'input[value*="Submit" i]',
            'button[type="submit"]',
        ]:
            try:
                el = page.locator(selector).first
                el.wait_for(timeout=5000)
                submit_btn = el
                break
            except PlaywrightTimeout:
                continue

        if not submit_btn:
            screenshot_path = DATA_DIR / f'debug_{imdb_id}.png'
            page.screenshot(path=str(screenshot_path))
            return False, f'could_not_find_submit_button (screenshot: {screenshot_path})'

        time.sleep(random.uniform(1, 3))
        submit_btn.click()
        time.sleep(random.uniform(3, 6))

        # Verify submission — look for a confirmation message
        try:
            page.locator('text=Thank').first.wait_for(timeout=10000)
            return True, 'submitted'
        except PlaywrightTimeout:
            # Check for error messages
            for err_text in ['error', 'already exists', 'duplicate', 'rejected']:
                if page.locator(f'text=/{err_text}/i').first.is_visible():
                    return False, f'submission_error: {err_text}'

            # No clear confirmation or error — take screenshot, assume success
            screenshot_path = DATA_DIR / f'debug_{imdb_id}_post_submit.png'
            page.screenshot(path=str(screenshot_path))
            return True, f'submitted_no_confirmation (screenshot: {screenshot_path})'

    except PlaywrightTimeout as e:
        return False, f'timeout: {e}'
    except Exception as e:
        return False, f'exception: {e}'


# ===================================================================
# Main session loop
# ===================================================================

def run_session(args):
    progress = load_progress()
    reviews = load_missing_reviews()
    already_done = set(progress['submitted'] + progress['skipped'])

    # Filter to reviews not yet attempted
    pending = [r for r in reviews if r['imdb_id'] not in already_done]
    random.shuffle(pending)  # randomize order to look less bot-like

    if not pending:
        log.info("All reviews have been submitted! Nothing to do.")
        return

    log.info(f"Reviews pending: {len(pending)} / {len(reviews)} total")
    log.info(f"Already submitted: {len(progress['submitted'])}")
    log.info(f"Session length: {args.hours} hours")

    if args.dry_run:
        for rev in pending[:20]:
            author = get_author_for_review(rev['review_url'])
            desc = build_description(rev['label'], author)
            log.info(f"  {rev['imdb_id']}  {rev['title']}")
            log.info(f"    URL:  {rev['review_url']}")
            log.info(f"    Desc: {desc}")
        if len(pending) > 20:
            log.info(f"  ... and {len(pending) - 20} more")
        return

    # Calculate session budget
    session_end = time.time() + (args.hours * 3600)
    work_block_start = time.time()
    submitted_this_session = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            slow_mo=random.randint(50, 150),
        )
        context = browser.new_context(
            viewport={'width': random.randint(1200, 1440),
                      'height': random.randint(800, 900)},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
            locale='en-US',
            timezone_id='America/New_York',
        )
        page = context.new_page()

        # Log in
        if not ensure_logged_in(page, context):
            log.error("Could not log in. Exiting.")
            browser.close()
            return

        log.info("Starting submissions...\n")

        for rev in pending:
            # Check session time
            if time.time() >= session_end:
                log.info(f"Session time limit reached ({args.hours}h).")
                break

            # Check if it's break time
            if should_take_break(work_block_start):
                take_break()
                work_block_start = time.time()

            imdb_id = rev['imdb_id']
            title = rev['title']
            review_url = rev['review_url']

            # Get author from the HTML file
            author = get_author_for_review(review_url)
            description = build_description(rev['label'], author)

            log.info(f"[{submitted_this_session + 1}] {title} ({imdb_id})")
            log.info(f"  URL:  {review_url}")
            log.info(f"  Desc: {description}")

            success, detail = submit_one_review(
                page, imdb_id, review_url, description, dry_run=args.dry_run)

            if success:
                log.info(f"  ✓ {detail}")
                progress['submitted'].append(imdb_id)
                progress['total_submitted'] += 1
                submitted_this_session += 1
            else:
                log.warning(f"  ✗ {detail}")
                progress['failed'].append({
                    'imdb_id': imdb_id,
                    'error': detail,
                    'timestamp': datetime.now().isoformat(),
                })

            log_submission(imdb_id, title, review_url,
                           'ok' if success else 'fail', detail)
            save_progress(progress)

            # Wait between submissions
            if time.time() < session_end:
                human_delay()

        # Save auth state for next session
        try:
            cookies = context.cookies()
            AUTH_STATE.write_text(json.dumps(cookies, indent=2))
        except Exception:
            pass

        browser.close()

    log.info(f"\nSession complete!")
    log.info(f"  Submitted this session: {submitted_this_session}")
    log.info(f"  Total submitted (all time): {progress['total_submitted']}")
    log.info(f"  Remaining: {len(pending) - submitted_this_session}")


def check_single(args):
    """Check/submit a single title."""
    imdb_id = args.check
    reviews = load_missing_reviews()
    rev = next((r for r in reviews if r['imdb_id'] == imdb_id), None)

    if not rev:
        log.error(f"{imdb_id} not found in {MISSING_CSV}")
        return

    author = get_author_for_review(rev['review_url'])
    description = build_description(rev['label'], author)

    log.info(f"Title:  {rev['title']} ({imdb_id})")
    log.info(f"URL:    {rev['review_url']}")
    log.info(f"Desc:   {description}")

    if args.dry_run:
        log.info("[DRY RUN] Would submit the above.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # always headed for single
        context = browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
        )
        page = context.new_page()

        if not ensure_logged_in(page, context):
            browser.close()
            return

        success, detail = submit_one_review(
            page, imdb_id, rev['review_url'], description)

        if success:
            log.info(f"✓ {detail}")
        else:
            log.warning(f"✗ {detail}")

        input("Press Enter to close the browser...")
        browser.close()


# ===================================================================
# Entry point
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Submit Nitrate Online reviews to IMDb External Reviews')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be submitted without touching IMDb')
    parser.add_argument('--headed', action='store_true',
                        help='Run with visible browser window')
    parser.add_argument('--hours', type=float, default=DEFAULT_SESSION_HOURS,
                        help=f'Session length in hours (default: {DEFAULT_SESSION_HOURS})')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last session (default behavior)')
    parser.add_argument('--reset', action='store_true',
                        help='Reset progress and start fresh')
    parser.add_argument('--check', type=str, metavar='IMDB_ID',
                        help='Check/submit a single title (e.g. tt0114746)')

    args = parser.parse_args()

    if args.reset:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
            log.info("Progress reset.")

    if args.check:
        check_single(args)
    else:
        run_session(args)


if __name__ == '__main__':
    main()
