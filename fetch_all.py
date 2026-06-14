# -*- coding: utf-8 -*-
"""
FULL collection of all /api/case records (~225k) — gentle and resumable.

Cloudflare protection:
  * global backoff: on a block (429/403/non-JSON) ALL threads freeze
    for a cooldown (60s -> doubling -> up to 900s); after a success the cooldown resets;
  * by default 1 thread + a --delay pause (safe, verified on a sample).
Resumability: writes/reads data/all_cases.jsonl; on restart it
skips what is already collected. You can interrupt (Ctrl+C) and run again.

Run:           python fetch_all.py
A bit faster:  python fetch_all.py --workers 2 --delay 0.3
Then:          python build_full_csv.py
"""

import argparse
import json
import os
import queue
import random
import threading
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SLUGS_FILE = os.path.join(HERE, "data", "urls.json")
OUT_FILE = os.path.join(HERE, "data", "all_cases.jsonl")
API = "https://200.zona.media/api/case/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DROP = ("mapPrev", "mapNext")

_block_until = 0.0
_cooldown = 60
_block_lock = threading.Lock()
_write_lock = threading.Lock()
_count_lock = threading.Lock()
_n = 0


def load_done():
    done = set()
    if os.path.exists(OUT_FILE):
        for line in open(OUT_FILE, encoding="utf-8"):
            try:
                done.add(json.loads(line)["slug"])
            except Exception:
                pass
    return done


def signal_block():
    """Turn on a global pause for all threads; return the pause length."""
    global _block_until, _cooldown
    with _block_lock:
        cur = _cooldown
        _block_until = time.time() + cur
        _cooldown = min(_cooldown * 2, 900)
    return cur


def signal_ok():
    global _cooldown
    with _block_lock:
        _cooldown = 60


def wait_if_blocked(stop):
    while not stop.is_set():
        with _block_lock:
            wait = _block_until - time.time()
        if wait <= 0:
            return
        time.sleep(min(wait, 5))


def worker(q, out, delay, total, stop):
    global _n
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "https://200.zona.media/"})
    start = time.time()
    while not stop.is_set():
        try:
            slug = q.get_nowait()
        except queue.Empty:
            return
        wait_if_blocked(stop)
        while not stop.is_set():
            try:
                r = s.get(API + urllib.parse.quote(slug), timeout=20)
                ct = r.headers.get("content-type", "")
                if r.status_code == 200 and "json" in ct:
                    data = r.json()
                    if isinstance(data, dict):
                        for k in DROP:
                            data.pop(k, None)
                        data["slug"] = slug
                    else:
                        data = {"slug": slug, "_notfound": True}
                    with _write_lock:
                        out.write(json.dumps(data, ensure_ascii=False) + "\n")
                    signal_ok()
                    break
                cur = signal_block()
                print(f"  [!] block HTTP {r.status_code} — all threads "
                      f"wait {cur}s")
                time.sleep(cur)
            except Exception as e:
                print(f"  [!] network: {e}, pause 20s")
                time.sleep(20)
        with _count_lock:
            _n += 1
            n = _n
        if n % 500 == 0:
            out.flush()
            rate = n / (time.time() - start) if (time.time() - start) else 0
            eta = (total - n) / rate / 3600 if rate else 0
            print(f"  {n:,}/{total:,}  ({rate:.1f} req/s, "
                  f"~{eta:.1f} h left)")
        time.sleep(delay + random.uniform(0, 0.3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    slugs = json.load(open(SLUGS_FILE, encoding="utf-8"))
    done = load_done()
    todo = [s for s in slugs if s not in done]
    print(f"Total: {len(slugs):,} | already have: {len(done):,} | "
          f"remaining: {len(todo):,}")
    if not todo:
        print("Everything collected. Next: python build_full_csv.py")
        return

    q = queue.Queue()
    for s in todo:
        q.put(s)
    out = open(OUT_FILE, "a", encoding="utf-8")
    stop = threading.Event()
    threads = [threading.Thread(target=worker,
                                args=(q, out, args.delay, len(todo), stop),
                                daemon=True)
               for _ in range(args.workers)]
    try:
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads):
            for t in threads:
                t.join(timeout=1)
    except KeyboardInterrupt:
        stop.set()
        print("\nInterrupted — progress saved; run again to continue.")
    finally:
        out.flush()
        out.close()
    print(f"\nCollected in this run: {_n:,}. Next: python build_full_csv.py")


if __name__ == "__main__":
    main()
