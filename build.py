#!/usr/bin/env python3
"""Static site generator for the portfolio.

Reads content/site.json and content/projects/*.json and writes plain HTML
pages (index.html, about/, professional_works/<slug>/, ...) into the repo
root so the site can be served directly by GitHub Pages.

Usage: python3 build.py
"""
import datetime
import json
import os
import re
import shutil
from html import escape, unescape

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8"))
PROJECTS = {}
for name in os.listdir(os.path.join(ROOT, "content", "projects")):
    if name.endswith(".json"):
        p = json.load(open(os.path.join(ROOT, "content", "projects", name), encoding="utf-8"))
        PROJECTS[p["slug"]] = p

YEAR = datetime.date.today().year

NAV = [
    ("Work", "professional_works/", "professional_works"),
    ("Other Works", "other_works/", "other_works"),
    ("About", "about/", "about"),
    ("Services", "service/", "service"),
    ("Contact", "contact/", "contact"),
]


def icon(name):
    paths = {
        "arrow-ur": '<path d="M7 17 17 7M8 7h9v9"/>',
        "arrow-r": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "arrow-l": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
        "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
        "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
        "phone": '<path d="M6.6 3.5h2.8l1.4 4.2-2 1.3a11 11 0 0 0 6.2 6.2l1.3-2 4.2 1.4v2.8a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z"/>',
        "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
        "linkedin": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10v7M8 7v.01M12 17v-4a2 2 0 0 1 4 0v4M12 10v7"/>',
        "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
        "search": '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
        "pin": '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    }
    return f'<svg class="i" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</svg>'


SERVICE_ICONS = [
    '<ellipse cx="12" cy="12" rx="10" ry="4"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)"/>',
    '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/>',
    '<circle cx="6.5" cy="15" r="3.5"/><circle cx="17.5" cy="15" r="3.5"/><path d="M10 15h4M3 15l2-8h3M21 15l-2-8h-3"/>',
    '<path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
    '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="3" y="16" width="6" height="5" rx="1"/><rect x="15" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M6 16v-4h12v4"/>',
    '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2a6.5 6.5 0 0 1 3.5 5.8"/>',
]


def text(html):
    return unescape(re.sub(r"<[^>]+>", "", html)).strip()


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def ext(href, label, cls=""):
    return f'<a class="{cls}" href="{escape(href)}" target="_blank" rel="noopener">{label}</a>'


def resume(base):
    return base + SITE["links"]["resume"]


def fix_links(html, base):
    """Rewrite Framer-relative links, open external links in a new tab, trim stray <br>s."""
    html = re.sub(r"^(\s*<br>\s*)+|(\s*<br>\s*)+$", "", html)

    def local(m):
        s = m.group(1)
        sec = PROJECTS[s]["section"] if s in PROJECTS else "other_works"
        return f'href="{base}{sec}/{s}/"'

    html = re.sub(r'href="\./([a-z0-9\-]+)"', local, html)
    html = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', html)
    return html


def img(src, base, alt="", cls="", eager=False):
    loading = "" if eager else ' loading="lazy" decoding="async"'
    return f'<img class="{cls}" src="{base}{escape(src)}" alt="{escape(alt)}"{loading}>'


def tags_of(p):
    return [t.strip() for t in p.get("tags", "").split("|") if t.strip()]


def search_index(base):
    L = SITE["links"]
    items = [
        {"t": "Home", "s": "Page", "u": base or "./"},
        {"t": "Professional works", "s": "Page", "u": base + "professional_works/"},
        {"t": "Other works", "s": "Page", "u": base + "other_works/"},
        {"t": "About", "s": "Page", "u": base + "about/"},
        {"t": "Services", "s": "Page", "u": base + "service/"},
        {"t": "Contact", "s": "Page", "u": base + "contact/"},
        {"t": "Resume (PDF)", "s": "Link", "u": base + L["resume"], "x": 1},
        {"t": "Book a call", "s": "Link", "u": L["calendly"], "x": 1},
        {"t": "LinkedIn", "s": "Link", "u": L["linkedin"], "x": 1},
        {"t": "Email " + SITE["email"], "s": "Link", "u": "mailto:" + SITE["email"]},
    ]
    for key, label in (("professional", "Professional work"), ("other", "Side project")):
        for s in SITE[key]:
            q = PROJECTS[s]
            items.append({"t": q["title"], "s": f'{label} · {q.get("category", "")}', "u": url_for(q, base)})
    return json.dumps(items, ensure_ascii=False).replace("</", "<\\/")


def url_for(p, base):
    return f'{base}{p["section"]}/{p["slug"]}/'


def excerpt(p, n=190):
    src = (p.get("overview") or [b["h"] for b in p["blocks"] if b["t"] == "p" and "list" not in b] or [""])[0]
    t = text(src)
    return t if len(t) <= n else t[: n].rsplit(" ", 1)[0] + "…"


# ---------- layout ----------

def page(title, active, base, body, description=None, body_class=""):
    current = ' aria-current="page"'
    nav = "".join(
        f'<a href="{base}{href}"{current if key == active else ""}>{label}</a>'
        for label, href, key in NAV
    )
    desc = escape(description or SITE["intro"])
    full_title = escape(f'{title} — {SITE["name"]}' if title else f'{SITE["name"]} — Product & UX Designer')
    L = SITE["links"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:image" content="{SITE["url"]}{SITE["photoSquare"]}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#000000">
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Gabarito:wght@400..900&family=Red+Hat+Display:wght@400;500;600&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/css/style.css">
<script>document.documentElement.classList.add("js");if(/[?&]shot(&|=|$)/.test(location.search))document.documentElement.classList.add("shot");if(!("onpagereveal" in window))document.documentElement.classList.add("no-vt")</script>
</head>
<body class="{body_class}">
<div class="loader" aria-hidden="true"><p class="loader-word" data-greetings='{GREETINGS}'>Hello</p></div>
<canvas class="glow-canvas" aria-hidden="true"></canvas>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{base}" aria-label="{escape(SITE["name"])} — home">
      <img class="brand-mark" src="{base}{SITE["avatar"]}" alt="" width="36" height="36"><span class="brand-name">{escape(SITE["name"])}</span><span class="brand-role">— Product designer</span>
    </a>
    <nav class="nav" aria-label="Main">{nav}</nav>
    {ext(L["calendly"], "Let’s talk " + icon("arrow-ur"), "btn btn-accent btn-sm header-cta")}
    <button class="search-btn" type="button" aria-label="Search projects and pages" data-open-palette>{icon("search")}<kbd>⌘K</kbd></button>
    <button class="menu-toggle" aria-label="Open menu" aria-expanded="false" aria-controls="mobile-menu"><span></span><span></span></button>
  </div>
  <div class="mobile-menu" id="mobile-menu" data-lenis-prevent>
    <a href="{base}">Home</a>{nav}
    {ext(L["calendly"], "Let’s talk " + icon("arrow-ur"), "btn btn-accent")}
  </div>
</header>
<main id="main">
{body}
</main>
{footer(base)}
<div class="palette" data-lenis-prevent role="dialog" aria-modal="true" aria-label="Search" hidden>
  <div class="palette-box">
    <input class="palette-input" type="search" placeholder="Jump to a project or page…" aria-label="Search" autocomplete="off">
    <ul class="palette-list" role="listbox"></ul>
    <p class="palette-hint"><kbd>↑</kbd><kbd>↓</kbd> to move · <kbd>Enter</kbd> to open · <kbd>Esc</kbd> to close</p>
  </div>
</div>
<div class="lightbox" hidden><img alt=""><button type="button" aria-label="Close image">×</button></div>
<script>window.__INDEX={search_index(base)}</script>
<script src="{base}assets/js/vendor/lenis.min.js" defer></script>
<script src="{base}assets/js/main.js" defer></script>
</body>
</html>
"""


def footer(base):
    L = SITE["links"]
    return f"""<footer class="site-footer">
  <div class="wrap footer-grid">
    <div>
      <a class="brand" href="{base}"><img class="brand-mark" src="{base}{SITE["avatar"]}" alt="" width="36" height="36"><span class="brand-name">{escape(SITE["name"])}</span></a>
      <p class="muted footer-blurb">{escape(SITE["contactBlurb"])}</p>
    </div>
    <div>
      <h2 class="label">Pages</h2>
      <ul class="footer-links">
        <li><a href="{base}professional_works/">Professional works</a></li>
        <li><a href="{base}other_works/">Other works</a></li>
        <li><a href="{base}about/">About</a></li>
        <li><a href="{base}service/">Services</a></li>
        <li><a href="{base}contact/">Contact</a></li>
      </ul>
    </div>
    <div>
      <h2 class="label">Elsewhere</h2>
      <ul class="footer-links">
        <li>{ext(L["linkedin"], "LinkedIn")}</li>
        <li>{ext(resume(base), "Resume")}</li>
        <li>{ext(L["calendly"], "Book a call")}</li>
        <li><a href="mailto:{SITE["email"]}">{SITE["email"]}</a></li>
      </ul>
    </div>
  </div>
  <div class="wrap footer-bottom">
    <span>&copy; <span data-year>{YEAR}</span> {escape(SITE["name"])}<span class="footer-time" data-local-time data-prefix=" · Bangalore "></span></span>
    <a href="#main" class="to-top">Back to top ↑</a>
  </div>
</footer>"""


# ---------- components ----------

GREETINGS = escape(json.dumps([
    ["Hello", "en"], ["Hej", "sv"], ["നമസ്കാരം", "ml"], ["Hola", "es"], ["Bonjour", "fr"],
    ["Ciao", "it"], ["Olá", "pt"], ["こんにちは", "ja"], ["你好", "zh"], ["مرحبا", "ar"],
    ["Hi, I’m Gauthem.", "en"],
], ensure_ascii=False), quote=True)


def section_head(label, title, aside=""):
    if aside and not aside.lstrip().startswith("<"):
        aside = f'<p class="section-desc">{aside}</p>'
    return f"""<div class="section-head reveal">
  <div><p class="label">{label}</p><h2 class="section-title">{title}</h2></div>
  {aside}
</div>"""


def ticker():
    items = "".join(f'<span>{escape(s)}</span><span class="sep" aria-hidden="true">/</span>' for s in SITE["skills"])
    return f"""<div class="ticker" aria-label="Skills"><div class="ticker-track">{items * 4}</div></div>"""


def stats():
    rows = SITE["stats"]
    cells = "".join(f'<div class="stat reveal"><strong data-count>{v}</strong><span>{escape(l)}</span></div>' for v, l in rows)
    return f'<section class="stats wrap" id="highlights" aria-label="Highlights">{cells}</section>'


def feature_row(p, i, base):
    tags = "".join(f"<li>{escape(t)}</li>" for t in tags_of(p))
    meta = " · ".join(x for x in [p.get("employer"), p.get("period")] if x)
    return f"""<article class="feature reveal">
  <a class="feature-link" href="{url_for(p, base)}">
    <span class="badge">{i:02d}</span>
    <span class="feature-corner">{escape(p.get("role") or p.get("domain") or p.get("category", ""))}</span>
    <div class="feature-media" style="view-transition-name:cover-{p["slug"]}">{img(p["cover"], base, p["title"])}</div>
    <div class="feature-body">
      <p class="feature-meta">{escape(meta)}</p>
      <h3>{escape(p["title"])}</h3>
      <ul class="chips">{tags}</ul>
      <p class="feature-excerpt">{escape(excerpt(p, 150))}</p>
      <span class="pill-btn">View case study {icon("arrow-r")}</span>
    </div>
  </a>
</article>"""


def work_card(p, base, show_tags=True):
    tag = escape(tags_of(p)[0]) if show_tags and tags_of(p) else ""
    return f"""<a class="work-card reveal" href="{url_for(p, base)}" data-category="{escape(p.get("category", ""))}">
  <div class="work-media" style="view-transition-name:cover-{p["slug"]}">{img(p["cover"], base, p["title"])}<span class="work-arrow">{icon("arrow-ur")}</span></div>
  <div class="work-info">
    <div><h3>{escape(p["title"])}</h3><p>{escape(p.get("category", ""))}</p></div>
    {f'<span class="pill">{tag}</span>' if tag else ""}
  </div>
</a>"""


def filters(projects):
    cats = []
    for p in projects:
        c = p.get("category", "")
        if c and c not in cats:
            cats.append(c)
    btns = '<button class="filter is-active" data-filter="all" aria-pressed="true">All <span>{}</span></button>'.format(len(projects))
    for c in cats:
        n = sum(1 for p in projects if p.get("category") == c)
        btns += f'<button class="filter" data-filter="{escape(c)}" aria-pressed="false">{escape(c)} <span>{n}</span></button>'
    return f'<div class="filters" role="group" aria-label="Filter projects">{btns}</div>'


def experience_list(detailed=False):
    rows = ""
    for e in SITE["experience"]:
        note = f' · {escape(e["note"])}' if e.get("note") else ""
        points = e["points"] if detailed else e["points"][:1]
        pts = "".join(f"<li>{escape(x)}</li>" for x in points)
        rows += f"""<li class="exp reveal"><span class="exp-period">{escape(e["period"])}</span><span class="exp-role">{escape(e["role"])}</span><span class="exp-place">{escape(e["org"])}{note}</span><ul class="exp-points">{pts}</ul></li>"""
    return f'<ol class="exp-list">{rows}</ol>'


def education_list():
    return "".join(
        f"""<li class="edu reveal"><span class="label">{escape(x["kind"])} · {escape(x["year"])}</span><strong>{escape(x["title"])}</strong><span class="muted">{escape(x["org"])}</span></li>"""
        for x in SITE["education"]
    )


def service_cards(full=True):
    out = ""
    for i, s in enumerate(SITE["services"]):
        items = "".join(f"<li>{icon('check')}{escape(it)}</li>" for it in s["items"])
        body = f'<p>{escape(s["text"])}</p>' if full else ""
        out += f"""<article class="service reveal">
  <div class="service-top"><span class="index">{i + 1:02d}</span><svg class="service-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{SERVICE_ICONS[i % len(SERVICE_ICONS)]}</svg></div>
  <h3>{escape(s["title"])}</h3>
  {body}
  <ul class="checks">{items}</ul>
</article>"""
    return out


def toolkit(base):
    return "".join(
        f'<li class="tool reveal">{img(t["icon"], base, "")}<span>{escape(t["name"])}</span></li>' for t in SITE["stack"]
    )


def cta(base):
    L = SITE["links"]
    return f"""<section class="cta wrap">
  <div class="cta-card reveal">
    <div class="cta-glow" aria-hidden="true"></div>
    <p class="label">Have a project in mind?</p>
    <h2>Let’s build something <em>people love</em> to use.</h2>
    <div class="cta-actions">
      {ext(L["calendly"], icon("calendar") + " Book a call", "btn btn-accent btn-lg")}
      <a class="btn btn-ghost btn-lg" href="mailto:{SITE["email"]}">{icon("mail")} {SITE["email"]}</a>
    </div>
  </div>
</section>"""


# ---------- rich-text blocks ----------

def heading_shift(blocks):
    levels = [int(b["t"][1]) for b in blocks if b["t"] in ("h1", "h2", "h3")]
    return (min(levels) if levels else 2) - 2


def render_blocks(blocks, base, toc=None):
    out = []
    list_open = None
    shift = heading_shift(blocks)
    for b in blocks:
        t = b["t"]
        lst = b.get("list")
        if list_open and lst != list_open:
            out.append(f"</{list_open}>")
            list_open = None
        if t == "img":
            cap = f'<figcaption>{escape(b["caption"])}</figcaption>' if b.get("caption") else ""
            out.append(f'<figure class="shot reveal">{img(b["src"], base, b.get("alt", ""))}{cap}</figure>')
        elif t == "quiz":
            opts = "".join(
                f'<li><button type="button" class="quiz-opt" data-correct="{1 if k == b["answer"] else 0}"><span class="quiz-key">{"ABCDE"[k]}</span>{escape(o)}</button></li>'
                for k, o in enumerate(b["options"])
            )
            out.append(f"""<div class="quiz reveal" data-quiz>
  <div class="quiz-bar"><span class="quiz-tag">{escape(b.get("tag", ""))}</span><span class="quiz-meta">{escape(b.get("meta", ""))}</span></div>
  <p class="quiz-q">{escape(b["question"])}</p>
  <ol class="quiz-opts">{opts}</ol>
  <div class="quiz-expl" hidden><p class="quiz-result"></p><p><strong>{escape(b.get("explainer", "Explanation"))}:</strong> {escape(b["explanation"])}</p><button type="button" class="quiz-reset">Try again</button></div>
  <p class="quiz-caption">{escape(b.get("caption", ""))}</p>
</div>""")
        elif t == "video":
            cap = f'<figcaption>{escape(b["caption"])}</figcaption>' if b.get("caption") else ""
            out.append(
                f'<figure class="shot reveal"><video src="{base}{escape(b["src"])}" poster="{base}{escape(b.get("poster", ""))}" '
                f'autoplay muted loop playsinline preload="metadata" aria-label="{escape(b.get("caption", ""))}"></video>{cap}</figure>'
            )
        elif t == "button":
            out.append(f'<p>{ext(b["href"], escape(b["label"]) + " " + icon("arrow-ur"), "btn btn-accent")}</p>')
        elif lst:
            if not list_open:
                out.append(f"<{lst}>")
                list_open = lst
            out.append(f'<li>{fix_links(b["h"], base)}</li>')
        elif t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = int(t[1])
            if lvl <= 3:
                lvl = max(2, lvl - shift)
            else:
                lvl = min(6, max(4, lvl))
            inner = fix_links(b["h"], base)
            if lvl == 2 and toc is not None:
                label = text(inner).rstrip(" :")
                hid = slugify(label) or f"s{len(toc)}"
                toc.append((hid, label))
                out.append(f'<h2 id="{hid}">{inner}</h2>')
            else:
                cls = ' class="note"' if t in ("h5", "h6") else ""
                out.append(f"<h{lvl}{cls}>{inner}</h{lvl}>")
        else:
            out.append(f"<p>{fix_links(b['h'], base)}</p>")
    if list_open:
        out.append(f"</{list_open}>")
    return "\n".join(out)


# ---------- pages ----------

def home():
    base = ""
    L = SITE["links"]
    prof = [PROJECTS[s] for s in SITE["professional"]]
    other = [PROJECTS[s] for s in SITE["other"]]
    features = "".join(feature_row(p, i + 1, base) for i, p in enumerate(prof))
    body = f"""<section class="hero">
  <div class="wrap hero-inner">
    <p class="hero-hello reveal">Hi, I’m Gauthem.</p>
    <h1 class="hero-title reveal">I design products that <em class="rotator" data-words="grow|convert|scale|delight|last"><span class="sr-only">grow</span><span class="rotator-word" aria-hidden="true">grow</span></em> — <br class="br-lg">from first insight to shipped pixel.</h1>
    <p class="hero-meta reveal"><span>Head of Product at HP-appen</span><i></i><span>{escape(SITE["stats"][0][0])} Years of Experience</span><i></i><span>{escape(SITE["location"])}</span><i></i><span>{escape(SITE["relocation"])}</span></p>
    <div class="hero-actions reveal">
      <a class="btn btn-accent btn-lg" href="#work">View selected work {icon("arrow-r")}</a>
      {ext(resume(base), icon("file") + " Resume", "btn btn-ghost btn-lg")}
      {ext(L["linkedin"], icon("linkedin") + '<span class="sr-only">LinkedIn</span>', "btn btn-ghost btn-lg btn-icon")}
    </div>
    <p class="hero-lede reveal">{escape(SITE["intro"])}</p>
  </div>
</section>
{ticker()}
{stats()}
<section class="section wrap" id="work">
  {section_head("Professional work", "Selected case studies", "Founding, lead and senior design roles across ed-tech, agri-tech, food delivery and research — measured by real outcomes.")}
  <div class="features">{features}</div>
  <div class="center reveal"><a class="pill-btn pill-lg" href="{base}professional_works/">Check all works {icon("arrow-r")}</a></div>
</section>
<section class="section wrap" id="other">
  {section_head("Explorations", "Side projects and redesigns", "Self-initiated products, concept redesigns and research studies — where I try new ideas, tools and AI-assisted workflows.")}
  {filters(other)}
  <div class="work-grid" data-filter-grid>{"".join(work_card(p, base) for p in other)}</div>
</section>
<section class="section wrap split">
  <div class="split-side has-portrait">
    <figure class="portrait home-portrait reveal"><img src="{base}{SITE["photo"]}" alt="{escape(SITE["name"])}" loading="lazy"><figcaption>{escape(SITE["name"])} · {escape(SITE["location"])}</figcaption></figure>
    {section_head("Career", "Experience")}
    <p class="muted reveal">{escape(SITE["bio"])}</p>
    <a class="text-link reveal" href="{base}about/">More about me {icon("arrow-r")}</a>
  </div>
  {experience_list()}
</section>
<section class="section wrap">
  {section_head("What I do", "How I can help", f'<a class="pill-btn" href="{base}service/">Service details {icon("arrow-r")}</a>')}
  <div class="services-grid">{service_cards(full=False)}</div>
</section>
<section class="section wrap">
  {section_head("Toolkit", "Tools I use")}
  <ul class="toolkit">{toolkit(base)}</ul>
</section>
{cta(base)}"""
    return page("", "home", base, body, body_class="home")


def page_hero(label, title, lede="", portrait=None, compact=False):
    lede_html = f'<p class="page-lede reveal">{lede}</p>' if lede else ""
    text = f"""<div class="page-hero-text{"" if portrait else " centered"}">
    <p class="eyebrow reveal">{label}</p>
    <h1 class="page-title reveal">{title}</h1>
    {lede_html}
  </div>"""
    if not portrait:
        return f'<section class="page-hero"><div class="wrap">{text}</div></section>'
    cls = "portrait compact" if compact else "portrait"
    return f"""<section class="page-hero">
  <div class="wrap page-hero-split">
  {text}
  <figure class="{cls} reveal"><img src="{portrait}" alt="{escape(SITE["name"])}" loading="eager"><figcaption>{escape(SITE["location"])} · {escape(SITE["relocation"])}</figcaption></figure>
  </div>
</section>"""


def listing(section):
    base = "../"
    if section == "professional_works":
        prof = [PROJECTS[s] for s in SITE["professional"]]
        body = page_hero("Professional works", "Work that shipped, <em>measured</em> by real outcomes.",
                         "Founding, lead and senior design roles across ed-tech, agri-tech, food delivery and non-profit — from research and strategy to launch.")
        body += f'<section class="section wrap"><div class="features">{"".join(feature_row(p, i + 1, base) for i, p in enumerate(prof))}</div></section>'
        title = "Professional Works"
    else:
        other = [PROJECTS[s] for s in SITE["other"]]
        body = page_hero("Other works", "Explorations, redesigns &amp; <em>side projects</em>.",
                         "Self-initiated products, concept redesigns and research studies — where I try new ideas, tools and AI-assisted workflows.")
        body += f'<section class="section wrap">{filters(other)}<div class="work-grid" data-filter-grid>{"".join(work_card(p, base) for p in other)}</div></section>'
        title = "Other Works"
    return page(title, section, base, body + cta(base))


def about():
    base = "../"
    body = page_hero("About", "Founding designer, researcher &amp; <em>product lead.</em>", escape(SITE["bio"]), portrait=base + SITE["photo"])
    body += f"""<section class="section wrap split">
  <div class="split-side">{section_head("Career", "Work history")}
    <div class="reveal about-actions">
      {ext(resume(base), icon("file") + " Download resume", "btn btn-accent")}
      <a class="btn btn-ghost" href="{base}contact/">Get in touch</a>
    </div>
  </div>
  {experience_list(detailed=True)}
</section>
<section class="section wrap">
  {section_head("Learning", "Education and certificates")}
  <ul class="edu-grid">{education_list()}</ul>
</section>
<section class="section wrap">
  {section_head("Toolkit", "My tech stack")}
  <ul class="toolkit">{toolkit(base)}</ul>
</section>
<section class="section wrap">
  {section_head("Recent work", "Featured projects", f'<a class="text-link" href="{base}professional_works/">View all {icon("arrow-r")}</a>')}
  <div class="work-grid">{"".join(work_card(PROJECTS[s], base) for s in SITE["professional"][:3])}</div>
</section>
{cta(base)}"""
    return page("About", "about", base, body, SITE["bio"])


def services():
    base = "../"
    body = page_hero("Services", "End-to-end design, from <em>first question</em> to shipped product.",
                     "Research, product strategy, interface design, testing and hands-on development support — for teams that want measurable results.")
    body += f"""<section class="section wrap"><div class="services-grid full">{service_cards(full=True)}</div></section>
{cta(base)}"""
    return page("Services", "service", base, body)


def contact():
    base = "../"
    L = SITE["links"]
    phones = "".join(f'<a href="tel:{p.replace(" ", "")}">{escape(p)}</a>' for p in SITE["phones"])
    body = page_hero("Contact", "Let’s <em>talk</em>.", escape(SITE["contactBlurb"]), portrait=base + SITE["photoSquare"], compact=True)
    body += f"""<section class="section wrap contact-grid">
  <a class="contact-card reveal" href="mailto:{SITE["email"]}">
    {icon("mail")}<span class="label">Email</span><strong>{SITE["email"]}</strong>
  </a>
  <a class="contact-card reveal" href="{escape(L["calendly"])}" target="_blank" rel="noopener">
    {icon("calendar")}<span class="label">Book a call</span><strong>calendly.com/gauthemk99</strong>
  </a>
  <div class="contact-card reveal">
    {icon("phone")}<span class="label">Phone</span><strong class="phones">{phones}</strong>
  </div>
  <a class="contact-card reveal" href="{escape(L["linkedin"])}" target="_blank" rel="noopener">
    {icon("linkedin")}<span class="label">LinkedIn</span><strong>in/gauthemkrishna</strong>
  </a>
  <a class="contact-card reveal" href="{escape(resume(base))}" target="_blank" rel="noopener">
    {icon("file")}<span class="label">Resume</span><strong>Download PDF</strong>
  </a>
  <div class="contact-card reveal">
    {icon("pin")}<span class="label">Based in</span><strong>{escape(SITE["location"])}</strong><span class="muted">{escape(SITE["relocation"])}</span><span class="muted local-time" data-local-time></span>
  </div>
</section>
<section class="section wrap">
  {section_head("While you’re here", "Selected work")}
  <div class="work-grid">{"".join(work_card(PROJECTS[s], base) for s in SITE["professional"][:3])}</div>
</section>"""
    return page("Contact", "contact", base, body)


def project_page(p):
    base = "../../"
    prof = p["section"] == "professional_works"
    section_title = "Professional works" if prof else "Other works"
    order = SITE["professional" if prof else "other"]
    nxt = PROJECTS[order[(order.index(p["slug"]) + 1) % len(order)]]
    toc = []

    body_blocks = p["blocks"]
    lead = ""
    if prof:
        lead = "".join(f"<p>{fix_links(o, base)}</p>" for o in p.get("overview", []))
        cover = p["hero"]
    else:
        cover = p["cover"]
        # the first image of an "other works" page is the cover; skip it in the body
        if body_blocks and body_blocks[0]["t"] == "img" and body_blocks[0]["src"] == cover:
            body_blocks = body_blocks[1:]

    meta = []
    if p.get("employer"):
        meta.append(("Employer", escape(p["employer"])))
    if p.get("role"):
        meta.append(("Role", escape(p["role"])))
    if p.get("period"):
        meta.append(("Timeline", escape(p["period"])))
    meta.append(("Domain", escape(p.get("domain") or p.get("category", ""))))
    if tags_of(p):
        meta.append(("Industry", escape(", ".join(tags_of(p)))))
    if p.get("visit"):
        meta.append(("Link", ext(p["visit"], escape(p.get("visitLabel", "Visit site")) + " " + icon("arrow-ur"), "text-link")))
    meta_html = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in meta)

    gallery = ""
    if p.get("gallery"):
        gallery = "".join(f'<figure class="shot reveal">{img(g, base, p["title"])}</figure>' for g in p["gallery"])

    content = render_blocks(body_blocks, base, toc)
    if lead:
        toc.insert(0, ("overview", "Overview"))
        lead = f'<h2 id="overview">Overview</h2>{lead}{gallery}'
    toc_html = ""
    if len(toc) > 1:
        toc_html = '<nav class="toc" aria-label="On this page"><p class="label">On this page</p><ol>' + "".join(
            f'<li><a href="#{h}">{escape(l)}</a></li>' for h, l in toc) + "</ol></nav>"

    body = f"""<div class="progress" aria-hidden="true"><span></span></div>
<section class="case-hero">
  <div class="wrap">
    <a class="back-link reveal" href="{base}{p["section"]}/">{icon("arrow-l")} {section_title}</a>
    <p class="eyebrow reveal">Case study / {escape(p.get("category", ""))}</p>
    <h1 class="case-title reveal">{escape(p["title"])}</h1>
    <dl class="case-meta reveal">{meta_html}</dl>
  </div>
</section>
<div class="wrap">
  <figure class="case-cover reveal" style="view-transition-name:cover-{p["slug"]}">{img(cover, base, p["title"], eager=True)}</figure>
</div>
<section class="wrap case-layout{" no-toc" if not toc_html else ""}">
  <aside class="case-aside">{toc_html}</aside>
  <article class="prose">
    {lead}
    {content}
  </article>
</section>
<section class="wrap next-wrap">
  <a class="next-card reveal" href="{url_for(nxt, base)}">
    <div class="next-text"><p class="label">Next project</p><h2>{escape(nxt["title"])}</h2><p class="muted">{escape(nxt.get("category", ""))}</p>
      <span class="text-link">View case study {icon("arrow-r")}</span></div>
    <div class="next-media" style="view-transition-name:cover-{nxt["slug"]}">{img(nxt["cover"], base, nxt["title"])}</div>
  </a>
</section>
{cta(base)}"""
    return page(p["title"], p["section"], base, body, excerpt(p, 160), body_class="case")


# ---------- write ----------

def write(rel, html):
    path = os.path.join(ROOT, rel, "index.html") if rel else os.path.join(ROOT, "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    for d in ("professional_works", "other_works", "about", "service", "contact"):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    write("", home())
    write("professional_works", listing("professional_works"))
    write("other_works", listing("other_works"))
    write("about", about())
    write("service", services())
    write("contact", contact())
    for p in PROJECTS.values():
        write(f'{p["section"]}/{p["slug"]}', project_page(p))
    print(f"Built {6 + len(PROJECTS)} pages")


if __name__ == "__main__":
    main()
