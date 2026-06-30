#!/usr/bin/env python3
"""
Push actual WC2026 results into Supabase and rescore the bracket-challenge
leaderboard — so user scores update as group standings and knockout results
come in.

It reads the data produced by update_wc_live.py (static/wc2026/wc_live.json +
scripts/wc_results.json), converts it into the `results` table rows the scoring
function expects, and calls the public RPCs:

    upsert_result(p_round, p_slot_idx, p_team, p_opponent)   # one row per result
    calculate_scores()                                       # recompute leaderboard

Both RPCs are SECURITY DEFINER and callable with the anon key (the same key the
site already ships), so no service-role secret is required.

ROWS PRODUCED
  grp1  slot 0-11 (A=0..L=11)  team = group winner            (group complete)
  grp2  slot 0-11              team = group runner-up          (group complete)
  grpT  slot 0-7               team = "G:Team" best-8 thirds   (all 12 complete)
  r32..final  slot = KO index  team = winner, opponent = loser (per played match)

KO matches are mapped to bracket slots from the final group standings using the
official FIFA 495 third-place table (scripts/wc_combo495.py). Each KO pairing is
unique, so results are matched by their two teams regardless of round labelling.

SAFETY
  Dry-run by default — prints the rows it WOULD push. Pass --push (or set
  SUPABASE_PUSH=1) to actually write and rescore.

RUN
  python scripts/push_results_supabase.py            # dry run
  python scripts/push_results_supabase.py --push     # write + rescore
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wc_combo495 import COMBO495, SLOT_ORDER_495  # noqa: E402

# Use `or` (not get's default) so an empty GitHub secret falls back to the public
# values below — an unset secret arrives as "" in the Action, not as absent.
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://cfnlnksqnmtscchtugtd.supabase.co"
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY") or (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmbmxua3Nxbm10c2NjaHR1Z3RkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg5MzM0MzIsImV4cCI6MjA5NDUwOTQzMn0.9HgzuCdTQ61BQY8LsY1KI7vlvypQY4anWBRDVHzbkE4"
)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
LIVE_JSON = ROOT / "static" / "wc2026" / "wc_live.json"
RESULTS_FILE = SCRIPTS / "wc_results.json"
STANDINGS_FILE = SCRIPTS / "wc_standings.json"

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
GROUP_IDX = {g: i for i, g in enumerate("ABCDEFGHIJKL")}

# R32 bracket: each slot's two feeders. "WX"=winner grp X, "RX"=runner-up grp X,
# "TXX"=third placed in the M-slot key. Mirrors KO.r32 / runOnce() in index.html.
R32_FEEDERS = [
    ("W:E", "T:M74"), ("W:I", "T:M77"), ("R:A", "R:B"), ("W:F", "R:C"),
    ("R:K", "R:L"), ("W:H", "R:J"), ("W:D", "T:M81"), ("W:G", "T:M82"),
    ("W:C", "R:F"), ("R:E", "R:I"), ("W:A", "T:M79"), ("W:L", "T:M80"),
    ("W:J", "R:H"), ("R:D", "R:G"), ("W:B", "T:M85"), ("W:K", "T:M87"),
]


def load_standings():
    """Prefer the results-derived standings in wc_live.json (with 'order' and
    head-to-head); fall back to the authoritative wc_standings.json."""
    if LIVE_JSON.exists():
        d = json.loads(LIVE_JSON.read_text())
        if d.get("standings"):
            return d["standings"], d.get("fifaRank", {})
    s = json.loads(STANDINGS_FILE.read_text())
    return s["standings"], s.get("fifaRank", {})


def group_order(g, entry, fifa_rank):
    """Final 1st->4th order for a group. Uses the authoritative 'order' if the
    updater computed it (full FIFA incl. head-to-head); else ranks by
    pts -> GD -> GF -> FIFA position from the aggregate table."""
    if entry.get("order"):
        return entry["order"]
    teams = GROUPS[g]
    pts, gd, gf = entry["pts"], entry["gd"], entry["gf"]
    return sorted(teams, key=lambda t: (-pts[t], -gd[t], -gf[t], fifa_rank.get(t, 999)))


def best_eight_thirds(standings, fifa_rank):
    """The 8 qualifying third-placed teams (3rd place tie-break: pts->GD->GF->FIFA).
    Returns list of (group, team) or None if not all 12 groups are complete."""
    thirds = []
    for g in GROUPS:
        e = standings.get(g)
        if not e or e.get("md", 0) < 3:
            return None
        t = group_order(g, e, fifa_rank)[2]
        thirds.append((g, t, e["pts"][t], e["gd"][t], e["gf"][t]))
    thirds.sort(key=lambda x: (-x[2], -x[3], -x[4], fifa_rank.get(x[1], 999)))
    return [(g, t) for g, t, *_ in thirds[:8]]


def r32_matchups(standings, fifa_rank):
    """Return {slot_idx: (teamA, teamB)} for the Round of 32, or None if the
    bracket isn't fully determined yet (group stage incomplete)."""
    if any(standings.get(g, {}).get("md", 0) < 3 for g in GROUPS):
        return None
    winners, runners = {}, {}
    for g in GROUPS:
        order = group_order(g, standings[g], fifa_rank)
        winners[g], runners[g] = order[0], order[1]
    thirds = best_eight_thirds(standings, fifa_rank)
    if not thirds:
        return None
    key = "".join(sorted(g for g, _ in thirds))
    enc = COMBO495.get(key)
    if not enc:
        return None
    third_by_group = {g: t for g, t in thirds}
    third_by_slot = {SLOT_ORDER_495[i]: third_by_group[enc[i]] for i in range(8)}

    def resolve(tok):
        kind, ref = tok.split(":")
        if kind == "W":
            return winners[ref]
        if kind == "R":
            return runners[ref]
        return third_by_slot[ref]  # kind == "T", ref like "M74"

    return {i: (resolve(a), resolve(b)) for i, (a, b) in enumerate(R32_FEEDERS)}


def ko_pairs(results):
    """{ frozenset({a,b}) -> (winner, loser) } for finished KO matches.

    Draws are decided on penalties and carry an explicit `winner` field.
    """
    out = {}
    for m in results:
        if m.get("stage") != "ko":
            continue
        a, b, sa, sb = m["teamA"], m["teamB"], int(m["scoreA"]), int(m["scoreB"])
        win = m.get("winner")
        if sa == sb and not win:
            continue
        if win:
            w, l = (win, b if win == a else a)
        else:
            w, l = (a, b) if sa > sb else (b, a)
        out[frozenset((a, b))] = (w, l)
    return out


def build_rows(standings, fifa_rank, results):
    """Produce the full list of (round, slot_idx, team, opponent) results rows."""
    rows = []
    # Group stage (only for completed groups)
    for g in GROUPS:
        e = standings.get(g)
        if not e or e.get("md", 0) < 3:
            continue
        order = group_order(g, e, fifa_rank)
        rows.append(("grp1", GROUP_IDX[g], order[0], None))
        rows.append(("grp2", GROUP_IDX[g], order[1], None))
    thirds = best_eight_thirds(standings, fifa_rank)
    if thirds:
        for i, (g, t) in enumerate(thirds):
            rows.append(("grpT", i, f"{g}:{t}", None))

    # Knockouts — map each finished match to its bracket slot, level by level.
    pairs = ko_pairs(results)
    r32 = r32_matchups(standings, fifa_rank)
    if not r32 or not pairs:
        return rows

    def emit_round(round_name, matchups):
        winners = {}
        for idx, (a, b) in matchups.items():
            if not a or not b:
                continue
            res = pairs.get(frozenset((a, b)))
            if res:
                w, l = res
                rows.append((round_name, idx, w, l))
                winners[idx] = w
        return winners

    w32 = emit_round("r32", r32)
    r16 = {i: (w32.get(2 * i), w32.get(2 * i + 1)) for i in range(8)}
    w16 = emit_round("r16", r16)
    qf = {i: (w16.get(2 * i), w16.get(2 * i + 1)) for i in range(4)}
    wqf = emit_round("qf", qf)
    sf = {i: (wqf.get(2 * i), wqf.get(2 * i + 1)) for i in range(2)}
    wsf = emit_round("sf", sf)
    fin = {0: (wsf.get(0), wsf.get(1))}
    emit_round("final", fin)
    return rows


def rpc(name, body):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/rpc/{name}",
        data=json.dumps(body).encode(),
        headers={
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


# ── Leaderboard scoring (computed here, then written via replace_scores) ──────
# Rules mirror static/wc2026/index.html and the published "How scoring works":
#   Group: winner 3, runner-up 2, third 2.
#   KO   : trajectory (your pick won its match), exact slot (right winner in the
#          right bracket position), matchup (you PREDICTED these two teams to
#          face each other — i.e. your bracket pairs them — and they did).
#   Final: winner 10, either finalist 25.  Champion bonus: +10.
# The matchup tier is the "predicted the pairing" definition (your group/KO
# picks actually stage that fixture), NOT merely having both teams alive.
KO_PTS = {"r32": (2, 5, 3), "r16": (3, 8, 5), "qf": (4, 13, 8), "sf": (6, 18, 11)}
PREV_ROUND = {"r16": "r32", "qf": "r16", "sf": "qf"}
# Site-error compensations (mirror score_compensations / SCORE_COMPENSATIONS):
# (display_name, r32 slot, wrongly-shown pick) -> team to score instead (group winner).
COMPENSATIONS = {
    ("Rokkekoro", 10, "Sweden"): "South Korea",
    ("Tetsu", 6, "Senegal"): "Turkey",
    ("raeesbhai", 10, "Senegal"): "Mexico",
    ("Yellowstone", 10, "Ecuador"): "Mexico",
}


def _get(table, select="*"):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?select={select}&limit=100000",
        headers={"apikey": SUPABASE_ANON_KEY,
                 "Authorization": f"Bearer {SUPABASE_ANON_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _user_third_slots(grpt_list):
    """A user's predicted thirds ("G:Team") assigned to R32 third-slots via the
    official FIFA 495 table — exactly how their own bracket places them."""
    thirds = [(e.split(":", 1)[0], e.split(":", 1)[1]) for e in grpt_list if ":" in e]
    enc = COMBO495.get("".join(sorted(set(g for g, _ in thirds))))
    out = {}
    if enc:
        for i in range(8):
            out[SLOT_ORDER_495[i]] = next((tm for g, tm in thirds if g == enc[i]), None)
    return out


def _user_r32_pairs(b):
    """{slot_idx: (teamA, teamB)} the user predicted to meet in each R32 match."""
    ta = _user_third_slots(b["grpT"])

    def resolve(spec):
        kind, key = spec.split(":")
        if kind == "W":
            return b["grp1"].get(GROUP_IDX[key])
        if kind == "R":
            return b["grp2"].get(GROUP_IDX[key])
        return ta.get(key)  # "T:M74" -> the third assigned to M74

    return {i: (resolve(f1), resolve(f2)) for i, (f1, f2) in enumerate(R32_FEEDERS)}


def compute_scores(rows, predictions, profiles):
    """Return [{user_id, round, points}] from result rows + everyone's picks."""
    id2name = {p["id"]: p.get("display_name") for p in profiles}
    Rg = {"grp1": {}, "grp2": {}, "grpT": set()}
    Rk = {"r32": [], "r16": [], "qf": [], "sf": [], "final": []}
    for rnd, idx, team, opp in rows:
        if rnd in ("grp1", "grp2"):
            Rg[rnd][idx] = team
        elif rnd == "grpT":
            Rg["grpT"].add(team)
        elif rnd in Rk:
            Rk[rnd].append((idx, team, opp))

    B = defaultdict(lambda: {"grp1": {}, "grp2": {}, "grpT": [],
                             "r32": {}, "r16": {}, "qf": {}, "sf": {}, "final": {}})
    for p in predictions:
        u, rnd = p["user_id"], p["round"]
        if rnd == "grpT":
            B[u]["grpT"].append(p["picked_team"])
        elif rnd in B[u]:
            B[u][rnd][p["slot_idx"]] = p["picked_team"]

    out = []
    for u, b in B.items():
        name = id2name.get(u)
        if Rg["grp1"]:
            out.append({"user_id": u, "round": "grp1",
                        "points": sum(3 for s, t in b["grp1"].items() if Rg["grp1"].get(s) == t)})
        if Rg["grp2"]:
            out.append({"user_id": u, "round": "grp2",
                        "points": sum(2 for s, t in b["grp2"].items() if Rg["grp2"].get(s) == t)})
        if Rg["grpT"]:
            out.append({"user_id": u, "round": "grpT",
                        "points": sum(2 for e in b["grpT"] if e in Rg["grpT"])})
        pairs = _user_r32_pairs(b)
        for rnd in ("r32", "r16", "qf", "sf"):
            rr = Rk[rnd]
            if not rr:
                continue
            tp, sp, mp = KO_PTS[rnd]
            picks = dict(b[rnd])
            if rnd == "r32":  # apply site-error compensation to affected picks
                for s, t in list(picks.items()):
                    repl = COMPENSATIONS.get((name, s, t))
                    if repl:
                        picks[s] = repl
            pset = set(picks.values())
            pts = 0
            for idx, team, opp in rr:
                if team in pset:
                    pts += tp                       # trajectory
                if picks.get(idx) == team:
                    pts += sp                       # exact slot
                if rnd == "r32":
                    pp = {x for x in pairs.get(idx, (None, None)) if x}
                else:
                    prev = b[PREV_ROUND[rnd]]
                    pp = {x for x in (prev.get(idx * 2), prev.get(idx * 2 + 1)) if x}
                if pp == {team, opp}:
                    pts += mp                        # matchup (predicted the pairing)
            out.append({"user_id": u, "round": rnd, "points": pts})
        if Rk["final"]:
            _, team, opp = Rk["final"][0]
            fp = b["final"].get(0)
            fpts = (10 if fp == team else 0) + (25 if fp in (team, opp) else 0)
            out.append({"user_id": u, "round": "final", "points": fpts})
            if fp == team:
                out.append({"user_id": u, "round": "champion", "points": 10})
    return out


def main():
    push = "--push" in sys.argv or os.environ.get("SUPABASE_PUSH") == "1"
    standings, fifa_rank = load_standings()
    results = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else []
    rows = build_rows(standings, fifa_rank, results)

    print(f"{len(rows)} result rows "
          f"({sum(1 for r in rows if r[0].startswith('grp'))} group, "
          f"{sum(1 for r in rows if not r[0].startswith('grp'))} knockout):")
    for rnd, idx, team, opp in rows:
        print(f"  {rnd:6} slot {idx:2}  {team}" + (f"  def. {opp}" if opp else ""))

    # Score everyone from the canonical result rows + their saved predictions.
    preds = _get("predictions", "user_id,round,slot_idx,picked_team")
    profiles = _get("profiles", "id,display_name")
    score_rows = compute_scores(rows, preds, profiles)
    by_user = defaultdict(int)
    for s in score_rows:
        by_user[s["user_id"]] += s["points"]
    id2name = {p["id"]: p.get("display_name") or p["id"][:8] for p in profiles}
    print(f"\nLeaderboard ({len(by_user)} scored, total {sum(by_user.values())} pts):")
    for uid, tot in sorted(by_user.items(), key=lambda x: -x[1]):
        print(f"  {tot:4d}  {id2name.get(uid, uid[:8])}")

    if not push:
        print("\nDry run — pass --push (or SUPABASE_PUSH=1) to write and rescore.")
        return
    for rnd, idx, team, opp in rows:
        rpc("upsert_result", {"p_round": rnd, "p_slot_idx": idx,
                              "p_team": team, "p_opponent": opp})
    print("Pushed results. Writing tightened scores…")
    print(rpc("replace_scores", {"p_rows": score_rows}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
