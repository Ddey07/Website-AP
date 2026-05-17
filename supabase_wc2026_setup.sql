-- ============================================================
-- WC 2026 Bracket Predictor — Supabase Database Setup
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================
-- TABLE OVERVIEW
--   results     : actual tournament outcomes (populate after each matchday)
--   scores      : per-user per-round points (populated by calculate_scores())
--   predictions : already exists (user submissions, read-only here)
--   profiles    : already exists (display names, ab_group)
-- ============================================================


-- ============================================================
-- STEP 1: CREATE TABLES
-- ============================================================

-- Drop and recreate results for a clean setup.
-- Safe to rerun — scores are recalculated from scratch each time.
DROP TABLE IF EXISTS results CASCADE;

CREATE TABLE results (
  round      text    NOT NULL,
  -- grp1  : actual group winner      (slot_idx = group A=0 … L=11)
  -- grp2  : actual group runner-up   (slot_idx = group A=0 … L=11)
  -- grpT  : actual qualifying thirds (slot_idx = 0–7, format "G:Team")
  -- r32   : R32 match winner         (slot_idx = KO.r32 array index 0–15)
  -- r16   : R16 match winner         (slot_idx = KO.r16 array index 0–7)
  -- qf    : QF match winner          (slot_idx = KO.qf  array index 0–3)
  -- sf    : SF match winner          (slot_idx = KO.sf  array index 0–1)
  -- final : Final winner             (slot_idx = 0)
  slot_idx   integer NOT NULL,
  team       text    NOT NULL,   -- the winning / qualifying team
  opponent   text,               -- KO only: the losing team (needed for matchup scoring)
  PRIMARY KEY (round, slot_idx)
);

-- Scores: one row per (user, round). Populated by calculate_scores().
-- Leaderboard reads: SELECT user_id, round, points FROM scores
CREATE TABLE IF NOT EXISTS scores (
  user_id  uuid    NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  round    text    NOT NULL,
  -- rounds: grp1 | grp2 | grpT | r32 | r16 | qf | sf | final | champion
  points   integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, round)
);


-- ============================================================
-- STEP 2: ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE results ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores  ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "results_public_read" ON results;
DROP POLICY IF EXISTS "scores_public_read"  ON scores;

-- Anyone (including anonymous visitors) can read results and scores.
-- Only service-role (backend / Edge Functions) can write.
CREATE POLICY "results_public_read" ON results FOR SELECT USING (true);
CREATE POLICY "scores_public_read"  ON scores  FOR SELECT USING (true);


-- ============================================================
-- STEP 3: DEMO DATA — RESULTS
-- Based on model-projected WC2026 outcomes.
-- Replace row-by-row as the real tournament progresses.
-- ============================================================

TRUNCATE results;

-- ── Group 1st place ──────────────────────────────────────
-- slot_idx matches group letter offset: A=0, B=1, C=2 … L=11
INSERT INTO results (round, slot_idx, team) VALUES
  ('grp1',  0, 'Mexico'),       -- Group A
  ('grp1',  1, 'Switzerland'),  -- Group B
  ('grp1',  2, 'Brazil'),       -- Group C
  ('grp1',  3, 'USA'),          -- Group D
  ('grp1',  4, 'Germany'),      -- Group E
  ('grp1',  5, 'Netherlands'),  -- Group F
  ('grp1',  6, 'Belgium'),      -- Group G
  ('grp1',  7, 'Spain'),        -- Group H
  ('grp1',  8, 'France'),       -- Group I
  ('grp1',  9, 'Argentina'),    -- Group J
  ('grp1', 10, 'Portugal'),     -- Group K
  ('grp1', 11, 'England');      -- Group L

-- ── Group 2nd place ──────────────────────────────────────
INSERT INTO results (round, slot_idx, team) VALUES
  ('grp2',  0, 'South Korea'),  -- Group A
  ('grp2',  1, 'Canada'),       -- Group B
  ('grp2',  2, 'Morocco'),      -- Group C
  ('grp2',  3, 'Turkey'),       -- Group D
  ('grp2',  4, 'Ecuador'),      -- Group E
  ('grp2',  5, 'Japan'),        -- Group F
  ('grp2',  6, 'Iran'),         -- Group G
  ('grp2',  7, 'Uruguay'),      -- Group H
  ('grp2',  8, 'Senegal'),      -- Group I
  ('grp2',  9, 'Austria'),      -- Group J
  ('grp2', 10, 'Colombia'),     -- Group K
  ('grp2', 11, 'Croatia');      -- Group L

-- ── Best 8 third-place qualifiers ────────────────────────
-- Format: "GROUP:Team"  — must match exactly how the frontend stores predictions
-- (thirdPicks saved as `${group}:${team}`, e.g. "E:Ivory Coast")
-- Groups A/B/C/D thirds are eliminated in this demo; E–L qualify.
INSERT INTO results (round, slot_idx, team) VALUES
  ('grpT', 0, 'E:Ivory Coast'),
  ('grpT', 1, 'F:Sweden'),
  ('grpT', 2, 'G:Egypt'),
  ('grpT', 3, 'H:Cape Verde'),
  ('grpT', 4, 'I:Norway'),
  ('grpT', 5, 'J:Algeria'),
  ('grpT', 6, 'K:DR Congo'),
  ('grpT', 7, 'L:Ghana');

-- ── Round of 32 ──────────────────────────────────────────
-- slot_idx follows the KO.r32 array order defined in index.html
-- opponent = the losing team (needed for matchup scoring)
INSERT INTO results (round, slot_idx, team, opponent) VALUES
  ('r32',  0, 'Germany',     'Sweden'),      -- M74: W-E  vs 3rd-F
  ('r32',  1, 'France',      'Cape Verde'),  -- M77: W-I  vs 3rd-H
  ('r32',  2, 'South Korea', 'Canada'),      -- M73: RU-A vs RU-B
  ('r32',  3, 'Netherlands', 'Morocco'),     -- M75: W-F  vs RU-C
  ('r32',  4, 'Colombia',    'Croatia'),     -- M83: RU-K vs RU-L
  ('r32',  5, 'Spain',       'Austria'),     -- M84: W-H  vs RU-J
  ('r32',  6, 'USA',         'Norway'),      -- M81: W-D  vs 3rd-I
  ('r32',  7, 'Belgium',     'Algeria'),     -- M82: W-G  vs 3rd-J
  ('r32',  8, 'Brazil',      'Japan'),       -- M76: W-C  vs RU-F
  ('r32',  9, 'Ecuador',     'Senegal'),     -- M78: RU-E vs RU-I
  ('r32', 10, 'Mexico',      'Ivory Coast'), -- M79: W-A  vs 3rd-E
  ('r32', 11, 'England',     'DR Congo'),    -- M80: W-L  vs 3rd-K
  ('r32', 12, 'Argentina',   'Uruguay'),     -- M86: W-J  vs RU-H
  ('r32', 13, 'Turkey',      'Iran'),        -- M88: RU-D vs RU-G
  ('r32', 14, 'Switzerland', 'Egypt'),       -- M85: W-B  vs 3rd-G
  ('r32', 15, 'Portugal',    'Ghana');       -- M87: W-K  vs 3rd-L

-- ── R16 / QF / SF / Final ────────────────────────────────
-- Leave empty until those matches are played.
-- Add rows here as the tournament progresses, then rerun calculate_scores().
-- Example for R16 (uncomment and fill in after R32 is complete):
--
-- INSERT INTO results (round, slot_idx, team, opponent) VALUES
--   ('r16', 0, 'France',    'Germany'),   -- M89: W(M74) vs W(M77)
--   ('r16', 1, 'South Korea','Netherlands'),-- M90: W(M73) vs W(M75)
--   ... etc.


-- ============================================================
-- STEP 4a: UPSERT HELPER (used by the nightly scheduled task)
-- ============================================================
-- Allows the anon key to write individual results via Supabase RPC.
-- SECURITY DEFINER means it runs as the DB owner regardless of caller.
-- Call via: POST /rest/v1/rpc/upsert_result  { "p_round":"r32", "p_slot_idx":0,
--                                              "p_team":"Germany", "p_opponent":"Sweden" }
-- For group stage rows (grp1/grp2/grpT), omit p_opponent or pass null.
CREATE OR REPLACE FUNCTION upsert_result(
  p_round     text,
  p_slot_idx  integer,
  p_team      text,
  p_opponent  text DEFAULT NULL
) RETURNS void LANGUAGE sql SECURITY DEFINER AS $$
  INSERT INTO results (round, slot_idx, team, opponent)
  VALUES (p_round, p_slot_idx, p_team, p_opponent)
  ON CONFLICT (round, slot_idx) DO UPDATE
    SET team = EXCLUDED.team, opponent = EXCLUDED.opponent;
$$;


-- ============================================================
-- STEP 4: SCORING FUNCTION
-- ============================================================
-- Scoring rules (mirrors index.html constants):
--   Trajectory : your picked team actually WON their match in this round
--   Exact slot : your pick won AND was in the correct bracket slot (R32–SF only)
--   Matchup    : you predicted BOTH teams in a match (regardless of which won)
--   Champion   : bonus for nailing the tournament winner (on top of Final pts)
--
--   R32 : Traj=2, Slot=5, Match=3
--   R16 : Traj=3, Slot=8, Match=5
--   QF  : Traj=4, Slot=13, Match=8
--   SF  : Traj=6, Slot=18, Match=11
--   Final: Traj=10, Slot=0 (one slot only), Match=25 (fired if you predicted either finalist)
--   Champion bonus: +10 (separate from Final Trajectory)
-- ============================================================

CREATE OR REPLACE FUNCTION calculate_scores()
RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_total int := 0;
BEGIN
  -- Full recalculation — wipe existing scores first
  DELETE FROM scores;

  -- ── GROUP STAGE ────────────────────────────────────────

  -- grp1: 3 pts for each correct group winner
  WITH hits AS (
    SELECT p.user_id, COUNT(*) * 3 AS pts
    FROM predictions p
    JOIN results r ON r.round = 'grp1'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'grp1'
    GROUP BY p.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'grp1', COALESCE(h.pts, 0)
  FROM (SELECT DISTINCT user_id FROM predictions WHERE round = 'grp1') u
  LEFT JOIN hits h ON h.user_id = u.user_id;

  -- grp2: 2 pts for each correct group runner-up
  WITH hits AS (
    SELECT p.user_id, COUNT(*) * 2 AS pts
    FROM predictions p
    JOIN results r ON r.round = 'grp2'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'grp2'
    GROUP BY p.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'grp2', COALESCE(h.pts, 0)
  FROM (SELECT DISTINCT user_id FROM predictions WHERE round = 'grp2') u
  LEFT JOIN hits h ON h.user_id = u.user_id;

  -- grpT: 2 pts per correctly picked qualifying third
  -- Slot order doesn't matter — just checks if picked team is in the qualified set
  WITH hits AS (
    SELECT p.user_id, COUNT(*) * 2 AS pts
    FROM predictions p
    WHERE p.round = 'grpT'
      AND EXISTS (
        SELECT 1 FROM results r WHERE r.round = 'grpT' AND r.team = p.picked_team
      )
    GROUP BY p.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'grpT', COALESCE(h.pts, 0)
  FROM (SELECT DISTINCT user_id FROM predictions WHERE round = 'grpT') u
  LEFT JOIN hits h ON h.user_id = u.user_id;

  -- ── R32 ── Traj=2, Slot=5, Match=3 ──────────────────────
  WITH
  all_u AS (SELECT DISTINCT user_id FROM predictions WHERE round = 'r32'),
  traj AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'r32' AND r.team = p.picked_team
    WHERE p.round = 'r32'
    GROUP BY p.user_id
  ),
  xslot AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'r32'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'r32'
    GROUP BY p.user_id
  ),
  matchup AS (
    -- Count distinct matches where user predicted BOTH the winner and the loser
    SELECT p1.user_id, COUNT(DISTINCT r.slot_idx) AS n
    FROM results r
    JOIN predictions p1 ON p1.round = 'r32' AND p1.picked_team = r.team
    JOIN predictions p2 ON p2.user_id = p1.user_id
                       AND p2.round = 'r32'
                       AND p2.picked_team = r.opponent
    WHERE r.round = 'r32'
    GROUP BY p1.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'r32',
    COALESCE(t.n, 0) * 2   -- Trajectory
    + COALESCE(x.n, 0) * 5  -- Exact slot
    + COALESCE(m.n, 0) * 3  -- Matchup
  FROM all_u u
  LEFT JOIN traj    t ON t.user_id = u.user_id
  LEFT JOIN xslot   x ON x.user_id = u.user_id
  LEFT JOIN matchup m ON m.user_id = u.user_id;

  -- ── R16 ── Traj=3, Slot=8, Match=5 ──────────────────────
  WITH
  all_u AS (SELECT DISTINCT user_id FROM predictions WHERE round = 'r16'),
  traj AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'r16' AND r.team = p.picked_team
    WHERE p.round = 'r16'
    GROUP BY p.user_id
  ),
  xslot AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'r16'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'r16'
    GROUP BY p.user_id
  ),
  matchup AS (
    SELECT p1.user_id, COUNT(DISTINCT r.slot_idx) AS n
    FROM results r
    JOIN predictions p1 ON p1.round = 'r16' AND p1.picked_team = r.team
    JOIN predictions p2 ON p2.user_id = p1.user_id
                       AND p2.round = 'r16'
                       AND p2.picked_team = r.opponent
    WHERE r.round = 'r16'
    GROUP BY p1.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'r16',
    COALESCE(t.n, 0) * 3
    + COALESCE(x.n, 0) * 8
    + COALESCE(m.n, 0) * 5
  FROM all_u u
  LEFT JOIN traj    t ON t.user_id = u.user_id
  LEFT JOIN xslot   x ON x.user_id = u.user_id
  LEFT JOIN matchup m ON m.user_id = u.user_id;

  -- ── QF ── Traj=4, Slot=13, Match=8 ──────────────────────
  WITH
  all_u AS (SELECT DISTINCT user_id FROM predictions WHERE round = 'qf'),
  traj AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'qf' AND r.team = p.picked_team
    WHERE p.round = 'qf'
    GROUP BY p.user_id
  ),
  xslot AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'qf'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'qf'
    GROUP BY p.user_id
  ),
  matchup AS (
    SELECT p1.user_id, COUNT(DISTINCT r.slot_idx) AS n
    FROM results r
    JOIN predictions p1 ON p1.round = 'qf' AND p1.picked_team = r.team
    JOIN predictions p2 ON p2.user_id = p1.user_id
                       AND p2.round = 'qf'
                       AND p2.picked_team = r.opponent
    WHERE r.round = 'qf'
    GROUP BY p1.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'qf',
    COALESCE(t.n, 0) * 4
    + COALESCE(x.n, 0) * 13
    + COALESCE(m.n, 0) * 8
  FROM all_u u
  LEFT JOIN traj    t ON t.user_id = u.user_id
  LEFT JOIN xslot   x ON x.user_id = u.user_id
  LEFT JOIN matchup m ON m.user_id = u.user_id;

  -- ── SF ── Traj=6, Slot=18, Match=11 ─────────────────────
  WITH
  all_u AS (SELECT DISTINCT user_id FROM predictions WHERE round = 'sf'),
  traj AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'sf' AND r.team = p.picked_team
    WHERE p.round = 'sf'
    GROUP BY p.user_id
  ),
  xslot AS (
    SELECT p.user_id, COUNT(*) AS n
    FROM predictions p
    JOIN results r ON r.round = 'sf'
                  AND r.slot_idx = p.slot_idx
                  AND r.team = p.picked_team
    WHERE p.round = 'sf'
    GROUP BY p.user_id
  ),
  matchup AS (
    SELECT p1.user_id, COUNT(DISTINCT r.slot_idx) AS n
    FROM results r
    JOIN predictions p1 ON p1.round = 'sf' AND p1.picked_team = r.team
    JOIN predictions p2 ON p2.user_id = p1.user_id
                       AND p2.round = 'sf'
                       AND p2.picked_team = r.opponent
    WHERE r.round = 'sf'
    GROUP BY p1.user_id
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'sf',
    COALESCE(t.n, 0) * 6
    + COALESCE(x.n, 0) * 18
    + COALESCE(m.n, 0) * 11
  FROM all_u u
  LEFT JOIN traj    t ON t.user_id = u.user_id
  LEFT JOIN xslot   x ON x.user_id = u.user_id
  LEFT JOIN matchup m ON m.user_id = u.user_id;

  -- ── Final ── Traj=10, Slot=0 (no bonus), Match=25 ────────
  -- Match bonus fires if user predicted EITHER finalist to win the final
  -- (i.e. their pick appeared in the final, even as the loser)
  WITH
  all_u AS (SELECT DISTINCT user_id FROM predictions WHERE round = 'final'),
  traj AS (
    -- Predicted the winner
    SELECT p.user_id, 1 AS n
    FROM predictions p
    JOIN results r ON r.round = 'final'
                  AND r.slot_idx = 0
                  AND r.team = p.picked_team
    WHERE p.round = 'final'
  ),
  matchup AS (
    -- Predicted either finalist (winner or loser)
    SELECT p.user_id, 1 AS n
    FROM predictions p
    JOIN results r ON r.round = 'final'
                  AND r.slot_idx = 0
                  AND (p.picked_team = r.team OR p.picked_team = r.opponent)
    WHERE p.round = 'final'
  )
  INSERT INTO scores (user_id, round, points)
  SELECT u.user_id, 'final',
    COALESCE(t.n, 0) * 10   -- Trajectory: predicted winner
    + COALESCE(m.n, 0) * 25  -- Matchup: predicted either finalist
  FROM all_u u
  LEFT JOIN traj    t ON t.user_id = u.user_id
  LEFT JOIN matchup m ON m.user_id = u.user_id;

  -- ── Champion Bonus ── +10 pts (stacks with Final Trajectory) ──
  INSERT INTO scores (user_id, round, points)
  SELECT p.user_id, 'champion', 10
  FROM predictions p
  JOIN results r ON r.round = 'final'
                AND r.slot_idx = 0
                AND r.team = p.picked_team
  WHERE p.round = 'final'
  ON CONFLICT (user_id, round) DO UPDATE SET points = EXCLUDED.points;

  SELECT SUM(points) INTO v_total FROM scores;
  RETURN format('Scores recalculated. Total points across all users: %s', COALESCE(v_total, 0));
END;
$$;


-- ============================================================
-- STEP 5: VERIFY DEMO DATA
-- Run this to confirm results table looks correct.
-- ============================================================
SELECT
  round,
  slot_idx,
  team,
  COALESCE(opponent, '—') AS opponent
FROM results
ORDER BY
  CASE round
    WHEN 'grp1'  THEN 1
    WHEN 'grp2'  THEN 2
    WHEN 'grpT'  THEN 3
    WHEN 'r32'   THEN 4
    WHEN 'r16'   THEN 5
    WHEN 'qf'    THEN 6
    WHEN 'sf'    THEN 7
    WHEN 'final' THEN 8
  END,
  slot_idx;


-- ============================================================
-- STEP 6: HOW TO TEST SCORING
-- ============================================================
-- 1. Submit a test bracket via the site (or use your own).
--    To match demo results exactly, pick:
--    Group winners : Mexico, Switzerland, Brazil, USA, Germany, Netherlands,
--                    Belgium, Spain, France, Argentina, Portugal, England
--    Group runners : South Korea, Canada, Morocco, Turkey, Ecuador, Japan,
--                    Iran, Uruguay, Senegal, Austria, Colombia, Croatia
--    8 Thirds (any 8 from the groups; E–L qualify in this demo):
--                    Ivory Coast(E), Sweden(F), Egypt(G), Cape Verde(H),
--                    Norway(I), Algeria(J), DR Congo(K), Ghana(L)
--    R32 picks : match the results table (Germany, France, South Korea, ...)
--
-- 2. After submitting, run:
--    SELECT calculate_scores();
--
-- 3. Check leaderboard scores:
SELECT
  pr.display_name,
  SUM(sc.points) AS total,
  MAX(CASE WHEN sc.round = 'grp1'    THEN sc.points END) AS grp1,
  MAX(CASE WHEN sc.round = 'grp2'    THEN sc.points END) AS grp2,
  MAX(CASE WHEN sc.round = 'grpT'    THEN sc.points END) AS grpT,
  MAX(CASE WHEN sc.round = 'r32'     THEN sc.points END) AS r32,
  MAX(CASE WHEN sc.round = 'champion'THEN sc.points END) AS champion
FROM scores sc
JOIN profiles pr ON pr.id = sc.user_id
GROUP BY pr.display_name
ORDER BY total DESC;

-- ============================================================
-- EXPECTED SCORE for a perfect demo bracket (all R32 correct):
--   grp1   : 12 correct × 3 pts  = 36
--   grp2   : 12 correct × 2 pts  = 24
--   grpT   :  8 correct × 2 pts  = 16
--   r32    : 16 correct           = 16 × (2+5+3) = 160
--              traj(2) + slot(5) + matchup(3) per match
--   Total group+R32               = 36+24+16+160 = 236 pts
-- ============================================================
