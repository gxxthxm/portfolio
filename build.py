#!/usr/bin/env python3
"""Static site generator for the portfolio.

Reads content/site.json and content/projects/*.json and writes plain HTML
pages (index.html, about/, professional_works/<slug>/, ...) into the repo
root so the site can be served directly by GitHub Pages.

Usage: python3 build.py
"""
import json
import os
import re
import shutil
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = json.load(open(os.path.join(ROOT, "content", "site.json"), encoding="utf-8"))
PROJECTS = {}
for name in os.listdir(os.path.join(ROOT, "content", "projects")):
    if name.endswith(".json"):
        p = json.load(open(os.path.join(ROOT, "content", "projects", name), encoding="utf-8"))
        PROJECTS[p["slug"]] = p

NAV = [
    ("Home", "", "home"),
    ("Professional Works", "professional_works/", "professional_works"),
    ("Other Works", "other_works/", "other_works"),
    ("About", "about/", "about"),
    ("Services", "service/", "service"),
    ("Contact", "contact/", "contact"),
]

ARROW_UP_RIGHT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
ARROW_RIGHT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="m7.5 12.2 3 3 6-6.2" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
MAIL = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m3.5 6 8.5 7 8.5-7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
PHONE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 3.5h2.8l1.4 4.2-2 1.3a11 11 0 0 0 6.2 6.2l1.3-2 4.2 1.4v2.8a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'

SERVICE_ICONS = [
    # atom, browser, glasses, code, hierarchy, people
    '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="12" rx="10" ry="4" fill="none" stroke="currentColor" stroke-width="1.5"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(60 12 12)" fill="none" stroke="currentColor" stroke-width="1.5"/><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(120 12 12)" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/></svg>',
    '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3 9h18" stroke="currentColor" stroke-width="1.5"/></svg>',
    '<svg viewBox="0 0 24 24"><circle cx="6.5" cy="15" r="3.5" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="17.5" cy="15" r="3.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 15h4M3 15l2-8h3M21 15l-2-8h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
    '<svg viewBox="0 0 24 24"><path d="m8 7-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    '<svg viewBox="0 0 24 24"><rect x="9" y="3" width="6" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="3" y="16" width="6" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><rect x="15" y="16" width="6" height="5" rx="1" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M12 8v4M6 16v-4h12v4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>',
    '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.2a6.5 6.5 0 0 1 3.5 5.8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>',
]


def ext_link(href, label, cls=""):
    return f'<a class="{cls}" href="{escape(href)}" target="_blank" rel="noopener">{label}</a>'


def fix_links(html, base):
    """Rewrite Framer-relative links (./molasses), open external links in a new tab, trim stray <br>s."""
    html = re.sub(r"^(\s*<br>\s*)+|(\s*<br>\s*)+$", "", html)
    html = re.sub(r'href="\./([a-z0-9\-]+)"', lambda m: f'href="{base}other_works/{m.group(1)}/"' if m.group(1) in PROJECTS and PROJECTS[m.group(1)]["section"] == "other_works" else f'href="{base}professional_works/{m.group(1)}/"', html)
    html = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', html)
    return html


def img(src, base, alt="", cls="", lazy=True):
    loading = ' loading="lazy" decoding="async"' if lazy else ""
    return f'<img class="{cls}" src="{base}{escape(src)}" alt="{escape(alt)}"{loading}>'


def page(title, active, base, body, description=None):
    nav = "".join(
        f'<a href="{base}{href}" class="{"active" if key == active else ""}">{label}</a>'
        for label, href, key in NAV
    )
    desc = escape(description or SITE["intro"])
    full_title = escape(title + " - " + SITE["title"] if title else SITE["title"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta name="theme-color" content="#000000">
<link rel="icon" href="{base}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,500;0,700;1,400&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/css/style.css">
<script>document.documentElement.classList.add("js")</script>
</head>
<body>
<header class="nav-wrap">
  <nav class="nav" aria-label="Main">
    <button class="nav-toggle" aria-label="Open menu" aria-expanded="false"><span></span><span></span></button>
    <div class="nav-links">{nav}</div>
  </nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <span>&copy; <span data-year></span> {escape(SITE["name"])}</span>
  <span><a href="mailto:{SITE["email"]}">{SITE["email"]}</a></span>
</footer>
<script src="{base}assets/js/main.js" defer></script>
</body>
</html>
"""


# ---------- shared components ----------

def social_buttons():
    L = SITE["links"]
    return f"""<section class="social">
  {ext_link(L["linkedin"], "Linkedin", "btn-ghost")}
  {ext_link(L["resume"], "Resume", "btn-ghost")}
</section>"""


def marquee():
    items = "".join(
        f'<span class="skill{" accent" if i % 2 else ""}">{escape(s)}</span><span class="dot" aria-hidden="true"></span>'
        for i, s in enumerate(SITE["skills"])
    )
    return f"""<section class="marquee" aria-label="Skills">
  <div class="marquee-track">{items}{items}{items}{items}</div>
</section>"""


def cta():
    return f"""<section class="cta card">
  <h4>Let’s Work Together</h4>
  {ext_link(SITE["links"]["calendly"], "Let's chat " + ARROW_RIGHT, "cta-link")}
</section>"""


def url_for(p, base):
    return f'{base}{p["section"]}/{p["slug"]}/'


def project_card(p, base, size="md", subtitle="category"):
    sub = p.get(subtitle) or p.get("category", "")
    return f"""<a class="project-card card size-{size} reveal" href="{url_for(p, base)}">
  <div class="project-card-head">
    <div>
      <h3>{escape(p["title"])}</h3>
      <p>{escape(sub)}</p>
    </div>
    <span class="arrow-btn" aria-hidden="true">{ARROW_UP_RIGHT}</span>
  </div>
  <div class="project-card-media">{img(p["cover"], base, p["title"])}</div>
</a>"""


def works_preview(base):
    def strip(slugs):
        return "".join(f'<div class="thumb">{img(PROJECTS[s]["cover"], base, PROJECTS[s]["title"])}</div>' for s in slugs)
    return f"""<section class="works-preview">
  <a class="card preview reveal" href="{base}professional_works/">
    <div class="project-card-head"><h5>Professional Works</h5><span class="arrow-btn" aria-hidden="true">{ARROW_UP_RIGHT}</span></div>
    <div class="thumb-row">{strip(SITE["professional"][:3])}</div>
  </a>
  <a class="card preview reveal" href="{base}other_works/">
    <div class="project-card-head"><h5>Other Works</h5><span class="arrow-btn" aria-hidden="true">{ARROW_UP_RIGHT}</span></div>
    <div class="thumb-row">{strip(SITE["other"][:3])}</div>
  </a>
</section>"""


# ---------- rich-text blocks ----------

def render_blocks(blocks, base):
    out = []
    list_open = None
    for b in blocks:
        t = b["t"]
        lst = b.get("list")
        if list_open and lst != list_open:
            out.append(f"</{list_open}>")
            list_open = None
        if t == "img":
            out.append(f'<figure class="shot">{img(b["src"], base, b.get("alt", ""))}</figure>')
        elif t == "button":
            out.append(f'<p class="btn-row">{ext_link(b["href"], escape(b["label"]), "btn-solid")}</p>')
        elif lst:
            if not list_open:
                out.append(f"<{lst}>")
                list_open = lst
            out.append(f'<li>{fix_links(b["h"], base)}</li>')
        else:
            tag = {"h1": "h2", "h2": "h3", "h3": "h4", "h4": "h5", "h5": "h6", "h6": "h6"}.get(t, "p")
            cls = f' class="note"' if t == "h5" else ""
            out.append(f"<{tag}{cls}>{fix_links(b['h'], base)}</{tag}>")
    if list_open:
        out.append(f"</{list_open}>")
    return "\n".join(out)


# ---------- pages ----------

def home():
    base = ""
    order = [PROJECTS[s] for s in SITE["home"]]
    cards = [project_card(p, base, "lg") for p in order[:2]]
    cards += [project_card(p, base, "sm") for p in order[2:5]]
    cards += [project_card(p, base, "md") for p in order[5:]]
    body = f"""<div class="container">
{social_buttons()}
</div>
{marquee()}
<div class="container">
<section class="hero card">
  <h1>Hi, I'm Gauthem :)</h1>
  <p>{escape(SITE["intro"])}</p>
</section>
<section class="projects">
  <h2 class="section-title">Projects</h2>
  <div class="grid grid-2">{"".join(cards[:2])}</div>
  <div class="grid grid-3">{"".join(cards[2:5])}</div>
  <div class="grid grid-2">{"".join(cards[5:])}</div>
</section>
{cta()}
</div>"""
    return page("", "home", base, body)


def listing(section):
    base = "../"
    slugs = SITE["professional" if section == "professional_works" else "other"]
    cards = "".join(project_card(PROJECTS[s], base, "sm", "tags") for s in slugs)
    title = "Professional Works" if section == "professional_works" else "Other Works"
    body = f"""<div class="container">
<section class="listing">
  <h1 class="section-title">{title}</h1>
  <div class="grid grid-3">{cards}</div>
</section>
{cta()}
{social_buttons()}
</div>"""
    return page(title, section, base, body)


def about():
    base = "../"
    exp = "".join(
        f"""<li><span class="period">{escape(e["period"])}</span><strong>{escape(e["role"])}</strong><span class="place">{escape(e["place"])}</span></li>"""
        for e in SITE["experience"]
    )
    stack = "".join(
        f'<div class="tool card">{img(t["icon"], base, "")}<h6>{escape(t["name"])}</h6></div>' for t in SITE["stack"]
    )
    body = f"""<div class="container">
<section class="card about">
  <p class="bio">{escape(SITE["bio"])}</p>
  <h2 class="eyebrow">Experience</h2>
  <ul class="timeline">{exp}</ul>
  <a class="btn-solid wide" href="{base}contact/">Get in touch</a>
</section>
<section class="card stack">
  <h3 class="section-title">My Tech Stack</h3>
  <div class="grid grid-2 tools">{stack}</div>
</section>
{works_preview(base)}
{cta()}
</div>"""
    return page("About", "about", base, body, SITE["bio"])


def services():
    base = "../"
    cards = ""
    for i, s in enumerate(SITE["services"]):
        items = "".join(f"<li>{CHECK}<span>{escape(it)}</span></li>" for it in s["items"])
        cards += f"""<article class="service card">
  <header><h3>{escape(s["title"])}</h3><span class="service-icon" aria-hidden="true">{SERVICE_ICONS[i % len(SERVICE_ICONS)]}</span></header>
  <p>{escape(s["text"])}</p>
  <ul class="checks">{items}</ul>
</article>"""
    body = f"""<div class="container">
<section class="card services-wrap">
  <h1 class="section-title">Services</h1>
  <div class="grid grid-2">{cards}</div>
</section>
{works_preview(base)}
{cta()}
{social_buttons()}
</div>"""
    return page("Services", "service", base, body)


def contact():
    base = "../"
    phones = " | ".join(f'<a href="tel:{p.replace(" ", "")}">{escape(p)}</a>' for p in SITE["phones"])
    body = f"""<div class="container">
{social_buttons()}
<section class="grid grid-2 contact-cards">
  <div class="card contact-me">
    <h3>{escape(SITE["name"])}</h3>
    <p>{escape(SITE["contactBlurb"])}</p>
    <a class="btn-solid wide" href="mailto:{SITE["email"]}">Get in touch</a>
  </div>
  <div class="card contact-info">
    <h3>Let’s Work Together</h3>
    <p>{MAIL}<a href="mailto:{SITE["email"]}">{SITE["email"]}</a></p>
    <p>{PHONE}<span>{phones}</span></p>
  </div>
</section>
{works_preview(base)}
</div>"""
    return page("Contact", "contact", base, body)


def project_page(p):
    base = "../../"
    section_title = "Professional Works" if p["section"] == "professional_works" else "Other Works"
    back = f'<a class="back-link" href="{base}{p["section"]}/">&larr; {section_title}</a>'
    if p["section"] == "professional_works":
        visit = ""
        if p.get("visit"):
            visit = ext_link(p["visit"], escape(p.get("visitLabel", "Visit Site")), "btn-solid")
        overview = "".join(f"<p>{fix_links(o, base)}</p>" for o in p.get("overview", []))
        gallery = ""
        if p.get("gallery"):
            gallery = '<section class="gallery">' + "".join(
                f'<figure class="shot">{img(g, base, p["title"])}</figure>' for g in p["gallery"]
            ) + "</section>"
        more = [PROJECTS[s] for s in SITE["professional"] if s != p["slug"]]
        body = f"""<div class="container">
{back}
<figure class="hero-shot">{img(p["hero"], base, p["title"], lazy=False)}</figure>
<section class="overview">
  <aside class="meta">
    <h1 class="visually-hidden">{escape(p["title"])}</h1>
    <h6>Employer :</h6><p class="meta-value">{escape(p.get("employer", ""))}</p>
    <h6>Domain :</h6><p class="meta-value">{escape(p.get("domain", ""))}</p>
    {visit}
  </aside>
  <div class="prose">
    <h2>Overview</h2>
    {overview}
  </div>
</section>
{gallery}
<article class="prose case-body">
{render_blocks(p["blocks"], base)}
</article>
<section class="more">
  <h2 class="section-title">More Professional Works</h2>
  <div class="grid grid-3">{"".join(project_card(m, base, "sm") for m in more[:3])}</div>
</section>
{cta()}
{social_buttons()}
</div>"""
    else:
        order = SITE["other"]
        i = order.index(p["slug"])
        prev_p = PROJECTS[order[i - 1]] if i > 0 else None
        next_p = PROJECTS[order[i + 1]] if i + 1 < len(order) else None
        pager = '<nav class="pager" aria-label="Project navigation">'
        pager += f'<a href="{url_for(prev_p, base)}">&lsaquo; {escape(prev_p["title"])}</a>' if prev_p else "<span></span>"
        pager += f'<a href="{url_for(next_p, base)}">{escape(next_p["title"])} &rsaquo;</a>' if next_p else "<span></span>"
        pager += "</nav>"
        body = f"""<div class="container narrow">
{back}
<header class="case-head">
  <h1>{escape(p["title"])}</h1>
  <p>{escape(p.get("category", ""))}</p>
</header>
<article class="prose case-body">
{render_blocks(p["blocks"], base)}
</article>
{pager}
</div>
<div class="container">{cta()}</div>"""
    desc = re.sub("<[^>]+>", "", (p.get("overview") or [next((b["h"] for b in p["blocks"] if b["t"] == "p"), "")])[0])[:160]
    return page(p["title"], p["section"], base, body, desc)


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
