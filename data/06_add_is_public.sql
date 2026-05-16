-- ============================================================
-- ThinkSprint — Migration: Add is_public to quizzes
-- Run in pgAdmin4 on the thinksprint database
-- ============================================================

ALTER TABLE quizzes
  ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;

-- Existing quizzes default to private (FALSE).
-- Creators can toggle this per quiz via Create/Edit Quiz.
