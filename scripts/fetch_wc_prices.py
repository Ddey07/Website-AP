"""
FIFA World Cup 2026 — Price Fetcher
=====================================
Fetches:
  1. Ticket resale prices via Apify hoholabs/vividseats-scraper
       Primary:  queryType=venue, one call per stadium ID (rows=200)
                 Filters to WC-only events; extracts official match numbers.
       Fallback: queryType=performer, single run (~25 matches)
       Last resort: SeatGeek → placeholder if Apify unavailable.
  2. Hotel nightly rates via SerpAPI (Google Hotels) → prices.json["hotels"]
     Hotels are fetched per venue × round (~44 queries/run), cached 10 hours.

SETUP — add these to your .env file in the project root:
  APIFY_TOKEN=your_token      # apify.com → Settings → Integrations
  SERPAPI_KEY=your_key        # serpapi.com → Dashboard
  SEATGEEK_CLIENT_ID=your_id  # optional, last fallback

FIRST RUN — install Apify client:
  pip install apify-client

RUN:
  python scripts/fetch_wc_prices.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env file from project root if it exists (no extra packages needed)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── CONFIG ─────────────────────────────────────────────────────────────────────
APIFY_TOKEN        = os.environ.get("APIFY_TOKEN",        "")
SEATGEEK_CLIENT_ID = os.environ.get("SEATGEEK_CLIENT_ID", "YOUR_SEATGEEK_CLIENT_ID")
SERPAPI_KEY        = os.environ.get("SERPAPI_KEY",        "YOUR_SERPAPI_KEY")

_ROOT       = Path(__file__).parent.parent
OUTPUT_PATH    = _ROOT / "static" / "wc2026" / "prices.json"
OUTPUT_PATH_JS = _ROOT / "static" / "wc2026" / "prices.js"
# Also mirror to public/ so Hugo-built sites pick it up without a rebuild
OUTPUT_PATH_PUBLIC    = _ROOT / "public" / "wc2026" / "prices.json"
OUTPUT_PATH_PUBLIC_JS = _ROOT / "public" / "wc2026" / "prices.js"

SEATGEEK_API      = "https://api.seatgeek.com/2"
SERPAPI_URL       = "https://serpapi.com/search.json"
WC_PERFORMER_SLUG = "fifa-world-cup"

# Date ranges for each round (inclusive).
# Classify tickets by localDate first; fall back to name keywords.
ROUND_DATE_RANGES = {
    "group": ("2026-06-11", "2026-06-27"),
    "r32":   ("2026-06-28", "2026-07-03"),
    "r16":   ("2026-07-04", "2026-07-07"),
    "qf":    ("2026-07-09", "2026-07-11"),
    "sf":    ("2026-07-14", "2026-07-15"),
    "final": ("2026-07-18", "2026-07-19"),  # Jul 18 = M103 third place, Jul 19 = M104 final
}

ROUND_KEYWORDS = {
    "group": ["group stage", "group a", "group b", "group c", "group d",
              "group e", "group f", "group g", "group h", "group i",
              "group j", "group k", "group l"],
    "r32":   ["round of 32"],
    "r16":   ["round of 16"],
    "qf":    ["quarterfinal", "quarter-final"],
    "sf":    ["semifinal", "semi-final"],
    "final": ["final"],
}

# ── VENUE × ROUND DATE MAP ────────────────────────────────────────────────────
# Each entry lists which rounds a venue hosts and the date of the first match
# in that round at that venue. This drives one SerpAPI hotel query per combo.
# Total: 44 queries per run (within 100/month free tier → ~2 runs/month).
VENUE_ROUND_DATES = {
    "East Rutherford (MetLife)": {
        "group": ("New York City",   "2026-06-13"),
        "r32":   ("New York City",   "2026-06-30"),
        "r16":   ("New York City",   "2026-07-05"),
        "final": ("New York City",   "2026-07-19"),
    },
    "Philadelphia (Lincoln Financial)": {
        "group": ("Philadelphia PA", "2026-06-14"),
        "r16":   ("Philadelphia PA", "2026-07-04"),
    },
    "Foxborough (Gillette)": {
        "group": ("Boston MA",       "2026-06-13"),
        "r32":   ("Boston MA",       "2026-06-29"),
        "qf":    ("Boston MA",       "2026-07-09"),
    },
    "Atlanta (Mercedes-Benz)": {
        "group": ("Atlanta GA",      "2026-06-18"),
        "r32":   ("Atlanta GA",      "2026-07-01"),
        "r16":   ("Atlanta GA",      "2026-07-07"),
        "sf":    ("Atlanta GA",      "2026-07-15"),
    },
    "Miami (Hard Rock)": {
        "group": ("Miami FL",        "2026-06-15"),
        "r32":   ("Miami FL",        "2026-07-03"),
        "qf":    ("Miami FL",        "2026-07-11"),
        "final": ("Miami FL",        "2026-07-18"),
    },
    "Dallas (AT&T)": {
        "group": ("Dallas TX",       "2026-06-17"),
        "r32":   ("Dallas TX",       "2026-06-30"),
        "r16":   ("Dallas TX",       "2026-07-06"),
        "sf":    ("Dallas TX",       "2026-07-14"),
    },
    "Houston (NRG)": {
        "group": ("Houston TX",      "2026-06-21"),
        "r32":   ("Houston TX",      "2026-06-29"),
        "r16":   ("Houston TX",      "2026-07-04"),
    },
    "Kansas City (Arrowhead)": {
        "group": ("Kansas City MO",  "2026-06-14"),
        "r32":   ("Kansas City MO",  "2026-07-03"),
        "qf":    ("Kansas City MO",  "2026-07-11"),
    },
    "Seattle (Lumen Field)": {
        "group": ("Seattle WA",      "2026-06-19"),
        "r32":   ("Seattle WA",      "2026-07-01"),
        "r16":   ("Seattle WA",      "2026-07-06"),
    },
    "Santa Clara (Levi's)": {
        "group": ("San Jose CA",     "2026-06-13"),
        "r32":   ("San Jose CA",     "2026-07-01"),
    },
    "Inglewood (SoFi)": {
        "group": ("Los Angeles CA",  "2026-06-12"),
        "r32":   ("Los Angeles CA",  "2026-06-28"),
        "qf":    ("Los Angeles CA",  "2026-07-10"),
    },
    "Vancouver (BC Place)": {
        "group": ("Vancouver BC",    "2026-06-18"),
        "r32":   ("Vancouver BC",    "2026-07-02"),
        "r16":   ("Vancouver BC",    "2026-07-07"),
    },
    "Toronto (BMO Field)": {
        "group": ("Toronto ON",      "2026-06-12"),
        "r32":   ("Toronto ON",      "2026-07-02"),
    },
    "Mexico City (Azteca)": {
        "group": ("Mexico City",     "2026-06-17"),
        "r32":   ("Mexico City",     "2026-06-30"),
        "r16":   ("Mexico City",     "2026-07-05"),
    },
    "Guadalajara (Akron)": {
        "group": ("Guadalajara",     "2026-06-18"),
        "r32":   ("Guadalajara",     "2026-06-29"),
    },
    "Monterrey (BBVA)": {
        "group": ("Monterrey",       "2026-06-14"),
    },
}

# ── VIVID SEATS VENUE ID MAP ─────────────────────────────────────────────────
# VividSeats numeric venue IDs → internal venue keys used in prices.json.
# These IDs are used with queryType=venue to fetch per-venue event listings.
# NOTE: Mexican / Canadian venues (Azteca, Akron, BBVA) are not in VividSeats
# as US-accessible venue IDs, so they are omitted here and fall back to the
# performer-based or direct-Hermes fetches.
VIVID_VENUE_IDS: dict[int, str] = {
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

# World Cup 2026 date window (inclusive) — used to filter non-WC events
WC_START_DATE = "2026-06-11"
WC_END_DATE   = "2026-07-19"

# ── VENUE NAME MAP ────────────────────────────────────────────────────────────
# Maps VividSeats venue.name strings → internal venue keys used in prices.json
VENUE_NAME_MAP = {
    "BMO Field":                        "Toronto (BMO Field)",
    "SoFi Stadium":                     "Inglewood (SoFi)",
    "Gillette Stadium":                 "Foxborough (Gillette)",
    "MetLife Stadium":                  "East Rutherford (MetLife)",
    "Lincoln Financial Field":          "Philadelphia (Lincoln Financial)",
    "Mercedes-Benz Stadium":            "Atlanta (Mercedes-Benz)",
    "Hard Rock Stadium":                "Miami (Hard Rock)",
    "AT&T Stadium":                     "Dallas (AT&T)",
    "NRG Stadium":                      "Houston (NRG)",
    "GEHA Field at Arrowhead Stadium":  "Kansas City (Arrowhead)",
    "Arrowhead Stadium":                "Kansas City (Arrowhead)",
    "Lumen Field":                      "Seattle (Lumen Field)",
    "Levi's Stadium":                   "Santa Clara (Levi's)",
    "Levis Stadium":                    "Santa Clara (Levi's)",
    "BC Place Stadium":                 "Vancouver (BC Place)",
    "BC Place":                         "Vancouver (BC Place)",
    "Estadio Azteca":                   "Mexico City (Azteca)",
    "Estadio AKRON":                    "Guadalajara (Akron)",
    "Estadio Akron":                    "Guadalajara (Akron)",
    "Estadio BBVA":                     "Monterrey (BBVA)",
}

# VividSeats adds a ~34% service fee on top of listed prices.
# All ticket prices stored in prices.json are all-in (fee already included).
VIVID_FEE_FACTOR = 1.34

# Fallback ticket prices — already include the 34% VividSeats service fee
FALLBACK_TIERS = {
    "group": {"low":   127, "high":   563},
    "r32":   {"low":  201, "high":   831},
    "r16":   {"low":  295, "high":  1206},
    "qf":    {"low":  509, "high":  2412},
    "sf":    {"low":  804, "high":  4690},
    "final": {"low": 1608, "high": 16080},
}

# Fallback hotel prices per venue per round
# KO rounds are priced ~30-60% higher than group stage due to demand surge
FALLBACK_HOTELS = {
    "East Rutherford (MetLife)": {
        "group": {"low": 220, "high": 580},
        "r32":   {"low": 280, "high": 720},
        "r16":   {"low": 320, "high": 820},
        "final": {"low": 500, "high": 1400},
    },
    "Philadelphia (Lincoln Financial)": {
        "group": {"low": 140, "high": 380},
        "r16":   {"low": 200, "high": 520},
    },
    "Foxborough (Gillette)": {
        "group": {"low": 160, "high": 440},
        "r32":   {"low": 210, "high": 560},
        "qf":    {"low": 260, "high": 700},
    },
    "Atlanta (Mercedes-Benz)": {
        "group": {"low": 130, "high": 360},
        "r32":   {"low": 170, "high": 460},
        "r16":   {"low": 210, "high": 560},
        "sf":    {"low": 300, "high": 800},
    },
    "Miami (Hard Rock)": {
        "group": {"low": 190, "high": 520},
        "r32":   {"low": 240, "high": 640},
        "qf":    {"low": 300, "high": 820},
        "final": {"low": 420, "high": 1100},
    },
    "Dallas (AT&T)": {
        "group": {"low": 120, "high": 330},
        "r32":   {"low": 160, "high": 430},
        "r16":   {"low": 200, "high": 540},
        "sf":    {"low": 300, "high": 780},
    },
    "Houston (NRG)": {
        "group": {"low": 110, "high": 300},
        "r32":   {"low": 150, "high": 390},
        "r16":   {"low": 190, "high": 490},
    },
    "Kansas City (Arrowhead)": {
        "group": {"low": 100, "high": 280},
        "r32":   {"low": 140, "high": 370},
        "qf":    {"low": 200, "high": 520},
    },
    "Seattle (Lumen Field)": {
        "group": {"low": 160, "high": 430},
        "r32":   {"low": 210, "high": 550},
        "r16":   {"low": 260, "high": 680},
    },
    "Santa Clara (Levi's)": {
        "group": {"low": 180, "high": 480},
        "r32":   {"low": 240, "high": 620},
    },
    "Inglewood (SoFi)": {
        "group": {"low": 160, "high": 440},
        "r32":   {"low": 210, "high": 560},
        "qf":    {"low": 280, "high": 740},
    },
    "Vancouver (BC Place)": {
        "group": {"low": 180, "high": 480},
        "r32":   {"low": 230, "high": 600},
        "r16":   {"low": 280, "high": 740},
    },
    "Toronto (BMO Field)": {
        "group": {"low": 150, "high": 420},
        "r32":   {"low": 200, "high": 540},
    },
    "Mexico City (Azteca)": {
        "group": {"low":  70, "high": 220},
        "r32":   {"low":  90, "high": 280},
        "r16":   {"low": 110, "high": 340},
    },
    "Guadalajara (Akron)": {
        "group": {"low":  60, "high": 180},
        "r32":   {"low":  80, "high": 230},
    },
    "Monterrey (BBVA)": {
        "group": {"low":  65, "high": 200},
    },
}

# ── HELPERS ────────────────────────────────────────────────────────────────────

def api_get(url, params):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full_url, headers={"User-Agent": "wc2026-price-fetcher/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def classify_round(title: str) -> str | None:
    t = title.lower()
    for tier, kws in ROUND_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return tier
    return None


# ── TICKET PRICES (VividSeats via Apify hoholabs/vividseats-scraper) ──────────
# Install once: pip install apify-client


def _ensure_apify_client():
    """Import apify_client, auto-installing if missing."""
    try:
        from apify_client import ApifyClient
        return ApifyClient
    except ImportError:
        print("   Installing apify-client…")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install",
             "apify-client", "--break-system-packages", "-q"],
            stdout=subprocess.DEVNULL,
        )
        from apify_client import ApifyClient
        return ApifyClient


def classify_round_by_date(date_str: str) -> str | None:
    """Map YYYY-MM-DD to a round key using the official schedule."""
    if not date_str:
        return None
    for rnd, (start, end) in ROUND_DATE_RANGES.items():
        if start <= date_str <= end:
            return rnd
    return None


def classify_round_by_name(title: str) -> str | None:
    """Fall back to keyword matching on the event name."""
    t = title.lower()
    for tier, kws in ROUND_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return tier
    return None


def _is_wc_event(name: str, local_date_str: str) -> bool:
    """Return True only for FIFA World Cup 2026 matches (not NFL, concerts, etc.)."""
    if "world cup" not in name.lower():
        return False
    date_part = local_date_str[:10]  # keep YYYY-MM-DD prefix
    return WC_START_DATE <= date_part <= WC_END_DATE


def _extract_match_number(name: str) -> int | None:
    """
    Pull the official match number out of a VividSeats event name.
    Examples:
      "Argentina vs Algeria - World Cup - Match 19 (Group J)" → 19
      "2026 World Cup - Match 87"                             → 87
      "2026 World Cup - Match 100 (Quarter-Final)"            → 100
    """
    import re
    m = re.search(r"[Mm]atch\s+(\d+)", name)
    return int(m.group(1)) if m else None


def _fetch_apify_by_venues() -> list | None:
    """
    Primary Apify strategy: query each venue individually with queryType=venue.

    Input per call:
      {"queryType": "venue", "rows": 200, "venueId": "<id>", "start": 0}

    Each response includes all upcoming events at that venue (WC games, NFL,
    concerts, etc.). We keep only events whose name contains 'World Cup' and
    whose date falls within the WC 2026 window (Jun 11 – Jul 19, 2026).

    Each retained event gets two extra fields injected:
      _venue_key    – our internal venue label (e.g. "Kansas City (Arrowhead)")
      _match_number – official match number parsed from the event name, or None

    Returns a flat list of all WC events across all venues, or None on failure.
    """
    if not APIFY_TOKEN:
        return None
    ApifyClient = _ensure_apify_client()
    client = ApifyClient(APIFY_TOKEN)

    all_wc_events: list = []
    errors = 0

    print("   Apify venue-by-venue fetch…")
    for venue_id, venue_key in VIVID_VENUE_IDS.items():
        print(f"     [{venue_id}] {venue_key[:35]:35s} …", end=" ", flush=True)
        try:
            run = client.actor("hoholabs/vividseats-scraper").call(
                run_input={
                    "queryType": "venue",
                    "venueId":   str(venue_id),
                    "rows":      200,
                    "start":     0,
                },
            )
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

            wc_items = []
            for item in items:
                local_date = item.get("localDate") or ""
                name       = item.get("name")       or ""
                if _is_wc_event(name, local_date):
                    item["_venue_key"]    = venue_key
                    item["_match_number"] = _extract_match_number(name)
                    wc_items.append(item)

            print(f"{len(wc_items)} WC / {len(items)} total")
            all_wc_events.extend(wc_items)

        except Exception as exc:
            print(f"❌ {exc}")
            errors += 1

    if not all_wc_events:
        return None

    # Deduplicate by (date, venue_key) — keep entry with lower minPrice
    deduped: dict[str, dict] = {}
    for ev in all_wc_events:
        date_part = (ev.get("localDate") or "")[:10]
        key       = f"{date_part}|{ev['_venue_key']}"
        if key not in deduped or (ev.get("minPrice") or 0) < (deduped[key].get("minPrice") or 0):
            deduped[key] = ev

    result = list(deduped.values())
    print(f"   ✅ {len(result)} unique WC matches across {len(VIVID_VENUE_IDS)} venues"
          f"  ({errors} venue errors)")
    return result


def _fetch_apify_single() -> list | None:
    """
    Last-resort Apify fallback: single performer-based run (first 25 matches only).
    The actor ignores start/page/dateFrom so coverage is limited to ~25 events.
    """
    if not APIFY_TOKEN:
        return None
    ApifyClient = _ensure_apify_client()
    client = ApifyClient(APIFY_TOKEN)
    print("   Apify single performer run (first 25 matches)…", end=" ", flush=True)
    try:
        run = client.actor("hoholabs/vividseats-scraper").call(
            run_input={
                "performerId": "944",
                "queryType":   "performer",
                "rows":        200,
            },
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"{len(items)} matches")
        return items or None
    except Exception as exc:
        print(f"❌ {exc}")
        return None


def fetch_vividseats_prices() -> tuple[dict | None, dict | None, str]:
    """
    Collect all WC 2026 VividSeats match prices via Apify.

    Strategy 1 – Apify hoholabs/vividseats-scraper, venue-by-venue
                 (queryType=venue, one call per stadium ID → precise WC filtering,
                  match numbers extracted from event names).
    Strategy 2 – Apify single performer run (first ~25 matches only, last resort).

    Returns: tiers, match_prices, source_label
    """
    print("🎟️  Fetching VividSeats prices via Apify…")

    # The venue-by-venue queries (queryType=venue) currently return 0 results with
    # the stored VividSeats venue IDs, and each one is a billable pay-per-event
    # Apify run — so firing ~13 of them just drains a free-plan budget and leaves
    # nothing for the query that works. Use the performer query directly: it returns
    # the ~25 soonest WC matches with live prices in a single run.
    all_prods = _fetch_apify_single()
    source_tag = "VividSeats via Apify (performer)"

    if not all_prods:
        print("   Performer run failed — trying venue-by-venue…")
        all_prods = _fetch_apify_by_venues()
        source_tag = "VividSeats via Apify (venue-by-venue)"

    if not all_prods:
        return None, None, "vividseats-unavailable"

    print(f"\n   ✅ Total WC productions to process: {len(all_prods)}")

    # ── Bucket by round + build per-match prices ─────────────────────────────
    # round_buckets: round → list of {low, high}   (for global tier aggregation)
    # match_prices:  "YYYY-MM-DD|venue_key" → {low, high, name, sample, [matchNum]}
    round_buckets: dict[str, list] = {k: [] for k in ROUND_DATE_RANGES}
    match_prices: dict[str, dict] = {}

    for prod in all_prods:
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

        min_p = float(min_p) * VIVID_FEE_FACTOR   # include 34% VividSeats service fee
        raw_max = float(max_p) if max_p else float(min_p) / VIVID_FEE_FACTOR * 5
        max_p = raw_max * VIVID_FEE_FACTOR

        # Venue key: pre-tagged by venue-based fetch takes priority;
        # otherwise fall back to venue name → key lookup (Hermes / performer path).
        venue_key = prod.get("_venue_key")
        if not venue_key:
            raw_venue = ""
            if isinstance(prod.get("venue"), dict):
                raw_venue = prod["venue"].get("name", "")
            elif isinstance(prod.get("venue"), str):
                raw_venue = prod["venue"]
            venue_key = VENUE_NAME_MAP.get(raw_venue)

        entry = {"low": min_p, "high": max_p}
        round_buckets[rnd].append(entry)

        if venue_key and date_str:
            match_key = f"{date_str}|{venue_key}"
            match_entry: dict = {
                "low":  int(min_p),
                "high": int(max_p),
                "name":   prod.get("name", ""),
                "sample": int(prod.get("listingCount") or 0),
            }
            # Include official match number when available (from venue-based fetch)
            match_num = prod.get("_match_number")
            if match_num:
                match_entry["matchNum"] = match_num
            match_prices[match_key] = match_entry

        print(f"   {rnd:6s}  ${min_p:.0f}–${max_p:.0f}  "
              f"{(venue_key or '?')[:32]}  [{date_str}]"
              + (f"  M{prod['_match_number']}" if prod.get("_match_number") else ""))

    fetched = sum(len(v) for v in round_buckets.values())
    if fetched == 0:
        return None, None, "vividseats-apify-no-prices"

    # ── Aggregate global tiers (fallback when match not yet listed) ───────────
    def _aggregate(rows: list, fallback: dict) -> dict:
        if not rows:
            return fallback
        lows  = sorted(r["low"]  for r in rows)
        highs = sorted(r["high"] for r in rows)
        return {
            "low":    int(lows[0]),
            "high":   int(highs[-1]),
            "sample": len(rows),
        }

    tiers: dict = {}
    print("\n── Global tiers ─────────────────────────────────────")
    for rnd in ROUND_DATE_RANGES:
        rows = round_buckets[rnd]
        tiers[rnd] = _aggregate(rows, FALLBACK_TIERS[rnd])
        t = tiers[rnd]
        src = f"{t['sample']} matches" if rows else "fallback"
        print(f"   {rnd:6s}: ${t['low']}–${t['high']}  ({src})")

    print(f"\n── Per-match prices ─────────────────────────────────")
    for mk, mv in sorted(match_prices.items()):
        print(f"   {mk:45s}  ${mv['low']}–${mv['high']}")

    return tiers, match_prices, "VividSeats"


# ── TICKET PRICES (SeatGeek) ──────────────────────────────────────────────────

def fetch_ticket_prices() -> tuple[dict, str]:
    if SEATGEEK_CLIENT_ID == "YOUR_SEATGEEK_CLIENT_ID":
        print("⚠️  No SeatGeek key — using placeholder ticket prices.")
        return FALLBACK_TIERS, "Placeholder — set SEATGEEK_CLIENT_ID"

    print("🎟️  Fetching ticket prices from SeatGeek…")
    try:
        data = api_get(f"{SEATGEEK_API}/events", {
            "performers.slug": WC_PERFORMER_SLUG,
            "per_page": 200,
            "sort": "datetime_local.asc",
            "client_id": SEATGEEK_CLIENT_ID,
        })
    except Exception as exc:
        print(f"   ❌ SeatGeek error: {exc} — using placeholder prices.")
        return FALLBACK_TIERS, "Placeholder (SeatGeek unavailable)"

    events = data.get("events", [])
    print(f"   Found {len(events)} events")

    buckets: dict[str, list] = {k: [] for k in ROUND_KEYWORDS}
    for ev in events:
        title = ev.get("title", "") or ev.get("short_title", "")
        tier = classify_round(title)
        if not tier:
            continue
        stats = ev.get("stats", {})
        low  = stats.get("lowest_price")
        avg  = stats.get("average_price")
        high = stats.get("highest_price")
        if low is not None:
            buckets[tier].append({"low": low, "avg": avg, "high": high})

    tiers = {}
    for tier, rows in buckets.items():
        if rows:
            lows  = [r["low"]  for r in rows if r["low"]  is not None]
            avgs  = [r["avg"]  for r in rows if r["avg"]  is not None]
            highs = [r["high"] for r in rows if r["high"] is not None]
            tiers[tier] = {
                "low":  int(min(lows))  if lows  else FALLBACK_TIERS[tier]["low"],
                "high": int(max(highs)) if highs else FALLBACK_TIERS[tier]["high"],
                "sample": len(rows),
            }
            print(f"   {tier:6s}: ${tiers[tier]['low']}–${tiers[tier]['high']}  ({len(rows)} events)")
        else:
            tiers[tier] = FALLBACK_TIERS[tier]
            print(f"   {tier:6s}: no events — using placeholder")

    return tiers, "SeatGeek API"


# ── HOTEL PRICES (SerpAPI Google Hotels) ─────────────────────────────────────

def fetch_one_hotel(city: str, check_in: str) -> dict | None:
    """Fetch hotels for one city+date. Returns {low, high} or None on error."""
    check_out = (
        datetime.strptime(check_in, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")
    data = api_get(SERPAPI_URL, {
        "engine":         "google_hotels",
        "q":              f"Hotels in {city}",
        "check_in_date":  check_in,
        "check_out_date": check_out,
        "adults":         "2",
        "currency":       "USD",
        "api_key":        SERPAPI_KEY,
    })
    prices_found = []
    for prop in data.get("properties", []):
        val = prop.get("rate_per_night", {}).get("extracted_lowest")
        if val and isinstance(val, (int, float)) and val > 0:
            prices_found.append(int(val))
    if not prices_found:
        return None
    prices_found.sort()
    q25 = prices_found[max(0, len(prices_found) // 4)]
    q75 = prices_found[min(len(prices_found) - 1, (3 * len(prices_found)) // 4)]
    return {
        "low":    q25,
        "high":   q75,
        "min":    prices_found[0],
        "max":    prices_found[-1],
        "sample": len(prices_found),
    }


def fetch_hotel_prices() -> tuple[dict, str]:
    if SERPAPI_KEY == "YOUR_SERPAPI_KEY":
        print("⚠️  No SerpAPI key — using placeholder hotel prices.")
        return FALLBACK_HOTELS, "Placeholder — set SERPAPI_KEY"

    # Count total queries upfront
    total = sum(len(rounds) for rounds in VENUE_ROUND_DATES.values())
    print(f"\n🏨 Fetching hotel prices from SerpAPI — {total} queries (venue × round)…")

    hotels: dict[str, dict] = {}
    errors = 0
    done = 0

    for venue, rounds in VENUE_ROUND_DATES.items():
        hotels[venue] = {}
        for rnd, (city, check_in) in rounds.items():
            done += 1
            label = f"[{done}/{total}] {venue[:30]:30s} {rnd:6s}"
            try:
                result = fetch_one_hotel(city, check_in)
                if result:
                    hotels[venue][rnd] = result
                    print(f"   {label}: ${result['low']}–${result['high']}/night  ({result['sample']} props)")
                else:
                    hotels[venue][rnd] = FALLBACK_HOTELS[venue][rnd]
                    print(f"   {label}: no results — using placeholder")
            except Exception as exc:
                hotels[venue][rnd] = FALLBACK_HOTELS[venue].get(
                    rnd, FALLBACK_HOTELS[venue].get("group", {"low": 150, "high": 400})
                )
                print(f"   {label}: ❌ {exc} — using placeholder")
                errors += 1

    source = (
        "SerpAPI Google Hotels" if errors == 0
        else f"SerpAPI Google Hotels (partial — {errors} fallbacks)"
        if errors < total
        else "Placeholder (SerpAPI unavailable)"
    )
    return hotels, source


# ── MAIN ──────────────────────────────────────────────────────────────────────

HOTEL_CACHE_HOURS = 10  # skip hotel API if data is fresher than this


def load_existing_prices() -> dict:
    """Load prices.json if it exists, otherwise return empty dict."""
    if OUTPUT_PATH.exists():
        try:
            return json.loads(OUTPUT_PATH.read_text())
        except Exception:
            pass
    return {}


def hotels_are_fresh(existing: dict) -> bool:
    """Return True if hotel data was fetched less than HOTEL_CACHE_HOURS ago."""
    ts = existing.get("hotels_fetched_at")
    if not ts:
        return False
    try:
        fetched = datetime.fromisoformat(ts)
        age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
        return age_hours < HOTEL_CACHE_HOURS
    except Exception:
        return False


def main():
    existing = load_existing_prices()

    # Ticket prices: VividSeats via Apify → SeatGeek → placeholder
    tiers, match_prices, ticket_source = fetch_vividseats_prices()
    if tiers is None:
        print(f"\n   ⚠️  VividSeats unavailable ({ticket_source}) — trying SeatGeek…")
        tiers, ticket_source = fetch_ticket_prices()
        match_prices = None

    # SAFETY: never downgrade good prices. If this run produced placeholder/SeatGeek
    # data (no real VividSeats per-match prices) but the existing file already holds
    # real VividSeats prices, keep the existing data instead of overwriting it.
    def _is_real(src, matches):
        s = (src or "").lower()
        return bool(matches) and "placeholder" not in s and "unavailable" not in s
    if not _is_real(ticket_source, match_prices) and _is_real(existing.get("ticket_source"), existing.get("matches")):
        print("   ⚠️  Live ticket fetch unavailable — KEEPING existing real VividSeats prices "
              "(not overwriting with placeholders).")
        tiers         = existing.get("tiers", tiers)
        match_prices  = existing.get("matches")
        ticket_source = existing.get("ticket_source", ticket_source) + " (kept — live fetch failed)"

    # Hotel prices: reuse cached data if fresh enough
    if hotels_are_fresh(existing):
        hotels       = existing.get("hotels", {})
        hotel_source = existing.get("hotel_source", "cached")
        fetched_at   = existing["hotels_fetched_at"]
        age_minutes  = int((datetime.now(timezone.utc) -
                            datetime.fromisoformat(fetched_at)).total_seconds() / 60)
        print(f"\n🏨 Hotel prices cached ({age_minutes} min ago) — skipping API calls "
              f"(refresh after {HOTEL_CACHE_HOURS}h).")
    else:
        hotels, hotel_source = fetch_hotel_prices()
        fetched_at = datetime.now(timezone.utc).isoformat()

    output = {
        "last_updated":      datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hotels_fetched_at": fetched_at,
        "ticket_source":     ticket_source,
        "hotel_source":      hotel_source,
        "tiers":             tiers,
        "hotels":            hotels,
    }
    # Per-match ticket prices (present only when VividSeats data available)
    # Primary index  — "YYYY-MM-DD|venue_key" e.g. "2026-06-16|Kansas City (Arrowhead)"
    # Secondary index — matchById[<int>]       e.g. matchById[87]  (KO match numbers)
    if match_prices:
        output["matches"] = match_prices
        # Build integer-keyed secondary index for KO match number lookups
        match_by_id: dict[int, dict] = {}
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

    # Mirror to public/ so Hugo-built sites pick it up without a rebuild
    for src, dst in [(payload, OUTPUT_PATH_PUBLIC), (payload_js, OUTPUT_PATH_PUBLIC_JS)]:
        if dst.parent.exists():
            dst.write_text(src)
            print(f"   Mirrored  → {dst}")
    print(f"   Tickets: {ticket_source}")
    if match_prices:
        print(f"   Per-match ticket data: {len(match_prices)} matches")
    print(f"   Hotels:  {hotel_source}")
    print(f"   Updated: {output['last_updated']}")


if __name__ == "__main__":
    main()
