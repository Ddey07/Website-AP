"""
Chunked hotel price fetcher — fetches N SerpAPI hotel queries per run.
State is saved to /tmp/wc_hotel_state.json.

Usage:
    python scripts/fetch_hotels_chunked.py [--batch N]   # fetch next N queries (default 20)
    python scripts/fetch_hotels_chunked.py --status      # show progress
    python scripts/fetch_hotels_chunked.py --apply       # merge hotel data into prices.json
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
HOTEL_STATE = Path("/tmp/wc_hotel_state.json")

_ROOT = Path(__file__).parent.parent
OUTPUT_PATH    = _ROOT / "static" / "wc2026" / "prices.json"
OUTPUT_PATH_JS = _ROOT / "static" / "wc2026" / "prices.js"
OUTPUT_PATH_PUBLIC    = _ROOT / "public" / "wc2026" / "prices.json"
OUTPUT_PATH_PUBLIC_JS = _ROOT / "public" / "wc2026" / "prices.js"

VENUE_ROUND_DATES = {
    "East Rutherford (MetLife)": {
        "group": ("East Rutherford NJ", "2026-06-14"),
        "r32":   ("East Rutherford NJ", "2026-06-29"),
        "r16":   ("East Rutherford NJ", "2026-07-05"),
        "final": ("East Rutherford NJ", "2026-07-19"),
    },
    "Philadelphia (Lincoln Financial)": {
        "group": ("Philadelphia",       "2026-06-16"),
        "r32":   ("Philadelphia",       "2026-07-01"),
        "r16":   ("Philadelphia",       "2026-07-07"),
    },
    "Dallas (AT&T)": {
        "group": ("Arlington TX",       "2026-06-15"),
        "r32":   ("Arlington TX",       "2026-06-30"),
        "r16":   ("Arlington TX",       "2026-07-06"),
        "qf":    ("Arlington TX",       "2026-07-11"),
    },
    "Inglewood (SoFi)": {
        "group": ("Inglewood CA",       "2026-06-17"),
        "r32":   ("Inglewood CA",       "2026-07-02"),
        "r16":   ("Inglewood CA",       "2026-07-08"),
        "sf":    ("Inglewood CA",       "2026-07-14"),
        "final": ("Inglewood CA",       "2026-07-19"),
    },
    "Santa Clara (Levi's)": {
        "group": ("Santa Clara CA",     "2026-06-18"),
        "r32":   ("Santa Clara CA",     "2026-06-28"),
        "r16":   ("Santa Clara CA",     "2026-07-09"),
    },
    "Miami (Hard Rock)": {
        "group": ("Miami Gardens FL",   "2026-06-20"),
        "r32":   ("Miami Gardens FL",   "2026-07-04"),
        "qf":    ("Miami Gardens FL",   "2026-07-12"),
    },
    "Atlanta (Mercedes-Benz)": {
        "group": ("Atlanta",            "2026-06-19"),
        "r32":   ("Atlanta",            "2026-07-03"),
        "r16":   ("Atlanta",            "2026-07-10"),
    },
    "Houston (NRG)": {
        "group": ("Houston",            "2026-06-13"),
        "r32":   ("Houston",            "2026-07-01"),
        "r16":   ("Houston",            "2026-07-06"),
    },
    "Kansas City (Arrowhead)": {
        "group": ("Kansas City",        "2026-06-16"),
        "r32":   ("Kansas City",        "2026-06-30"),
    },
    "Seattle (Lumen Field)": {
        "group": ("Seattle",            "2026-06-15"),
        "r32":   ("Seattle",            "2026-07-02"),
    },
    "Foxborough (Gillette)": {
        "group": ("Foxborough MA",      "2026-06-12"),
        "r32":   ("Foxborough MA",      "2026-07-04"),
        "r16":   ("Foxborough MA",      "2026-07-09"),
    },
    "Toronto (BMO Field)": {
        "group": ("Toronto",            "2026-06-16"),
        "r32":   ("Toronto",            "2026-07-03"),
        "r16":   ("Toronto",            "2026-07-07"),
    },
    "Vancouver (BC Place)": {
        "group": ("Vancouver",          "2026-06-14"),
        "r32":   ("Vancouver",          "2026-07-01"),
    },
    "Mexico City (Azteca)": {
        "group": ("Mexico City",        "2026-06-12"),
        "r32":   ("Mexico City",        "2026-06-29"),
        "r16":   ("Mexico City",        "2026-07-05"),
    },
    "Guadalajara (Akron)": {
        "group": ("Guadalajara",        "2026-06-18"),
        "r32":   ("Guadalajara",        "2026-06-29"),
    },
    "Monterrey (BBVA)": {
        "group": ("Monterrey",          "2026-06-14"),
    },
}

FALLBACK_HOTELS = {
    "East Rutherford (MetLife)": {
        "group": {"low": 220, "high": 580}, "r32": {"low": 280, "high": 720},
        "r16": {"low": 320, "high": 820}, "final": {"low": 500, "high": 1400},
    },
    "Philadelphia (Lincoln Financial)": {
        "group": {"low": 180, "high": 450}, "r32": {"low": 230, "high": 580},
        "r16": {"low": 270, "high": 680},
    },
    "Dallas (AT&T)": {
        "group": {"low": 160, "high": 400}, "r32": {"low": 200, "high": 520},
        "r16": {"low": 240, "high": 620}, "qf": {"low": 350, "high": 900},
    },
    "Inglewood (SoFi)": {
        "group": {"low": 220, "high": 580}, "r32": {"low": 280, "high": 720},
        "r16": {"low": 320, "high": 820}, "sf": {"low": 450, "high": 1200},
        "final": {"low": 600, "high": 1600},
    },
    "Santa Clara (Levi's)": {
        "group": {"low": 200, "high": 520}, "r32": {"low": 260, "high": 680},
        "r16": {"low": 300, "high": 780},
    },
    "Miami (Hard Rock)": {
        "group": {"low": 200, "high": 520}, "r32": {"low": 260, "high": 680},
        "qf": {"low": 360, "high": 950},
    },
    "Atlanta (Mercedes-Benz)": {
        "group": {"low": 160, "high": 420}, "r32": {"low": 210, "high": 550},
        "r16": {"low": 250, "high": 650},
    },
    "Houston (NRG)": {
        "group": {"low": 150, "high": 390}, "r32": {"low": 200, "high": 520},
        "r16": {"low": 240, "high": 620},
    },
    "Kansas City (Arrowhead)": {
        "group": {"low": 140, "high": 360}, "r32": {"low": 180, "high": 480},
    },
    "Seattle (Lumen Field)": {
        "group": {"low": 170, "high": 440}, "r32": {"low": 220, "high": 580},
    },
    "Foxborough (Gillette)": {
        "group": {"low": 160, "high": 420}, "r32": {"low": 210, "high": 550},
        "r16": {"low": 250, "high": 650},
    },
    "Toronto (BMO Field)": {
        "group": {"low": 180, "high": 460}, "r32": {"low": 230, "high": 600},
        "r16": {"low": 270, "high": 700},
    },
    "Vancouver (BC Place)": {
        "group": {"low": 170, "high": 440}, "r32": {"low": 220, "high": 580},
    },
    "Mexico City (Azteca)": {
        "group": {"low": 120, "high": 320}, "r32": {"low": 160, "high": 430},
        "r16": {"low": 200, "high": 530},
    },
    "Guadalajara (Akron)": {
        "group": {"low": 100, "high": 270}, "r32": {"low": 130, "high": 360},
    },
    "Monterrey (BBVA)": {
        "group": {"low": 100, "high": 270},
    },
}


def all_queries():
    result = []
    for venue, rounds in VENUE_ROUND_DATES.items():
        for rnd, (city, check_in) in rounds.items():
            result.append((venue, rnd, city, check_in))
    return result


def load_state():
    if HOTEL_STATE.exists():
        try:
            return json.loads(HOTEL_STATE.read_text())
        except Exception:
            pass
    return {"done": [], "hotels": {}}


def save_state(state):
    HOTEL_STATE.write_text(json.dumps(state, indent=2))


def fetch_one_hotel(city: str, check_in: str) -> dict | None:
    check_out = (datetime.fromisoformat(check_in) + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "engine": "google_hotels",
        "q": f"hotels in {city} World Cup 2026",
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": "2",
        "currency": "USD",
        "gl": "us",
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.loads(r.read())
    props = data.get("properties") or []
    prices = []
    for p in props:
        rate = p.get("rate_per_night", {})
        val = rate.get("extracted_lowest") or rate.get("extracted_before_taxes_fees")
        if val:
            prices.append(float(val))
    if not prices:
        return None
    prices.sort()
    n = len(prices)
    return {
        "low":    int(prices[max(0, int(n * 0.10))]),
        "high":   int(prices[min(n - 1, int(n * 0.90))]),
        "min":    int(prices[0]),
        "max":    int(prices[-1]),
        "sample": n,
    }


def cmd_status():
    state = load_state()
    qs = all_queries()
    done_keys = {(d[0], d[1]) for d in state["done"]}
    done = sum(1 for q in qs if (q[0], q[1]) in done_keys)
    print(f"Hotel queries: {done}/{len(qs)} done, {len(qs)-done} pending")


def cmd_batch(n: int):
    state = load_state()
    qs = all_queries()
    done_keys = {(d[0], d[1]) for d in state["done"]}
    pending = [q for q in qs if (q[0], q[1]) not in done_keys]

    if not pending:
        print("All hotel queries done! Run --apply to write to prices.json.")
        return

    batch = pending[:n]
    total = len(qs)
    done_count = len(qs) - len(pending)

    for venue, rnd, city, check_in in batch:
        done_count += 1
        label = f"[{done_count}/{total}] {venue[:28]:28s} {rnd:6s}"
        try:
            result = fetch_one_hotel(city, check_in)
            if result:
                state.setdefault("hotels", {}).setdefault(venue, {})[rnd] = result
                print(f"   {label}: ${result['low']}–${result['high']}/night ({result['sample']} props)")
            else:
                fb = FALLBACK_HOTELS.get(venue, {}).get(rnd, {"low": 150, "high": 400})
                state.setdefault("hotels", {}).setdefault(venue, {})[rnd] = fb
                print(f"   {label}: no results — fallback ${fb['low']}–${fb['high']}")
        except Exception as exc:
            fb = FALLBACK_HOTELS.get(venue, {}).get(rnd, {"low": 150, "high": 400})
            state.setdefault("hotels", {}).setdefault(venue, {})[rnd] = fb
            print(f"   {label}: ERROR {exc} — fallback")
        state.setdefault("done", []).append([venue, rnd])

    save_state(state)
    remaining = len(pending) - len(batch)
    print(f"\nBatch complete. {remaining} queries remaining.")
    if remaining == 0:
        print("All done! Run --apply to write to prices.json.")


def cmd_apply():
    state = load_state()
    hotels = state.get("hotels", {})
    if not hotels:
        print("No hotel data in state. Run batches first.")
        return

    # Load existing prices.json
    existing = {}
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text())
        except Exception:
            pass

    existing["hotels"] = hotels
    existing["hotels_fetched_at"] = datetime.now(timezone.utc).isoformat()
    existing["hotel_source"] = "SerpAPI Google Hotels"
    existing["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    payload = json.dumps(existing, indent=2)
    payload_js = f"window.WC_PRICES={json.dumps(existing)};"

    OUTPUT_PATH.write_text(payload)
    OUTPUT_PATH_JS.write_text(payload_js)
    print(f"✅ Wrote {OUTPUT_PATH}")
    print(f"   Wrote {OUTPUT_PATH_JS}")
    for src_txt, dst in [(payload, OUTPUT_PATH_PUBLIC), (payload_js, OUTPUT_PATH_PUBLIC_JS)]:
        if dst.parent.exists():
            dst.write_text(src_txt)
            print(f"   Mirrored → {dst}")
    print(f"   Hotels: {len(hotels)} venues")
    print(f"   Updated: {existing['last_updated']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--status" in args:
        cmd_status()
    elif "--apply" in args:
        cmd_apply()
    else:
        n = 20
        for i, a in enumerate(args):
            if a == "--batch" and i + 1 < len(args):
                n = int(args[i + 1])
        cmd_batch(n)
