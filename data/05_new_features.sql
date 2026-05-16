-- ============================================================
-- ThinkSprint — Migration: 5 new features
-- Run in pgAdmin4 on the thinksprint database
-- ============================================================

-- 1. Configurable join window on quizzes
ALTER TABLE quizzes
  ADD COLUMN IF NOT EXISTS join_window_minutes INTEGER NOT NULL DEFAULT 10;

-- 2. Negative marking settings on quizzes
ALTER TABLE quizzes
  ADD COLUMN IF NOT EXISTS negative_marking  BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS negative_penalty  NUMERIC(5,2) NOT NULL DEFAULT 0.5;

-- 3. Question image support
ALTER TABLE questions
  ADD COLUMN IF NOT EXISTS image_path VARCHAR(300);

-- 4. Penalty tracking on attempts
ALTER TABLE attempts
  ADD COLUMN IF NOT EXISTS penalty NUMERIC(6,2) NOT NULL DEFAULT 0.0;

-- (shuffle_questions was added in 04_add_shuffle_questions.sql)
-- No changes needed for regenerate-code or live count — those are route-only features.
