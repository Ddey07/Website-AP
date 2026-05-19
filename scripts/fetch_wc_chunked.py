"""
Chunked WC price fetcher — processes one Apify venue per run, accumulating
results in /tmp/wc_chunk_state.json. Run repeatedly until all venues are done,
then run with --finalize to write prices.json.

Usage:
    python scripts/fetch_wc_chunked.py          # process next pending venue
    python scripts/fetch_wc_chunked.py --status  # show progress
    python scripts/fetch_wc_chunked.py --hotels  # fetch hotel prices & finalize
    python scripts/fetch_wc_chunked.py --finalize # write final prices.json (no hotel re-fetch)
"""

import json
import os
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")

STATE_FILE = Path("/tmp/wc_chunk_state.json")

_ROOT = Path(__file__).parent.parent
OUTPUT_PATH    = _ROOT / "static" / "wc2026" / "prices.json"
OUTPUT_PATH_JS = _ROOT / "static" / "wc2026" / "prices.js"
OUTPUT_PATH_PUBLIC    = _ROOT / "public" / "wc2026" / "prices.json"
OUTPUT_PATH_PUBLIC_JS = _ROOT / "public" / "wc2026" / "prices.js"

VIVID_FEE_FACTOR = 1.34

VIVID_VENUE_IDS = {
    4906:  "Toronto (BMO Field)",
    21877: "Inglewood (SoFi)",
    2429:  "Foxborough (Gillette)",
    2739:  "Vancouver (BC Place)",
    8136:  "East Rutherford (MetLife)",
    11464: "Santa Clara (Levi's)",
    2766:  "Philadelphia (Lincoln Financial)",
    2411:  "Houston (NRG)",
    6409:  "Dallas (AT&T)",
    1366:  "Miami (Hard Rock)",
    14188: "Atlanta (Mercedes-Benz)",
    2440:  "Seattle (Lumen Field)",
    92:    "Kansas City (Arrowhead)",
}

WC_START_DATE = "2026-06-11"
WC_END_DATE   = "2026-07-19"

ROUND_DATE_RANGES = {
    "group": ("2026-06-11", "2026-06-27"),
    "r32":   ("2026-06-28", "2026-07-04"),
    "r16":   ("2026-07-05", "2026-07-10"),
    "qf":    ("2026-07-11", "2026-07-12"),
    "sf":    ("2026-07-14", "2026-07-15"),
    "final": ("2026-07-19", "2026-07-19"),
}

FALLBACK_TIERS = {
    "group": {"low": 127, "high": 563},
    "r32":   {"low": 201, "high": 831},
    "r16":   {"low": 295, "high": 1206},
    "qf":    {"low": 509, "high": 2412},
    "sf":    {"low": 804, "high": 4690},
    "final": {"low": 1608, "high": 16080},
}

VENUE_NAME_MAP = {
    "BMO Field": "Toronto (BMO Field)",
    "SoFi Stadium": "Inglewood (SoFi)",
    "Gillette Stadium": "Foxborough (Gillette)",
    "MetLife Stadium": "East Rutherford (MetLife)",
    "Lincoln Financial Field": "Philadelphia (Lincoln Financial)",
    "Mercedes-Benz Stadium": "Atlanta (Mercedes-Benz)",
    "Hard Rock Stadium": "Miami (Hard Rock)",
    "AT&T Stadium": "Dallas (AT&T)",
    "NRG Stadium": "Houston (NRG)",
    "GEHA Field at Arrowhead Stadium": "Kansas City (Arrowhead)",
    "Arrowhead Stadium": "Kansas City (Arrowhead)",
    "Lumen Field": "Seattle (Lumen Field)",
    "Levi's Stadium": "Santa Clara (Levi's)",
    "Levis Stadium": "Santa Clara (Levi's)",
    "BC Place Stadium": "Vancouver (BC Place)",
    "BC Place": "Vancouver (BC Place)",
    "Estadio Azteca": "Mexico City (Azteca)",
    "Estadio AKRON": "Guadalajara (Akron)",
    "Estadio Akron": "Guadalajara (Akron)",
    "Estadio BBVA": "Monterrey (BBVA)",
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


def _ensure_apify_client():
    try:
        from apify_client import ApifyClient
        return ApifyClient
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "apify-client", "-q"], check=True)
        from apify_client import ApifyClient
        return ApifyClient


def _is_wc_event(name: str, local_date: str) -> bool:
    if not (WC_START_DATE <= local_date[:10] <= WC_END_DATE):
        return False
    kw = name.lower()
    return "world cup" in kw or "fifa" in kw or "wc2026" in kw


def _extract_match_number(name: str):
    m = re.search(r"[Mm]atch\s+(\d+)", name)
    return int(m.group(1)) if m else None


def classify_round_by_date(date_str: str) -> str | None:
    for rnd, (start, end) in ROUND_DATE_RANGES.items():
        if start <= date_str <= end:
            return rnd
    return None


def classify_round_by_name(name: str) -> str | None:
    name_l = name.lower()
    if "final" in name_l and "semi" not in name_l and "quarter" not in name_l:
        return "final"
    if "semi" in name_l:
        return "sf"
    if "quarter" in name_l:
        return "qf"
    if "round of 16" in name_l or "round of sixteen" in name_l:
        return "r16"
    if "round of 32" in name_l or "round of thirty" in name_l:
        return "r32"
    if "group" in name_l:
        return "group"
    return None


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"done_venues": [], "wc_events": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_one_hotel(city: str, check_in: str) -> dict | None:
    import urllib.request, urllib.parse
    check_out = (datetime.fromisoformat(check_in) + __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")
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
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read())
    except Exception as exc:
        raise RuntimeError(f"SerpAPI request failed: {exc}") from exc

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
    low_idx  = max(0, int(n * 0.10))
    high_idx = min(n - 1, int(n * 0.90))
    return {
        "low":    int(prices[low_idx]),
        "high":   int(prices[high_idx]),
        "min":    int(prices[0]),
        "max":    int(prices[-1]),
        "sample": n,
    }


def process_wc_events(all_events: list) -> tuple[dict, dict]:
    """Convert raw WC events list into tiers + match_prices."""
    round_buckets: dict[str, list] = {k: [] for k in ROUND_DATE_RANGES}
    match_prices: dict[str, dict] = {}

    for prod in all_events:
        date_str = (prod.get("localDate") or "")[:10]
        rnd = classify_round_by_date(date_str)
        if not rnd:
            rnd = classify_round_by_name(prod.get("name", ""))
        if not rnd:
            continue

        min_p = prod.get("minPrice")
        max_p = prod.get("maxPrice")
        if min_p is None:
            continue

        min_p = float(min_p) * VIVID_FEE_FACTOR
        raw_max = float(max_p) if max_p else float(min_p) / VIVID_FEE_FACTOR * 5
        max_p = raw_max * VIVID_FEE_FACTOR

        venue_key = prod.get("_venue_key")
        if not venue_key:
            raw_venue = ""
            if isinstance(prod.get("venue"), dict):
                raw_venue = prod["venue"].get("name", "")
            elif isinstance(prod.get("venue"), str):
                raw_venue = prod["venue"]
            venue_key = VENUE_NAME_MAP.get(raw_venue)

        round_buckets[rnd].append({"low": min_p, "high": max_p})

        if venue_key and date_str:
            match_key = f"{date_str}|{venue_key}"
            match_entry: dict = {
                "low":    int(min_p),
                "high":   int(max_p),
                "name":   prod.get("name", ""),
                "sample": int(prod.get("listingCount") or 0),
            }
            match_num = prod.get("_match_number")
            if match_num:
                match_entry["matchNum"] = match_num
            match_prices[match_key] = match_entry

    def _aggregate(rows, fallback):
        if not rows:
            return fallback
        lows  = sorted(r["low"]  for r in rows)
        highs = sorted(r["high"] for r in rows)
        return {"low": int(lows[0]), "high": int(highs[-1]), "sample": len(rows)}

    tiers = {}
    print("\n── Global tiers ─────────────────────────────────────")
    for rnd in ROUND_DATE_RANGES:
        rows = round_buckets[rnd]
        tiers[rnd] = _aggregate(rows, FALLBACK_TIERS[rnd])
        t = tiers[rnd]
        src = f"{t['sample']} matches" if rows else "fallback"
        print(f"   {rnd:6s}: ${t['low']}–${t['high']}  ({src})")

    return tiers, match_prices


def fetch_hotels() -> tuple[dict, str]:
    total = sum(len(rounds) for rounds in VENUE_ROUND_DATES.values())
    print(f"\n🏨 Fetching hotel prices from SerpAPI — {total} queries…")
    hotels: dict[str, dict] = {}
    errors = 0
    done = 0
    for venue, rounds in VENUE_ROUND_DATES.items():
        hotels[venue] = {}
        for rnd, (city, check_in) in rounds.items():
            done += 1
            label = f"[{done}/{total}] {venue[:28]:28s} {rnd:6s}"
            try:
                result = fetch_one_hotel(city, check_in)
                if result:
                    hotels[venue][rnd] = result
                    print(f"   {label}: ${result['low']}–${result['high']}/night ({result['sample']} props)")
                else:
                    hotels[venue][rnd] = FALLBACK_HOTELS.get(venue, {}).get(rnd, {"low": 150, "high": 400})
                    print(f"   {label}: no results — using placeholder")
            except Exception as exc:
                hotels[venue][rnd] = FALLBACK_HOTELS.get(venue, {}).get(rnd, {"low": 150, "high": 400})
                print(f"   {label}: ERROR {exc} — using placeholder")
                errors += 1
    source = (
        "SerpAPI Google Hotels" if errors == 0
        else f"SerpAPI Google Hotels (partial — {errors} fallbacks)"
        if errors < total
        else "Placeholder (SerpAPI unavailable)"
    )
    return hotels, source


def write_output(tiers, match_prices, hotels, hotel_source, ticket_source):
    now = datetime.now(timezone.utc)
    output = {
        "last_updated":      now.strftime("%Y-%m-%d"),
        "hotels_fetched_at": now.isoformat(),
        "ticket_source":     ticket_source,
        "hotel_source":      hotel_source,
        "tiers":             tiers,
        "hotels":            hotels,
    }
    if match_prices:
        output["matches"] = match_prices
        match_by_id = {}
        for mv in match_prices.values():
            num = mv.get("matchNum")
            if num:
                match_by_id[num] = mv
        if match_by_id:
            output["matchById"] = match_by_id

    payload    = json.dumps(output, indent=2)
    payload_js = f"window.WC_PRICES={json.dumps(output)};"

    OUTPUT_PATH.write_text(payload)
    OUTPUT_PATH_JS.write_text(payload_js)
    print(f"\n✅ Wrote {OUTPUT_PATH}")
    print(f"   Wrote {OUTPUT_PATH_JS}")

    for src_txt, dst in [(payload, OUTPUT_PATH_PUBLIC), (payload_js, OUTPUT_PATH_PUBLIC_JS)]:
        if dst.parent.exists():
            dst.write_text(src_txt)
            print(f"   Mirrored  → {dst}")

    print(f"   Tickets: {ticket_source}")
    if match_prices:
        print(f"   Per-match ticket data: {len(match_prices)} matches")
    print(f"   Hotels:  {hotel_source}")
    print(f"   Updated: {output['last_updated']}")
    return output


def cmd_status():
    state = load_state()
    done = set(str(v) for v in state.get("done_venues", []))
    total = len(VIVID_VENUE_IDS)
    print(f"Progress: {len(done)}/{total} venues done")
    for vid, vkey in VIVID_VENUE_IDS.items():
        status = "DONE" if str(vid) in done else "PENDING"
        print(f"  [{vid}] {vkey:35s} {status}")
    print(f"Accumulated WC events: {len(state.get('wc_events', []))}")


def cmd_fetch_next():
    """Fetch the next pending venue from Apify."""
    state = load_state()
    done = set(str(v) for v in state.get("done_venues", []))
    pending = [(vid, vkey) for vid, vkey in VIVID_VENUE_IDS.items() if str(vid) not in done]

    if not pending:
        print("All venues already fetched! Run --finalize or --hotels to write output.")
        return True  # all done

    ApifyClient = _ensure_apify_client()
    client = ApifyClient(APIFY_TOKEN)

    venue_id, venue_key = pending[0]
    print(f"Fetching [{venue_id}] {venue_key} ({len(done)+1}/{len(VIVID_VENUE_IDS)})…")

    try:
        run = client.actor("hoholabs/vividseats-scraper").call(
            run_input={"queryType": "venue", "venueId": str(venue_id), "rows": 200, "start": 0},
            timeout_secs=35,
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        wc_items = []
        for item in items:
            local_date = item.get("localDate") or ""
            name = item.get("name") or ""
            if _is_wc_event(name, local_date):
                item["_venue_key"] = venue_key
                item["_match_number"] = _extract_match_number(name)
                wc_items.append(item)
        print(f"  {len(wc_items)} WC / {len(items)} total")

        state.setdefault("wc_events", []).extend(wc_items)
        state.setdefault("done_venues", []).append(str(venue_id))
        save_state(state)
        print(f"  Saved. {len(pending)-1} venues remaining.")
    except Exception as exc:
        print(f"  ERROR: {exc}")
        # Mark as done with error so we skip and continue
        state.setdefault("done_venues", []).append(str(venue_id))
        state.setdefault("errors", []).append({"venue_id": venue_id, "venue_key": venue_key, "error": str(exc)})
        save_state(state)

    remaining = len(VIVID_VENUE_IDS) - len(state.get("done_venues", []))
    return remaining == 0


def cmd_finalize(fetch_hotels_flag=False):
    """Assemble final prices.json from accumulated state."""
    state = load_state()
    wc_events = state.get("wc_events", [])
    if not wc_events:
        print("No WC events in state! Run venue fetches first.")
        return

    # Deduplicate
    deduped: dict[str, dict] = {}
    for ev in wc_events:
        date_part = (ev.get("localDate") or "")[:10]
        key = f"{date_part}|{ev['_venue_key']}"
        if key not in deduped or (ev.get("minPrice") or 0) < (deduped[key].get("minPrice") or 0):
            deduped[key] = ev
    all_events = list(deduped.values())
    print(f"Total unique WC matches: {len(all_events)}")

    tiers, match_prices = process_wc_events(all_events)

    if fetch_hotels_flag:
        hotels, hotel_source = fetch_hotels()
    else:
        # Load existing hotel data from prices.json
        existing = {}
        if OUTPUT_PATH.exists():
            try:
                existing = json.loads(OUTPUT_PATH.read_text())
            except Exception:
                pass
        hotels = existing.get("hotels", FALLBACK_HOTELS)
        hotel_source = existing.get("hotel_source", "cached from previous run")
        print(f"\n🏨 Using existing hotel data ({hotel_source})")

    errors = state.get("errors", [])
    ticket_source = f"VividSeats via Apify (venue-by-venue{', ' + str(len(errors)) + ' errors' if errors else ''})"
    write_output(tiers, match_prices, hotels, hotel_source, ticket_source)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--status" in args:
        cmd_status()
    elif "--hotels" in args:
        cmd_finalize(fetch_hotels_flag=True)
    elif "--finalize" in args:
        cmd_finalize(fetch_hotels_flag=False)
    else:
        # Default: fetch next venue
        all_done = cmd_fetch_next()
        if all_done:
            print("\nAll venues fetched! Running finalize…")
            cmd_finalize(fetch_hotels_flag=False)
