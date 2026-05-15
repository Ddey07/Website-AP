"""
FIFA World Cup 2026 — Price Fetcher
=====================================
Fetches:
  1. Ticket resale prices — tries sources in order:
       a) VividSeats via Apify (free tier, ~$0.05/run) ← active now
       b) SeatGeek API (free, pending approval)
       c) Placeholder estimates
  2. Hotel nightly rates via SerpAPI (Google Hotels) → prices.json["hotels"]
     Hotels are fetched per venue × round (~44 queries/run).

SETUP — add these to your .env file in the project root:
  APIFY_TOKEN=your_apify_token       # apify.com → Settings → Integrations
  SERPAPI_KEY=your_serpapi_key       # serpapi.com → Dashboard
  SEATGEEK_CLIENT_ID=your_id        # optional, fallback once approved

RUN:
  python scripts/fetch_wc_prices.py

SCHEDULE (Cowork):
  Prompt: "Run the Python script at scripts/fetch_wc_prices.py
           to update World Cup ticket and hotel prices"
"""

import json
import os
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
APIFY_TOKEN        = os.environ.get("APIFY_TOKEN",        "YOUR_APIFY_TOKEN")
APIFY_ACTOR_ID     = "hoholabs~vividseats-scraper"   # VividSeats scraper
SEATGEEK_CLIENT_ID = os.environ.get("SEATGEEK_CLIENT_ID", "YOUR_SEATGEEK_CLIENT_ID")
SERPAPI_KEY        = os.environ.get("SERPAPI_KEY",        "YOUR_SERPAPI_KEY")

OUTPUT_PATH = Path(__file__).parent.parent / "static" / "wc2026" / "prices.json"

APIFY_API         = "https://api.apify.com/v2"
SEATGEEK_API      = "https://api.seatgeek.com/2"
SERPAPI_URL       = "https://serpapi.com/search.json"
VIVIDSEATS_API    = "https://www.vividseats.com/api/v3"
WC_PERFORMER_ID   = "944"   # /performer/944 on VividSeats
WC_PERFORMER_SLUG = "fifa-world-cup"

# Date ranges for each round (inclusive).
# Classify tickets by localDate first; fall back to name keywords.
ROUND_DATE_RANGES = {
    "group": ("2026-06-11", "2026-06-27"),
    "r32":   ("2026-06-28", "2026-07-03"),
    "r16":   ("2026-07-04", "2026-07-07"),
    "qf":    ("2026-07-09", "2026-07-11"),
    "sf":    ("2026-07-14", "2026-07-15"),
    "final": ("2026-07-19", "2026-07-19"),
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
        "qf":    ("Miami FL",        "2026-07-11"),
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

# Fallback ticket prices
FALLBACK_TIERS = {
    "group": {"low":   95, "median":  185, "high":   420},
    "r32":   {"low":  150, "median":  280, "high":   620},
    "r16":   {"low":  220, "median":  420, "high":   900},
    "qf":    {"low":  380, "median":  700, "high":  1800},
    "sf":    {"low":  600, "median": 1200, "high":  3500},
    "final": {"low": 1200, "median": 3500, "high": 12000},
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
        "qf":    {"low": 300, "high": 820},
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


def api_post(url, params, body):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        full_url, data=data,
        headers={"User-Agent": "wc2026-price-fetcher/1.0",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def classify_round(title: str) -> str | None:
    t = title.lower()
    for tier, kws in ROUND_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return tier
    return None


# ── TICKET PRICES (VividSeats via Apify) ─────────────────────────────────────

def _extract_price(item) -> tuple[float | None, float | None, float | None]:
    """Return (low, median, high) from a VividSeats item. Any value may be None."""
    def _f(key):
        val = item.get(key)
        if val is None:
            return None
        try:
            return float(str(val).replace("$", "").replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    # VividSeats scraper returns these directly on each event item
    low    = _f("minPrice") or _f("lowestPrice") or _f("startingPrice") or _f("price")
    high   = _f("maxPrice") or _f("highestPrice")
    median = _f("medianPrice") or _f("avgPrice") or _f("averagePrice")
    return low, median, high


def _extract_title(item) -> str:
    for key in ("name", "title", "eventName", "productionTitle", "event", "event_name"):
        val = item.get(key)
        if val and isinstance(val, str):
            return val
    return ""


def _extract_date(item) -> str:
    """Return YYYY-MM-DD string from localDate / utcDate, or ''."""
    for key in ("localDate", "utcDate", "date", "eventDate", "startDate"):
        val = item.get(key)
        if val and isinstance(val, str):
            # Handle ISO strings like "2026-06-14T19:00:00" or plain "2026-06-14"
            return val[:10]
    return ""


def classify_round_by_date(date_str: str) -> str | None:
    """Map a YYYY-MM-DD date string to a round key using the official schedule."""
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


def fetch_vividseats_prices() -> tuple[dict | None, str]:
    """
    Call VividSeats internal API directly (no Apify, no key needed).
    Tries multiple known endpoint patterns; returns (tiers, source) or (None, reason).
    """
    print("🎟️  Fetching VividSeats prices (direct API)…")

    # VividSeats uses different internal API paths across app versions.
    # We try them in order until one returns WC productions.
    ENDPOINTS = [
        f"{VIVIDSEATS_API}/productions?performerIds={WC_PERFORMER_ID}&pageSize=200",
        f"{VIVIDSEATS_API}/productions?performerId={WC_PERFORMER_ID}&pageSize=200",
        f"https://www.vividseats.com/api/v2/productions?performerId={WC_PERFORMER_ID}&rows=200",
        f"https://www.vividseats.com/api/productions?performerId={WC_PERFORMER_ID}&pageSize=200",
    ]

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.vividseats.com/",
    }

    raw_productions = None
    used_endpoint   = None

    for endpoint in ENDPOINTS:
        try:
            req = urllib.request.Request(endpoint, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
            # Response may be a list or {"productions": [...]} or {"data": [...]}
            prods = (
                data if isinstance(data, list)
                else data.get("productions") or data.get("data") or data.get("events") or []
            )
            if prods:
                raw_productions = prods
                used_endpoint   = endpoint
                print(f"   ✅ Got {len(prods)} productions from {endpoint.split('?')[0]}")
                break
            else:
                print(f"   ⚠️  {endpoint.split('?')[0]} → empty list, trying next…")
        except Exception as exc:
            print(f"   ⚠️  {endpoint.split('?')[0]} → {exc}, trying next…")

    if not raw_productions:
        print("   ❌ All VividSeats endpoints failed.")
        return None, "vividseats-unreachable"

    # Debug: show first item's keys and a few sample items
    if raw_productions:
        print(f"   Sample keys: {list(raw_productions[0].keys())[:12]}")
        print("   ── First 3 productions ──")
        for p in raw_productions[:3]:
            date = _extract_date(p)
            low, median, high = _extract_price(p)
            print(f"     {_extract_title(p)!r:55s}  date={date}  "
                  f"low={low}  high={high}")
        print("   ────────────────────────")

    # Bucket by round using date ranges
    buckets: dict[str, list] = {k: [] for k in ROUND_DATE_RANGES}
    skipped = 0
    for prod in raw_productions:
        date = _extract_date(prod)
        tier = classify_round_by_date(date) or classify_round_by_name(_extract_title(prod))
        if not tier:
            skipped += 1
            continue
        low, median, high = _extract_price(prod)
        if low and low > 0:
            buckets[tier].append({"low": low, "median": median, "high": high})

    print(f"   {skipped} productions outside WC date range (skipped)")

    tiers = {}
    for tier, rows in buckets.items():
        if rows:
            lows    = sorted(r["low"]    for r in rows if r["low"])
            medians = [r["median"] for r in rows if r["median"]]
            highs   = [r["high"]   for r in rows if r["high"]]
            tiers[tier] = {
                "low":    int(lows[0]),
                "median": int(sum(medians) / len(medians)) if medians else int(lows[len(lows)//2]),
                "high":   int(max(highs)) if highs else int(lows[-1]),
                "sample": len(rows),
            }
            print(f"   {tier:6s}: ${tiers[tier]['low']}–${tiers[tier]['median']}–"
                  f"${tiers[tier]['high']}  ({len(rows)} events)")
        else:
            tiers[tier] = FALLBACK_TIERS[tier]
            print(f"   {tier:6s}: no data — using placeholder")

    return tiers, "VividSeats (direct)"


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
                "low":    int(min(lows))           if lows  else FALLBACK_TIERS[tier]["low"],
                "median": int(sum(avgs)/len(avgs)) if avgs  else FALLBACK_TIERS[tier]["median"],
                "high":   int(max(highs))          if highs else FALLBACK_TIERS[tier]["high"],
                "sample": len(rows),
            }
            print(f"   {tier:6s}: ${tiers[tier]['low']}–${tiers[tier]['median']}–${tiers[tier]['high']}  ({len(rows)} events)")
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

    # Try VividSeats via Apify first; fall back to SeatGeek if unavailable
    tiers, ticket_source = fetch_vividseats_prices()
    if tiers is None:
        print(f"   ⚠️  VividSeats unavailable ({ticket_source}) — trying SeatGeek…")
        tiers, ticket_source = fetch_ticket_prices()

    # Hotel prices: reuse cached data if fresh enough
    if hotels_are_fresh(existing):
        hotels      = existing.get("hotels", {})
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
        "last_updated":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hotels_fetched_at": fetched_at,
        "ticket_source":   ticket_source,
        "hotel_source":    hotel_source,
        "tiers":           tiers,
        "hotels":          hotels,
    }

    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\n✅ Wrote prices to {OUTPUT_PATH}")
    print(f"   Tickets: {ticket_source}")
    print(f"   Hotels:  {hotel_source}")
    print(f"   Updated: {output['last_updated']}")


if __name__ == "__main__":
    main()
