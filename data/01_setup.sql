-- ============================================================
-- ThinkSprint — Database Setup
-- Run this first in pgAdmin4
-- DB: thinksprint  |  User: postgres  |  Pass: kali
-- ============================================================

-- Connect to the thinksprint database before running this file.
-- In pgAdmin4: right-click thinksprint > Query Tool > paste & run.

-- Enable UUID extension (optional, not used but good practice)
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── USERS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(150)  NOT NULL UNIQUE,
    password    VARCHAR(256)  NOT NULL,
    created_at  TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- ─── QUIZZES ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quizzes (
    id                      SERIAL PRIMARY KEY,
    title                   VARCHAR(200)  NOT NULL,
    description             TEXT,
    join_code               VARCHAR(6)    UNIQUE,
    code_expires_at         TIMESTAMP,
    timer_per_question      INTEGER       NOT NULL DEFAULT 30,
    allow_multiple_attempts BOOLEAN       NOT NULL DEFAULT FALSE,
    bonus_enabled           BOOLEAN       NOT NULL DEFAULT TRUE,
    bonus_points            INTEGER       NOT NULL DEFAULT 2,
    creator_id              INTEGER       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_active               BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP     NOT NULL DEFAULT NOW()
);

-- ─── QUESTIONS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
    id              SERIAL PRIMARY KEY,
    quiz_id         INTEGER  NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text   TEXT     NOT NULL,
    order_index     INTEGER  NOT NULL DEFAULT 0
);

-- ─── OPTIONS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS options (
    id              SERIAL PRIMARY KEY,
    question_id     INTEGER       NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    option_text     VARCHAR(500)  NOT NULL,
    is_correct      BOOLEAN       NOT NULL DEFAULT FALSE
);

-- ─── ATTEMPTS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attempts (
    id              SERIAL PRIMARY KEY,
    quiz_id         INTEGER   NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id         INTEGER   REFERENCES users(id) ON DELETE SET NULL,
    score           INTEGER   NOT NULL DEFAULT 0,
    total           INTEGER   NOT NULL DEFAULT 0,
    time_taken      INTEGER   NOT NULL DEFAULT 0,   -- total seconds
    bonus_points    INTEGER   NOT NULL DEFAULT 0,
    is_submitted    BOOLEAN   NOT NULL DEFAULT FALSE,
    taken_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ─── ATTEMPT ANSWERS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attempt_answers (
    id                  SERIAL PRIMARY KEY,
    attempt_id          INTEGER  NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id         INTEGER  NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    selected_option_id  INTEGER  REFERENCES options(id) ON DELETE SET NULL,  -- NULL = unanswered
    is_correct          BOOLEAN  NOT NULL DEFAULT FALSE,
    time_taken_seconds  INTEGER  NOT NULL DEFAULT 0
);
