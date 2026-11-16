# Ottoline Wigs site

A small static site: guides are plain text files, and one script turns them into web pages.

## What's in here

| Path | What it is |
|---|---|
| `site.json` | Site name, tagline, domain, categories. Change the name here and it changes everywhere. |
| `content/guides/*.md` | One file per guide. Edit these to change the words. |
| `content/pages/*.md` | About, contact, privacy and affiliate disclosure. |
| `assets/style.css` | The look of the site. |
| `build.py` | Turns the content into the site. |
| `dist/` | The finished site. This is the folder you upload. |
| `preview.html` | The whole site in one file, for checking on a phone. |
| `shopify-export/` | The same content packaged for Shopify, for the later move. |
| `TODO.md` | Every note left for you inside the guides, collected in one list. |

## Before you launch

1. Buy the domain and put it in `site.json` (`domain` and `contact_email`).
2. Work through `TODO.md`. The most important items are your own About page, your own photos, and checking the VAT and NHS guides against the official pages.
3. Run `python3 build.py` and upload `dist/`.

## Soft launch and going public

`site.json` has `"noindex": true`. While it is set, the site works for anyone who has the address, but every page asks search engines not to list it. When the content checks in `TODO.md` are done, change it to `false`, rebuild and upload. Only then submit the sitemap to Google.

## Building

```
pip install markdown pyyaml
python3 build.py
```

## Weekly releases

Twenty guides carry a `publish:` date in their header. The live site leaves a guide out until that day, and removes links pointing to guides that aren't out yet. Nothing breaks in the meantime.

To release that week's guides, run the build and upload `dist` again:

```
python3 build.py                     # builds the site as of today
python3 build.py --date 2026-12-21   # shows what will be live on a given day
python3 build.py --all               # puts every guide live at once
```

`preview.html`, the Shopify export and `TODO.md` always include all 30 guides.

To move a release, change the `publish:` date in that guide's header. To release a guide immediately, delete the line.

## Adding or editing a guide

Each guide starts with a short header:

```
---
title: "How to Wash a Synthetic Wig"
handle: how-to-wash-a-synthetic-wig
category: care
order: 23
updated: 2026-11-14
description: One or two sentences. Shown under the title and to Google.
sources:
  - Name of the source | https://link
---
```

- `handle` becomes the web address. Never change it once the page is live.
- `category` must match an `id` in `site.json`.
- `disclaimer` is optional: `medical`, `tax` or `costs`.
- `publish` is optional: a date the guide goes live. Leave it out and the guide is live straight away.
- Anything inside `<!-- OWNER: ... -->` is a note to you. It never appears on the site.
- Link to other guides as `/blogs/guides/the-handle`.

## Hosting

Any static host works. Cloudflare Pages and Netlify both have free tiers and let you use your own domain.

- Upload the `dist` folder, or connect the project and set the build command to `pip install markdown pyyaml && python3 build.py` with `dist` as the output folder.
- Both hosts serve `something.html` at `/something`, so the addresses come out as `/blogs/guides/your-guide`. After the first deploy, open three or four pages and check the address bar shows no `.html` and no trailing slash. If it does, look for the host's "pretty URLs" setting.

## Moving to Shopify later

The site already uses Shopify's address patterns, so the web addresses stay the same and you keep your search history.

| This site | Shopify |
|---|---|
| `/blogs/guides` | A blog whose handle is `guides` |
| `/blogs/guides/<handle>` | A blog post with the same handle |
| `/pages/<handle>` | A page with the same handle |

Steps:

1. In Shopify, create a blog called "Guides" and confirm its handle is `guides`.
2. Import the posts from `shopify-export/articles.json` (or `articles.csv`) and the pages from `pages.json`. Shopify's admin has had no built-in importer for blog posts, so this is done with an import app or through Shopify's API. Check what's available at the time.
3. Confirm each post kept its handle. This is the step that protects your rankings.
4. Rebuild the look as a Shopify theme. `assets/style.css` is the reference.
5. Point the domain at Shopify.
6. Open every old address and check it loads. Add a redirect in Shopify for any that don't.

## Affiliate links

Links are kept in one file, `affiliates.json`, so a tracking URL is pasted once and changed in one place.

1. Add an entry to `affiliates.json` with a short key and the tracking URL the network gives you:

```
"natural-image": {"name": "Natural Image Wigs", "network": "Awin", "url": "https://..."}
```

2. In any guide or page, write the key and the words to link:

```
[[aff:natural-image|Natural Image Wigs]]
```

3. Run `python3 build.py`.

The build then does the rest:

- The words become a link, followed by "(affiliate link)".
- The link is marked `rel="sponsored nofollow"`, which is what Google asks for on paid links.
- A notice appears at the top of any guide that contains one.
- If an entry's `url` is empty, the words show as plain text. So you can place links now and switch them on when you're approved.
- The build prints how many links are active and which keys still need a URL.

For a link to a specific product, add another entry with its own key, such as `natural-image-style-name`.

Each guide's notes in `TODO.md` say where links belong. Keep the NHS, VAT and chemotherapy guides free of them.

## Tools

| Page | File with the working parts |
|---|---|
| `/pages/wig-finder-quiz` | `tools/quiz.html` (questions and matching rules) |
| `/pages/vat-relief-calculator` | `tools/vat-calculator.html` |
| `/pages/wig-glossary` | `content/pages/wig-glossary.md` (plain text, edit freely) |

The quiz only links to guides that are live, so it never points at a page that isn't out yet.

On Shopify, the glossary imports as an ordinary page. The quiz and calculator contain scripts, so they are best rebuilt as theme sections at that point. The files in `tools/` are the reference.
