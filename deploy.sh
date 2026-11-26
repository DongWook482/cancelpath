#!/usr/bin/env bash
# Rebuild CancelPath and push to GitHub Pages (DongWook482/cancelpath).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

export SITE_BASE_URL="${SITE_BASE_URL:-https://dongwook482.github.io/cancelpath}"
PUBLIC_HOME="${SITE_BASE_URL}/"
PUBLIC_SITEMAP="${SITE_BASE_URL}/sitemap.xml"

echo "==> Building site (SITE_BASE_URL=${SITE_BASE_URL})"
python3 generate.py

if [ ! -d .git ]; then
  echo "error: ${ROOT} is not a git repository" >&2
  exit 1
fi

git add -A
if git diff --cached --quiet; then
  echo "==> No source changes to commit"
else
  MSG="${DEPLOY_MESSAGE:-Publish $(date +%Y-%m-%d) CancelPath update}"
  git commit -m "$MSG"
fi

SHA="$(git rev-parse HEAD)"
echo "==> Pushing main (sha ${SHA})"
git push origin main

# Wait for the run whose headSha matches this push, not a previous successful run.
if command -v gh >/dev/null 2>&1; then
  RUN_ID=""
  for i in $(seq 1 24); do
    RUN_ID="$(gh run list --repo DongWook482/cancelpath --branch main --workflow "Deploy GitHub Pages" --limit 10 --json databaseId,headSha --jq ".[] | select(.headSha==\"${SHA}\") | .databaseId" | head -n 1 || true)"
    if [ -n "${RUN_ID}" ]; then
      break
    fi
    echo "    waiting for Actions run for ${SHA} (attempt ${i})"
    sleep 5
  done
  if [ -n "${RUN_ID}" ]; then
    echo "==> Waiting for Actions run ${RUN_ID} (sha ${SHA})"
    gh run watch "${RUN_ID}" --repo DongWook482/cancelpath --exit-status
  else
    echo "warning: no Actions run found for ${SHA} after waiting" >&2
  fi
fi

GA_ID="$(python3 -c 'import json; print(json.load(open("site.json")).get("ga_measurement_id",""))' 2>/dev/null || true)"

echo "==> Waiting for GitHub Pages to serve the new build"
ok=0
for i in $(seq 1 24); do
  code=$(curl -sS -o /tmp/cancelpath-home.body -w "%{http_code}" -A "CancelPath-deploy/1.0" "$PUBLIC_HOME" || true)
  if [ "$code" = "200" ]; then
    if [ -n "$GA_ID" ] && ! grep -q "$GA_ID" /tmp/cancelpath-home.body; then
      echo "    attempt ${i}: homepage HTTP 200 but missing ${GA_ID} (retry in 10s)"
      sleep 10
      continue
    fi
    if ! grep -q "contact.html" /tmp/cancelpath-home.body; then
      echo "    attempt ${i}: homepage HTTP 200 but missing contact.html (stale Pages build, retry in 10s)"
      sleep 10
      continue
    fi
    if ! grep -qE "Plus\+Jakarta\+Sans|hero-home" /tmp/cancelpath-home.body; then
      echo "    attempt ${i}: homepage HTTP 200 but missing redesigned typography/hero (stale Pages build, retry in 10s)"
      sleep 10
      continue
    fi
    ok=1
    break
  fi
  echo "    attempt ${i}: homepage HTTP ${code:-000} (retry in 10s)"
  sleep 10
done

if [ "$ok" != "1" ]; then
  echo "error: public homepage did not return 200 at ${PUBLIC_HOME}" >&2
  echo "Check Actions: https://github.com/DongWook482/cancelpath/actions" >&2
  exit 1
fi

echo "==> Verifying public URLs"
fail=0
for path in "/" "/index.html" "/styles.css" "/guides/planet-fitness-cancel-membership.html" "/categories/gyms-fitness.html" "/about.html" "/contact.html" "/privacy.html" "/sitemap.xml"; do
  url="${SITE_BASE_URL}${path}"
  # strip double slash except after https:
  code=$(curl -sS -o /tmp/cancelpath-verify.body -w "%{http_code}" -A "CancelPath-deploy/1.0" "$url" || true)
  echo "    ${url} -> HTTP ${code}"
  if [ "$code" != "200" ]; then
    fail=1
  fi
done

css_code=$(curl -sS -o /tmp/cancelpath-css.body -w "%{http_code}" -A "CancelPath-deploy/1.0" "${SITE_BASE_URL}/styles.css" || true)
if [ "$css_code" != "200" ] || ! grep -q "hero-home" /tmp/cancelpath-css.body; then
  echo "error: styles.css is missing the redesigned hero-home rule (HTTP ${css_code})" >&2
  fail=1
fi
contact_code=$(curl -sS -o /tmp/cancelpath-contact.body -w "%{http_code}" -A "CancelPath-deploy/1.0" "${SITE_BASE_URL}/contact.html" || true)
if [ "$contact_code" != "200" ] || ! grep -q "github.com/DongWook482/cancelpath/issues" /tmp/cancelpath-contact.body; then
  echo "error: contact.html is missing the GitHub Issues channel (HTTP ${contact_code})" >&2
  fail=1
fi

if ! grep -q "https://dongwook482.github.io/cancelpath/" /tmp/cancelpath-verify.body && \
   ! grep -q "urlset" /tmp/cancelpath-verify.body; then
  :
fi

if [ "$fail" != "0" ]; then
  echo "error: one or more public URLs failed verification" >&2
  exit 1
fi

echo "==> Deployed: ${PUBLIC_HOME}"
echo "    Sitemap: ${PUBLIC_SITEMAP}"
