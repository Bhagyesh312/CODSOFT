-- ============================================================
-- ThinkSprint — Migration: Add shuffle_questions to quizzes
-- Run this in pgAdmin4 on the thinksprint database
-- ============================================================

ALTER TABLE quizzes
  ADD COLUMN IF NOT EXISTS shuffle_questions BOOLEAN NOT NULL DEFAULT TRUE;

-- Existing quizzes default to TRUE (shuffle enabled)
-- Creators can change this per quiz via the Edit Quiz page.
