-- R Theory forum schema (PostgreSQL 16 + TimescaleDB + pgvector/pgvectorscale + pgAI)
-- Run: psql -h 127.0.0.1 -U forum -d forum -f schema.sql
--
-- Required extensions (see forum-stack README §4):
--   timescaledb, vector, vectorscale, ai

-- ---------------------------------------------------------------- core tables
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(32)  NOT NULL UNIQUE,
    email         VARCHAR(254) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT username_format CHECK (username ~ '^[A-Za-z0-9_]{3,32}$')
);

CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(80) NOT NULL,
    description TEXT        NOT NULL DEFAULT '',
    sort_order  INT         NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS threads (
    id          SERIAL PRIMARY KEY,
    category_id INT          NOT NULL REFERENCES categories(id),
    user_id     INT          NOT NULL REFERENCES users(id),
    title       VARCHAR(200) NOT NULL,
    is_locked   BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS posts (
    id         SERIAL PRIMARY KEY,
    thread_id  INT         NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    user_id    INT         NOT NULL REFERENCES users(id),
    body       TEXT        NOT NULL CHECK (char_length(body) BETWEEN 1 AND 20000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS posts_thread_idx ON posts (thread_id, id);
CREATE INDEX IF NOT EXISTS threads_category_idx ON threads (category_id, id);

-- ---------------------------------------------------------------- seed boards
INSERT INTO categories (name, description, sort_order) VALUES
    ('General', 'General discussion', 1),
    ('Book discussions', 'One thread per book or section', 2),
    ('Site feedback', 'Bugs, typos, and suggestions for the site', 3)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------- TimescaleDB metrics
-- Every interesting event is logged here; the continuous aggregate below
-- powers the /metrics page. Hypertable = time-partitioned automatically.
CREATE TABLE IF NOT EXISTS forum_events (
    ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_type TEXT        NOT NULL,  -- user_registered | thread_created | post_created
    user_id    INT         REFERENCES users(id),
    thread_id  INT         REFERENCES threads(id)
);

SELECT create_hypertable('forum_events', 'ts', if_not_exists => TRUE);

CREATE MATERIALIZED VIEW IF NOT EXISTS forum_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', ts) AS day,
       event_type,
       COUNT(*) AS n
FROM forum_events
GROUP BY 1, 2
WITH NO DATA;

-- refresh policy: keep the aggregate fresh (run once, after extension setup)
-- SELECT add_continuous_aggregate_policy('forum_daily',
--     start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour',
--     schedule_interval => INTERVAL '1 hour', if_not_exists => TRUE);

-- ---------------------------------------------------------------- pgAI semantic search
-- The vectorizer over posts is created AFTER the ai extension is installed,
-- using the installed pgAI version's exact API (it varies by release).
-- Placeholder — filled in during stack bring-up:
--
--   SELECT ai.create_vectorizer(
--       'public.posts'::regclass,
--       destination => 'posts_embedding',
--       embedding   => ai.embedding_ollama('nomic-embed-text', 768),
--       chunking    => ai.chunking_recursive_character_text_splitter('body')
--   );
--
-- The embedding store then gets a pgvectorscale DiskANN index:
--   CREATE INDEX ON <embedding_store> USING diskann (embedding);
--
-- The /search route queries the vectorizer's search view; if the vectorizer
-- does not exist yet it degrades to a plain ILIKE fallback (see app.py).

-- ---------------------------------------------------------------- docs (populate phase 2026-09-22)
-- Architecture diagrams stored IN the database; served by /docs routes.
CREATE TABLE IF NOT EXISTS docs (
    id SERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    diagram_kind TEXT NOT NULL,
    image BYTEA NOT NULL,
    image_mime TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
