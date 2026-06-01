#!/usr/bin/env python3
"""
convert_reviews.py
Convert 160 missing FrontPage HTML review files from git main branch
to the new nitrate.css design used on ModernDesign branch.
"""

import subprocess
import os
import re
import sys
from html.parser import HTMLParser
from html import unescape

REPO_DIR = "/Users/scott/Code/nitrateonline"

# Author link → name mapping
AUTHOR_MAP = {
    "carrie.html": "Carrie Gorringe",
    "eddie.html": "Eddie Cockrell",
    "joe.html": "Joe Barlow",
    "dan.html": "Dan Jardine",
    "lyall.html": "Lyall Bush",
    "kj.html": "KJ Doughton",
    "elias.html": "Elias Savada",
    "cynthia.html": "Cynthia Fuchs",
    "paolo.html": "Paolo Cabrelli",
    "michael.html": "Michael Dequina",
    "alex.html": "Alex Pell",
    "gary.html": "Gary Johnson",
    "paul.html": "Paul Brennan",
    "chris.html": "Chris Dashiell",
    "mel.html": "Mel Valentin",
}

# Files to place at ROOT level
ROOT_FILES = [
    "ralien.html", "rantz.html", "rarmaged.html", "ravengers.html", "rbarbwir.html",
    "rbaseket.html", "rbeloved.html", "rboogie.html", "rbulworth.html", "rcentral.html",
    "rdelta.html", "relizabeth.html", "renemy.html", "rfaculty.html", "rgeneral.html",
    "rgetshrt.html", "rgodmon.html", "rhiljack.html", "rjackieb.html", "rlifebeaut.html",
    "rlughnasa.html", "rlvoice.html", "rmulan.html", "roppositeofsex.html", "routsight.html",
    "rpatchadams.html", "rpecker.html", "rphantom.html", "rpmagic.html", "rprivateryan.html",
    "rpsntville.html", "rpsycho.html", "rronin.html", "rrushhour.html", "rrushmore.html",
    "rscream.html", "rseven.html", "rshakespeare.html", "rsnakeeyes.html", "rspecies2.html",
    "rsplan.html", "rswingers.html", "rtherock.html", "rtimekll.html", "rtoystry.html",
    "rtrumanshow.html", "rurban.html", "rvampires.html", "rverybad.html", "rwaterboy.htm",
]

# Files to place in 1996/ subfolder
FILES_1996 = [
    "rcasino.html", "rclock.html", "rdadetown.html", "rdevilb.html", "rgetshrt.html",
    "rheat.html", "rjumanji.html", "rllv.html", "rma.html", "rnixon.html", "roliver.html",
    "rsense.html", "rseven.html", "rtodiefor.html", "rtoystry.html", "rwaterwrld.html",
    "rwildbch.html",
]

# Files to place in 1997/ subfolder
FILES_1997 = [
    "r101pups.html", "rbcage.html", "rbutcherboy.html", "rbwaves.html", "rescape.html",
    "revita.html", "rhunch.html", "rid4.html", "rjmaguire.html", "rkolya.html",
    "rlapromesse.html", "rmarsattacks.html", "rmi.html", "rmulfalls.html", "rransom.html",
    "rtherock.html", "rtwister.html",
]

# Files to place in 1998/ subfolder
FILES_1998 = [
    "r101pups.html", "r12monky.html", "r2girls.html", "raceven.html", "rairforce1.html",
    "ralien.html", "ramistad.html", "rapostle.html", "rapower.html", "ratl.html",
    "rbarbwir.html", "rbarrow.html", "rbatman.html", "rbcage.html", "rbfwedding.html",
    "rboogie.html", "rbwaves.html", "rcasino.html", "rclock.html", "rconair.html",
    "rcontact.html", "rcopland.html", "rct.html", "rdevilb.html", "rdiabol.html",
    "rfaceoff.html", "rfifthe.html", "rfirstcon.html", "rgattaca.html", "rgetshrt.html",
    "rgldneye.html", "rgod.html", "rgoodas.html", "rgpblank.html", "rharry.html",
    "rheat.html", "rhereafter.html", "rhorse.html", "ricestorm.html", "rid4.html",
    "rinout.html", "rjackal.html", "rjackieb.html", "rjmaguire.html", "rjumanji.html",
    "rkids.html", "rlacon.html", "rllv.html", "rlovely.html", "rma.html",
    "rmadcity.html", "rmi.html", "rmib.html", "rmousehunt.html", "roscar.html",
    "rpeacemaker.html", "rpicperfect.html", "rpostman.html", "rrainmaker.html",
    "rransom.html", "rscream.html", "rseven.html", "rshowgrl.html", "rspanish.html",
    "rspawn.html", "rspeed2.html", "rsummer.html", "rswingers.html", "rtherock.html",
    "rtomorrow.html", "rtowong.html", "rtoystry.html", "rtwister.html", "rwag.html",
    "rwaterwrld.html", "rwildbch.html",
]


def get_file_from_git(filename):
    """Get file content from git main branch."""
    result = subprocess.run(
        ["git", "show", f"main:{filename}"],
        capture_output=True,
        cwd=REPO_DIR
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("windows-1252", errors="replace")


def clean_text(text):
    """Clean up HTML entities and special chars."""
    text = text.replace("&quot;", '"')
    text = text.replace("&#150;", "—")
    text = text.replace("&#x27;", "'")
    text = text.replace("&#146;", "'")
    text = text.replace("&#147;", "\u201c")
    text = text.replace("&#148;", "\u201d")
    text = text.replace("&#145;", "'")
    text = text.replace("&amp;", "&")
    text = text.replace("&nbsp;", "\u00a0")
    text = text.replace("&#151;", "—")
    text = text.replace("&#153;", "™")
    text = text.replace("&#169;", "©")
    text = text.replace("&#174;", "®")
    return text


def strip_tag_attrs(tag, html, keep_attrs=None):
    """Strip attributes from a specific tag except those in keep_attrs."""
    if keep_attrs is None:
        keep_attrs = []
    # This is used for cleaning up inline styles from <p> tags etc.
    pass


def extract_meta_description(html):
    """Extract meta description."""
    # Try double-quote delimited first
    m = re.search(r'<meta\s+name=["\']description["\']\s+content="(.*?)"', html, re.IGNORECASE | re.DOTALL)
    if m:
        return unescape(m.group(1))
    # Try single-quote delimited
    m = re.search(r"<meta\s+name=['\"]description['\"]\s+content='(.*?)'", html, re.IGNORECASE | re.DOTALL)
    if m:
        return unescape(m.group(1))
    return ""


def extract_title(html):
    """Extract film title from <title> tag."""
    m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
    if not m:
        return "Unknown"
    title = m.group(1)
    # Remove " - Nitrate Online Review" or similar suffixes
    title = re.sub(r'\s*[-–]\s*Nitrate Online.*$', '', title, flags=re.IGNORECASE)
    title = title.strip()
    return title


def extract_author(html):
    """Extract author link and name from 'Review by <a href=...>Name</a>'."""
    # Look for "Review by <a href="xxx.html"...>Name</a>"
    m = re.search(
        r'[Rr]eview\s+by\s+<a\s+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL
    )
    if m:
        href = m.group(1).strip()
        name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        # Normalize href to just the filename
        href = os.path.basename(href)
        # Look up name if not found
        if not name and href in AUTHOR_MAP:
            name = AUTHOR_MAP[href]
        elif not name:
            name = href.replace(".html", "").capitalize()
        return href, name
    return "carrie.html", "Carrie Gorringe"


def extract_year_from_content(html, default_year="1998"):
    """Try to detect year from posted date or content."""
    # Look for "Posted DD Month YYYY" pattern
    m = re.search(r'Posted\s+\d+\s+\w+\s+(\d{4})', html, re.IGNORECASE)
    if m:
        return m.group(1)
    # Look for copyright year
    m = re.search(r'Copyright[^1-9]*(\d{4})', html, re.IGNORECASE)
    if m:
        return m.group(1)
    return default_year


def extract_credits(html):
    """Extract film credits from the credits table."""
    credits = {}

    # Patterns to find credits in various formats:
    # "Directed by XXX", "Starring XXX", etc.
    credit_patterns = [
        (r'<em>\s*Directed\s+(?:and\s+\w+\s+)?by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Directed by"),
        (r'<i>\s*Directed\s+(?:and\s+\w+\s+)?by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Directed by"),
        (r'<em>\s*Starring\s*</em>\s*(.*?)(?=<p|</td|<strong><big><em>|<em>|</strong>|$)',
         "Starring"),
        (r'<i>\s*Starring\s*</i>\s*(.*?)(?=<p|</td|<strong><big><em>|<em>|</strong>|$)',
         "Starring"),
        (r'<em>\s*Screenplay\s+by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Screenplay by"),
        (r'<i>\s*Screenplay\s+by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Screenplay by"),
        (r'<em>\s*Written\s+(?:and\s+Directed\s+)?by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Written by"),
        (r'<i>\s*Written\s+(?:and\s+Directed\s+)?by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Written by"),
        (r'<em>\s*Based\s+on\s*(.*?)</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Based on"),
        (r'<em>\s*Produced\s+by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Produced by"),
        (r'<i>\s*Produced\s+by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Produced by"),
        (r'<em>\s*Cinematography\s+by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Cinematography by"),
        (r'<i>\s*Cinematography\s+by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Cinematography by"),
        (r'<em>\s*Music\s+by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Music by"),
        (r'<i>\s*Music\s+by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Music by"),
        (r'<em>\s*Edited\s+by\s*</em>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Edited by"),
        (r'<i>\s*Edited\s+by\s*</i>\s*(.*?)(?=<br|<p|</td|</strong|<em>|$)',
         "Edited by"),
    ]

    # Also handle the plain text "Directed by X" pattern inside strong/big tags
    plain_patterns = [
        (r'Directed\s+(?:and\s+Written\s+)?by\s+([^<\n]+?)(?=\s*<|\s*\n|$)', "Directed by"),
        (r'Starring\s+([^<\n]+?)(?=\s*<br|\s*</|\s*\n|$)', "Starring"),
        (r'Screenplay\s+by\s+([^<\n]+?)(?=\s*<|\s*\n|$)', "Screenplay by"),
    ]

    # Find credits table (between the first <hr> and the review paragraphs)
    # The credits are usually in a table before the review body
    hr_match = re.search(r'<hr[^>]*>', html, re.IGNORECASE)
    if hr_match:
        credits_section = html[hr_match.end():]
        # Find next <hr> or first review paragraph that starts with big/capital letter
        next_hr = re.search(r'<hr[^>]*>|<p>\s*<(?:big|font)', credits_section, re.IGNORECASE)
        if next_hr:
            credits_section = credits_section[:next_hr.start()]
    else:
        credits_section = html[:5000]  # fallback: check first 5000 chars

    # Try each credit pattern
    for pattern, label in credit_patterns:
        m = re.search(pattern, credits_section, re.IGNORECASE | re.DOTALL)
        if m and label not in credits:
            if label == "Based on":
                # Special case: "Based on X by Y"
                qualifier = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                value = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if value:
                    credits[label] = f"{qualifier} {value}".strip()
            else:
                raw = m.group(1)
                # Clean up the value
                val = re.sub(r'<br\s*/?>', ', ', raw, flags=re.IGNORECASE)
                val = re.sub(r'<[^>]+>', '', val)
                val = val.strip().strip(',').strip()
                val = re.sub(r'\s+', ' ', val)
                val = clean_text(val)
                # Clean up multiple commas and comma-space-comma patterns
                val = re.sub(r',\s*,+', ',', val)
                val = re.sub(r',\s+,', ',', val)
                val = val.strip().strip(',').strip()
                if val and len(val) > 1:
                    credits[label] = val

    # If we didn't find Directed by, try the plain pattern in the full credits section
    if "Directed by" not in credits:
        for pattern, label in plain_patterns:
            if label in credits:
                continue
            m = re.search(pattern, credits_section, re.IGNORECASE)
            if m:
                val = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                val = clean_text(val)
                if val and len(val) > 1:
                    credits[label] = val

    # Also try searching with big/strong/font tags wrapping the credit labels
    # Pattern: <strong><big><em>Directed by</em> NAME</big></strong>
    combined_pattern = r'<strong[^>]*>.*?<(?:em|i)>\s*(Directed\s+(?:and\s+\S+\s+)?by|Starring|Screenplay\s+by|Written\s+by|Produced\s+by|Based\s+on[^<]*|Cinematography\s+by|Music\s+by|Edited\s+by)\s*</(?:em|i)>\s*(.*?)(?=<(?:p|br|/td|/strong)|$)'
    for m in re.finditer(combined_pattern, credits_section, re.IGNORECASE | re.DOTALL):
        label_raw = m.group(1).strip()
        # Normalize label
        label = re.sub(r'\s+', ' ', label_raw)
        label = label.rstrip()
        value_raw = m.group(2)
        val = re.sub(r'<br\s*/?>', ', ', value_raw, flags=re.IGNORECASE)
        val = re.sub(r'<[^>]+>', '', val)
        val = val.strip().strip(',').strip()
        val = re.sub(r'\s+', ' ', val)
        val = clean_text(val)
        val = re.sub(r',\s*,+', ',', val)
        val = re.sub(r',\s+,', ',', val)
        val = val.strip().strip(',').strip()
        if val and len(val) > 1 and label not in credits:
            credits[label] = val

    return credits


def extract_review_body(html):
    """Extract the review body paragraphs."""
    # The review body starts after the credits table, after the first <hr>
    # and ends before the trailing navigation section

    # First, find the <hr> that separates the header from the content
    hr_match = re.search(r'<hr[^>]*>', html, re.IGNORECASE)
    if not hr_match:
        # No hr found, try to find body after the header table
        body_start = 0
    else:
        body_start = hr_match.end()

    body_html = html[body_start:]

    # Remove the film title heading paragraph (usually first big heading after hr)
    body_html = re.sub(
        r'<p[^>]*align=["\']center["\'][^>]*>\s*<font[^>]*size=["\']7["\'][^>]*><strong>.*?</strong></font>\s*</p>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove the "Review by Author / Posted date" paragraph
    body_html = re.sub(
        r'<p[^>]*align=["\']center["\'][^>]*>.*?[Rr]eview\s+by.*?</p>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove the credits table (div align=center containing the table with images/credits)
    body_html = re.sub(
        r'<div\s+align=["\']center["\']>\s*<center>.*?</center>\s*</div>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove trailing navigation (Contents | Features | Reviews...)
    body_html = re.sub(
        r'<hr[^>]*>.*?<p[^>]*align=["\']center["\'][^>]*>.*?(?:Contents|Features|Reviews).*?</p>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )
    # Also remove trailing nav with no hr
    body_html = re.sub(
        r'<p[^>]*align=["\']center["\'][^>]*>.*?(?:Contents|Features|Reviews).*?</p>\s*$',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove copyright lines at the end
    body_html = re.sub(
        r'<p[^>]*align=["\']center["\'][^>]*>\s*<font[^>]*>\s*<em>Copyright.*?</em>\s*</font>\s*</p>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )
    body_html = re.sub(
        r'<p[^>]*>\s*<font[^>]*>\s*<em>Copyright.*?</em>\s*</font>\s*</p>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove <img> tags
    body_html = re.sub(r'<img[^>]*/?>', '', body_html, flags=re.IGNORECASE)

    # Remove target="_top" attributes
    body_html = re.sub(r'\s+target=["\']_top["\']', '', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'\s+target=["\'][^"\']*["\']', '', body_html, flags=re.IGNORECASE)

    # Clean up font tags (remove them but keep content)
    body_html = re.sub(r'<font[^>]*>', '', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'</font>', '', body_html, flags=re.IGNORECASE)

    # Clean up big tags (remove them but keep content)
    body_html = re.sub(r'<big>', '', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'</big>', '', body_html, flags=re.IGNORECASE)

    # Remove center tags
    body_html = re.sub(r'</?center>', '', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'<div[^>]*align=["\']center["\'][^>]*>', '', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'</div>', '', body_html, flags=re.IGNORECASE)

    # Clean p tag attributes (align, style, etc.)
    body_html = re.sub(r'<p\s+[^>]*>', '<p>', body_html, flags=re.IGNORECASE)

    # Convert <i> to <em>
    body_html = re.sub(r'<i>', '<em>', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'</i>', '</em>', body_html, flags=re.IGNORECASE)

    # Convert <b> to <strong>
    body_html = re.sub(r'<b>', '<strong>', body_html, flags=re.IGNORECASE)
    body_html = re.sub(r'</b>', '</strong>', body_html, flags=re.IGNORECASE)

    # Clean up <a> tags - remove store/imdb links, keep review links
    # Remove store/imdb/default links
    body_html = re.sub(
        r'<a\s+[^>]*href=["\'][^"\']*(?:storeitm|imdb\.com|default\.htm|store\.html|archive\.html)[^"\']*["\'][^>]*>.*?</a>',
        '', body_html, flags=re.IGNORECASE | re.DOTALL
    )

    # Clean HTML entities
    body_html = clean_text(body_html)

    # Extract just the <p>...</p> blocks
    paragraphs = re.findall(r'<p>(.*?)</p>', body_html, re.IGNORECASE | re.DOTALL)

    # Also get <h2> tags (some reviews have subheadings)
    # Get all meaningful block elements in order
    blocks = re.findall(r'<(?:p|h[2-4])[^>]*>.*?</(?:p|h[2-4])>', body_html, re.IGNORECASE | re.DOTALL)

    if not blocks:
        # Fallback: try to get content between <p> tags without closing tags
        # or content that follows the credits
        pass

    result_parts = []
    for block in blocks:
        # Clean up the block
        text = block.strip()

        # Skip if it's just whitespace or nav links
        text_only = re.sub(r'<[^>]+>', '', text).strip()
        if not text_only:
            continue
        # Skip nav paragraphs
        if re.search(r'Contents\s*\|\s*Features', text_only, re.IGNORECASE):
            continue
        if re.search(r'Copyright.*Nitrate', text_only, re.IGNORECASE):
            continue
        # Skip credit-only paragraphs (the ones we already handled)
        if re.search(r'^(?:Directed|Starring|Screenplay)', text_only.strip()):
            continue

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        result_parts.append(text)

    if not result_parts:
        # Last resort: collect all text between the first review paragraph and end
        # Look for first paragraph that starts with a large letter or quote
        review_text = body_html.strip()
        result_parts = [review_text] if review_text else ["<p>Review text unavailable.</p>"]

    return "\n\n".join(result_parts)


def build_credits_html(credits):
    """Build the film-credits <dl> HTML."""
    if not credits:
        return ""

    # Preferred order
    order = [
        "Directed by", "Written by", "Screenplay by", "Based on",
        "Starring", "Produced by", "Cinematography by", "Music by", "Edited by"
    ]

    lines = []
    seen = set()

    for label in order:
        if label in credits and label not in seen:
            seen.add(label)
            val = credits[label]
            lines.append(f'            <div class="film-credit">')
            lines.append(f'              <dt class="credit-label">{label}</dt>')
            lines.append(f'              <dd class="credit-value">{val}</dd>')
            lines.append(f'            </div>')

    # Add any remaining credits not in the preferred order
    for label, val in credits.items():
        if label not in seen:
            lines.append(f'            <div class="film-credit">')
            lines.append(f'              <dt class="credit-label">{label}</dt>')
            lines.append(f'              <dd class="credit-value">{val}</dd>')
            lines.append(f'            </div>')

    return "\n".join(lines)


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{FILM_TITLE} — Nitrate Online</title>
  <meta name="description" content="{DESCRIPTION}">
  <link rel="icon" href="{PATH}favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=Raleway:wght@300;400;500;600;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{PATH}nitrate.css">
  <script type="text/javascript">
    (function(c,l,a,r,i,t,y){{
        c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    }})(window, document, "clarity", "script", "vw8ttkpeq2");
  </script>
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-KS8ZVV0EZX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-KS8ZVV0EZX');
  </script>
</head>
<body>

  <header class="masthead">
    <div class="masthead-inner">
      <a href="{PATH}index.html" class="site-logo" aria-label="Nitrate Online — Home">
        <img src="{PATH}logo.svg" alt="Nitrate Online" height="42">
      </a>
      <nav aria-label="Primary navigation">
        <ul class="primary-nav">
          <li><a href="{PATH}index.html">Home</a></li>
          <li><a href="{PATH}archive.html">Archive</a></li>
          <li><a href="{PATH}aboutus.html">About</a></li>
          <li><a href="{PATH}search.html" class="nav-search" aria-label="Search"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="vertical-align:middle;margin-right:.25rem;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Search</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <div class="breadcrumb-inner">
      <a href="{PATH}index.html">Home</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <a href="{PATH}archive.html">Reviews</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <span aria-current="page">{FILM_TITLE}</span>
    </div>
  </nav>

  <div class="article-header">
    <div class="article-header-inner">
      <p class="article-eyebrow">Review &nbsp;·&nbsp; {YEAR}</p>
      <h1 class="article-title"><em>{FILM_TITLE}</em></h1>
      <p class="article-meta"><span class="meta-byline">Review by <a href="{AUTHOR_LINK}">{AUTHOR_NAME}</a></span></p>
    </div>
  </div>

  <div class="article-layout">

    <article class="article-body" aria-label="Review">
{REVIEW_BODY}
      <div class="article-footer">
        <div class="article-footer-rule">
          <div class="footer-rule-line"></div>
          <div class="footer-diamond"></div>
          <div class="footer-rule-line"></div>
        </div>
        <div class="article-footer-meta">
          <p>Review by <a href="{AUTHOR_LINK}">{AUTHOR_NAME}</a> &nbsp;·&nbsp; Nitrate Online</p>
        </div>
      </div>
    </article>

    <aside class="article-sidebar" aria-label="Film information and navigation">

      <div class="film-card">
        <div class="film-card-poster">
          <div class="film-card-poster-placeholder">&#9654;</div>
        </div>
        <div class="film-card-body">
          <h2 class="film-card-title"><em>{FILM_TITLE}</em> ({YEAR})</h2>
          <dl class="film-credits">
{CREDITS_HTML}
          </dl>
        </div>
      </div>

      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Archive</h3></div>
        <div class="widget-body">
          <div class="archive-tags">
            <a href="{PATH}2004/">2004</a>
            <a href="{PATH}2003/">2003</a>
            <a href="{PATH}2002/">2002</a>
            <a href="{PATH}2001/">2001</a>
            <a href="{PATH}2000/">2000</a>
            <a href="{PATH}1999/">1999</a>
            <a href="{PATH}1998/">1998</a>
            <a href="{PATH}1997/">1997</a>
            <a href="{PATH}1996/">1996</a>
          </div>
        </div>
      </div>

      <div class="sidebar-widget">
        <div class="widget-header"><h3 class="widget-title">Search</h3></div>
        <div class="widget-body">
          <form class="search-form" aria-label="Site search">
            <input class="search-input" type="text" placeholder="Film or director…" aria-label="Search">
            <button class="search-btn" type="submit">Go</button>
          </form>
        </div>
      </div>

    </aside>
  </div>

  <footer>
    <div class="footer-inner">
      <div class="footer-top">
        <div>
          <p class="footer-wordmark">Nitrate Online</p>
          <p class="footer-tagline">In-depth film criticism and festival coverage, 1996–2004.</p>
        </div>
        <nav class="footer-nav-col" aria-label="Archive navigation">
          <h4>Archive</h4>
          <ul>
            <li><a href="{PATH}2004/">2004</a></li>
            <li><a href="{PATH}2003/">2003</a></li>
            <li><a href="{PATH}2002/">2002</a></li>
            <li><a href="{PATH}2001/">2001</a></li>
            <li><a href="{PATH}2000/">2000</a></li>
            <li><a href="{PATH}1999/">1999</a></li>
            <li><a href="{PATH}1998/">1998</a></li>
            <li><a href="{PATH}1997/">1997</a></li>
            <li><a href="{PATH}1996/">1996</a></li>
          </ul>
        </nav>
        <nav class="footer-nav-col" aria-label="Site navigation">
          <h4>Site</h4>
          <ul>
            <li><a href="{PATH}aboutus.html">About</a></li>
            <li><a href="{PATH}links.html">Links</a></li>
            <li><a href="{PATH}search.html">Search</a></li>
          </ul>
        </nav>
      </div>
      <div class="footer-bottom">
        <p class="footer-copy">
          Copyright &copy; 1996–2004 Nitrate Productions, Inc. &nbsp;·&nbsp; nitrateonline.com
        </p>
        <div class="footer-ornament">
          <div class="d-chev d-chev-l"></div>
          <span>Nitrate Online</span>
          <div class="d-chev d-chev-r"></div>
        </div>
      </div>
    </div>
  </footer>

  <script src="{PATH}nitrate.js"></script>
</body>
</html>"""


def convert_file(source_filename, output_path, path_prefix, year_hint=None):
    """Convert a single source file and write to output_path."""
    html = get_file_from_git(source_filename)
    if html is None:
        return False, f"File not found in git: main:{source_filename}"

    # Extract components
    film_title = extract_title(html)
    description = extract_meta_description(html)
    author_href, author_name = extract_author(html)

    # Determine year
    if year_hint:
        year = year_hint
    else:
        year = extract_year_from_content(html, "1998")

    # Look up author name from map if we have the href
    if author_href in AUTHOR_MAP and (not author_name or author_name == author_href):
        author_name = AUTHOR_MAP[author_href]

    # Build author link with path prefix
    author_link = f"{path_prefix}{author_href}"

    # Extract credits
    credits = extract_credits(html)
    credits_html = build_credits_html(credits)

    # Extract review body
    review_body = extract_review_body(html)

    # Truncate description if too long
    if len(description) > 500:
        description = description[:497] + "..."

    # Escape description for HTML attribute
    description = description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

    # Build the output HTML
    output = TEMPLATE.format(
        FILM_TITLE=film_title,
        DESCRIPTION=description,
        PATH=path_prefix,
        YEAR=year,
        AUTHOR_LINK=author_link,
        AUTHOR_NAME=author_name,
        REVIEW_BODY=review_body,
        CREDITS_HTML=credits_html,
    )

    # Write the file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    return True, f"OK: {output_path}"


def check_already_exists(path):
    """Never skip - always overwrite to apply latest fixes."""
    return False


def main():
    written = []
    skipped = []
    errors = []

    # Build the full list of (source_filename, output_path, path_prefix, year_hint)
    tasks = []

    # ROOT files
    for fname in ROOT_FILES:
        out_path = os.path.join(REPO_DIR, fname)
        tasks.append((fname, out_path, "", None))

    # 1996 files
    for fname in FILES_1996:
        out_path = os.path.join(REPO_DIR, "1996", fname)
        tasks.append((fname, out_path, "../", "1996"))

    # 1997 files
    for fname in FILES_1997:
        out_path = os.path.join(REPO_DIR, "1997", fname)
        tasks.append((fname, out_path, "../", "1997"))

    # 1998 files
    for fname in FILES_1998:
        out_path = os.path.join(REPO_DIR, "1998", fname)
        tasks.append((fname, out_path, "../", "1998"))

    total = len(tasks)
    print(f"Processing {total} file conversion tasks...")
    print()

    for i, (src, out_path, path_prefix, year_hint) in enumerate(tasks, 1):
        if check_already_exists(out_path):
            skipped.append(out_path)
            print(f"[{i:3d}/{total}] SKIP (exists): {out_path}")
            continue

        ok, msg = convert_file(src, out_path, path_prefix, year_hint)
        if ok:
            written.append(out_path)
            print(f"[{i:3d}/{total}] WRITE: {out_path}")
        else:
            errors.append((src, msg))
            print(f"[{i:3d}/{total}] ERROR: {msg}")

    print()
    print("=" * 60)
    print(f"SUMMARY:")
    print(f"  Written:  {len(written)}")
    print(f"  Skipped:  {len(skipped)} (already existed)")
    print(f"  Errors:   {len(errors)}")
    if errors:
        print()
        print("ERRORS:")
        for src, msg in errors:
            print(f"  {src}: {msg}")


if __name__ == "__main__":
    main()
