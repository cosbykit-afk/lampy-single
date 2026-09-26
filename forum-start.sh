#!/bin/sh
# forum-start.sh — startup wrapper for the Lampy forum app (xapp).
#
# Waits for postgres, creates the forum database/user on first boot,
# applies schema.sql, then runs gunicorn on 127.0.0.1:8000.
#
# Environment (from container):
#   POSTGRES_PASSWORD — postgres superuser password (default 'password' in ship image)
#   FORUM_SECRET_KEY  — Flask secret key (generated random on first boot if unset)
set -e

PGUSER=postgres
PGHOST=127.0.0.1
PGPORT=5432
export PGPASSWORD="${POSTGRES_PASSWORD:-password}"

# Wait for postgres to accept connections (max 60s).
echo "forum-start: waiting for postgres..." >&2
for i in $(seq 1 60); do
  if pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; then
  echo "forum-start: postgres not ready after 60s, exiting" >&2
  exit 1
fi

# Create forum user and database on first boot (idempotent).
if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -tAc "SELECT 1 FROM pg_roles WHERE rolname='forum'" | grep -q 1; then
  echo "forum-start: creating forum user..." >&2
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -c "CREATE USER forum WITH PASSWORD '${POSTGRES_PASSWORD:-password}';"
fi
if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -tAc "SELECT 1 FROM pg_database WHERE datname='forum'" | grep -q 1; then
  echo "forum-start: creating forum database..." >&2
  psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -c "CREATE DATABASE forum OWNER forum;"
fi

# Apply schema if the users table doesn't exist (idempotent).
if ! psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d forum -tAc "SELECT 1 FROM information_schema.tables WHERE table_name='users'" | grep -q 1; then
  echo "forum-start: enabling TimescaleDB and applying schema.sql..." >&2
  PGPASSWORD="${POSTGRES_PASSWORD:-password}" psql -h "$PGHOST" -p "$PGPORT" -U forum -d forum -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
  PGPASSWORD="${POSTGRES_PASSWORD:-password}" psql -h "$PGHOST" -p "$PGPORT" -U forum -d forum -f /opt/forum/schema.sql
fi

# Flask secret key: use FORUM_SECRET_KEY if set, else generate and persist.
if [ -z "${FORUM_SECRET_KEY:-}" ]; then
  KEYFILE=/var/lib/postgresql/forum_secret.key
  if [ ! -f "$KEYFILE" ]; then
    echo "forum-start: generating Flask secret key..." >&2
    python3 -c "import secrets; print(secrets.token_hex(32))" > "$KEYFILE"
    chmod 600 "$KEYFILE"
  fi
  export FORUM_SECRET_KEY="$(cat "$KEYFILE")"
fi

# Database connection for the app.
export FORUM_DB_HOST="$PGHOST"
export FORUM_DB_PORT="$PGPORT"
export FORUM_DB_NAME="forum"
export FORUM_DB_USER="forum"
export FORUM_DB_PASS="${POSTGRES_PASSWORD:-password}"
export FORUM_SMTP_HOST="127.0.0.1"
export FORUM_SMTP_PORT="2525"

echo "forum-start: launching gunicorn on 127.0.0.1:8000..." >&2
cd /opt/forum
exec /usr/local/bin/gunicorn -w 2 -b 127.0.0.1:8000 app:app
