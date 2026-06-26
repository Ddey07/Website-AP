#!/usr/bin/env python3
"""
FIFA World Cup 2026 — Live Elo / strength / results updater
===========================================================
Keeps the bracket predictor (static/wc2026/index.html) in sync with the real
tournament. Run every 2 hours by .github/workflows/update-wc-live.yml. Pushing
the regenerated data file triggers a Netlify rebuild (Hugo copies static/ ->
public/), so every tab — Champion Odds, Round of 32/16, QF, SF, Final, the 3rd
Place Race — re-projects from the latest ratings and results on the next load.

WHAT IT DOES EACH RUN
  1. Live Elo  : fetch eloratings.net/World.tsv -> Elo for the 48 WC teams.
                 strength = liveElo + FORM_WEIGHT * annualChange  ("form + live Elo").
  2. Results   : fetch finished matches from TheSportsDB and MERGE them into the
                 authoritative store scripts/wc_results.json (accumulates history).
  3. Standings : for any group whose 6 matches are all known, recompute the table
                 with the FULL official FIFA tie-break (incl. head-to-head). Groups
                 that aren't complete in the feed keep scripts/wc_standings.json.
  4. Knockouts : every finished KO match becomes a {pair -> winner} entry so the
                 engine pins it (the bracket shows the real winner, simulates the rest).
  5. Emit      : static/wc2026/wc_live.js  (window.WC_LIVE = {...}) + wc_live.json.

DATA SOURCES
  Elo      https://www.eloratings.net/World.tsv          (no key, tab-separated)
  Results  https://www.thesportsdb.com/api/v1/json/<KEY>/eventsround.php
           THESPORTSDB_KEY env var. The free key "3" caps responses at 5 rows;
           a Patreon premium key returns full rounds. Either way wc_results.json
           accumulates whatever finished matches each run can see.

TIE-BREAKS (official 2026 rules)
  Group   : pts -> H2H(pts,GD,GF among tied, re-applied) -> overall GD -> overall GF
            -> fair play (not modelled) -> FIFA ranking (June 11 2026).
  3rd place: pts -> GD -> GF -> fair play (not modelled) -> FIFA ranking.

RUN
  python scripts/update_wc_live.py
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ELO_URL = "https://www.eloratings.net/World.tsv"
TSDB_KEY = os.environ.get("THESPORTSDB_KEY") or "3"  # "3" = free/limited; set a premium key for full data
TSDB_LEAGUE = "4429"   # FIFA World Cup on TheSportsDB
TSDB_SEASON = "2026"

FORM_WEIGHT = 0.33  # strength = liveElo + FORM_WEIGHT * annualChange

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "static" / "wc2026"
SCRIPTS = Path(__file__).resolve().parent
STANDINGS_FILE = SCRIPTS / "wc_standings.json"
RESULTS_FILE = SCRIPTS / "wc_results.json"

# eloratings.net code -> exact team name used in index.html
CODE_TO_NAME = {
    "MX": "Mexico", "ZA": "South Africa", "KR": "South Korea", "CZ": "Czechia",
    "CA": "Canada", "BA": "Bosnia-Herz.", "QA": "Qatar", "CH": "Switzerland",
    "BR": "Brazil", "MA": "Morocco", "HT": "Haiti", "SQ": "Scotland",
    "US": "USA", "PY": "Paraguay", "AU": "Australia", "TR": "Turkey",
    "DE": "Germany", "CW": "Curacao", "CI": "Ivory Coast", "EC": "Ecuador",
    "NL": "Netherlands", "JP": "Japan", "SE": "Sweden", "TN": "Tunisia",
    "BE": "Belgium", "EG": "Egypt", "IR": "Iran", "NZ": "New Zealand",
    "ES": "Spain", "CV": "Cape Verde", "SA": "Saudi Arabia", "UY": "Uruguay",
    "FR": "France", "SN": "Senegal", "IQ": "Iraq", "NO": "Norway",
    "AR": "Argentina", "DZ": "Algeria", "AT": "Austria", "JO": "Jordan",
    "CO": "Colombia", "PT": "Portugal", "CD": "DR Congo", "UZ": "Uzbekistan",
    "EN": "England", "HR": "Croatia", "GH": "Ghana", "PA": "Panama",
}

# TheSportsDB team name -> site team name (only the ones that differ).
TSDB_NORMALIZE = {
    "Czech Republic": "Czechia", "Bosnia-Herzegovina": "Bosnia-Herz.",
    "Bosnia and Herzegovina": "Bosnia-Herz.", "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast", "Ivory Coast": "Ivory Coast",
    "Congo DR": "DR Congo", "DR Congo": "DR Congo", "Curaçao": "Curacao",
    "Cabo Verde": "Cape Verde", "United States": "USA", "South Korea": "South Korea",
}

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia-Herz.", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}
TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}


def _num(s):
    s = str(s).strip().replace("−", "-").replace("+", "")
    return int(s) if s and s not in ("-", "–") else 0


# ---------------------------------------------------------------- live Elo ----
def fetch_elo():
    req = urllib.request.Request(ELO_URL, headers={"User-Agent": "wc2026-updater/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    out = {}
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) < 16:
            continue
        name = CODE_TO_NAME.get(f[2].strip())
        if not name:
            continue
        try:
            out[name] = {"elo": _num(f[3]), "change": _num(f[15])}
        except ValueError:
            continue
    missing = [c for c in CODE_TO_NAME.values() if c not in out]
    if missing:
        raise RuntimeError(f"Missing {len(missing)} teams from Elo feed: {missing}")
    return out


def compute_strength(elo_map):
    return {n: round(d["elo"] + FORM_WEIGHT * d["change"]) for n, d in elo_map.items()}


# ------------------------------------------------------------ live results ----
def _norm_team(name):
    return TSDB_NORMALIZE.get(name, name)


def fetch_results():
    """Pull finished matches from TheSportsDB. Returns a list of dicts:
    {id, teamA, teamB, scoreA, scoreB, round, stage}. Group matches -> stage
    'group'; everything else -> 'ko'. Best-effort: a limited key just returns
    fewer rows, which the caller merges into the accumulated store."""
    seen, matches = set(), []
    # Group matchdays are rounds 1-3; knockout rounds follow. Query a generous span.
    rounds = ["1", "2", "3", "4", "5", "6", "7", "8",
              "125", "150", "160", "170", "180", "200"]  # TSDB KO round codes vary; harmless if empty
    for r in rounds:
        url = (f"https://www.thesportsdb.com/api/v1/json/{TSDB_KEY}"
               f"/eventsround.php?id={TSDB_LEAGUE}&r={r}&s={TSDB_SEASON}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wc2026-updater/1.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001 — a missing/empty round is fine
            continue
        for e in (data.get("events") or []):
            if e.get("strStatus") != "FT":
                continue
            if e.get("intHomeScore") in (None, "") or e.get("intAwayScore") in (None, ""):
                continue
            eid = e.get("idEvent")
            if eid in seen:
                continue
            seen.add(eid)
            a, b = _norm_team(e["strHomeTeam"]), _norm_team(e["strAwayTeam"])
            rnd = e.get("intRound", "")
            matches.append({
                "id": eid, "teamA": a, "teamB": b,
                "scoreA": int(e["intHomeScore"]), "scoreB": int(e["intAwayScore"]),
                "round": rnd,
                "stage": "group" if rnd in ("1", "2", "3") else "ko",
            })
    return matches


def _match_key(m):
    """Identity of a match independent of data source: stage + the two teams.
    Each pair meets at most once per stage, so this safely dedupes the hand-
    entered results against anything the live feed returns for the same game."""
    return (m.get("stage", "group"), tuple(sorted([m["teamA"], m["teamB"]])))


def merge_results(fetched):
    """Merge newly-finished matches into the persistent wc_results.json store,
    keyed by match identity (not event id) so the feed never duplicates a game
    that's already recorded. Returns the full accumulated list."""
    store = {}
    if RESULTS_FILE.exists():
        try:
            for m in json.loads(RESULTS_FILE.read_text()):
                store[_match_key(m)] = m
        except (ValueError, OSError):
            store = {}
    for m in fetched:
        store[_match_key(m)] = m  # a finished feed result refreshes the stored one
    merged = sorted(store.values(), key=lambda m: (m.get("stage", ""), m["teamA"], m["teamB"]))
    RESULTS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    return merged


# --------------------------------------------------- FIFA group tie-breaks ----
def _mini_table(teams, games):
    pts = {t: 0 for t in teams}
    gd = {t: 0 for t in teams}
    gf = {t: 0 for t in teams}
    for a, b, sa, sb in games:
        if a not in teams or b not in teams:
            continue
        gf[a] += sa; gf[b] += sb
        gd[a] += sa - sb; gd[b] += sb - sa
        if sa > sb: pts[a] += 3
        elif sb > sa: pts[b] += 3
        else: pts[a] += 1; pts[b] += 1
    return pts, gd, gf


def rank_group(teams, games, fifa_rank):
    """Official 2026 group classification. `games` = [(a,b,sa,sb), ...] for the
    whole group. Returns the ordered list of teams (best first)."""
    overall_pts, overall_gd, overall_gf = _mini_table(teams, games)

    def resolve(group):
        """Order a set of teams that are tied on the criterion above this call."""
        if len(group) == 1:
            return group
        # Criteria a-c: head-to-head among exactly the tied teams.
        h2h_games = [g for g in games if g[0] in group and g[1] in group]
        hp, hgd, hgf = _mini_table(group, h2h_games)
        buckets = {}
        for t in group:
            buckets.setdefault((hp[t], hgd[t], hgf[t]), []).append(t)
        if len(buckets) > 1:
            ordered = []
            for key in sorted(buckets, reverse=True):
                sub = buckets[key]
                # If H2H separated this sub-bucket fully, recurse on the smaller
                # tie (re-apply a-c); else fall through to overall criteria.
                ordered.extend(resolve(sub) if len(sub) < len(group) else _by_overall(sub))
            return ordered
        # H2H did not separate anyone -> overall criteria d-h.
        return _by_overall(group)

    def _by_overall(group):
        return sorted(
            group,
            key=lambda t: (-overall_pts[t], -overall_gd[t], -overall_gf[t],
                           fifa_rank.get(t, 999)),
        )

    # Top level: bucket by overall points, then resolve ties within each bucket.
    by_pts = {}
    for t in teams:
        by_pts.setdefault(overall_pts[t], []).append(t)
    result = []
    for p in sorted(by_pts, reverse=True):
        result.extend(resolve(by_pts[p]))
    return result


def standings_from_results(results, fifa_rank, fallback):
    """Build standings per group. Recompute a group from results ONLY when all 6
    of its matches are present (so partial feeds never corrupt a table); else use
    the authoritative `fallback` (wc_standings.json) entry unchanged."""
    standings = dict(fallback or {})
    by_group = {g: [] for g in GROUPS}
    for m in results:
        if m.get("stage") != "group":
            continue
        g = TEAM_GROUP.get(m["teamA"])
        if g and TEAM_GROUP.get(m["teamB"]) == g:
            by_group[g].append((m["teamA"], m["teamB"], int(m["scoreA"]), int(m["scoreB"])))
    for g, games in by_group.items():
        if len(games) < 6:
            continue  # incomplete in the feed -> keep authoritative table
        teams = GROUPS[g]
        pts, gd, gf = _mini_table(teams, games)
        order = rank_group(teams, games, fifa_rank)
        standings[g] = {
            "md": 3, "pts": pts, "gd": gd, "gf": gf,
            "clinched": order[:2], "ranked4th": order[3], "order": order,
        }
    return standings


def attach_group_matches(standings, results):
    """Attach each group's played match results as `matches` = [[a,b,ga,gb],...]
    so the browser engine can apply the official head-to-head tie-break. Only
    games between two teams of the same group are included."""
    by_group = {g: [] for g in GROUPS}
    for m in results:
        if m.get("stage") != "group":
            continue
        g = TEAM_GROUP.get(m["teamA"])
        if g and TEAM_GROUP.get(m["teamB"]) == g:
            by_group[g].append([m["teamA"], m["teamB"], int(m["scoreA"]), int(m["scoreB"])])
    for g, games in by_group.items():
        if games and g in standings:
            standings[g]["matches"] = games
    return standings


def ko_results(results):
    """{ 'TeamA|TeamB' (sorted) -> winner } for every finished knockout match."""
    out = {}
    for m in results:
        if m.get("stage") != "ko":
            continue
        a, b, sa, sb = m["teamA"], m["teamB"], int(m["scoreA"]), int(m["scoreB"])
        if sa == sb:
            continue  # KO draws are decided on penalties; the feed's winner field
                      # would be needed — skip until scores reflect the decision.
        out["|".join(sorted([a, b]))] = a if sa > sb else b
    return out


# ---------------------------------------------------------------------- main --
def main():
    elo_map = fetch_elo()
    elo = {n: d["elo"] for n, d in elo_map.items()}
    change = {n: d["change"] for n, d in elo_map.items()}
    strength = compute_strength(elo_map)

    fifa_rank, fallback_standings = {}, None
    if STANDINGS_FILE.exists():
        sdata = json.loads(STANDINGS_FILE.read_text())
        fifa_rank = sdata.get("fifaRank", {})
        fallback_standings = sdata.get("standings")

    try:
        fetched = fetch_results()
    except Exception as e:  # noqa: BLE001
        print(f"WARN: results fetch failed ({e}); using stored results only", file=sys.stderr)
        fetched = []
    results = merge_results(fetched) if (fetched or RESULTS_FILE.exists()) else []

    standings = standings_from_results(results, fifa_rank, fallback_standings)
    attach_group_matches(standings, results)
    ko = ko_results(results)

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "eloratings.net/World.tsv + thesportsdb.com",
        "formWeight": FORM_WEIGHT,
        "elo": elo, "eloChange": change, "strength": strength,
    }
    if standings:
        payload["standings"] = standings
    if fifa_rank:
        payload["fifaRank"] = fifa_rank
    if ko:
        payload["koResults"] = ko

    json_path = OUT_DIR / "wc_live.json"
    if json_path.exists():
        try:
            prev = json.loads(json_path.read_text())
            cmp_keys = ("elo", "eloChange", "strength", "standings", "fifaRank",
                        "koResults", "formWeight")
            if all(prev.get(k) == payload.get(k) for k in cmp_keys):
                print("No change in ratings/results — wc_live.js left untouched.")
                return
        except (ValueError, OSError):
            pass

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    (OUT_DIR / "wc_live.js").write_text(
        "/* Auto-generated by scripts/update_wc_live.py — do not edit by hand. */\n"
        "window.WC_LIVE=" + json.dumps(payload, ensure_ascii=False) + ";\n"
    )
    print(f"Wrote wc_live.js/json — {len(elo)} teams, "
          f"{len(results)} stored matches, {len(ko)} KO results, "
          f"updated {payload['updated']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
