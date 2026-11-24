#!/usr/bin/env python3
"""Static site generator for CancelPath (pure Python stdlib)."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
ENTRIES_DIR = ROOT / "entries"
PUBLIC_DIR = ROOT / "public"
CONFIG_PATH = ROOT / "site.json"
SITE_TITLE = "CancelPath"
SITE_TAGLINE = "Verified subscription & membership cancellation routes built from real user friction."
DEFAULT_PRODUCTION_URL = "https://dongwook482.github.io/cancelpath"

PLANNED_CATEGORIES = [
    ("gyms-fitness", "Gyms & Fitness", "In-person loops, franchise contracts, and billing cutoffs."),
    ("wearables-hardware", "Wearables & Hardware", "App-hidden cancel buttons and lost-device billing traps."),
    ("ai-saas", "AI & SaaS Tools", "Past-due lockouts, trial errors, and billing portal dead-ends."),
    ("media-news", "Media & Newsletters", "Print/digital login loops and phone-only retention desks."),
    ("streaming-apps", "Streaming & App Billing", "Apple App Store, Google Play, and direct-card mismatches."),
]


def load_site_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "base_url": DEFAULT_PRODUCTION_URL,
        "ads_enabled": False,
        "ga_measurement_id": "",
    }
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    env = os.environ.get("SITE_BASE_URL")
    if env:
        cfg["base_url"] = env
    cfg["base_url"] = str(cfg["base_url"]).rstrip("/")
    cfg["ads_enabled"] = bool(cfg.get("ads_enabled", False))
    raw_ga = str(cfg.get("ga_measurement_id") or "").strip()
    cfg["ga_measurement_id"] = raw_ga if re.fullmatch(r"G-[A-Z0-9]+", raw_ga) else ""
    return cfg


SITE_CONFIG = load_site_config()
BASE_URL = SITE_CONFIG["base_url"]
ADS_ENABLED = SITE_CONFIG["ads_enabled"]
GA_MEASUREMENT_ID = SITE_CONFIG["ga_measurement_id"]
_parsed_path = urlparse(BASE_URL).path.rstrip("/")
BASE_PATH = f"{_parsed_path}/" if _parsed_path else "/"


def href(path: str) -> str:
    """Root-relative path that works under the GitHub Pages project subpath."""
    return BASE_PATH + path.lstrip("/")


def parse_entry(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(raw)
        data.setdefault("body_md", "")
        return data

    match = re.match(r"^---json\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if not match:
        raise ValueError(f"{path.name}: expected ---json ... --- frontmatter")
    meta = json.loads(match.group(1))
    meta["body_md"] = match.group(2).strip()
    return meta


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    code_tokens: list[str] = []

    def _save_code(m: re.Match[str]) -> str:
        idx = len(code_tokens)
        code_tokens.append(f"<code>{m.group(1)}</code>")
        return f"\x00CODE{idx}\x00"

    escaped = re.sub(r"`([^`]+)`", _save_code, escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)

    for idx, tok in enumerate(code_tokens):
        escaped = escaped.replace(f"\x00CODE{idx}\x00", tok)
    return escaped


def render_markdown(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            code_html = html.escape("\n".join(code_lines))
            cls = f' class="lang-{html.escape(lang)}"' if lang else ""
            out.append(f"<pre><code{cls}>{code_html}</code></pre>")
            continue

        if stripped.startswith("### "):
            out.append(f"<h3>{render_inline(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            out.append(f"<h2>{render_inline(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{render_inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            out.append(f"<blockquote><p>{render_inline(' '.join(quote_lines))}</p></blockquote>")
            continue

        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{render_inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item_text = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append(f"<li>{render_inline(item_text)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        para_lines = []
        while (
            i < len(lines)
            and lines[i].strip()
            and not lines[i].strip().startswith(("##", "#", "> ", "- ", "```"))
            and not re.match(r"^\d+\.\s+", lines[i].strip())
        ):
            para_lines.append(lines[i].strip())
            i += 1
        out.append(f"<p>{render_inline(' '.join(para_lines))}</p>")

    return "\n".join(out)


def gtag_head_html() -> str:
    """Standard GA4 gtag.js snippet, omitted when no valid measurement ID is set."""
    if not GA_MEASUREMENT_ID:
        return ""
    mid = html.escape(GA_MEASUREMENT_ID, quote=True)
    return f"""  <script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{mid}');
  </script>
"""


def ad_slot_html(slot_id: str) -> str:
    """Reserved spot for a future approved ad unit. No dummy creatives."""
    escaped = html.escape(slot_id)
    if ADS_ENABLED:
        return (
            f'<aside class="ad-slot is-active" id="ad-slot-{escaped}" '
            f'data-ad-slot="{escaped}" aria-label="Advertisement"></aside>'
        )
    return (
        f'<!-- Reserved ad slot "{escaped}": add an approved ad unit only after a network is connected. -->\n'
        f'<aside class="ad-slot" id="ad-slot-{escaped}" data-ad-slot="{escaped}" hidden></aside>'
    )


def page_shell(title: str, description: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="stylesheet" href="{href('styles.css')}">
{gtag_head_html()}
</head>
<body>
  <header class="site-header">
    <div class="container header-inner">
      <a class="brand" href="{href('index.html')}">{SITE_TITLE}</a>
      <nav class="nav">
        <a href="{href('index.html')}">Directory</a>
        <a href="{href('categories/index.html')}">Categories</a>
        <a href="{href('about.html')}">About</a>
        <a href="{href('privacy.html')}">Privacy</a>
      </nav>
    </div>
  </header>

  <main class="container">
    {ad_slot_html('top')}
    {body_html}
    {ad_slot_html('bottom')}
  </main>

  <footer class="site-footer">
    <div class="container">
      <p><strong>{SITE_TITLE}</strong> — Independent cancellation route directory built from public support docs &amp; real user complaints.</p>
      <p class="muted"><a href="{href('about.html')}">About</a> &middot; <a href="{href('privacy.html')}">Privacy</a> &middot; <a href="{href('sitemap.xml')}">Sitemap</a></p>
      <p class="muted">Always confirm cancellation in writing and check your next statement. No affiliate or ad networks are active yet.</p>
    </div>
  </footer>
</body>
</html>
"""


CSS = """
:root {
  --bg: #f7f8fa;
  --card: #ffffff;
  --text: #161b22;
  --muted: #57606a;
  --border: #d8dee4;
  --accent: #0b57d0;
  --accent-soft: #eef4ff;
  --warn-bg: #fff8e6;
  --warn-border: #e3b341;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
}
.container { max-width: 880px; margin: 0 auto; padding: 0 20px; }
.site-header {
  background: var(--card);
  border-bottom: 1px solid var(--border);
  padding: 14px 0;
}
.header-inner { display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.brand { font-weight: 800; font-size: 1.15rem; color: var(--text); text-decoration: none; letter-spacing: -0.02em; }
.nav { display: flex; gap: 18px; flex-wrap: wrap; }
.nav a { color: var(--muted); text-decoration: none; font-size: 0.95rem; font-weight: 500; }
.nav a:hover { color: var(--accent); }
main { padding: 32px 0 48px; }
.hero {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px;
  margin-bottom: 24px;
}
.hero h1 { margin: 0 0 10px; font-size: 1.9rem; line-height: 1.25; }
.hero p { margin: 0 0 16px; color: var(--muted); }
.search-input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 1rem;
  background: var(--bg);
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 28px; }
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px;
}
.card h3 { margin: 0 0 6px; font-size: 1.05rem; }
.card a { color: var(--accent); text-decoration: none; }
.card a:hover { text-decoration: underline; }
.badge {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  margin-right: 6px;
}
.muted { color: var(--muted); font-size: 0.92rem; }
.fact-box {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  margin: 20px 0;
}
.fact-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
.fact-label { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.fact-val { font-weight: 600; margin-top: 2px; word-break: break-word; }
.alert-box {
  background: var(--warn-bg);
  border-left: 4px solid var(--warn-border);
  padding: 12px 16px;
  border-radius: 6px;
  margin: 18px 0;
}
article {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 28px;
}
article h1 { margin-top: 8px; line-height: 1.25; }
article h2 { margin-top: 28px; border-bottom: 1px solid var(--border); padding-bottom: 6px; font-size: 1.25rem; }
blockquote {
  margin: 16px 0;
  padding: 10px 16px;
  border-left: 3px solid var(--accent);
  background: var(--accent-soft);
  border-radius: 0 6px 6px 0;
}
pre {
  background: #0d1117;
  color: #e6edf3;
  padding: 14px 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.9rem;
}
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
.sources { margin-top: 28px; padding-top: 16px; border-top: 1px solid var(--border); }
.site-footer { border-top: 1px solid var(--border); padding: 22px 0; font-size: 0.9rem; }
.legal-page { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 28px; }
.legal-page h1 { margin-top: 0; }
.ad-slot { margin: 0; padding: 0; min-height: 0; }
.ad-slot.is-active { margin: 0 0 16px; min-height: 90px; }
"""

ABOUT_BODY = """
<article class="legal-page">
  <h1>About CancelPath</h1>
  <p>CancelPath is an independent, free directory of verified routes for canceling subscriptions and memberships. Official help pages, billing portals, and mobile apps often hide, relocate, or break the cancel button. We publish one practical, source-cited guide at a time so people can find the working path before the next charge hits.</p>
  <h2>How guides are written</h2>
  <ul>
    <li>Each page starts from a real, recent complaint (public posts on X or Reddit) and is checked against the company's official support or terms page.</li>
    <li>We do not invent URLs, cutoff dates, phone numbers, or quotes. Every claim is cited.</li>
    <li>CancelPath is not affiliated with Planet Fitness, WHOOP, Oura, Apple, Google, or any other service named in a guide.</li>
  </ul>
  <h2>Project status</h2>
  <p>The site is a static directory published at <a href="https://dongwook482.github.io/cancelpath/">dongwook482.github.io/cancelpath</a> from the public repository <a href="https://github.com/DongWook482/cancelpath">github.com/DongWook482/cancelpath</a>. No user accounts, comments, or payments are collected here.</p>
  <p>Advertising and affiliate links are not active yet. Reserved slots exist in the page layout for a future approved ad unit; they stay empty until a network is connected and disclosed.</p>
  <p>We use Google Analytics 4 to measure visits. Details are in the <a href="https://dongwook482.github.io/cancelpath/privacy.html">Privacy Policy</a>.</p>
  <h2>Contact</h2>
  <p>For corrections to a guide, open an issue or pull request on the public GitHub repository linked above.</p>
</article>
"""

PRIVACY_BODY = """
<article class="legal-page">
  <h1>Privacy Policy</h1>
  <p>Last updated: 24 November 2026.</p>
  <p>CancelPath is a static informational website. We want this policy to stay accurate, so it only describes practices that are in use today.</p>
  <h2>Information we collect</h2>
  <p>This site does not ask you to create an account, submit a form, or pay for anything. We do not run advertising or an affiliate program at this time, and we do not operate a first-party comment system.</p>
  <h2>Google Analytics</h2>
  <p>CancelPath uses Google Analytics 4 (GA4) to understand how the public site is used (for example, how many people visit, which pages are viewed, and from which general regions or devices). The measurement tag runs on every generated page. Google may collect device and usage data such as IP address, browser type, referring URL, and page path, and may set or read cookies or similar storage in your browser.</p>
  <p>This processing is handled by Google under the <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Privacy Policy</a>. Google also explains how it uses data from sites and apps that use its services at <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener noreferrer">policies.google.com/technologies/partner-sites</a>.</p>
  <h2>Hosting logs</h2>
  <p>The site is hosted on GitHub Pages. GitHub may process standard server or CDN request data (such as IP address, user agent, and requested URL) according to the <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener noreferrer">GitHub Privacy Statement</a>. CancelPath does not receive a copy of those logs.</p>
  <h2>Cookies and advertising</h2>
  <p>CancelPath does not run Google AdSense or any other ad or affiliate network today. Google Analytics may set or read cookies (or similar storage) for measurement only. If advertising or affiliate links are added later, this Privacy Policy will be updated before those features go live, and any required consent or disclosure will be added at the same time.</p>
  <h2>External links</h2>
  <p>Guides link to official company portals, support pages, and public discussion threads. Those third-party sites have their own privacy practices, which we do not control.</p>
  <h2>Changes</h2>
  <p>Material changes to this policy will be posted on this page with an updated date. Questions about this policy can be raised on the project's public GitHub repository.</p>
</article>
"""


def build() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "guides").mkdir(exist_ok=True)
    (PUBLIC_DIR / "categories").mkdir(exist_ok=True)

    entries: list[dict[str, Any]] = []
    if ENTRIES_DIR.exists():
        for p in sorted(ENTRIES_DIR.iterdir()):
            if p.suffix in {".md", ".json"}:
                entries.append(parse_entry(p))

    entries.sort(key=lambda e: (e.get("updated_at", ""), e["slug"]), reverse=True)

    (PUBLIC_DIR / "styles.css").write_text(CSS.strip() + "\n", encoding="utf-8")

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for slug, _, _ in PLANNED_CATEGORIES:
        by_cat[slug] = []
    for e in entries:
        by_cat.setdefault(e["category_slug"], []).append(e)

    sitemap_urls: list[tuple[str, str]] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for e in entries:
        sources_li = "".join(
            f'<li><a href="{html.escape(s["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(s["label"])}</a></li>'
            for s in e.get("sources", [])
        )
        direct_link_html = (
            f'<a href="{html.escape(e["direct_url"])}" target="_blank" rel="noopener noreferrer">{html.escape(e["direct_url"])}</a>'
            if e.get("direct_url")
            else "N/A"
        )
        alt_html = (
            f'<div><div class="fact-label">Alternate Portal</div><div class="fact-val"><a href="{html.escape(e["alt_url"])}" target="_blank" rel="noopener noreferrer">{html.escape(e["alt_url"])}</a></div></div>'
            if e.get("alt_url")
            else ""
        )
        body = f"""
        <p class="muted"><a href="{href('index.html')}">Directory</a> / <a href="{href('categories/' + e['category_slug'] + '.html')}">{html.escape(e['category'])}</a> / {html.escape(e['service_name'])}</p>
        <article>
          <span class="badge">{html.escape(e['category'])}</span>
          <span class="badge">Difficulty: {html.escape(e.get('difficulty', 'Unknown'))}</span>
          <h1>{html.escape(e['title'])}</h1>
          <p class="muted">Updated: {html.escape(e.get('updated_at', today))} &middot; Method: {html.escape(e.get('cancel_method', 'Web'))}</p>

          <div class="fact-box">
            <div class="fact-grid">
              <div>
                <div class="fact-label">Direct Cancellation Link</div>
                <div class="fact-val">{direct_link_html}</div>
              </div>
              {alt_html}
              <div>
                <div class="fact-label">Billing Cutoff Rule</div>
                <div class="fact-val">{html.escape(e.get('cutoff_rule', 'Check billing date'))}</div>
              </div>
            </div>
          </div>

          <div class="alert-box">
            <strong>Quick takeaway:</strong> {html.escape(e['summary'])}
          </div>

          {render_markdown(e['body_md'])}

          <div class="sources">
            <h2>Verified Sources &amp; Real User Reports</h2>
            <ul>{sources_li}</ul>
          </div>
        </article>
        """
        out_path = PUBLIC_DIR / "guides" / f"{e['slug']}.html"
        out_path.write_text(
            page_shell(f"{e['title']} | {SITE_TITLE}", e["summary"], body),
            encoding="utf-8",
        )
        sitemap_urls.append((f"{BASE_URL}/guides/{e['slug']}.html", e.get("updated_at", today)))

    cat_meta_map = {slug: (name, desc) for slug, name, desc in PLANNED_CATEGORIES}
    for slug, cat_entries in by_cat.items():
        name, desc = cat_meta_map.get(slug, (slug.replace("-", " ").title(), "Cancellation guides in this category."))
        if cat_entries:
            cards = "".join(
                f"""<div class="card">
                  <span class="badge">{html.escape(e.get('difficulty', 'Guide'))}</span>
                  <h3><a href="{href('guides/' + e['slug'] + '.html')}">{html.escape(e['title'])}</a></h3>
                  <p class="muted">{html.escape(e['summary'])}</p>
                </div>"""
                for e in cat_entries
            )
        else:
            cards = '<div class="card"><p class="muted">No guides published in this category yet. Nightly publishing adds one verified guide per day.</p></div>'

        cat_body = f"""
        <p class="muted"><a href="{href('index.html')}">Directory</a> / <a href="{href('categories/index.html')}">Categories</a> / {html.escape(name)}</p>
        <div class="hero">
          <h1>{html.escape(name)}</h1>
          <p>{html.escape(desc)}</p>
        </div>
        <div class="grid">{cards}</div>
        """
        (PUBLIC_DIR / "categories" / f"{slug}.html").write_text(
            page_shell(f"{name} Cancellation Guides | {SITE_TITLE}", desc, cat_body),
            encoding="utf-8",
        )
        sitemap_urls.append((f"{BASE_URL}/categories/{slug}.html", today))

    cat_cards = "".join(
        f"""<div class="card">
          <span class="badge">{len(by_cat.get(slug, []))} guide(s)</span>
          <h3><a href="{href('categories/' + slug + '.html')}">{html.escape(name)}</a></h3>
          <p class="muted">{html.escape(desc)}</p>
        </div>"""
        for slug, name, desc in PLANNED_CATEGORIES
    )
    cats_index_body = f"""
    <div class="hero">
      <h1>Categories</h1>
      <p>Browse cancellation escape routes by sector. Updated nightly from live X and Reddit friction reports.</p>
    </div>
    <div class="grid">{cat_cards}</div>
    """
    (PUBLIC_DIR / "categories" / "index.html").write_text(
        page_shell(f"Categories | {SITE_TITLE}", "All cancellation guide categories on CancelPath.", cats_index_body),
        encoding="utf-8",
    )
    sitemap_urls.append((f"{BASE_URL}/categories/index.html", today))

    guide_cards = "".join(
        f"""<div class="card guide-card" data-search="{html.escape((e['service_name'] + ' ' + e['title'] + ' ' + e['category'] + ' ' + e['summary']).lower())}">
          <span class="badge">{html.escape(e['category'])}</span>
          <span class="badge">{html.escape(e.get('difficulty', 'Guide'))}</span>
          <h3><a href="{href('guides/' + e['slug'] + '.html')}">{html.escape(e['title'])}</a></h3>
          <p class="muted">{html.escape(e['summary'])}</p>
          <p class="muted"><strong>Cutoff / Trap:</strong> {html.escape(e.get('cutoff_rule', 'See guide'))}</p>
        </div>"""
        for e in entries
    )
    cat_pills = "".join(
        f'<a class="badge" href="{href("categories/" + slug + ".html")}">{html.escape(name)} ({len(by_cat.get(slug, []))})</a>'
        for slug, name, _ in PLANNED_CATEGORIES
    )
    index_body = f"""
    <section class="hero">
      <h1>Escape Hidden Cancellation Loops.</h1>
      <p>{SITE_TAGLINE}</p>
      <input id="filterInput" class="search-input" type="search" placeholder="Filter guides by service, gym, app, or issue (e.g. Planet Fitness, billing)..." aria-label="Filter guides">
      <div style="margin-top: 14px;">{cat_pills}</div>
    </section>

    <h2>Published Guides ({len(entries)})</h2>
    <div class="grid" id="guidesGrid">
      {guide_cards}
    </div>

    <section class="card">
      <h3>Why CancelPath Exists</h3>
      <p class="muted">Every day, people post on X and Reddit asking why a mobile app hides its cancel button, why a gym demands in-person cancellation after moving, or why an expired invoice blocks cancellation. This directory publishes one verified, source-cited escape guide each night.</p>
    </section>

    <script>
      const input = document.getElementById('filterInput');
      const cards = Array.from(document.querySelectorAll('.guide-card'));
      input.addEventListener('input', () => {{
        const q = input.value.trim().toLowerCase();
        cards.forEach(c => {{
          c.style.display = (!q || c.dataset.search.includes(q)) ? '' : 'none';
        }});
      }});
    </script>
    """
    (PUBLIC_DIR / "index.html").write_text(
        page_shell(f"{SITE_TITLE} — Verified Cancellation Route Directory", SITE_TAGLINE, index_body),
        encoding="utf-8",
    )

    (PUBLIC_DIR / "about.html").write_text(
        page_shell(
            f"About | {SITE_TITLE}",
            "What CancelPath is, how guides are researched, and the current project status.",
            ABOUT_BODY,
        ),
        encoding="utf-8",
    )
    (PUBLIC_DIR / "privacy.html").write_text(
        page_shell(
            f"Privacy Policy | {SITE_TITLE}",
            "CancelPath privacy policy: Google Analytics, cookies, hosting, and advertising status.",
            PRIVACY_BODY,
        ),
        encoding="utf-8",
    )
    not_found_body = (
        '<article class="legal-page">'
        "<h1>Page not found</h1>"
        f'<p>That address is not in the directory. Return to the <a href="{href("index.html")}">CancelPath homepage</a> '
        f'or browse <a href="{href("categories/index.html")}">categories</a>.</p>'
        "</article>"
    )
    (PUBLIC_DIR / "404.html").write_text(
        page_shell(
            f"Page not found | {SITE_TITLE}",
            "This CancelPath page does not exist.",
            not_found_body,
        ),
        encoding="utf-8",
    )

    sitemap_urls = [
        (f"{BASE_URL}/", today),
        (f"{BASE_URL}/index.html", today),
        (f"{BASE_URL}/about.html", today),
        (f"{BASE_URL}/privacy.html", today),
        (f"{BASE_URL}/404.html", today),
        *sitemap_urls,
    ]

    url_nodes = "\n".join(
        f"  <url>\n    <loc>{html.escape(u)}</loc>\n    <lastmod>{html.escape(d)}</lastmod>\n  </url>"
        for u, d in sitemap_urls
    )
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_nodes}
</urlset>
"""
    (PUBLIC_DIR / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
    (PUBLIC_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )

    print(f"Built {len(entries)} guide(s), {len(sitemap_urls)} total URLs")
    print(f"BASE_URL={BASE_URL}")
    print(f"BASE_PATH={BASE_PATH}")
    print(f"GA_MEASUREMENT_ID={GA_MEASUREMENT_ID or '(disabled)'}")
    print(f"ADS_ENABLED={ADS_ENABLED}")


if __name__ == "__main__":
    build()
