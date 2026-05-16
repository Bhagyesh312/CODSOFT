-- ============================================================
-- ThinkSprint — Migration 07: Streak tracking & Badges
-- Run this in pgAdmin Query Tool against your thinksprint DB
-- Safe to run multiple times (uses IF NOT EXISTS / IF EXISTS)
-- ============================================================

-- ── 1. Add streak columns to users ──────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS current_streak  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS longest_streak  INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_quiz_date  DATE;

-- ── 2. Create user_badges table ─────────────────────────────
CREATE TABLE IF NOT EXISTS user_badges (
    id         SERIAL      PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_key  VARCHAR(50) NOT NULL,
    earned_at  TIMESTAMP   NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_badge UNIQUE (user_id, badge_key)
);

-- ── 3. Index for fast badge lookups per user ─────────────────
CREATE INDEX IF NOT EXISTS idx_user_badges_user_id
    ON user_badges (user_id);

-- ── 4. Update Alembic version table ─────────────────────────
-- Tells Flask-Migrate that this migration has been applied.
-- Only run this if you are NOT using `flask db upgrade`.
-- If you already ran `flask db upgrade` or `flask db stamp`,
-- skip this block.
INSERT INTO alembic_version (version_num)
VALUES ('a1b2c3d4e5f6')
ON CONFLICT DO NOTHING;

-- ── Verification queries (run after to confirm) ──────────────
-- SELECT column_name, data_type
--   FROM information_schema.columns
--  WHERE table_name = 'users'
--    AND column_name IN ('current_streak','longest_streak','last_quiz_date');

-- SELECT tablename FROM pg_tables
--  WHERE schemaname = 'public' AND tablename = 'user_badges';
