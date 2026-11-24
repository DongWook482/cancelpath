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

echo "==> Pushing main"
git push origin main

# Wait for the just-pushed workflow rather than accepting a stale 200 from the previous Pages build.
if command -v gh >/dev/null 2>&1; then
  RUN_ID="$(gh run list --repo DongWook482/cancelpath --branch main --workflow "Deploy GitHub Pages" --limit 1 --json databaseId --jq '.[0].databaseId' || true)"
  if [ -n "${RUN_ID}" ]; then
    echo "==> Waiting for Actions run ${RUN_ID}"
    gh run watch "${RUN_ID}" --repo DongWook482/cancelpath --exit-status
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
for path in "/" "/index.html" "/styles.css" "/guides/planet-fitness-cancel-membership.html" "/categories/gyms-fitness.html" "/about.html" "/privacy.html" "/sitemap.xml"; do
  url="${SITE_BASE_URL}${path}"
  # strip double slash except after https:
  code=$(curl -sS -o /tmp/cancelpath-verify.body -w "%{http_code}" -A "CancelPath-deploy/1.0" "$url" || true)
  echo "    ${url} -> HTTP ${code}"
  if [ "$code" != "200" ]; then
    fail=1
  fi
done

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
