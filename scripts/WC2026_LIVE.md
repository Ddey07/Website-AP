# WC2026 live pipeline

Keeps the bracket predictor tracking the real tournament — live Elo **and** match
results — so every tab (Champion Odds, Round of 32/16, QF, SF, Final, 3rd Place
Race) re-projects from the latest data on each page load. No edits to the
4,700-line `index.html` are needed once it's wired.

## Flow

```
eloratings.net/World.tsv ─┐
                          ├─▶ scripts/update_wc_live.py ─▶ static/wc2026/wc_live.js
thesportsdb.com (results) ┘        (every 2h via GitHub Action)   (window.WC_LIVE)
                                          │                              │
                          scripts/wc_results.json (accumulates)         ▼
                          scripts/wc_standings.json (authoritative)  index.html overrides
                                                          ELO / STRENGTH / LIVE_STANDINGS /
                                                          FIFA_TIEBREAK / KO_RESULTS
```

Commit → Netlify rebuild (Hugo copies `static/` → `public/`). If `wc_live.js`
ever fails to load, the page falls back to its hardcoded snapshot.

## 1. Ratings (always automatic)

```
strength(team) = liveElo + FORM_WEIGHT * annualChange      # FORM_WEIGHT = 0.33
```
Live Elo from eloratings.net plus a third of the team's last-year momentum. Host
home advantage is applied per match in the page's `wp()`, not here.

## 2. Results → standings (drives all bracket tabs)

`update_wc_live.py` fetches finished matches from TheSportsDB and merges them into
`scripts/wc_results.json` (keyed by event id; accumulates over runs). Then:

- **Group stage** — a group's table is recomputed from results **only when all 6
  of its matches are known**, using the full official tie-break:
  Points → head-to-head (pts/GD/GF among the tied teams, re-applied) → overall GD
  → overall GF → fair play *(not modelled)* → FIFA ranking (June 11 2026).
  Until a group is complete in the feed it keeps the authoritative table in
  `scripts/wc_standings.json`, so a partial feed can never corrupt a standing.
- **Knockouts** — every finished KO match becomes a `"TeamA|TeamB" -> winner`
  entry (`koResults`). The engine **pins** it: that match shows the real winner
  and only the remaining matches are simulated. As R32 results land, R16/QF/SF/
  Final and the champion odds all re-weight automatically.

Because the browser re-runs the Monte Carlo from `standings + elo + koResults`
on every load, updating those inputs updates **every** tab.

### TheSportsDB key

`THESPORTSDB_KEY` (GitHub Action secret). The free key `"3"` works but caps each
response at ~5 rows; a [TheSportsDB Patreon](https://www.thesportsdb.com/) premium
key returns full rounds. Either way `wc_results.json` accumulates what each run
sees, and you can hand-edit it (or `wc_standings.json`) directly.

## 3. Tie-break data

`fifaRank` in `wc_standings.json` is the FIFA-ranking tie-breaker (lower = better).
Replace it with the **June 11 2026** release when available. Fair-play scores need
per-match card data that no free feed exposes — that single criterion is skipped
(falls through to FIFA ranking).

## 4. Bracket-challenge leaderboard (auto-scored)

`scripts/push_results_supabase.py` turns the standings + KO results into the
`results`-table rows the scorer expects and calls the public RPCs
`upsert_result` + `calculate_scores` (callable with the anon key — no service
secret). KO matches are mapped to bracket slots via the official 495 table
(`scripts/wc_combo495.py`), so exact-slot and matchup points score correctly.
The Action runs it every 2h, so user scores update as results come in.

```
python scripts/push_results_supabase.py          # dry run — prints the rows
python scripts/push_results_supabase.py --push    # write + rescore
```
Optional GitHub secrets `SUPABASE_URL` / `SUPABASE_ANON_KEY` override the
defaults (which already match the site).

## 5. Monte Carlo benchmark on the leaderboard

`scripts/generate_mc_bracket.py` builds the model's **pre-tournament** bracket
from `PRIOR_PROBS` + the group projections and writes `static/wc2026/mc_bracket.js`.
The leaderboard scores it **client-side** against the live `results` table (same
rules as the DB scorer) and shows it as a `🤖 … BENCHMARK` row — no database
write, updates automatically as results come in. It's pre-tournament, so
generate it once (re-run only if you change the prior model):

```
python scripts/generate_mc_bracket.py
```

## Run manually

```
python scripts/update_wc_live.py         # ratings + results -> wc_live.js (only if changed)
python scripts/push_results_supabase.py  # rescore the leaderboard (add --push to write)
```
The first two run every 2h and on demand from the repo's **Actions** tab.
