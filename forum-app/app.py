"""R Theory forum — Python/Flask + PostgreSQL (+ TimescaleDB, pgAI, James mail).

Run (dev):
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:8080
Run (prod):
    gunicorn -w 3 -b 127.0.0.1:8000 app:app
"""
import hmac
import re
import secrets
import smtplib
from email.message import EmailMessage

import psycopg
from psycopg.rows import dict_row
from flask import (
    Flask, abort, g, redirect, render_template, request, session, url_for,
    Response,
)
from werkzeug.security import check_password_hash, generate_password_hash

import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["TEMPLATES_AUTO_RELOAD"] = True

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ---------------------------------------------------------------- database
def _conninfo() -> str:
    return (
        f"host={config.DB_HOST} port={config.DB_PORT} "
        f"dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASS}"
    )


def db():
    if "db" not in g:
        g.db = psycopg.connect(_conninfo(), row_factory=dict_row)
    return g.db


@app.teardown_appcontext
def _close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


# ---------------------------------------------------------------- auth
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute(
        "SELECT id, username, email, is_admin FROM users WHERE id = %s", (uid,)
    ).fetchone()


def require_login():
    user = current_user()
    if user is None:
        return redirect(url_for("login", next=request.full_path))
    return user


def login_user(user_id: int):
    session.clear()
    session["user_id"] = user_id


@app.context_processor
def _inject():
    return {"site_name": config.SITE_NAME, "current_user": current_user()}


# ---------------------------------------------------------------- CSRF
def _csrf_token() -> str:
    tok = session.get("csrf_token")
    if not tok:
        tok = secrets.token_hex(32)
        session["csrf_token"] = tok
    return tok


@app.context_processor
def _csrf():
    return {"csrf_token": _csrf_token}


@app.before_request
def _csrf_protect():
    if request.method == "POST":
        real = session.get("csrf_token", "")
        sent = request.form.get("csrf_token", "")
        if not real or not hmac.compare_digest(real, sent):
            abort(403, "CSRF check failed")


# ---------------------------------------------------------------- events + mail
def log_event(event_type: str, user_id=None, thread_id=None):
    db().execute(
        "INSERT INTO forum_events (event_type, user_id, thread_id)"
        " VALUES (%s, %s, %s)",
        (event_type, user_id, thread_id),
    )


def send_mail(to_addr: str, subject: str, body: str):
    """Best-effort mail via James. Never raises — logs and continues."""
    msg = EmailMessage()
    msg["From"] = config.MAIL_FROM
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASS)
            s.send_message(msg)
    except Exception as e:  # noqa: BLE001 — mail must never break a request
        app.logger.warning("mail to %s failed: %s", to_addr, e)


# ---------------------------------------------------------------- semantic search
# Probe once at startup: is there a pgAI vectorizer over public.posts?
# The exact ai catalog shape varies by pgAI release, so this is defensive:
# anything unexpected -> ILIKE fallback, and the page says which mode is on.
SEARCH_MODE = "keyword"
_probed = False


def _probe_vector_search() -> None:
    global SEARCH_MODE, _probed
    if _probed:
        return
    _probed = True
    try:
        conn = psycopg.connect(_conninfo(), row_factory=dict_row)
    except Exception as e:  # noqa: BLE001
        app.logger.warning("search probe: no DB: %s", e)
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('ai.vectorizer') AS r")
            if cur.fetchone()["r"] is None:
                return
            # TODO(pin): match this to the installed pgAI catalog once pgAI
            # is installed on the target host; verified shape goes here.
            cur.execute(
                "SELECT count(*) AS n FROM ai.vectorizer"
            )
            if cur.fetchone()["n"] > 0:
                SEARCH_MODE = "vectorizer-present"
    except Exception as e:  # noqa: BLE001
        app.logger.warning("search probe: falling back to keyword: %s", e)
    finally:
        conn.close()


def vector_search(query: str, limit: int = 20):
    """Semantic search if a vectorizer exists, else keyword fallback."""
    if SEARCH_MODE != "vectorizer-present":
        return None
    # TODO(pin): real vectorizer query once the ai catalog shape is verified
    # against the installed pgAI release. Until then, keyword fallback.
    return None


def keyword_search(query: str, limit: int = 20):
    like = f"%{query}%"
    return db().execute(
        """SELECT p.id, p.body, p.created_at, u.username,
                  t.id AS thread_id, t.title AS thread_title
           FROM posts p
           JOIN users u ON u.id = p.user_id
           JOIN threads t ON t.id = p.thread_id
           WHERE p.body ILIKE %s OR t.title ILIKE %s
           ORDER BY p.created_at DESC LIMIT %s""",
        (like, like, limit),
    ).fetchall()


# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    cats = db().execute(
        """SELECT c.id, c.name, c.description,
                  COUNT(DISTINCT t.id) AS thread_count,
                  COUNT(p.id) AS post_count
           FROM categories c
           LEFT JOIN threads t ON t.category_id = c.id
           LEFT JOIN posts p ON p.thread_id = t.id
           GROUP BY c.id ORDER BY c.sort_order, c.name"""
    ).fetchall()
    latest = db().execute(
        """SELECT t.id, t.title, t.created_at, u.username, c.name AS cat_name,
                  (SELECT COUNT(*) FROM posts p WHERE p.thread_id = t.id) AS post_count,
                  (SELECT MAX(p.created_at) FROM posts p WHERE p.thread_id = t.id) AS last_post_at
           FROM threads t
           JOIN users u ON u.id = t.user_id
           JOIN categories c ON c.id = t.category_id
           ORDER BY last_post_at DESC NULLS LAST LIMIT 15"""
    ).fetchall()
    return render_template("index.html", cats=cats, latest=latest)


@app.route("/category/<int:cat_id>")
def category(cat_id: int):
    cat = db().execute(
        "SELECT id, name, description FROM categories WHERE id = %s", (cat_id,)
    ).fetchone()
    if cat is None:
        abort(404)
    threads = db().execute(
        """SELECT t.id, t.title, t.created_at, t.is_locked, u.username,
                  (SELECT COUNT(*) FROM posts p WHERE p.thread_id = t.id) AS post_count,
                  (SELECT MAX(p.created_at) FROM posts p WHERE p.thread_id = t.id) AS last_post_at
           FROM threads t JOIN users u ON u.id = t.user_id
           WHERE t.category_id = %s
           ORDER BY last_post_at DESC NULLS LAST""",
        (cat_id,),
    ).fetchall()
    return render_template("category.html", cat=cat, threads=threads)


@app.route("/thread/<int:thread_id>", methods=["GET", "POST"])
def thread(thread_id: int):
    th = db().execute(
        """SELECT t.id, t.title, t.is_locked, t.category_id, t.user_id,
                  c.name AS cat_name, u.username AS author, u.email AS author_email
           FROM threads t
           JOIN categories c ON c.id = t.category_id
           JOIN users u ON u.id = t.user_id
           WHERE t.id = %s""",
        (thread_id,),
    ).fetchone()
    if th is None:
        abort(404)

    errors = []
    if request.method == "POST":
        user = current_user()
        if user is None:
            return redirect(url_for("login", next=request.full_path))
        body = request.form.get("body", "").strip()
        if th["is_locked"]:
            errors.append("This thread is locked.")
        elif not body:
            errors.append("Reply cannot be empty.")
        elif len(body) > 20000:
            errors.append("Reply is too long (max 20,000 characters).")
        else:
            db().execute(
                "INSERT INTO posts (thread_id, user_id, body) VALUES (%s, %s, %s)",
                (thread_id, user["id"], body),
            )
            log_event("post_created", user["id"], thread_id)
            db().commit()
            # notify thread author (unless they wrote it themselves)
            if th["user_id"] != user["id"] and th["author_email"]:
                send_mail(
                    th["author_email"],
                    f"[{config.SITE_NAME}] New reply in '{th['title']}'",
                    f"{user['username']} replied to your thread '{th['title']}'.\n",
                )
            return redirect(url_for("thread", thread_id=thread_id))

    total = db().execute(
        "SELECT COUNT(*) AS n FROM posts WHERE thread_id = %s", (thread_id,)
    ).fetchone()["n"]
    per = config.POSTS_PER_PAGE
    pages = max(1, -(-total // per))
    page = min(pages, max(1, request.args.get("page", 1, type=int)))
    posts = db().execute(
        """SELECT p.id, p.body, p.created_at, u.username
           FROM posts p JOIN users u ON u.id = p.user_id
           WHERE p.thread_id = %s ORDER BY p.id ASC LIMIT %s OFFSET %s""",
        (thread_id, per, (page - 1) * per),
    ).fetchall()
    return render_template(
        "thread.html", th=th, posts=posts, errors=errors,
        page=page, pages=pages,
    )


@app.route("/new_thread", methods=["GET", "POST"])
def new_thread():
    user = current_user()
    if user is None:
        return redirect(url_for("login", next=request.full_path))
    cat_id = request.args.get("category", type=int) or request.form.get("category", type=int)
    cat = db().execute(
        "SELECT id, name FROM categories WHERE id = %s", (cat_id,)
    ).fetchone()
    if cat is None:
        abort(404)

    errors, title, body = [], "", ""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title:
            errors.append("Title cannot be empty.")
        elif len(title) > 200:
            errors.append("Title is too long (max 200 characters).")
        if not body:
            errors.append("Message cannot be empty.")
        elif len(body) > 20000:
            errors.append("Message is too long (max 20,000 characters).")
        if not errors:
            t = db().execute(
                "INSERT INTO threads (category_id, user_id, title)"
                " VALUES (%s, %s, %s) RETURNING id",
                (cat["id"], user["id"], title),
            ).fetchone()
            db().execute(
                "INSERT INTO posts (thread_id, user_id, body) VALUES (%s, %s, %s)",
                (t["id"], user["id"], body),
            )
            log_event("thread_created", user["id"], t["id"])
            log_event("post_created", user["id"], t["id"])
            db().commit()
            return redirect(url_for("thread", thread_id=t["id"]))

    return render_template(
        "new_thread.html", cat=cat, errors=errors, title=title, body=body
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("index"))
    errors, username, email = [], "", ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not USERNAME_RE.match(username):
            errors.append("Username must be 3–32 chars: letters, digits, underscore.")
        elif not EMAIL_RE.match(email) or len(email) > 254:
            errors.append("Enter a valid email address.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        else:
            exists = db().execute(
                "SELECT 1 FROM users WHERE username = %s OR email = %s",
                (username, email),
            ).fetchone()
            if exists:
                errors.append("That username or email is taken.")
            else:
                u = db().execute(
                    "INSERT INTO users (username, email, password_hash)"
                    " VALUES (%s, %s, %s) RETURNING id",
                    (username, email, generate_password_hash(password)),
                ).fetchone()
                log_event("user_registered", u["id"])
                db().commit()
                login_user(u["id"])
                send_mail(
                    email,
                    f"[{config.SITE_NAME}] Welcome, {username}",
                    f"Hi {username},\n\nYour forum account is ready. See you in the threads.\n",
                )
                return redirect(url_for("index"))
    return render_template(
        "register.html", errors=errors, username=username, email=email
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))
    errors, username = [], ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = db().execute(
            "SELECT id, password_hash FROM users WHERE username = %s", (username,)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            login_user(row["id"])
            nxt = request.form.get("next", "")
            # relative-path redirects only (no open redirect)
            if not (nxt.startswith("/") and not nxt.startswith("//")):
                nxt = url_for("index")
            return redirect(nxt)
        errors.append("Invalid username or password.")
    return render_template(
        "login.html", errors=errors, username=username,
        next=request.args.get("next", ""),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/metrics")
def metrics():
    rows = []
    try:
        rows = db().execute(
            """SELECT day, event_type, SUM(n) AS n FROM forum_daily
               GROUP BY day, event_type ORDER BY day DESC LIMIT 90"""
        ).fetchall()
    except Exception as e:  # noqa: BLE001 — aggregate may not exist yet
        app.logger.warning("metrics unavailable: %s", e)
        db().rollback()  # failed SELECT aborts the txn; template's current_user() reuses this conn
    return render_template("metrics.html", rows=rows)


@app.route("/search")
def search():
    _probe_vector_search()  # lazy: works under gunicorn too
    q = request.args.get("q", "").strip()
    results, mode = [], "keyword"
    if q:
        vec = vector_search(q)
        if vec is not None:
            results, mode = vec, "semantic"
        else:
            results = keyword_search(q)
    return render_template("search.html", q=q, results=results, mode=mode)


# ---------------------------------------------------------------- docs
# Diagrams (ER + context) live IN the database (docs table, BYTEA images);
# these routes surface them. Added in the populate phase (2026-09-22).
@app.route("/docs")
def docs_index():
    docs = db().execute(
        "SELECT slug, title, diagram_kind, created_at FROM docs ORDER BY slug"
    ).fetchall()
    return render_template("docs.html", docs=docs)


@app.route("/docs/<slug>")
def doc_detail(slug):
    doc = db().execute(
        "SELECT slug, title, body, diagram_kind, image_mime, created_at"
        " FROM docs WHERE slug = %s",
        (slug,),
    ).fetchone()
    if doc is None:
        abort(404)
    return render_template("doc_detail.html", doc=doc)


@app.route("/docs/<slug>/image")
def doc_image(slug):
    row = db().execute(
        "SELECT image, image_mime FROM docs WHERE slug = %s", (slug,)
    ).fetchone()
    if row is None:
        abort(404)
    return Response(bytes(row["image"]), mimetype=row["image_mime"])


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
