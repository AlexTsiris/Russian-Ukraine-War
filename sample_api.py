# -*- coding: utf-8 -*-
"""
Collects a REPRESENTATIVE SAMPLE of records via /api/case — for analysing shares
(service branch, rank, date of death) that are absent from the open CDN files.

Why a sample: a mass crawl of all 225k is protected by Cloudflare (a bot challenge
after a burst). A single slow thread gets through. For percentages, a 10k sample
gives an error of <1%, so there is no need to download everything.

Mode:
  * one thread, a ~--delay-second pause between requests (default 1.0);
  * when Cloudflare triggers (429/403/non-JSON) — a long backoff;
  * RESUMABLE: writes to data/sample_cases.jsonl; on restart it
    tops up what is missing from the same (fixed-seed) sample.

Run:  python sample_api.py --n 10000 --delay 1.0
"""

import argparse
import json
import os
import random
import time
import urllib.parse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SLUGS_FILE = os.path.join(HERE, "data", "urls.json")
OUT_FILE = os.path.join(HERE, "data", "sample_cases.jsonl")
SAMPLE_FILE = os.path.join(HERE, "data", "sample_slugs.json")
API = "https://200.zona.media/api/case/"
SEED = 42
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
DROP = ("mapPrev", "mapNext")


def build_sample(n):
    """A fixed random sample of n slugs (reproducible via SEED)."""
    if os.path.exists(SAMPLE_FILE):
        sample = json.load(open(SAMPLE_FILE, encoding="utf-8"))
        if len(sample) >= n:
            return sample[:n]
    slugs = json.load(open(SLUGS_FILE, encoding="utf-8"))
    rnd = random.Random(SEED)
    sample = rnd.sample(slugs, n)
    json.dump(sample, open(SAMPLE_FILE, "w", encoding="utf-8"),
              ensure_ascii=False)
    return sample


def load_done():
    done = set()
    if os.path.exists(OUT_FILE):
        for line in open(OUT_FILE, encoding="utf-8"):
            try:
                done.add(json.loads(line)["slug"])
            except Exception:
                pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000, help="sample size")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="pause between requests, sec (don't reduce it much)")
    args = ap.parse_args()

    sample = build_sample(args.n)
    done = load_done()
    todo = [s for s in sample if s not in done]
    print(f"Sample: {len(sample):,} | already have: {len(done):,} | "
          f"remaining: {len(todo):,}")
    if not todo:
        print("Sample collected. Next: python build_sample_csv.py")
        return

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": "https://200.zona.media/"})
    out = open(OUT_FILE, "a", encoding="utf-8")
    n = 0
    start = time.time()
    cooldown = 60  # initial backoff on a block

    try:
        for slug in todo:
            url = API + urllib.parse.quote(slug)
            while True:  # retry the same slug until we get past the block
                try:
                    r = s.get(url, timeout=20)
                    if r.status_code == 200 and "json" in \
                            r.headers.get("content-type", ""):
                        data = r.json()
                        if isinstance(data, dict):
                            for k in DROP:
                                data.pop(k, None)
                            data["slug"] = slug
                        else:
                            data = {"slug": slug, "_notfound": True}
                        out.write(json.dumps(data, ensure_ascii=False) + "\n")
                        cooldown = 60  # success — reset the backoff
                        break
                    # Cloudflare / block
                    print(f"  [!] block (HTTP {r.status_code}), "
                          f"pause {cooldown}s...")
                    time.sleep(cooldown)
                    cooldown = min(cooldown * 2, 900)
                except Exception as e:
                    print(f"  [!] network error: {e}, pause 30s")
                    time.sleep(30)
            n += 1
            if n % 250 == 0:
                out.flush()
                rate = n / (time.time() - start)
                eta = (len(todo) - n) / rate / 60 if rate else 0
                print(f"  {n:,}/{len(todo):,}  "
                      f"({rate:.2f} req/s, ~{eta:.0f} min left)")
            time.sleep(args.delay + random.uniform(0, 0.4))  # jitter
    except KeyboardInterrupt:
        print("\nInterrupted — progress saved; run again to continue.")
    finally:
        out.flush()
        out.close()

    print(f"\nCollected in this run: {n:,}. Next: python build_sample_csv.py")


if __name__ == "__main__":
    main()
