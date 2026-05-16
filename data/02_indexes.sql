-- ============================================================
-- ThinkSprint — Indexes for Performance
-- Run this after 01_setup.sql
-- ============================================================

-- Fast lookup by join code (used on every quiz join)
CREATE INDEX IF NOT EXISTS idx_quizzes_join_code
    ON quizzes(join_code);

-- Fast lookup of quizzes by creator
CREATE INDEX IF NOT EXISTS idx_quizzes_creator_id
    ON quizzes(creator_id);

-- Fast lookup of questions by quiz
CREATE INDEX IF NOT EXISTS idx_questions_quiz_id
    ON questions(quiz_id);

-- Fast lookup of options by question
CREATE INDEX IF NOT EXISTS idx_options_question_id
    ON options(question_id);

-- Fast lookup of attempts by quiz (leaderboard queries)
CREATE INDEX IF NOT EXISTS idx_attempts_quiz_id
    ON attempts(quiz_id);

-- Fast lookup of attempts by user (my attempts)
CREATE INDEX IF NOT EXISTS idx_attempts_user_id
    ON attempts(user_id);

-- Enforce one attempt per user per quiz (when allow_multiple_attempts = false)
-- This is a partial unique index — only enforces uniqueness on submitted attempts
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_attempt_per_user_per_quiz
    ON attempts(quiz_id, user_id)
    WHERE is_submitted = TRUE;

-- Fast lookup of answers by attempt
CREATE INDEX IF NOT EXISTS idx_attempt_answers_attempt_id
    ON attempt_answers(attempt_id);
