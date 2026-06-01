#!/usr/bin/env python3
"""
tools/convert_bios.py
Convert legacy FrontPage bio pages to the nitrate.css design.
Usage: python3 tools/convert_bios.py
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

HEADER = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Nitrate Online</title>
  <meta name="description" content="{desc}">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=Raleway:wght@300;400;500;600;700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400;1,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="nitrate.css">
</head>
<body>

  <header class="masthead">
    <div class="masthead-inner">
      <a href="index.html" class="site-logo" aria-label="Nitrate Online — Home">
        <img src="logo.svg" alt="Nitrate Online" height="42">
      </a>
      <nav aria-label="Primary navigation">
        <ul class="primary-nav">
          <li><a href="index.html">Home</a></li>
          <li><a href="archive.html">Reviews</a></li>
          <li><a href="archive.html">Features</a></li>
          <li><a href="archive.html">Archive</a></li>
          <li><a href="aboutus.html" class="active">About</a></li>
          <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                 class="nav-search" target="_blank" rel="noopener"
                 aria-label="Search via Bing">Search</a></li>
        </ul>
      </nav>
    </div>
  </header>

  <nav class="breadcrumb" aria-label="Breadcrumb">
    <div class="breadcrumb-inner">
      <a href="index.html">Home</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <a href="aboutus.html">About</a>
      <span class="breadcrumb-sep" aria-hidden="true">›</span>
      <span aria-current="page">{name}</span>
    </div>
  </nav>

  <div class="article-header">
    <div class="article-header-inner">
      <p class="article-eyebrow">{role}</p>
      <h1 class="article-title">{name}</h1>
    </div>
  </div>

  <div class="info-layout">
    <div class="info-body">
'''

FOOTER = '''
    </div>
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
            <li><a href="2004/">2004</a></li>
            <li><a href="2003/">2003</a></li>
            <li><a href="2002/">2002</a></li>
            <li><a href="2001/">2001</a></li>
            <li><a href="2000/">2000</a></li>
            <li><a href="1999/">1999</a></li>
            <li><a href="1998/">1998</a></li>
            <li><a href="1997/">1997</a></li>
            <li><a href="1996/">1996</a></li>
          </ul>
        </nav>
        <nav class="footer-nav-col" aria-label="Site navigation">
          <h4>Site</h4>
          <ul>
            <li><a href="aboutus.html">About</a></li>
            <li><a href="links.html">Links</a></li>
            <li><a href="https://www.bing.com/search?q=site:nitrateonline.com+"
                   target="_blank" rel="noopener">Search</a></li>
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

  <script src="nitrate.js"></script>
</body>
</html>
'''

def photo_html(src, alt):
    return (f'      <img src="{src}" alt="{alt}" style="float:left;margin:0 1.5rem 1rem 0;'
            f'max-width:160px;border:1px solid var(--gold-dim);">\n')

BIOS = [
    {
        'file': 'carrie.html',
        'name': 'Carrie Gorringe',
        'role': 'Managing Editor',
        'desc': 'Carrie Gorringe is the Managing Editor of Nitrate Online.',
        'photo': 'images/carrie.gif',
        'body': '''\
      <p>Carrie Gorringe is the Managing Editor of <em>Nitrate Online</em> and a
      free-lance writer in Vancouver, Canada. She has been writing about film since
      1994. Her work has appeared on <em>London Calling Internet</em>, <em>Film.COM</em>,
      and <em>Dimension X Reeltalk</em>. Prior to writing about film, Carrie did
      graduate work in film, taught classes on film, and worked as an intern at the
      Motion Picture division of the Library of Congress. She holds degrees in Film
      and History from the University of Toronto.</p>
      <p><a href="carriecv.html">View Carrie's full résumé →</a></p>''',
    },
    {
        'file': 'eddie.html',
        'name': 'Eddie Cockrell',
        'role': 'Australia Editor',
        'desc': 'Eddie Cockrell is a film critic, public speaker and consulting programmer based in Sydney, Australia.',
        'photo': 'images/eddie.gif',
        'body': '''\
      <p>Eddie Cockrell is a film critic, public speaker and consulting programmer
      based in Sydney, Australia. For showbiz bible <em>Variety</em>, he reviews new
      international films from the Berlin, Karlovy Vary, Montreal and Toronto festivals,
      as well as notable DVD releases and the occasional Hollywood movie. He also writes
      the U.S. report to the annual <em>Variety International Film Guide</em>, reviews
      from selected festivals for <em>indieWIRE</em>, and pens catalogue notes for the
      annual "New Films from Germany" series at New York's Museum of Modern Art and the
      Visions cinema/bistro/lounge in Washington DC.</p>
      <p>Cockrell has contributed program notes to festivals in the Hamptons, Philadelphia,
      Sydney and Washington DC, serving as Senior Catalogue Editor and contributing
      programmer for Filmfest DC since its inception in 1986.</p>
      <p><a href="eddiecv.html">View Eddie's full résumé →</a></p>''',
    },
    {
        'file': 'gregory.html',
        'name': 'Gregory Avery',
        'role': 'Contributor',
        'desc': 'Gregory Avery is a film critic and contributor to Nitrate Online.',
        'photo': None,
        'body': '''\
      <p>Mr. Avery's interest in film dates back to when he was born in San Diego,
      California, in 1960, on the same day that Leslie Stevens' <em>Private Property</em>
      had its world premiere engagement in New York City, his mother's interest in the
      films of Gregory Peck, and to when his father, a lieutenant-commander in the U.S.
      Navy, met Harold Lloyd at the 1962 Cannes Film Festival.</p>
      <p>Mr. Avery had the privilege of living in Wisconsin, Virginia, Florida and the
      San Francisco Bay Area before settling in Medford, Oregon in 1971. He studied
      media communications at Brigham Young University and Southern Oregon State College
      before receiving a degree (in 1983) and working in film and video production, and
      in journalism. He has previously written about film for an Ashland, Oregon
      publication from 1989–91. Other interests include music, art, literature, history,
      and politics and world affairs.</p>''',
    },
    {
        'file': 'sean.html',
        'name': 'Sean Axmaker',
        'role': 'Contributor',
        'desc': 'Sean Axmaker is a film critic and contributor to Nitrate Online.',
        'photo': None,
        'body': '''\
      <p>I was born in 1963 and spent my early years in Oregon, my formative grade school
      years in Victoria, British Columbia, high school in Hawaii, and back to Oregon for
      college. My serious movie watching began with <em>Star Wars</em>, where my love of
      all things science fiction kicked my burgeoning interest in movies into a mania.</p>
      <p>After a misspent college stint — earning a Masters degree in Telecommunications
      and Film with my thesis on the career of Budd Boetticher — I began my career in
      video: 7½ years at Oregon's Flicks and Pics (6 years as manager) and 3 years at
      the legendary Scarecrow Video. Currently I reside in Seattle, Washington.</p>
      <p>In addition to writing for <em>Nitrate Online</em>, I contribute to
      <em>Film.com</em> (On Video, a weekly guide to Video, DVD and Laserdisc releases)
      and to the <em>Seattle Weekly</em>. I've contributed essays to local film programs
      and program notes to Seattle's Grand Illusion theater, and I'm currently a member
      of the Online Film Critics Society.</p>
      <dl style="margin-top:1.2rem;font-family:var(--font-ui);font-size:.82rem;display:flex;flex-direction:column;gap:.5rem;">
        <div><dt style="color:var(--gold);display:inline;">Favorite director:</dt> <dd style="display:inline;">Howard Hawks</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Director obsession:</dt> <dd style="display:inline;">Orson Welles</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Favorite films:</dt> <dd style="display:inline;"><em>The Searchers</em>, <em>Gun Crazy</em>, <em>French Can-Can</em>, <em>Touch of Evil</em>, and several Howard Hawks films</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Favorite performer:</dt> <dd style="display:inline;">Burt Lancaster</dd></div>
      </dl>''',
    },
    {
        'file': 'joe.html',
        'name': 'Joe Barlow',
        'role': 'Contributor',
        'desc': 'Joe Barlow is a freelance writer and film critic.',
        'photo': 'images/joe.gif',
        'body': '''\
      <p>Joe Barlow is a freelance writer who turned to film criticism after realizing
      his gross incompetence in everything else. A screenwriter and filmmaker, Joe won
      a small degree of national attention when his first cinematic offering — a spoof
      of <em>The Wizard of Oz</em> and <em>The Blair Witch Project</em> entitled
      <em>The Wicked Witch Project</em> — was featured on television and in newspapers
      from coast to coast.</p>
      <p>He is the author of <em>100 Nights in the Dark: A Collection of Contemporary
      Film Reviews and Essays</em> (ISBN: 0-595-16391-2).</p>
      <p>When he's not laughing his way through Joel Schumacher movies, Joe enjoys
      reading, playing guitar, and worrying about all kinds of evil things he can't
      change, such as death, taxes, and the frightening success of Pauly Shore.</p>''',
    },
    {
        'file': 'lyall.html',
        'name': 'Lyall Bush',
        'role': 'Contributor',
        'desc': 'Lyall Bush is a Seattle-based writer and Media Director of Washington Commission for the Humanities.',
        'photo': 'images/lyall.gif',
        'body': '''\
      <p>Lyall Bush is a Seattle-based writer and Media Director of Washington Commission
      for the Humanities. He is Editor at Large for <em>MovieMaker</em>, has written for
      <em>Film Comment</em>, <em>The Seattle Times</em>, and the Portland weekly
      <em>Willamette Week</em>. He is writing a book titled <em>Criminal Fictions</em>
      about fictional accounts of true crimes in books and movies.</p>''',
    },
    {
        'file': 'kj.html',
        'name': 'KJ Doughton',
        'role': 'Contributor',
        'desc': 'KJ Doughton is a film critic and contributor to Nitrate Online.',
        'photo': None,
        'body': '''\
      <p>KJ Doughton has resided in the northwest for most of his life, and has been
      writing about popular culture since 1982. He has written music reviews and features
      for such magazines as Seattle's <em>The Rocket</em>, <em>Bay Area Monthly</em>,
      <em>Tower Pulse</em>, Japan's <em>Burrn!</em>, and New York's
      <em>Guitar World</em>.</p>
      <p>He is the author of <em>Metallica Unbound</em>, published by Warner Books
      in 1993.</p>''',
    },
    {
        'file': 'emma.html',
        'name': 'Emma French',
        'role': 'Contributor',
        'desc': 'Emma French is a London-based Film, Theatre and English lecturer.',
        'photo': None,
        'body': '''\
      <p>Emma French is a London-based Film, Theatre and English lecturer and film
      reviewer for several online sites. She is currently completing a PhD in the
      marketing of Shakespeare on film, which she also plans to publish as a book.</p>''',
    },
    {
        'file': 'cynthia.html',
        'name': 'Cynthia Fuchs',
        'role': 'Contributor',
        'desc': 'Cynthia Fuchs is an associate professor of English, film & media studies at George Mason University.',
        'photo': None,
        'body': '''\
      <p>Cynthia Fuchs is an associate professor of English, film &amp; media studies,
      African American studies, and cultural studies at George Mason University, as well
      as a regular film, media, and book reviewer for the <em>Philadelphia Citypaper</em>,
      <em>popmatters.com</em> and <em>reelimagesmagazine.com</em>.</p>
      <p>She is the author of a variety of articles in books and journals, on topics
      ranging from Vietnam War, cyborg, porn, and interracial buddy movies, to Michael
      Jackson, the Artist, and Madonna, to grunge, queer punks, and hiphop.</p>''',
    },
    {
        'file': 'dave.html',
        'name': 'Dave Luty',
        'role': 'Contributor',
        'desc': 'Dave Luty is a New York-based film critic and script reader.',
        'photo': None,
        'body': '''\
      <p>Dave Luty has lived in the New York City area since September of 1996. He has
      worked as a script reader for Gotham Entertainment Group, the Independent Feature
      Project, and HBO NYC Productions. He has written on film for <em>The Queens
      Gazette</em> and <em>Film Journal International</em>.</p>''',
    },
    {
        'file': 'dan.html',
        'name': 'Dan Lybarger',
        'role': 'Contributor',
        'desc': 'Dan Lybarger is a Kansas City-based film critic and technical writer.',
        'photo': 'images/Dan.jpg',
        'body': '''\
      <p>In addition to contributing to <em>Nitrate Online</em>, Kansas Citian Dan
      Lybarger works as a technical writer and writes for the KC art journal
      <em>Review</em>. Previously, he was a contributing critic for <em>PitchWeekly</em>
      (a Kansas City alternative weekly with a readership of 296,000) from 1993 to
      May of 2000. Before that, he contributed reviews for the now-defunct
      <em>Spectrum Weekly</em> in Little Rock (1991–1992) and wrote profiles of
      Douglas Fairbanks, Jr. and Mel Brooks for <em>The (Buster) Keaton Chronicle</em>.</p>
      <p>Lybarger holds an M.A. in writing from the University of Arkansas at Little
      Rock and a B.A. in English from Ottawa University in Ottawa, KS.</p>''',
    },
    {
        'file': 'paula.html',
        'name': 'Paula Nechak',
        'role': 'Contributor',
        'desc': 'Paula Nechak is a freelance writer based in Seattle.',
        'photo': None,
        'body': '''\
      <p>Paula Nechak is a freelance writer based in Seattle. She is a regular
      contributor to <em>The Rocket</em>, <em>Stereophile Guide to Home Theatre</em>
      and <em>Amazon.com</em>. In addition, she has written for <em>MovieMaker
      Magazine</em> and <em>Filmmaker Magazine</em> (online). Her reviews and interviews
      can be found in <em>The Seattle Post-Intelligencer</em> and on the New York Times
      wire service.</p>''',
    },
    {
        'file': 'elias.html',
        'name': 'Elias Savada',
        'role': 'Contributor',
        'desc': 'Elias Savada is a film historian and copyright researcher based in Bethesda, Maryland.',
        'photo': None,
        'body': '''\
      <p>Raised in Harrison, NY, Elias Savada joined The American Film Institute
      immediately after his graduation from Cornell University in 1972, working on their
      ongoing project to catalog feature-length motion pictures produced and released in
      the United States. He returned to the AFI from 1983 to 1991, where he compiled a
      massive database of silent films released in the United States prior to 1911 —
      published in 1995 as the two-volume, 1,800-page <em>American Film Institute Catalog
      of Motion Pictures Produced in the United States: Film Beginnings, 1893–1910</em>,
      listing over 17,000 films.</p>
      <p>In 1977 Savada founded the Motion Picture Information Service (MPIS), which
      assists archives, festivals, and production companies with copyright research and
      film transportation worldwide. He has arranged for the transportation of more than
      2,000 films to institutions including the Cinemateca Portuguesa in Lisbon, the
      Filmoteca Española in Madrid, and the Pordenone Silent Film Festival.</p>
      <p>He is the co-author (with David J. Skal) of <em>Dark Carnival: The Secret World
      of Tod Browning, Hollywood's Master of the Macabre</em> (Doubleday, 1995).</p>''',
    },
    {
        'file': 'gianni.html',
        'name': 'Gianni Truzzi',
        'role': 'Contributor',
        'desc': 'Gianni Truzzi is a Seattle-based film critic writing for Seattle Weekly and Nitrate Online.',
        'photo': None,
        'body': '''\
      <p>In addition to <em>Nitrate Online</em>, Gianni Truzzi's reviews and features
      can be read regularly in <em>Seattle Weekly</em>, along with freelance contributions
      to other publications. Gianni has earned degrees in both Theater and Computer
      Science, and worked as an actor and software engineer before pursuing the writer's
      craft. He lives in Seattle with his wife and daughter.</p>
      <dl style="margin-top:1.2rem;font-family:var(--font-ui);font-size:.82rem;display:flex;flex-direction:column;gap:.5rem;">
        <div><dt style="color:var(--gold);display:inline;">Favorite film:</dt> <dd style="display:inline;"><em>The Candidate</em> (1972)</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Favorite writer:</dt> <dd style="display:inline;">David Mamet</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Favorite filmmaker:</dt> <dd style="display:inline;">John Sayles</dd></div>
        <div><dt style="color:var(--gold);display:inline;">Favorite actor:</dt> <dd style="display:inline;">William H. Macy</dd></div>
      </dl>''',
    },
    {
        'file': 'jerry.html',
        'name': 'Jerry White',
        'role': 'Contributor',
        'desc': 'Jerry White is a doctoral student in Comparative Literature at the University of Alberta.',
        'photo': None,
        'body': '''\
      <p>Jerry White is a doctoral student in Comparative Literature at the University
      of Alberta, where he also teaches Film Studies. He has written for publications in
      the United States, Canada, Quebec, India, Turkey, Australia, Austria and Denmark.</p>
      <p>He is the Ticket Manager of the Telluride Film Festival, a Program Consultant
      to the Philadelphia Festival of World Cinema (for whom he worked full time from
      1993 to 1996), and has curated a program of Arctic video for the Taos Talking
      Pictures Festival. Despite his quest for Canadian identity, he remains a
      Pirates fan.</p>''',
    },
]


def build_page(bio):
    header = HEADER.format(
        title=bio['name'],
        desc=bio['desc'],
        name=bio['name'],
        role=bio['role'],
    )
    body_parts = []
    if bio.get('photo'):
        body_parts.append(photo_html(bio['photo'], bio['name']))
    body_parts.append(bio['body'])
    body_parts.append('\n      <div style="clear:both;"></div>')
    return header + '\n'.join(body_parts) + '\n' + FOOTER


for bio in BIOS:
    path = ROOT / bio['file']
    content = build_page(bio)
    path.write_text(content, encoding='utf-8')
    print(f'  Written: {bio["file"]}')

print(f'\nDone — {len(BIOS)} bio pages converted.')
