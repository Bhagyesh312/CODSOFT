-- ============================================================
-- ThinkSprint — Migration Tracking Table
-- Run this after 01_setup.sql
-- Alembic (Flask-Migrate) needs this table to track versions.
-- ============================================================

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
