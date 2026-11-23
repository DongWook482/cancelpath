#!/usr/bin/env python3
"""Honest daily revenue & publishing report for CancelPath.
Reports strictly verified numbers only (defaults to $0.00 when no payout/ad/affiliate connector is active).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "publish_log.csv"
LEDGER_PATH = ROOT / "revenue_ledger.json"
ENTRIES_DIR = ROOT / "entries"
PUBLIC_DIR = ROOT / "public"


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
    print(f"Generated (box local KST): {datetime.now().strftime('%Y-%m-%d %H:%M KST')}")
    print(f"Hosting status: {ledger.get('hosting_status', 'local_only')}")
    print(f"Published guides: {entries_count} (log rows: {len(rows)})")
    if latest:
        print(f"Latest page: {latest['date_kst']} | {latest['slug']} ({latest['service_name']}) [{latest['status']}]")
    print(f"Connected monetization channels: {len(channels)} ({', '.join(channels) if channels else 'none'})")
    print(f"Verified gross revenue: ${total_usd:.2f} {ledger.get('currency', 'USD')}")
    print("Note: Revenue remains $0.00 until the site is publicly hosted and an ad/affiliate channel (e.g., AdSense, Impact/CJ/PartnerStack, or Privacy.com/Rocket Money affiliate) is connected and verified.")


if __name__ == "__main__":
    main()
