#!/usr/bin/env python3.9
"""
OpenRice HK Restaurant Scraper - Resumable District-Based
Avoids pagination 500 errors by fetching per-district.

Usage:
    python3.9 openrice_district_scraper.py --run           # Run full sync
    python3.9 openrice_district_scraper.py --resume        # Resume from checkpoint
    python3.9 openrice_district_scraper.py --stats         # Show DB stats
    python3.9 openrice_district_scraper.py --district 2010 # Single district
"""

import urllib.request
import urllib.parse
import json
import ssl
import sqlite3
import time
import os
import sys
import threading
from datetime import datetime

# ── Config ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, ".openrice-hk.db")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, ".openrice_checkpoint.json")
LOG_FILE = os.path.join(SCRIPT_DIR, ".openrice_sync.log")

DELAY = 2.5           # seconds between API calls
MAX_PAGES_PER_DISTRICT = 40

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.openrice.com/zh/hongkong/restaurants",
}

# ── Database ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            poi_id INTEGER PRIMARY KEY,
            name TEXT,
            name_other TEXT,
            address TEXT,
            address_other TEXT,
            score REAL,
            review_count INTEGER,
            price_range INTEGER,
            photo_count INTEGER,
            district_id INTEGER,
            district_name TEXT,
            cuisine TEXT,
            open_now INTEGER,
            map_lat REAL,
            map_lon REAL,
            phone TEXT,
            open_since TEXT,
            source TEXT DEFAULT 'openrice'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            district_id INTEGER,
            district_name TEXT,
            restaurants_added INTEGER,
            status TEXT
        )
    """)
    conn.commit()
    return conn

# ── API ──────────────────────────────────────────────────
def get_districts():
    ctx = ssl.create_default_context()
    url = "https://www.openrice.com/api/v2/metadata/region/all?uiLang=zh&uiCity=hongkong"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    data = json.loads(resp.read())
    return data.get("districts", [])


def fetch_page(district_id, start_at, rows=250):
    """Fetch a single page for a district. Returns (success, count, total, results)."""
    ctx = ssl.create_default_context()
    params = {
        "sortBy": "ORScoreDesc",
        "apiEntryPoint": "PoiSR1",
        "regionId": "0",
        "uiLang": "zh",
        "uiCity": "hongkong",
        "districtId": str(district_id),
        "rows": str(rows),
        "startAt": str(start_at),
    }
    url = f"https://www.openrice.com/api/v2/search?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        data = json.loads(resp.read())
        pagination = data.get("paginationResult", {})
        return True, len(pagination.get("results", [])), pagination.get("count", 0), pagination.get("results", [])
    except Exception as e:
        return False, 0, 0, []


def save_checkpoint(district_id, district_name, page, status):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            "district_id": district_id,
            "district_name": district_name,
            "last_page": page,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }, f)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return None


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")


# ── Scraper ──────────────────────────────────────────────
def scrape_district(conn, district_id, district_name, max_pages=40):
    """Scrape all restaurants for a district. Returns (added, total_pages, had_error)."""
    total_added = 0
    start_at = 0
    rows = 250
    total_count = None
    
    for page in range(max_pages):
        time.sleep(DELAY)
        
        if page > 0:
            time.sleep(DELAY)  # Extra delay on pagination
        
        success, returned, total, results = fetch_page(district_id, start_at)
        
        if not success or not results:
            log(f"  ✗ Page {page+1} failed (startAt={start_at}), stopping")
            break
        
        if total_count is None:
            total_count = total
            log(f"  → {district_name}: total={total_count}")
        
        # Save to DB
        cur = conn.cursor()
        for r in results:
            cuisines = [c["name"] for c in r.get("categories", []) if c.get("categoryTypeId") == 1]
            phones = r.get("phones", []) or []
            cur.execute("""
                INSERT OR REPLACE INTO restaurants 
                (poi_id, name, name_other, address, address_other, score, review_count,
                 price_range, photo_count, district_id, district_name, cuisine,
                 open_now, map_lat, map_lon, phone, open_since, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'openrice')
            """, (
                r.get("poiId"), r.get("name"), r.get("nameOther", ""),
                r.get("address"), r.get("addressOther", ""),
                r.get("scoreOverall"), r.get("reviewCount", 0),
                r.get("priceRangeId", 0), r.get("photoCount", 0),
                r.get("district", {}).get("districtId"),
                r.get("district", {}).get("name", district_name),
                ", ".join(cuisines),
                1 if r.get("openNow") else 0,
                r.get("mapLatitude"), r.get("mapLongitude"),
                "|".join(phones), r.get("openSince", ""),
            ))
            total_added += 1
        
        conn.commit()
        
        log(f"  Page {page+1}: +{len(results)} (total: {total_added}/{total_count})")
        
        # Check if done
        if len(results) < rows:
            log(f"  → Last page, district complete")
            break
        if start_at + len(results) >= total_count:
            log(f"  → Reached end of results")
            break
        
        start_at += rows
        save_checkpoint(district_id, district_name, page+1, "running")
    
    return total_added, total_count, False


def run_full_sync():
    log("=== OpenRice Full Sync Started ===")
    
    conn = init_db()
    checkpoint = load_checkpoint()
    
    # Get all districts
    log("Fetching district list...")
    districts = get_districts()
    
    # Filter valid (positive ID, not region-groups)
    valid = []
    for d in districts:
        did = d["districtId"]
        tc = d.get("nameLangDict", {}).get("tc", "")
        if did > 0 and did < 10000 and tc and not any(r in tc for r in ["香港島", "九龍", "新界", "離島"]):
            valid.append((did, tc))
    
    log(f"Found {len(valid)} valid districts")
    
    # Resume or start from beginning
    start_idx = 0
    if checkpoint and checkpoint.get("status") == "running":
        # Find this district in the list and start from next
        last_did = checkpoint.get("district_id")
        for i, (did, tc) in enumerate(valid):
            if did == last_did:
                start_idx = i + 1
                log(f"Resuming from district {start_idx}: {tc} (ID: {did})")
                break
    
    # Run
    for i in range(start_idx, len(valid)):
        did, tc = valid[i]
        log(f"\n[{i+1}/{len(valid)}] Processing: {tc} ({did})")
        
        try:
            added, total, err = scrape_district(conn, did, tc, MAX_PAGES_PER_DISTRICT)
            
            # Log to sync_log
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sync_log (district_id, district_name, restaurants_added, status)
                VALUES (?, ?, ?, ?)
            """, (did, tc, added, "success" if not err else "error"))
            conn.commit()
            
            save_checkpoint(did, tc, 0, "completed")
            log(f"  ✓ {tc}: +{added} restaurants")
            
        except Exception as e:
            log(f"  ✗ Error: {e}")
            save_checkpoint(did, tc, 0, f"error: {e}")
        
        # Progress
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM restaurants")
        total_now = cur.fetchone()[0]
        log(f"  DB total: {total_now} restaurants")
    
    # Final stats
    show_stats(conn)
    log("=== Sync Complete ===")


def show_stats(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM restaurants")
    total = cur.fetchone()[0]
    cur.execute("SELECT district_name, COUNT(*) as cnt FROM restaurants GROUP BY district_name ORDER BY cnt DESC LIMIT 20")
    print(f"\n╔══════════════════════════════════════╗")
    print(f"║     OpenRice DB: {total} restaurants     ║")
    print(f"╠══════════════════════════════════════╣")
    for row in cur.fetchall():
        print(f"║  {row[0]}: {row[1]:>5}                   ║")
    print(f"╚══════════════════════════════════════╝")
    conn.close()


# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "--run":
        run_full_sync()
    elif cmd == "--resume":
        checkpoint = load_checkpoint()
        if checkpoint:
            print(f"Will resume from: {checkpoint['district_name']} (ID: {checkpoint['district_id']})")
            print("Run with --run to start")
        else:
            print("No checkpoint found")
    elif cmd == "--stats":
        conn = init_db()
        show_stats(conn)
    elif cmd == "--district":
        did = int(sys.argv[2])
        conn = init_db()
        districts = get_districts()
        tc = next((d.get("nameLangDict", {}).get("tc", str(did)) for d in districts if d["districtId"] == did), str(did))
        added, total, err = scrape_district(conn, did, tc)
        print(f"Done. Added {added} restaurants for {tc}")
    else:
        print("Unknown command:", cmd)
        print(__doc__)