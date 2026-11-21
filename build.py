#!/usr/bin/env python3
"""Générateur du site Infinite Transfer.

Usage : python3 build.py
Produit le site complet dans public/ à partir de :
  - templates/home.html, templates/contact.html  (corps des pages Accueil et Contact)
  - services.py                                  (contenu des pages services)
  - content/articles/*.md                        (articles, un fichier par article)

Pour ajouter un article : créer content/articles/AAAA-MM-JJ-titre-court.md avec l'en-tête
---
title: Titre de l'article
description: Résumé de 150 caractères environ (affiché dans Google)
category: transfert-aeroport   (slug d'une page service, cf. services.py)
date: AAAA-MM-JJ
---
puis le texte en Markdown simple (## titres, listes, **gras**, [liens](url)), et relancer build.py.
"""
import html, json, os, re, shutil
from datetime import date
from services import SERVICES
from reviews import REVIEWS, RATING, COUNT

# Adresse publique du site. Sur Cloudflare Pages, la variable SITE_URL (réglages du projet) la définit,
# par exemple https://www.mondomaine.fr ; à défaut, l'adresse définitive infinitetransfer.eu est utilisée.
BASE_URL = os.environ.get("SITE_URL", "https://www.infinitetransfer.eu").rstrip("/")
GMB_URL = "https://maps.app.goo.gl/dCqBWjs9cmoYXrDV7"   # fiche Google Business Profile
HERE = os.path.dirname(os.path.abspath(__file__))
# Sur Netlify, URL = adresse principale du site. Tant que ce n'est pas infinitetransfer.eu
# (adresse provisoire *.netlify.app), les pages sont masquées à Google pour éviter le contenu en double.
NOINDEX = (bool(os.environ.get("NETLIFY")) and "infinitetransfer.eu" not in os.environ.get("URL", "")) \
    or (bool(os.environ.get("CF_PAGES")) and not os.environ.get("SITE_URL"))
OUT = os.path.join(HERE, "public")
SVC = {s["slug"]: s for s in SERVICES}
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def fr_date(d):
    return f"{d.day} {MOIS[d.month-1]} {d.year}"

def esc(t):
    return html.escape(t, quote=True)

def strip_tags(t):
    return re.sub(r"<[^>]+>", "", t)

# ——— Markdown minimal (titres, paragraphes, listes, citations, gras, italique, liens) ———
def inline(t):
    t = esc(t).replace("&#x27;", "'")
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    return t

def markdown(src):
    out, para, lst = [], [], None
    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>"); lst = None
    table = []
    def flush_table():
        nonlocal table
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table if not re.match(r"^\|?\s*:?-{3,}", r.strip())]
            head, rest = rows[0], rows[1:]
            out.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table></div>")
            table = []
    for line in src.splitlines():
        l = line.strip()
        if l.startswith("|"):
            flush(); table.append(l); continue
        flush_table()
        if not l:
            flush(); continue
        m = re.match(r"(#{2,3})\s+(.*)", l)
        if m:
            flush(); n = len(m.group(1)); out.append(f"<h{n}>{inline(m.group(2))}</h{n}>"); continue
        if l.startswith(">"):
            flush(); out.append("<blockquote>" + inline(l.lstrip("> ")) + "</blockquote>"); continue
        m = re.match(r"([-*]|\d+\.)\s+(.*)", l)
        if m:
            if para: flush()
            tag = "ol" if m.group(1)[0].isdigit() else "ul"
            if lst and lst[0] != tag: flush()
            if not lst: lst = (tag, [])
            lst[1].append(m.group(2)); continue
        if lst: flush()
        para.append(l)
    flush(); flush_table()
    return "\n".join(out)

# ——— Articles ———
def load_articles():
    arts = []
    d = os.path.join(HERE, "content", "articles")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        raw = open(os.path.join(d, f), encoding="utf-8").read()
        m = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", raw, re.S)
        if not m:
            raise SystemExit(f"En-tête manquant dans {f}")
        meta = dict(re.findall(r"^(\w+):\s*(.+?)\s*$", m.group(1), re.M))
        for k in ("title", "description", "category", "date"):
            if k not in meta:
                raise SystemExit(f"Champ « {k} » manquant dans {f}")
        if meta["category"] not in SVC:
            raise SystemExit(f"Catégorie inconnue « {meta['category']} » dans {f} (choix : {', '.join(SVC)})")
        slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f[:-3])
        body = m.group(2)
        arts.append({**meta, "slug": slug, "date": date.fromisoformat(meta["date"]), "md": body,
                     "minutes": max(2, round(len(body.split()) / 200))})
    arts.sort(key=lambda a: a["date"], reverse=True)
    return [a for a in arts if a["date"] <= date.today()]   # un article daté dans le futur attend sa date

# ——— Gabarit commun ———
ARROW = '<svg width="16" height="10" viewBox="0 0 16 10" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M0 5h15M11 1l4 4-4 4"/></svg>'
WA_ICON = '<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm0 18.2a8.2 8.2 0 01-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1112 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 01-3.3-2.9c-.2-.4.2-.4.7-1.3a.5.5 0 000-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 00-.7.3 3 3 0 00-.9 2.2 5.2 5.2 0 001.1 2.7 11.8 11.8 0 004.5 4c1.7.7 2.3.8 3.2.6a2.7 2.7 0 001.8-1.2 2.2 2.2 0 00.1-1.2c0-.1-.2-.2-.5-.3z"/></svg>'

ORG = {"@type": "LocalBusiness", "@id": BASE_URL + "/#entreprise", "name": "Infinite Transfer",
       "description": "Chauffeur privé VTC à Marseille et en Provence : transferts aéroport, gares, port de croisière, événements, affaires.",
       "url": BASE_URL + "/", "telephone": "+33767123512", "email": "contact@infinitetransfer.eu",
       "areaServed": ["Marseille", "Aix-en-Provence", "Provence-Alpes-Côte d'Azur"],
       "logo": BASE_URL + "/assets/img/icon-512.png", "image": BASE_URL + "/assets/img/og-image.jpg",
       "sameAs": ["https://www.instagram.com/infinite.transfer/", GMB_URL], "priceRange": "€€"}

def nav(root, current):
    cur_attr = ' aria-current="page"'
    sub = "".join(f'<li><a href="{root}{s["slug"]}.html"{cur_attr if current == s["slug"] else ""}>{esc(s["nav"])}</a></li>' for s in SERVICES)
    def item(href, label, key):
        cur = ' aria-current="page"' if current == key else ""
        return f'<li><a href="{root}{href}"{cur}>{label}</a></li>'
    return f'''<header class="top">
  <nav class="wrap nav" aria-label="Navigation principale">
    <a class="brand" href="{root}index.html" aria-label="Infinite Transfer, accueil"><img class="brand-icon" src="{root}assets/img/logo-icone.png" alt="" width="54" height="21"><span class="brand-txt"><b>INFINITE</b><small>Transfer · Marseille</small></span></a>
    <ul id="menu">
      <li class="has-sub"><button type="button" aria-expanded="false" aria-controls="subServices">Services</button><ul class="sub" id="subServices">{sub}</ul></li>
      {item("index.html#flotte", "Flotte", "flotte")}
      {item("index.html#faq", "FAQ", "faq")}
      {item("contact.html", "Contact", "contact")}
    </ul>
    <div class="nav-r">
      <a class="nav-tel" href="tel:+33767123512">+33 7 67 12 35 12</a>
      <a class="btn btn-or" href="{root}contact.html">Réserver</a>
      <button class="menu-btn" id="menuBtn" aria-label="Ouvrir le menu" aria-expanded="false" aria-controls="menu">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M3 8h18M3 16h18"/></svg>
      </button>
    </div>
  </nav>
</header>'''

def footer(root):
    svc = "".join(f'<li><a href="{root}{s["slug"]}.html">{esc(s["nav"])}</a></li>' for s in SERVICES)
    return f'''<footer>
  <div class="wrap">
    <div class="f-grid">
      <div>
        <a href="{root}index.html" class="foot-logo"><img src="{root}assets/img/logo-infinite-transfer.png" alt="Infinite Transfer, personal driver" width="180" height="98"></a>
        <p style="max-width:28em">Chauffeur privé VTC haut de gamme à Marseille et en Provence. Transferts aéroport, gares, croisières, affaires et événements.</p>
      </div>
      <div><h4>Services</h4><ul>{svc}</ul></div>
      <div><h4>Contact</h4><ul><li><a href="tel:+33767123512">+33 7 67 12 35 12</a></li><li><a href="mailto:contact@infinitetransfer.eu">contact@infinitetransfer.eu</a></li><li><a href="{root}contact.html">Demander un devis</a></li></ul></div>
      <div><h4>Infos</h4><ul><li><a href="{root}guide.html">Le guide</a></li><li><a href="https://www.instagram.com/infinite.transfer/">Instagram</a></li><li><a href="https://www.facebook.com/">Facebook</a></li><li><a href="{GMB_URL}">Nos avis Google</a></li></ul></div>
    </div>
    <div class="legal">
      <span>© {date.today().year} Infinite Transfer. Tous droits réservés.</span>
      <span><a href="{root}mentions-legales.html">Mentions légales</a> · <a href="{root}politique-confidentialite.html">Confidentialité</a> · <a href="{root}cgv.html">CGV</a></span>
    </div>
  </div>
</footer>'''

def clean(path):
    """Adresse publique d'un fichier : sans « .html », et « index.html » devient la racine."""
    path = re.sub(r"(^|/)index\.html$", r"\1", path)
    return re.sub(r"\.html$", "", path)

def clean_links(doc):
    """Retire « .html » des liens internes (Cloudflare Pages sert les pages sans extension)."""
    doc = re.sub(r'(href|action)="((?:\.\./)*)index\.html', lambda m: f'{m.group(1)}="{m.group(2) or "./"}', doc)
    doc = re.sub(r'(href|action)="((?:\.\./)*[\w\-/]+)\.html', r'\1="\2', doc)
    doc = re.sub(re.escape(BASE_URL) + r'/([\w\-/]*?)(?:index)?\.html', lambda m: BASE_URL + "/" + m.group(1), doc)
    return doc

def page(path, title, description, body, current="", jsonld=None, image=None):
    depth = path.count("/")
    root = "../" * depth
    canonical = BASE_URL + "/" + clean(path)
    robots = '<meta name="robots" content="noindex">' if NOINDEX else ""
    ld = ""
    if jsonld:
        ld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": jsonld}, ensure_ascii=False) + "</script>"
    doc = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">{robots}
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="Infinite Transfer">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE_URL}/{image or "assets/img/og-image.jpg"}">
<link rel="icon" type="image/png" sizes="32x32" href="{root}assets/img/favicon-32.png">
<link rel="apple-touch-icon" href="{root}assets/img/apple-touch-icon.png">
<link rel="preload" href="{root}assets/fonts/cormorant-garamond-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}assets/fonts/manrope-latin-300-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/style.css">
{ld}
</head>
<body>
{nav(root, current)}
<main>
{body.replace("{{root}}", root)}
</main>
{footer(root)}
<a class="float-wa" href="https://wa.me/33767123512" target="_blank" rel="noopener" aria-label="Nous écrire sur WhatsApp">{WA_ICON}</a>
<script src="{root}assets/site.js"></script>
</body>
</html>
'''
    doc = clean_links(doc)
    dest = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w", encoding="utf-8").write(doc)
    return path

def crumbs(items, root):
    lis = "".join(f'<li><a href="{root}{h}">{esc(t)}</a></li>' if h else f'<li aria-current="page">{esc(t)}</li>' for t, h in items)
    return f'<ol class="crumbs">{lis}</ol>'

def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": t, **({"item": BASE_URL + "/" + h.replace("index.html", "")} if h else {})}
        for i, (t, h) in enumerate(items)]}

def post_cards(arts, root, light=False):
    if not arts:
        return ""
    def pic(a):
        if a.get("image"):
            return f'<div class="post-img"><img src="{root}{a["image"]}" alt="{esc(a.get("image_alt", a["title"]))}" loading="lazy" width="600" height="400"></div>'
        return f'<div class="post-img post-img-empty"><img src="{root}assets/img/logo-icone.png" alt="" width="120" height="46"></div>'
    cards = "".join(f'''<a class="post" href="{root}articles/{a["slug"]}.html">{pic(a)}<small>{esc(SVC[a["category"]]["short"])} · {fr_date(a["date"])}</small><h3>{esc(a["title"])}</h3><p>{esc(a["description"])}</p><span class="more">Lire l'article</span></a>''' for a in arts)
    return f'<div class="posts">{cards}</div>'

def faq_html(faq, light=True):
    items = "".join(f'<details{" open" if i == 0 else ""}><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for i, (q, a) in enumerate(faq))
    return f'<div class="faq">{items}</div>'

def faq_ld(faq):
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

def cta_strip(title="Un trajet à prévoir ? <em>Votre prix fixe en quelques minutes.</em>"):
    return f'''<section class="cta-strip"><div class="wrap"><h2>{title}</h2><div class="ctas">
<a class="btn btn-or" href="{{{{root}}}}contact.html">Demander un devis {ARROW}</a><a class="btn btn-line" href="tel:+33767123512">+33 7 67 12 35 12</a></div></div></section>'''

# ——— Pages ———
def build_service(s, arts):
    mine = [a for a in arts if a["category"] == s["slug"]]
    path = s["slug"] + ".html"
    items = [("Accueil", "index.html"), ("Services", ""), (s["nav"], "")]
    items_ld = [("Accueil", "index.html"), (s["nav"], "")]
    facts = "".join(f'<div><b>{esc(v)}</b><small>{esc(l)}</small></div>' for v, l in s["facts"])
    aside = "".join(f'<li><span>{esc(a)}</span><span>{esc(b)}</span></li>' for a, b in s["aside"])
    points = "".join(f'<div><b>{esc(t)}</b><p>{esc(p)}</p></div>' for t, p in s["points"])
    data_from = f' data-from="{esc(s["from_hint"])}"' if s["from_hint"] else ""
    articles = post_cards(mine, "{{root}}", light=True) or f'<p class="empty">Nos premiers conseils sur ce thème arrivent très bientôt. En attendant, consultez <a href="{{{{root}}}}guide.html">le guide</a> ou <a href="{{{{root}}}}contact.html">demandez votre devis</a>.</p>'
    body = f'''
<section class="page-hero">
  <div class="wrap">
    {crumbs([("Accueil", "index.html"), (s["nav"], "")], "{{root}}")}
    <span class="label">{esc(s["label"])}</span>
    <h1>{s["h1"]}</h1>
    <p class="lead">{esc(s["lead"])}</p>
    <div class="ctas">
      <a class="btn btn-or" href="{{{{root}}}}contact.html"{data_from}>Obtenir mon prix fixe {ARROW}</a>
      <a class="btn btn-line" href="https://wa.me/33767123512" target="_blank" rel="noopener">WhatsApp</a>
    </div>
    <div class="hero-facts">{facts}</div>
  </div>
</section>

<section class="light">
  <div class="wrap split">
    <aside>
      <span class="label">{esc(s["intro_label"])}</span>
      <h2 style="margin:22px 0 40px">{s["intro_h2"]}</h2>
      <div class="aside-box">
        <h3>{esc(s["aside_title"])}</h3>
        <ul>{aside}</ul>
        <a class="btn btn-or" href="{{{{root}}}}contact.html"{data_from} style="color:var(--noir)">Demander un devis</a>
      </div>
    </aside>
    <div class="prose">{s["body"]}</div>
  </div>
</section>

<section class="dark" style="padding:clamp(60px,8vw,100px) 0">
  <div class="wrap"><div class="points">{points}</div></div>
</section>

<section class="light" id="articles">
  <div class="wrap">
    <div class="head">
      <div><span class="label">Conseils &amp; actualités</span><h2>Nos articles <em>{esc(s["short"].lower())}.</em></h2></div>
      <p>Conseils pratiques, temps de trajet, bons plans et actualités pour préparer votre déplacement.</p>
    </div>
    {articles}
  </div>
</section>

<section class="light" style="padding-top:0">
  <div class="wrap faq-grid">
    <div class="intro"><span class="label">Questions fréquentes</span><h2 style="margin-top:22px">{esc(s["short"])} : <em>vos questions.</em></h2></div>
    {faq_html(s["faq"])}
  </div>
</section>
{cta_strip()}'''
    ld = [ORG, {"@type": "Service", "name": s["nav"], "serviceType": "Chauffeur privé VTC", "description": s["description"],
                "provider": {"@id": ORG["@id"]}, "areaServed": ORG["areaServed"], "url": BASE_URL + "/" + path},
          faq_ld(s["faq"]), crumbs_ld(items_ld)]
    return page(path, s["title"], s["description"], body, current=s["slug"], jsonld=ld)

def build_article(a, arts):
    s = SVC[a["category"]]
    path = f"articles/{a['slug']}.html"
    related = [x for x in arts if x["category"] == a["category"] and x["slug"] != a["slug"]][:3]
    rel_html = ""
    if related:
        rel_html = f'''<section class="light" style="padding-top:0"><div class="wrap"><div class="head"><div><span class="label">À lire aussi</span><h2>Sur le même <em>thème.</em></h2></div></div>{post_cards(related, "{{root}}", True)}</div></section>'''
    items = [("Accueil", "index.html"), (s["nav"], s["slug"] + ".html"), (a["title"], "")]
    if a.get("image"):
        figure = f'<figure class="art-fig"><img src="{{{{root}}}}{a["image"]}" alt="{esc(a.get("image_alt", a["title"]))}" width="800" height="600"></figure>'
    else:
        figure = '<figure class="art-fig art-fig-empty"><img src="{{root}}assets/img/logo-icone.png" alt="" width="120" height="46"></figure>'
    body = f'''
<section class="page-hero">
  <div class="wrap">
    {crumbs(items, "{{root}}")}
    <span class="label">{esc(s["short"])}</span>
    <h1 style="max-width:20em">{esc(a["title"])}</h1>
    <p class="lead">{esc(a["description"])}</p>
    <div class="art-meta"><span>Publié le {fr_date(a["date"])}</span><span>Lecture : {a["minutes"]} min</span></div>
  </div>
</section>
<section class="light">
  <div class="wrap split">
    <aside class="aside-stack">
      <div class="aside-box">
        <span class="label">{esc(s["short"])}</span>
        <h3>Besoin d'un chauffeur ?</h3>
        <p style="color:#5e5f63;font-size:.95rem">{esc(s["lead"])}</p>
        <a class="btn btn-or" href="{{{{root}}}}contact.html" style="color:var(--noir)">Demander un devis</a>
        <a href="{{{{root}}}}{s["slug"]}.html" style="font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;color:#7a5f2e">Découvrir le service →</a>
      </div>
      {figure}
    </aside>
    <article class="prose">{markdown(a["md"])}</article>
  </div>
</section>
{rel_html}
{cta_strip()}'''
    ld = [ORG, {"@type": "BlogPosting", "headline": a["title"], "description": a["description"], "datePublished": a["date"].isoformat(),
                "inLanguage": "fr-FR", "author": {"@id": ORG["@id"]}, "publisher": {"@id": ORG["@id"]},
                "mainEntityOfPage": BASE_URL + "/" + path}, crumbs_ld(items)]
    if a.get("image"):
        ld[1]["image"] = BASE_URL + "/" + a["image"]
    return page(path, f'{a["title"]} | Infinite Transfer', a["description"], body, current=a["category"], jsonld=ld, image=a.get("image"))

def build_guide(arts):
    groups = ""
    for s in SERVICES:
        mine = [a for a in arts if a["category"] == s["slug"]]
        if mine:
            groups += f'<div style="margin-bottom:70px"><div class="head" style="margin-bottom:34px"><div><span class="label">{esc(s["short"])}</span></div><p><a href="{{{{root}}}}{s["slug"]}.html" style="color:#7a5f2e">Voir le service {esc(s["nav"].lower())} →</a></p></div>{post_cards(mine, "{{root}}", True)}</div>'
    if not groups:
        groups = '<p class="empty">Les premiers articles arrivent très bientôt.</p>'
    body = f'''
<section class="page-hero">
  <div class="wrap">
    {crumbs([("Accueil", "index.html"), ("Le guide", "")], "{{root}}")}
    <span class="label">Le guide</span>
    <h1>Conseils et actualités <em>pour voyager en Provence.</em></h1>
    <p class="lead">Temps de trajet, accès aux gares et à l'aéroport, escales de croisière, événements à Marseille : tout ce qu'il faut savoir pour préparer vos déplacements.</p>
  </div>
</section>
<section class="light"><div class="wrap">{groups}</div></section>
{cta_strip()}'''
    items = [("Accueil", "index.html"), ("Le guide", "")]
    return page("guide.html", "Le guide : conseils VTC et transports à Marseille et en Provence | Infinite Transfer",
                "Conseils pratiques pour vos transferts à Marseille et en Provence : aéroport, gares, croisières, événements, longues distances.",
                body, current="guide", jsonld=[ORG, crumbs_ld(items)])


STAR = '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.5l2.9 6.2 6.8.8-5 4.6 1.3 6.7L12 17.5l-6 3.3 1.3-6.7-5-4.6 6.8-.8z"/></svg>'
G_ICON = '<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>'

def reviews_html():
    cards = "".join(f'''<figure class="rev"><div class="rev-stars" aria-label="{r["stars"]} étoiles sur 5">{STAR * r["stars"]}</div>
<blockquote>{esc(r["text"])}</blockquote>
<figcaption><b>{esc(r["name"])}</b><span>{G_ICON} Avis Google · {esc(r["date"])}{" · traduit de l'anglais" if r["translated"] else ""}</span></figcaption></figure>''' for r in REVIEWS)
    return f'''<section class="dark reviews" id="avis">
  <div class="wrap">
    <div class="head">
      <div><span class="label">Avis clients</span><h2>Ils nous ont <em>fait confiance.</em></h2></div>
      <div class="rev-score">
        <div class="rev-big">{RATING}<small>/5</small></div>
        <div><div class="rev-stars">{STAR * 5}</div><p>{COUNT} avis sur Google</p></div>
        <a class="btn btn-line" href="{GMB_URL}" target="_blank" rel="noopener">Voir tous nos avis</a>
      </div>
    </div>
    <div class="rev-grid">{cards}</div>
  </div>
</section>'''

def build_home(arts):
    tpl = open(os.path.join(HERE, "templates", "home.html"), encoding="utf-8").read()
    latest = ""
    if arts:
        latest = f'''<section class="light" id="articles"><div class="wrap"><div class="head"><div><span class="label">Le guide</span><h2>Derniers <em>conseils.</em></h2></div><p>Nos articles pour préparer vos déplacements à Marseille et en Provence. <a href="{{{{root}}}}guide.html" style="color:#7a5f2e">Tout le guide →</a></p></div>{post_cards(arts[:3], "{{root}}", True)}</div></section>'''
    body = tpl.replace("{{latest_articles}}", latest).replace("{{reviews}}", reviews_html())
    faq = re.findall(r"<summary>(.*?)</summary><p>(.*?)</p>", body)
    ld = [ORG, faq_ld([(html.unescape(q), html.unescape(a)) for q, a in faq])]
    return page("index.html", "VTC Marseille : chauffeur privé haut de gamme en Provence | Infinite Transfer",
                "Chauffeur privé VTC à Marseille et en Provence : aéroport Marseille Provence, gares Saint-Charles et Aix TGV, port de croisière, événements, affaires. Prix fixe annoncé à la réservation.",
                body, jsonld=ld)

def build_contact():
    tpl = open(os.path.join(HERE, "templates", "contact.html"), encoding="utf-8").read()
    body = f'''
<section class="page-hero" style="padding-bottom:clamp(40px,5vw,60px)">
  <div class="wrap">
    {crumbs([("Accueil", "index.html"), ("Contact", "")], "{{root}}")}
    <span class="label">Contact &amp; devis</span>
    <h1>Réservez votre VTC <em>à Marseille.</em></h1>
    <p class="lead">Décrivez votre trajet : vous recevez un prix fixe, confirmé par écrit, sans engagement.</p>
  </div>
</section>
{tpl}'''
    items = [("Accueil", "index.html"), ("Contact", "")]
    return page("contact.html", "Contact et devis VTC Marseille : réservez votre chauffeur | Infinite Transfer",
                "Demandez votre devis VTC gratuit à Marseille : aéroport, gares, port de croisière, événements. Réponse rapide par WhatsApp, téléphone ou e-mail.",
                body, current="contact", jsonld=[ORG, crumbs_ld(items)])


# ——— Redirections de l'ancien site (fichier _redirects, format Netlify) ———
FIXED = {
    "/faq-w1": "/#faq", "/provence-transfert-gare-w1": "/transfert-gare.html",
    "/provence-transfert-aeroport-w1": "/transfert-aeroport.html",
    "/transfert-vtc-port-de-croisiere-w1": "/port-croisiere.html", "/vtc-evenementiel-w1": "/vtc-evenementiel.html",
    "/contact": "/contact.html", "/tarifs": "/contact.html", "/provence-tarifs": "/contact.html", "/provence-tarifs-w1": "/contact.html",
    "/guide-local-w1": "/guide.html", "/plan-du-site": "/", "/provence-w1": "/", "/toutes-nos-prestations-1": "/",
    "/secteurs": "/", "/nos-activites": "/", "/mentions-legales": "/mentions-legales.html", "/politique-confidentialite": "/politique-confidentialite.html",
    "/gare+saint-charles+marseille-y1": "/transfert-gare.html", "/aeroport+marseille-provence-y2": "/transfert-aeroport.html",
    "/gare+tgv+aix-en-provence-y4": "/transfert-gare.html", "/port+de+croisiere+mpct+marseille-y7": "/port-croisiere.html",
    "/parc+national+du+luberon-y3": "/vtc-longue-distance.html", "/toulon+dans+le+var-y5": "/vtc-longue-distance.html",
    "/avignon+84-y6": "/vtc-longue-distance.html", "/saint+remy+et+les+baux+de+provence+dans+les+alpilles-y8": "/vtc-longue-distance.html",
}
# Ordre = priorité : le premier thème trouvé dans l'adresse d'un ancien article l'emporte.
KEYWORDS = [
    ("/guide.html", ["vsl", "medical"]),
    ("/#flotte", ["flotte", "types+de+vehicules"]),
    ("/vtc-evenementiel.html", ["foire", "chanot", "mariage", "concert", "gala", "soiree", "evenement", "invites", "festival"]),
    ("/port-croisiere.html", ["croisiere", "mpct", "cruise"]),
    ("/vtc-affaires-vip.html", ["vip", "entreprise", "seminaire", "professionnel", "affaires", "corporate", "mise+a+disposition", "collaborateurs"]),
    ("/transfert-aeroport.html", ["aeroport", "airport", "amp", "+vol+"]),
    ("/transfert-gare.html", ["gare", "saint-charles", "tgv"]),
    ("/vtc-longue-distance.html", ["longue+distance", "avignon", "luberon", "toulon", "geneve", "nice", "ski", "val-thorens", "alpilles"]),
]
def old_target(url):
    if url in FIXED:
        return FIXED[url]
    for dest, words in KEYWORDS:
        if any(w in url for w in words):
            return dest
    return "/guide.html"

def build_redirects():
    lines = []
    for l in open(os.path.join(HERE, "old_urls.txt"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            target = "/" + clean(old_target(l).lstrip("/")) if old_target(l).endswith(".html") else old_target(l)
            if target.split("#")[0] != l:
                lines.append(f"{l}  {target}  301")
    lines += ["/archives-*  /guide  301", "/details-*  /guide  301"]
    open(os.path.join(OUT, "_redirects"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return len(lines)

def build_legal():
    """Pages légales : content/pages/<slug>.md (en-tête title, description, updated)."""
    out = []
    d = os.path.join(HERE, "content", "pages")
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        raw = open(os.path.join(d, f), encoding="utf-8").read()
        m = re.match(r"---\s*\n(.*?)\n---\s*\n(.*)", raw, re.S)
        meta = dict(re.findall(r"^(\w+):[ \t]*(.*?)[ \t]*$", m.group(1), re.M))
        slug = f[:-3]
        upd = f'<div class="art-meta"><span>Dernière mise à jour : {esc(meta["updated"])}</span></div>' if meta.get("updated") else ""
        body = f'''
<section class="page-hero" style="padding-bottom:clamp(40px,5vw,60px)">
  <div class="wrap">
    {crumbs([("Accueil", "index.html"), (meta["title"], "")], "{{root}}")}
    <h1>{esc(meta["title"])}</h1>
    {upd}
  </div>
</section>
<section class="light">
  <div class="wrap"><article class="prose legal">{markdown(m.group(2))}</article></div>
</section>'''
        out.append(page(slug + ".html", f'{meta["title"]} | Infinite Transfer', meta["description"], body,
                        jsonld=[ORG, crumbs_ld([("Accueil", "index.html"), (meta["title"], "")])]))
    return out

def build_404():
    body = f'''
<section class="page-hero" style="min-height:60vh">
  <div class="wrap">
    <span class="label">Erreur 404</span>
    <h1>Cette page <em>n'existe pas.</em></h1>
    <p class="lead">L'adresse demandée est introuvable ou a été déplacée. Retrouvez nos services ci-dessous, ou contactez-nous directement.</p>
    <div class="ctas">
      <a class="btn btn-or" href="/">Retour à l'accueil</a>
      <a class="btn btn-line" href="/contact">Demander un devis</a>
    </div>
  </div>
</section>'''
    page("404.html", "Page introuvable | Infinite Transfer", "Cette page n'existe pas.", body)
    # liens absolus : la page 404 peut s'afficher à n'importe quelle profondeur
    f = os.path.join(OUT, "404.html")
    doc = open(f, encoding="utf-8").read()
    doc = re.sub(r'(href|src|action)="(?:\./)?(?!https?:|/|#|tel:|mailto:)([^"]*)"', r'\1="/\2"', doc)
    doc = doc.replace('="/./', '="/').replace('<head>', '<head>\n<meta name="robots" content="noindex">', 1)
    open(f, "w", encoding="utf-8").write(doc)

def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(os.path.join(HERE, "assets"), os.path.join(OUT, "assets"))
    arts = load_articles()
    pages = [build_home(arts), build_contact(), build_guide(arts)]
    pages += [build_service(s, arts) for s in SERVICES]
    pages += build_legal()
    pages += [build_article(a, arts) for a in arts]
    build_404()
    lastmod = {f"articles/{a['slug']}.html": a["date"].isoformat() for a in arts}
    urls = "".join(f"<url><loc>{BASE_URL}/{clean(p)}</loc><lastmod>{lastmod.get(p, date.today().isoformat())}</lastmod></url>" for p in pages)
    open(os.path.join(OUT, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    open(os.path.join(OUT, "_headers"), "w").write("https://:project.pages.dev/*\n  X-Robots-Tag: noindex\n")
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    nred = build_redirects()
    print(f"{nred} redirections")
    print(f"{len(pages)} pages générées ({len(arts)} articles) dans public/")

if __name__ == "__main__":
    main()
