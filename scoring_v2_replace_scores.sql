-- ============================================================
-- WC 2026 Bracket Challenge — Scoring v2 (tightened matchup)
-- Run this ONCE in the Supabase SQL Editor.
-- ============================================================
-- Why: scoring now happens in scripts/push_results_supabase.py, which has each
-- player's full FIFA-495 bracket and can apply the "matchup" tier correctly —
-- you score the +matchup bonus only when your bracket actually stages that exact
-- fixture (you predicted the two teams to meet), not merely when both teams are
-- still alive in your picks. The old SQL calculate_scores() used the looser rule
-- and can't see each player's 495 bracket, so the scorer moved to Python.
--
-- This adds a small SECURITY DEFINER RPC that the push script calls to write the
-- freshly-computed per-round scores. It fully replaces the scores table each run,
-- exactly like calculate_scores() did. calculate_scores() is now unused (left in
-- place as a harmless fallback; the workflow no longer calls it).
-- ============================================================

CREATE OR REPLACE FUNCTION public.replace_scores(p_rows jsonb)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_total int := 0;
BEGIN
  -- Full replacement — wipe then insert the provided rows.
  DELETE FROM scores;

  INSERT INTO scores (user_id, round, points)
  SELECT (e ->> 'user_id')::uuid,
         e ->> 'round',
         (e ->> 'points')::int
  FROM jsonb_array_elements(p_rows) AS e;

  SELECT COALESCE(SUM(points), 0) INTO v_total FROM scores;
  RETURN format('Scores replaced. Total points across all users: %s', v_total);
END;
$$;

-- Allow the public (anon) key to call it, same trust model as calculate_scores().
GRANT EXECUTE ON FUNCTION public.replace_scores(jsonb) TO anon;

-- After running this once, rescore by running:
--   SUPABASE_PUSH=1 python scripts/push_results_supabase.py --push
-- (or just let the every-2-hours GitHub Action do it on its next run).
