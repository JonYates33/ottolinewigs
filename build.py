#!/usr/bin/env python3
"""Build the site.

Reads   site.json, content/guides/*.md, content/pages/*.md, assets/
Writes  dist/            the live site (upload this folder to your host)
        preview.html     the whole site in one file, for checking on a phone
        shopify-export/  articles and pages ready to import into Shopify later
        TODO.md          every note left for the site owner inside the content

URLs copy Shopify's patterns so nothing moves when the site migrates:
    /blogs/guides                 guide hub
    /blogs/guides/<handle>        one guide
    /pages/<handle>               info page

Needs: pip install markdown pyyaml
"""
import csv
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE = json.loads((ROOT / "site.json").read_text())
BLOG = SITE["blog_handle"]
OWNER_NOTE = re.compile(r"<!--\s*OWNER:(.*?)-->", re.S)
AFF_FILE = ROOT / "affiliates.json"
AFFILIATES = json.loads(AFF_FILE.read_text()) if AFF_FILE.exists() else {}
AFF_CODE = re.compile(r"\[\[aff:([a-z0-9-]+)\|([^\]]+)\]\]")
AFF_NOTICE = "This guide contains affiliate links, marked where they appear. If you buy through one we may earn a commission, at no extra cost to you."


def affiliate_links(body, meta):
    """[[aff:key|link text]] becomes a labelled affiliate link, using the URL saved under
    that key in affiliates.json. Until the key has a URL, the text shows with no link."""
    def swap(m):
        entry = AFFILIATES.get(m.group(1)) or {}
        url = (entry.get("url") or "").strip()
        meta.setdefault("aff_keys", []).append(m.group(1))
        if not url:
            return m.group(2)
        meta["has_aff"] = True
        return (f'<a class="aff" href="{html.escape(url, quote=True)}" rel="sponsored nofollow noopener">{m.group(2)}</a>'
                f' <span class="aff-tag">(affiliate link)</span>')
    return AFF_CODE.sub(swap, body)

DISCLAIMERS = {
    "medical": "This guide is general information, not medical advice. Your hospital team, GP or dermatologist can advise on your own situation.",
    "tax": "This guide is general information, not tax advice. HMRC's rules decide who qualifies, and only you can declare that you do.",
    "costs": "NHS charges and rules change, usually each April. Check the official pages linked below before relying on a figure.",
}


def load(folder):
    items = []
    for path in sorted((ROOT / "content" / folder).glob("*.md")):
        raw = path.read_text()
        _, front, body = raw.split("---", 2)
        meta = yaml.safe_load(front)
        meta["notes"] = [n.strip() for n in OWNER_NOTE.findall(body)]
        body = OWNER_NOTE.sub("", body)
        body = affiliate_links(body, meta)
        meta["html"] = markdown.markdown(body, extensions=["tables", "toc", "attr_list", "def_list"])
        if meta.get("tool"):
            meta["tool_html"] = (ROOT / "tools" / f"{meta['tool']}.html").read_text()
        meta["words"] = len(re.sub(r"<[^>]+>", " ", meta["html"]).split())
        meta["file"] = path.name
        items.append(meta)
    return items


def esc(text):
    return html.escape(str(text), quote=True)


def guide_url(g):
    return f"/blogs/{BLOG}/{g['handle']}"


def page_url(p):
    return f"/pages/{p['handle']}"


def layout(title, description, canonical, main, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{SITE['domain']}{canonical}">
<link rel="stylesheet" href="/assets/style.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%236b3a5b'/%3E%3Ctext x='32' y='45' font-family='Georgia,serif' font-size='40' font-weight='700' text-anchor='middle' fill='%23faf6f1'%3EO%3C/text%3E%3C/svg%3E">
{'<meta name="robots" content="noindex, nofollow">' if SITE.get("noindex") else ""}
{extra_head}
</head>
<body>
{header()}
<main>
{main}
</main>
{footer()}
</body>
</html>
"""


def header():
    return f"""<header class="site-header">
  <a class="brand" href="/">{esc(SITE['name'])}</a>
  <nav aria-label="Main">
    <a href="/blogs/{BLOG}">Guides</a>
    <a href="/pages/wig-finder-quiz">Wig finder</a>
    <a href="/pages/about">About</a>
    <a href="/pages/contact">Contact</a>
  </nav>
</header>"""


def footer():
    links = "".join(f'<a href="{page_url(p)}">{esc(p["title"])}</a>'
                    for p in sorted(PAGES, key=lambda p: p.get("group") != "tools"))
    return f"""<footer class="site-footer">
  <nav aria-label="Footer">{links}</nav>
  <p class="disclosure">{esc(SITE['footer_disclosure'])}</p>
  <p class="small">&copy; {date.today().year} {esc(SITE.get('legal_name', SITE['name']))}</p>
</footer>"""


def card(g):
    return f"""<a class="card" href="{guide_url(g)}">
  <span class="card-cat">{esc(CAT_TITLE[g['category']])}</span>
  <span class="card-title">{esc(g['title'])}</span>
  <span class="card-desc">{esc(g['description'])}</span>
</a>"""


def tool_card(p):
    return f"""<a class="card" href="{page_url(p)}">
  <span class="card-cat">Tool</span>
  <span class="card-title">{esc(p['title'])}</span>
  <span class="card-desc">{esc(p.get('description', ''))}</span>
</a>"""


def sources_block(g):
    rows = []
    for s in g.get("sources", []):
        if isinstance(s, dict):  # a source title containing ": " is read by YAML as a mapping
            s = ": ".join(f"{k}: {v}" if v is not None else str(k) for k, v in s.items()) if len(s) > 1 else "%s: %s" % next(iter(s.items()))
        label, url = [x.strip() for x in s.rsplit("|", 1)]
        rows.append(f'<li><a href="{esc(url)}" rel="noopener">{esc(label)}</a></li>')
    if not rows:
        return ""
    return f'<section class="sources"><h2 id="sources">Sources</h2><ul>{"".join(rows)}</ul></section>'


def guide_main(g):
    minutes = max(1, round(g["words"] / 220))
    updated = g["updated"].strftime("%-d %B %Y")
    note = DISCLAIMERS.get(g.get("disclaimer", ""), "")
    note_html = f'<p class="notice">{esc(note)}</p>' if note else ""
    if g.get("has_aff"):
        note_html += f'<p class="notice aff-notice">{esc(AFF_NOTICE)} <a href="/pages/affiliate-disclosure">How this works</a>.</p>'
    related = [x for x in GUIDES if x["category"] == g["category"] and x is not g][:3]
    related_html = ""
    if related:
        related_html = f'<section class="related"><h2>Related guides</h2><div class="cards">{"".join(card(x) for x in related)}</div></section>'
    return f"""<article class="guide">
  <p class="crumbs"><a href="/">Home</a> / <a href="/blogs/{BLOG}">Guides</a> / {esc(CAT_TITLE[g['category']])}</p>
  <h1>{esc(g['title'])}</h1>
  <p class="meta">Last reviewed {updated} &middot; {minutes} min read &middot; {esc(SITE['author'])}</p>
  <p class="lede">{esc(g['description'])}</p>
  {note_html}
  <div class="prose">{g['html']}</div>
  {sources_block(g)}
  {related_html}
</article>"""


def hub_main():
    out = ['<section class="hub"><h1>Guides</h1><p class="lede">Everything we have written, grouped by where you are on the way to a wig you like wearing.</p>']
    for cat in SITE["categories"]:
        items = [g for g in GUIDES if g["category"] == cat["id"]]
        if not items:
            continue
        out.append(f'<h2 id="{cat["id"]}">{esc(cat["title"])}</h2><p class="cat-intro">{esc(cat["intro"])}</p><div class="cards">{"".join(card(g) for g in items)}</div>')
    out.append("</section>")
    return "".join(out)


def home_main():
    start = [g for g in GUIDES if g["category"] == "starting-out"][:3]
    help_ = [g for g in GUIDES if g["category"] == "hair-loss"][:4]
    return f"""<section class="hero">
  <h1>{esc(SITE['tagline'])}</h1>
  <p class="lede">Buying a wig for the first time is confusing. We explain the choices in plain English, tell you what things really cost in the UK, and show you where help with the cost is available.</p>
  <p><a class="button" href="{guide_url(GUIDES[0])}">Start with the beginner's guide</a></p>
</section>
<section><h2>Start here</h2><div class="cards">{"".join(card(g) for g in start)}</div></section>
<section><h2>Help with medical hair loss</h2><div class="cards">{"".join(card(g) for g in help_)}</div></section>
<section><h2>Tools</h2><div class="cards">{"".join(tool_card(p) for p in PAGES if p.get("group") == "tools")}</div></section>
<p class="more"><a href="/blogs/{BLOG}">See all guides</a></p>"""


def page_main(p):
    live_handles = {g["handle"] for g in GUIDES}
    body = unlink_unpublished(p["html"], live_handles)
    tool = p.get("tool_html", "").replace("/*LIVE_HANDLES*/[]", json.dumps(sorted(live_handles)))
    aff = f'<p class="notice aff-notice">{esc(AFF_NOTICE)}</p>' if p.get("has_aff") else ""
    return f'<article class="guide"><h1>{esc(p["title"])}</h1>{aff}<div class="prose">{body}</div>{tool}{sources_block(p) if p.get("sources") else ""}</article>'


def article_schema(g):
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": g["title"],
        "description": g["description"],
        "dateModified": g["updated"].isoformat(),
        "author": {"@type": "Organization", "name": SITE["name"]},
        "mainEntityOfPage": SITE["domain"] + guide_url(g),
    }
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


def write(rel, text):
    path = DIST / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build_site():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "assets", DIST / "assets")
    write("index.html", layout(f"{SITE['name']}: {SITE['tagline']}", SITE["description"], "/", home_main()))
    write(f"blogs/{BLOG}.html", layout(f"Guides | {SITE['name']}", "All of our wig guides in one place.", f"/blogs/{BLOG}", hub_main()))
    for g in GUIDES:
        write(f"blogs/{BLOG}/{g['handle']}.html",
              layout(f"{g['title']} | {SITE['name']}", g["description"], guide_url(g), guide_main(g), article_schema(g)))
    for p in PAGES:
        write(f"pages/{p['handle']}.html", layout(f"{p['title']} | {SITE['name']}", p.get("description", p["title"]), page_url(p), page_main(p)))
    urls = ["/", f"/blogs/{BLOG}"] + [guide_url(g) for g in GUIDES] + [page_url(p) for p in PAGES]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{SITE['domain']}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    if SITE.get("noindex"):
        # Soft launch: the site works for anyone with the address, but search engines are asked to stay out.
        write("robots.txt", "User-agent: *\nDisallow: /\n")
    else:
        write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE['domain']}/sitemap.xml\n")
    not_found = ('<article class="guide"><h1>Page not found</h1><p class="lede">Sorry, there is nothing at this address.</p>'
                 f'<p><a class="button" href="/blogs/{BLOG}">See all guides</a></p><p><a href="/">Back to the home page</a></p></article>')
    write("404.html", layout(f"Page not found | {SITE['name']}", "Page not found.", "/404", not_found))


def build_preview():
    """One self-contained file: every page is a section, shown by its #name."""
    def localise(fragment):
        fragment = re.sub(rf'href="/blogs/{BLOG}/([a-z0-9-]+)"', r'href="#\1"', fragment)
        fragment = re.sub(rf'href="/blogs/{BLOG}(#[a-z0-9-]+)?"', 'href="#guides"', fragment)
        fragment = re.sub(r'href="/pages/([a-z0-9-]+)"', r'href="#page-\1"', fragment)
        fragment = fragment.replace('href="/"', 'href="#home"')
        fragment = fragment.replace('var GUIDE_BASE = "/blogs/%s/";' % BLOG, 'var GUIDE_BASE = "#";')
        return fragment

    views = [("home", home_main()), ("guides", hub_main())]
    views += [(g["handle"], guide_main(g)) for g in GUIDES]
    views += [("page-" + p["handle"], page_main(p)) for p in PAGES]
    sections = "".join(f'<section class="view" data-view="{name}" hidden>{localise(body)}</section>' for name, body in views)
    css = (ROOT / "assets" / "style.css").read_text()
    script = """
function show(){var n=location.hash.slice(1)||'home',found=false;
document.querySelectorAll('.view').forEach(function(v){var on=v.dataset.view===n;v.hidden=!on;if(on)found=true;});
if(!found){document.querySelector('[data-view=home]').hidden=false;}
window.scrollTo(0,0);}
window.addEventListener('hashchange',show);show();
"""
    page = f"""<!DOCTYPE html>
<html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(SITE['name'])} site preview</title>
<style>{css}
.preview-bar{{background:#2b2320;color:#faf6f1;font-size:.8rem;padding:.4rem 1rem;text-align:center}}</style></head>
<body><div class="preview-bar">Preview of all {len(GUIDES)} guides, including those not yet released. Not the live site.</div>
{localise(header())}<main>{sections}</main>{localise(footer())}
<script>{script}</script></body></html>"""
    (ROOT / "preview.html").write_text(page)


def build_shopify_export():
    out = ROOT / "shopify-export"
    out.mkdir(exist_ok=True)
    articles = []
    for g in GUIDES:
        body = g["html"] + sources_block(g)
        articles.append({
            "blog_handle": BLOG, "handle": g["handle"], "title": g["title"], "author": SITE["author"],
            "body_html": body, "summary_html": g["description"], "tags": CAT_TITLE[g["category"]],
            "seo_title": g["title"], "seo_description": g["description"],
            "published_at": (g.get("publish") or g["updated"]).isoformat(),
        })
    all_handles = json.dumps(sorted(g["handle"] for g in ALL_GUIDES))
    pages = [{"handle": p["handle"], "title": p["title"],
              "body_html": p["html"] + p.get("tool_html", "").replace("/*LIVE_HANDLES*/[]", all_handles)} for p in PAGES]
    (out / "articles.json").write_text(json.dumps(articles, indent=2))
    (out / "pages.json").write_text(json.dumps(pages, indent=2))
    with open(out / "articles.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(articles[0].keys()))
        w.writeheader()
        w.writerows(articles)


def build_todo():
    lines = ["# Notes for the site owner", "", "Generated by build.py from the OWNER comments inside each content file.", ""]
    for item in GUIDES + PAGES:
        if item["notes"]:
            lines.append(f"## {item['title']}  ({item['file']})")
            lines += [f"- {n}" for n in item["notes"]]
            lines.append("")
    (ROOT / "TODO.md").write_text("\n".join(lines))


def unlink_unpublished(fragment, live_handles):
    """On the live site, turn links to guides that are not out yet into plain text."""
    def swap(m):
        return m.group(0) if m.group(1) in live_handles else m.group(2)
    return re.sub(rf'<a href="/blogs/{BLOG}/([a-z0-9-]+)">(.*?)</a>', swap, fragment, flags=re.S)


ALL_GUIDES = sorted(load("guides"), key=lambda g: g["order"])
PAGES = load("pages")
CAT_TITLE = {c["id"]: c["title"] for c in SITE["categories"]}
GUIDES = ALL_GUIDES

if __name__ == "__main__":
    # A guide with a `publish:` date in its header stays off the live site until that day.
    # Run with --all to put everything live at once, or --date YYYY-MM-DD to build as of a day.
    today = date.today()
    if "--date" in sys.argv:
        today = date.fromisoformat(sys.argv[sys.argv.index("--date") + 1])
    everything = "--all" in sys.argv
    live = [g for g in ALL_GUIDES if everything or not g.get("publish") or g["publish"] <= today]
    waiting = [g for g in ALL_GUIDES if g not in live]

    # The live site: published guides only, with links to unpublished guides removed.
    live_handles = {g["handle"] for g in live}
    originals = {g["handle"]: g["html"] for g in ALL_GUIDES}
    for g in live:
        g["html"] = unlink_unpublished(g["html"], live_handles)
    GUIDES = live
    build_site()
    for g in ALL_GUIDES:
        g["html"] = originals[g["handle"]]

    # The preview, the Shopify export and the to-do list cover every guide.
    GUIDES = ALL_GUIDES
    build_preview()
    build_shopify_export()
    build_todo()

    print(f"Live site: {len(live)} guides and {len(PAGES)} pages in dist/ (as of {today})")
    for g in sorted(waiting, key=lambda g: g["publish"]):
        print(f"  waiting until {g['publish']}: {g['title']}")
    print(f"Preview and Shopify export: all {len(ALL_GUIDES)} guides")
    used = sorted({k for i in ALL_GUIDES + PAGES for k in i.get("aff_keys", [])})
    empty = [k for k in used if not (AFFILIATES.get(k) or {}).get("url")]
    print(f"Affiliate links: {len(used) - len(empty)} active, {len(empty)} waiting for a URL in affiliates.json" + (f" ({', '.join(empty)})" if empty else ""))
    print(f"Owner notes: {sum(len(i['notes']) for i in ALL_GUIDES + PAGES)} (see TODO.md)")
