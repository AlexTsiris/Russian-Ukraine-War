# -*- coding: utf-8 -*-
"""
Full download of casualty records via the "Russia 200" project API.
Endpoint: https://200.zona.media/api/case/<slug>

Features:
  * RESUMABLE — you can interrupt it (Ctrl+C) and run again; what is already downloaded
    is skipped. The result is written line by line to data/cases.jsonl.
  * Multiple threads + retries with exponential backoff.
  * Polite to the server: a limited number of threads, a pause on 429/5xx.

Run:              python fetch_full.py
You can limit it: python fetch_full.py --limit 1000   (for a test)
More threads:     python fetch_full.py --workers 8

When it finishes, build the table:  python build_full_csv.py
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SLUGS_FILE = os.path.join(HERE, "data", "urls.json")
OUT_FILE = os.path.join(HERE, "data", "cases.jsonl")
API = "https://200.zona.media/api/case/"

TIMEOUT = 20
MAX_RETRIES = 4
# map-navigation fields — not needed, drop them
DROP_FIELDS = ("mapPrev", "mapNext")

_local = threading.local()
_write_lock = threading.Lock()


def session():
    """One requests.Session per thread — reuses connections."""
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 (research; casualties analytics)"})
        _local.s = s
    return _local.s


def load_done():
    """Slugs already written to cases.jsonl — so we don't download them again."""
    done = set()
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["slug"])
                except Exception:
                    pass
    return done


def fetch(slug):
    """Fetches one record. Returns a dict (always with a slug key)."""
    url = API + urllib.parse.quote(slug)
    for attempt in range(MAX_RETRIES):
        try:
            r = session().get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    for k in DROP_FIELDS:
                        data.pop(k, None)
                    data["slug"] = slug
                    return data
                # the API returned [] — no record
                return {"slug": slug, "_notfound": True}
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)       # back off and try again
                continue
            return {"slug": slug, "_error": r.status_code}
        except Exception:
            time.sleep(2 ** attempt)
    return {"slug": slug, "_error": "failed"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6,
                    help="number of threads (default 6; don't push it too high — be polite)")
    ap.add_argument("--limit", type=int, default=0,
                    help="limit the number of requests (0 = all; for testing)")
    args = ap.parse_args()

    slugs = json.load(open(SLUGS_FILE, encoding="utf-8"))
    done = load_done()
    todo = [s for s in slugs if s not in done]
    if args.limit:
        todo = todo[:args.limit]

    print(f"Total in list  : {len(slugs):,}")
    print(f"Already fetched: {len(done):,}")
    print(f"Remaining      : {len(todo):,}")
    if not todo:
        print("Nothing to fetch — all done. Run build_full_csv.py")
        return

    out = open(OUT_FILE, "a", encoding="utf-8")
    n = 0
    start = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(fetch, s): s for s in todo}
            for fut in as_completed(futures):
                rec = fut.result()
                with _write_lock:
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
                if n % 500 == 0:
                    out.flush()
                    rate = n / (time.time() - start)
                    eta = (len(todo) - n) / rate / 60 if rate else 0
                    print(f"  {n:,}/{len(todo):,}  "
                          f"({rate:.0f} req/s, ~{eta:.0f} min left)")
    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved — run again and it will resume.")
    finally:
        out.flush()
        out.close()

    print(f"\nDone in this run: {n:,}. File: {OUT_FILE}")
    print("Next: python build_full_csv.py")


if __name__ == "__main__":
    main()
