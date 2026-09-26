"""Forum configuration — everything comes from the environment.

Single place to point the app at your PostgreSQL server, James mail
server, and embedding provider. No secrets live in this file.
"""
import os


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DB_HOST = _get("FORUM_DB_HOST", "127.0.0.1")  # WSL2 split: Windows host IP from WSL (see forum-stack README §3.6.2)
DB_PORT = _get("FORUM_DB_PORT", "5432")
DB_NAME = _get("FORUM_DB_NAME", "forum")
DB_USER = _get("FORUM_DB_USER", "forum")
DB_PASS = _get("FORUM_DB_PASS", "forum_dev_only")

SITE_NAME = _get("FORUM_SITE_NAME", "R Theory — Forum")

# Flask session signing. MUST be set to a long random value in production.
SECRET_KEY = _get("FORUM_SECRET_KEY", "dev-only-change-me")

# Apache James SMTP (outbound forum mail: welcome + reply notifications).
SMTP_HOST = _get("FORUM_SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(_get("FORUM_SMTP_PORT", "2525"))  # 25/587 in production
SMTP_USER = _get("FORUM_SMTP_USER", "")
SMTP_PASS = _get("FORUM_SMTP_PASS", "")
MAIL_FROM = _get("FORUM_MAIL_FROM", "notify@forum.local")

# posts-per-page on thread view
POSTS_PER_PAGE = 20
