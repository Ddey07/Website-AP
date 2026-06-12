-- ============================================================
-- WC 2026 Bracket Challenge — Scoring Compensation Fix
-- Run this in Supabase SQL Editor
-- ============================================================
-- Context: Five users were shown the wrong 3rd-place opponent in
-- their R32 bracket due to a site algorithm error (old backtracking
-- vs the official FIFA 495 combination table, now corrected).
--
-- Neutral fix: score their affected R32 pick as the group winner
-- (the safe conservative pick). This gives them the same credit as
-- any user who picked the group winner at that slot — no advantage,
-- no disadvantage relative to the rest.
--
-- Affected: Durkheim, Rokkekoro, Tetsu, raeesbhai, westhamno19
-- Cascade:  None — all 5 users had R16+ picks from the OTHER R32
--           branch, so downstream picks are entirely unaffected.
-- ============================================================


-- ── STEP 1: Create the compensation lookup table ───────────────────────────

CREATE TABLE IF NOT EXISTS score_compensations (
  display_name  TEXT        NOT NULL,
  round         TEXT        NOT NULL DEFAULT 'r32',
  slot_idx      INT         NOT NULL,
  wrong_pick    TEXT        NOT NULL,   -- what the site showed (incorrect)
  treat_as      TEXT        NOT NULL,   -- what to score instead (group winner)
  reason        TEXT,
  PRIMARY KEY (display_name, round, slot_idx)
);

INSERT INTO score_compensations (display_name, round, slot_idx, wrong_pick, treat_as, reason)
VALUES
  ('Durkheim',    'r32', 14, 'Egypt',    'Switzerland',
   'Site showed Egypt at M85 (W-B slot); correct 3rd per FIFA 495 is Austria. GW = Switzerland.'),
  ('Rokkekoro',   'r32', 10, 'Sweden',   'South Korea',
   'Site showed Sweden at M79 (W-A slot); correct 3rd per FIFA 495 is Uruguay. GW = South Korea.'),
  ('Tetsu',       'r32',  6, 'Senegal',  'Turkey',
   'Site showed Senegal at M81 (W-D slot); correct 3rd per FIFA 495 is Ecuador. GW = Turkey.'),
  ('raeesbhai',   'r32', 10, 'Senegal',  'Mexico',
   'Site showed Senegal at M79 (W-A slot); correct 3rd per FIFA 495 is Ecuador. GW = Mexico.'),
  ('westhamno19', 'r32', 14, 'Sweden',   'Switzerland',
   'Site showed Sweden at M85 (W-B slot); correct 3rd per FIFA 495 is Senegal. GW = Switzerland.')
ON CONFLICT DO NOTHING;


-- ── STEP 2: Replace the calculate_scores function ─────────────────────────
-- The ONLY change vs the original is the R32 block:
--   • Added eff_r32 CTE that substitutes picked_team → treat_as for the 5
--     affected (user, slot) rows; all other predictions pass through unchanged.
--   • All other rounds (r16, qf, sf, final, champion) are byte-for-byte
--     identical to the original function.
-- ─────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.calculate_scores()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
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

  -- ── R32 ── Traj=2, Slot=5, Match=3 ──────────────────────────────────────
  -- eff_r32: apply GW-credit compensation for site-error-affected picks.
  -- For the 5 affected (user, slot) rows, picked_team → treat_as (GW team).
  -- All other predictions pass through unchanged (COALESCE returns original).
  WITH
  eff_r32 AS (
    SELECT
      p.user_id,
      p.slot_idx,
      COALESCE(sc.treat_as, p.picked_team) AS picked_team
    FROM predictions p
    LEFT JOIN profiles prof ON prof.id = p.user_id
    LEFT JOIN score_compensations sc
      ON  sc.display_name = prof.display_name
      AND sc.round        = 'r32'
      AND sc.slot_idx     = p.slot_idx
      AND sc.wrong_pick   = p.picked_team
    WHERE p.round = 'r32'
  ),
  all_u AS (SELECT DISTINCT user_id FROM eff_r32),
  traj AS (
    SELECT e.user_id, COUNT(*) AS n
    FROM eff_r32 e
    JOIN results r ON r.round = 'r32' AND r.team = e.picked_team
    GROUP BY e.user_id
  ),
  xslot AS (
    SELECT e.user_id, COUNT(*) AS n
    FROM eff_r32 e
    JOIN results r ON r.round = 'r32'
                  AND r.slot_idx = e.slot_idx
                  AND r.team    = e.picked_team
    GROUP BY e.user_id
  ),
  matchup AS (
    -- Count distinct matches where user predicted BOTH the winner and the loser
    SELECT e1.user_id, COUNT(DISTINCT r.slot_idx) AS n
    FROM results r
    JOIN eff_r32 e1 ON e1.picked_team = r.team
    JOIN eff_r32 e2 ON e2.user_id     = e1.user_id
                   AND e2.picked_team = r.opponent
    WHERE r.round = 'r32'
    GROUP BY e1.user_id
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
$function$;


-- ── STEP 3: Apply and verify ───────────────────────────────────────────────

-- Trigger a rescore:
-- SELECT calculate_scores();

-- Confirm compensation table is populated:
-- SELECT * FROM score_compensations;

-- Spot-check the 5 affected users:
-- SELECT prof.display_name, s.round, s.points
-- FROM scores s
-- JOIN profiles prof ON prof.id = s.user_id
-- WHERE prof.display_name IN ('Durkheim','Rokkekoro','Tetsu','raeesbhai','westhamno19')
-- ORDER BY prof.display_name, s.round;
