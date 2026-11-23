# CancelPath — Nightly Publishing, Money Report & Hosting Guide

**Live site:** https://dongwook482.github.io/cancelpath/  
**Repository:** https://github.com/DongWook482/cancelpath  
**Local preview (optional):** `SITE_BASE_URL=http://127.0.0.1:8088 python3 generate.py` then `python3 -m http.server 8088 --directory public`

## 1. Directory Layout (on the Box)
- `/workspace/niche-site/entries/*.md` — Source guide entries (JSON frontmatter + Markdown body). **Keep source here; never use `dist/`, `build/`, or `out/` directory names.**
- `/workspace/niche-site/generate.py` — Pure Python stdlib static site builder (`entries/` → `public/`). All internal links and CSS use the `/cancelpath/` base path when `SITE_BASE_URL=https://dongwook482.github.io/cancelpath`.
- `/workspace/niche-site/site.json` — Canonical `base_url` and `ads_enabled` (leave `ads_enabled` false until a real ad unit is approved).
- `/workspace/niche-site/public/` — Generated HTML (`index.html`, `about.html`, `privacy.html`, `categories/`, `guides/`, `sitemap.xml`, `robots.txt`, `styles.css`).
- `/workspace/niche-site/deploy.sh` — Rebuild with the public base URL, commit, push `main`, and verify the live GitHub Pages URLs.
- `/workspace/niche-site/.github/workflows/pages.yml` — Builds `public/` and deploys it to GitHub Pages.
- `/workspace/niche-site/publish_log.csv` — Append-only nightly publishing log.
- `/workspace/niche-site/revenue_ledger.json` — Verified revenue ledger (strictly real payouts/conversions only).
- `/workspace/niche-site/money_report.py` — Prints verified site & revenue metrics.

---

## 2. Nightly Publishing Routine (Exact Steps)

Run once every night (recommended ~23:00 KST):

1. **Discover today's fresh cancellation complaint (X + Reddit):**
   - Search recent X posts via the `x` MCP (`search_posts_all`) with queries such as:
     `("how do i cancel" OR "can't cancel" OR "won't let me cancel") (subscription OR membership OR plan) -is:retweet lang:en`
   - Search recent Reddit threads (`WebSearch` `site:reddit.com` for `"can't cancel"` / `"cancel membership"` / specific brand + `2026`).
   - Pick **one specific service/brand** not already in `/workspace/niche-site/publish_log.csv` that has clear, repeatable friction (e.g., WHOOP, Oura Ring, Vanity Fair, ElevenLabs, Duolingo/Apple billing, YouTube TV, Crunch Gym).

2. **Verify official + community escape path:**
   - Look up the service's official Help/Terms cancellation URL (`WebSearch` / `WebFetch`) and cross-check with real user workarounds from X/Reddit.
   - Never invent URLs, cutoff dates, phone numbers, or quotes. Only include verified facts and cite every source URL.

3. **Write one new guide file:**
   - Create `/workspace/niche-site/entries/<slug>.md` using the `---json ... ---` frontmatter schema (see `entries/planet-fitness-cancel-membership.md` as template).
   - Required frontmatter keys: `slug`, `title`, `service_name`, `category`, `category_slug`, `difficulty`, `cancel_method`, `direct_url`, `cutoff_rule`, `summary`, `published_at`, `updated_at`, `sources`.

4. **Append to `/workspace/niche-site/publish_log.csv`:**
   - Add one line: `YYYY-MM-DD,<slug>,<service_name>,<category>,<sources_count>,published,<short_note>`.

5. **Rebuild, publish, and verify the public URL:**
   ```bash
   DEPLOY_MESSAGE="Publish YYYY-MM-DD: <slug>" /workspace/niche-site/deploy.sh
   curl -fsS https://dongwook482.github.io/cancelpath/guides/<slug>.html | grep -q "<service_name>"
   curl -fsS https://dongwook482.github.io/cancelpath/sitemap.xml | grep -q "<slug>"
   curl -fsS -o /dev/null -w "%{http_code}\n" https://dongwook482.github.io/cancelpath/styles.css
   ```
   `deploy.sh` sets `SITE_BASE_URL=https://dongwook482.github.io/cancelpath`, runs `generate.py`, commits, pushes `main`, waits for GitHub Actions to deploy, and checks that the homepage, guide, category, legal pages, sitemap, and CSS return HTTP 200. Do not treat the local `127.0.0.1:8088` preview as the published site.

6. **Run & send the Money Report:**
   - Execute `python3 /workspace/niche-site/money_report.py`.
   - Report **only real verified numbers** from `revenue_ledger.json` and `publish_log.csv`. Never estimate or fabricate earnings.

---

## 3. Money Report Approach & What's Needed for Real Revenue

- **Current state:** Gross revenue is strictly **`$0.00 USD`**. The site is on GitHub Pages at https://dongwook482.github.io/cancelpath/ but no ad or affiliate network is connected, and no Search Console property has been verified yet.
- **How `money_report.py` stays honest:**
  - Reads `publish_log.csv` for true page count and latest deployment.
  - Reads `revenue_ledger.json` for verified transactions and active monetization channels.
  - Once a monetization channel is connected (manually or via API export), verified payouts/commissions are appended to `revenue_ledger.json` (or pulled via that network's reporting API with user authorization).
- **Requirements to move from `$0.00` to real revenue:**
  1. Public hosting — **done** (GitHub Pages, no custom domain yet; a custom domain is optional and helps some ad programs).
  2. **Search indexing (needs the user's Google login):** Verify the property in [Google Search Console](https://search.google.com/search-console) with **gkseh7721@gmail.com**, then submit `https://dongwook482.github.io/cancelpath/sitemap.xml`. (Do not create or sign in to this account on the user's behalf until they start that step.)
  3. **AdSense application (user must apply; do not sign up automatically):** After Search Console is verified and the site has a stable About + Privacy Policy (already published), apply for [Google AdSense](https://www.google.com/adsense/) with the same Google account. When approved, paste the official ad unit into the reserved `#ad-slot-top` / `#ad-slot-bottom` slots and set `"ads_enabled": true` in `site.json`. Update `privacy.html` the same day any ad or analytics script is added.
  4. Optional analytics (Plausible or Cloudflare Web Analytics) after the user chooses a provider.
  5. Optional affiliates (Impact, CJ, PartnerStack, or direct programs such as Privacy.com / Rocket Money) with disclosed referral links.

---

## 4. Public Hosting Status

The site is public on **GitHub Pages** from `DongWook482/cancelpath` (`main` branch, GitHub Actions workflow deploys `public/`).

Other free options remain available if we ever leave GitHub Pages:

1. **Cloudflare Pages** — Cloudflare account linked to this repo (publish directory `public/`) or a `CLOUDFLARE_API_TOKEN` for Wrangler, plus optional custom-domain DNS.
2. **Netlify** — Netlify account linked to this repo (publish directory `public/`) or a personal access token for the CLI.
