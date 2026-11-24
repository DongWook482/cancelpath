#!/usr/bin/env python3
"""Honest daily revenue & publishing report for CancelPath.
Reports strictly verified numbers only (defaults to $0.00 when no payout/ad/affiliate connector is active).
Visitor counts are printed only from a fresh analytics_snapshot.json written by the parent; never invented.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "publish_log.csv"
LEDGER_PATH = ROOT / "revenue_ledger.json"
ENTRIES_DIR = ROOT / "entries"
PUBLIC_DIR = ROOT / "public"
SNAPSHOT_PATH = ROOT / "analytics_snapshot.json"
SNAPSHOT_MAX_AGE = timedelta(hours=48)
KST = timezone(timedelta(hours=9))


def _parse_fetched_at(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt


def _format_date_range(value: Any) -> str:
    if isinstance(value, dict):
        start = value.get("start") or value.get("begin") or ""
        end = value.get("end") or ""
        if start and end:
            return f"{start} to {end}"
        return str(start or end or "unspecified")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unspecified"


def format_visitor_section() -> str:
    if not SNAPSHOT_PATH.exists():
        return "Visitors: not yet fetched"

    try:
        data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "Visitors: not yet fetched"

    if not isinstance(data, dict):
        return "Visitors: not yet fetched"

    fetched = _parse_fetched_at(str(data.get("fetched_at") or ""))
    if fetched is None:
        return "Visitors: not yet fetched"

    now = datetime.now(timezone.utc)
    age = now - fetched.astimezone(timezone.utc)
    if age > SNAPSHOT_MAX_AGE:
        fetched_kst = fetched.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
        return f"Visitors: snapshot stale (fetched_at={fetched_kst}, older than 48h); not used"

    required = ("active_users", "sessions", "page_views")
    missing = [k for k in required if k not in data]
    if missing:
        return f"Visitors: snapshot incomplete (missing {', '.join(missing)}); not used"

    try:
        active_users = int(data["active_users"])
        sessions = int(data["sessions"])
        page_views = int(data["page_views"])
    except (TypeError, ValueError):
        return "Visitors: snapshot incomplete (non-numeric metrics); not used"

    range_label = _format_date_range(data.get("date_range"))
    fetched_kst = fetched.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [
        f"Visitors ({range_label}, fetched {fetched_kst}):",
        f"  Active users: {active_users}",
        f"  Sessions: {sessions}",
        f"  Page views: {page_views}",
    ]

    top_pages = data.get("top_pages")
    if isinstance(top_pages, list) and top_pages:
        lines.append("  Top pages:")
        for item in top_pages:
            if not isinstance(item, dict):
                continue
            path = item.get("path") or item.get("page") or item.get("page_path")
            views = item.get("page_views", item.get("views"))
            if path is None or views is None:
                continue
            try:
                views_n = int(views)
            except (TypeError, ValueError):
                continue
            lines.append(f"    - {path} ({views_n} views)")
        if len(lines) == 5:
            # header added but no valid rows
            lines[-1] = "  Top pages: none listed"
    else:
        lines.append("  Top pages: none listed")

    return "\n".join(lines)


def main() -> None:
    rows = []
    if LOG_PATH.exists():
        with LOG_PATH.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.exists() else {}
    txs = ledger.get("transactions", [])
    channels = ledger.get("connected_monetization_channels", [])
    total_usd = sum(float(t.get("amount_usd", 0.0)) for t in txs)

    entries_count = len([p for p in ENTRIES_DIR.iterdir() if p.suffix in {".md", ".json"}]) if ENTRIES_DIR.exists() else 0
    latest = rows[-1] if rows else None

    print("=== CancelPath Money & Publish Report ===")
    print(f"Generated (box local KST): {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}")
    print(f"Hosting status: {ledger.get('hosting_status', 'local_only')}")
    print(f"Published guides: {entries_count} (log rows: {len(rows)})")
    if latest:
        print(f"Latest page: {latest['date_kst']} | {latest['slug']} ({latest['service_name']}) [{latest['status']}]")
    print(f"Connected monetization channels: {len(channels)} ({', '.join(channels) if channels else 'none'})")
    print(f"Verified gross revenue: ${total_usd:.2f} {ledger.get('currency', 'USD')}")
    print(format_visitor_section())
    print("Note: Revenue remains $0.00 until an ad/affiliate channel (e.g., AdSense, Impact/CJ/PartnerStack, or Privacy.com/Rocket Money affiliate) is connected and verified. Visitor counts are printed only from a fresh analytics_snapshot.json; they are never estimated.")


if __name__ == "__main__":
    main()
