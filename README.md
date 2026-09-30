# Lampy Single

A single Docker container that runs the full Lampy forum stack: PostgreSQL (with TimescaleDB + pgvector), Apache, Ollama (with Gwen), James mail server, code-server, pgai-vectorizer worker, and a Flask forum app.

## Pull the prebuilt image

No build needed — pull from either registry:

```bash
# Docker Hub
docker pull kitcosby/lampy-single:latest

# GitHub Container Registry
docker pull ghcr.io/cosbykit-afk/lampy-single:latest
```

Both point to the same image
(digest `sha256:69a301fb52d664e31105972d88b1d2431d923e2bb8474e2c531e08a59e004455`).

## What's inside

| Program | Role |
|---|---|
| PostgreSQL 16 | Database (TimescaleDB, pgvector, pgai) |
| Apache 2 | Web server, proxies `/app` to the forum |
| Ollama | LLM runtime (ships `qwen3:0.6b` + `gwen:latest`) |
| James | Mail server (JPA/Guice) |
| code-server | VS Code in the browser (:8080) |
| pgai-worker | Vectorizer worker |
| forum | Flask + gunicorn app on 127.0.0.1:8000 |

## Build prerequisites

The Dockerfile expects two directories in the build context (they are **not** in this repo):

- `wheelhouse/` — offline Python wheelhouse (209 wheels: torch, pgai, flask, gunicorn, psycopg, etc.)
- `ollama-donor/` — vendored Ollama binaries (`/usr/bin/ollama`, `/usr/lib/ollama/`, `/usr/share/ollama/`)

Place them next to the Dockerfile, then:

```bash
docker build -t lampy-single .
```

## Run

With the ship defaults (password is `password` for code-server and PostgreSQL):

```bash
docker run -d --name lampy -p 8080:8080 -p 8000:8000 lampy-single
```

With your own passwords:

```bash
docker run -d --name lampy \
  -e PASSWORD='your-code-server-password' \
  -e POSTGRES_PASSWORD='your-db-password' \
  -p 8080:8080 -p 8000:8000 lampy-single
```

The forum app is served at `http://localhost:8000/` directly and via Apache at `http://localhost/app/`.

## Validate

```bash
./pressure-test.sh lampy-single
```

Checks the image filesystem for required binaries, configs, symlinks, and scans for leaked secrets. Needs a Linux host (or WSL2) — Git Bash on Windows cannot create the symlinks.

## Layout

- `Dockerfile` — the image definition
- `supervisord.conf` — process supervision (all 7 programs)
- `forum-app/` — Flask forum source (templates + schema)
- `forum-start.sh` — forum bootstrap (waits for Postgres, creates role/db, applies schema, starts gunicorn)
- `apache2-lampy.conf` — Apache vhost (proxies `/app` → 127.0.0.1:8000)
- `codeserver-start.sh`, `pgai-worker.sh` — service launchers
- `Modelfile.gwen` — Gwen model definition
- `pressure-test.sh` — image validation harness
- `build.sh`, `build-cloud.sh` — build helpers

## Build status (2026-09-28)

- **Image published** — `kitcosby/lampy-single:windows-1.0.0`
  (digest `sha256:69a301fb52d664e31105972d88b1d2431d923e2bb8474e2c531e08a59e004455`),
  mirrored as `ghcr.io/cosbykit-afk/lampy-single:latest`.
- **Build inputs** — the Dockerfile's `wheelhouse/` and `ollama-donor/`
  directories come from the
  [build-deps-v1 release](https://github.com/cosbykit-afk/lampy-deps/releases/tag/build-deps-v1)
  on [lampy-deps](https://github.com/cosbykit-afk/lampy-deps)
  (see that repo's README for assembly instructions and checksums).
- **Validated** — `pressure-test.sh` passes against the published image;
  all 7 supervisord programs start.

## Known issues

- **Empty `build-deps-v1` release on this repo** — a leftover tag with no
  assets; the real dependency files are on
  [lampy-deps](https://github.com/cosbykit-afk/lampy-deps/releases/tag/build-deps-v1).
  Ignore the one here.
- **`latest` tags float** — pin the digest
  (`sha256:69a301fb52d664e31105972d88b1d2431d923e2bb8474e2c531e08a59e004455`)
  if you need a reproducible pull.

## License

Public domain — see [UNLICENSE](UNLICENSE).
