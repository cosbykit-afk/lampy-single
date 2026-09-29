Living document — update these diagrams when adding features.

# lampy-single — Architecture

The lampy-single repo is the Docker single-container **build recipe and image-validation vehicle** for the Lampy forum stack — it is NOT the live Lampy, which runs natively in the WSL distro `lampy` on Toetop under supervisord. This repo holds the Dockerfile, supervisord config, the Flask forum app source, build/validation scripts, and a GitHub Actions workflow that copies the published image from Docker Hub to GHCR. The built image packs the whole stack (PostgreSQL 16 with TimescaleDB + pgvector, Apache, Ollama with Gwen, James mail server, code-server, pgai-vectorizer worker, Flask forum app) into one container, supervised by supervisord as PID 1.

Build inputs that are NOT in this repo: `wheelhouse/` (209-wheel offline Python wheelhouse) and `ollama-donor/` (vendored Ollama binaries) — both supplied by the **lampy-deps `build-deps-v1` release** (see the lampy-deps architecture doc). 13 commits total; HEAD is the SAD doc commit of 2026-09-28.

## 1. Context diagram (level 0)

```mermaid
flowchart LR
    E1["Kit"]
    E2["lampy-deps build-deps-v1 release"]
    E3["Upstream image sources"]
    E4["Docker Hub"]
    E5["GHCR"]
    E6["Image users"]

    subgraph SYS["lampy-single repo (system boundary)"]
        S0("lampy-single repo")
    end

    E1 -->|"build invocation"| S0
    E1 -->|"GHCR copy dispatch command"| S0
    E2 -->|"dependency tar part files"| S0
    E3 -->|"pinned base image layers"| S0
    S0 -->|"kitcosby/lampy-single:latest image"| E4
    E4 -->|"image pull for copy"| S0
    S0 -->|"ghcr.io/cosbykit-afk/lampy-single:latest image"| E5
    E4 -->|"image pulls"| E6
    E5 -->|"image pulls"| E6
    S0 -->|"validation report"| E1
```

## 2. Level-1 data flow diagram

```mermaid
flowchart LR
    E1["Kit"]
    E2["lampy-deps build-deps-v1 release"]
    E3["Upstream image sources"]
    E4["Docker Hub"]
    E5["GHCR"]
    E6["Image users"]
    P1("1.0 Fetch build dependencies")
    P2("2.0 Build image")
    P3("3.0 Validate image")
    P4("4.0 Publish to Docker Hub")
    P5("5.0 Copy to GHCR")
    D1[("D1 Build context dependencies")]
    D2[("D2 Repo source files")]
    D3[("D3 Built image")]

    E2 -->|"build-deps-v1 .partNN assets"| P1
    P1 -->|"concatenated wheelhouse.tar and ollama-donor.tar"| D1
    E1 -->|"runs build.sh"| P2
    D2 -->|"Dockerfile, forum-app, supervisord conf, scripts"| P2
    D1 -->|"extracted wheelhouse/ and ollama-donor/ dirs"| P2
    E3 -->|"pinned base image layers"| P2
    P2 -->|"lampy-single:latest image"| D3
    D3 -->|"image under test"| P3
    P3 -->|"pass/fail report"| E1
    P3 -->|"validated image"| P4
    P4 -->|"pushes kitcosby/lampy-single"| E4
    E1 -->|"workflow dispatch"| P5
    E4 -->|"kitcosby/lampy-single:latest"| P5
    P5 -->|"pushes ghcr.io/cosbykit-afk/lampy-single:latest"| E5
    E4 -->|"image pulls"| E6
    E5 -->|"image pulls"| E6
```

## 3. Entity–relationship diagram

No persistent data model of the repo's own — it is a build recipe; the `forum-app/schema.sql` belongs to the Flask app's runtime database, not to this repo. The only persisted records are the container image entries in the two registries:

```mermaid
erDiagram
    REGISTRY {
        string name PK
    }
    IMAGE {
        string registry FK
        string repository
        string tag
        string digest
    }
    REGISTRY ||--o{ IMAGE : hosts
```

Natural key of IMAGE is (registry, repository, tag). Observed rows: (`docker.io`, `kitcosby/lampy-single`, `latest`) and (`ghcr.io`, `cosbykit-afk/lampy-single`, `latest`), both with digest `sha256:69a301fb52d664e31105972d88b1d2431d923e2bb8474e2c531e08a59e004455`.

## Grounding notes

- OBSERVED: README.md states the image runs the full Lampy forum stack (PostgreSQL with TimescaleDB and pgvector, Apache, Ollama with Gwen, James mail server, code-server, pgai-vectorizer worker, Flask forum app), pullable from Docker Hub `kitcosby/lampy-single:latest` and GHCR `ghcr.io/cosbykit-afk/lampy-single:latest`, both pointing to digest `sha256:69a301fb52d664e31105972d88b1d2431d923e2bb8474e2c531e08a59e004455` (64 hex chars, copied verbatim from README via regex — the previous doc's digest string was corrupted; this one is exact).
- OBSERVED: Dockerfile header — base `timescale/timescaledb-ha:pg16` pinned at `sha256:4f288c0a521362cad799f265bc0ebd60c3f8f98596b850172cc2da72883420ff`; resets `USER root` and `ENTRYPOINT []`; ships defaults `PASSWORD=password`, `POSTGRES_PASSWORD=<redacted>`; seven supervisord programs: postgres, apache2, ollama, james, codeserver, pgai-worker, forum (confirmed in `supervisord.conf` with exact commands, e.g. James runs `/usr/bin/java -Dworking.directory=/opt/james/james-server-jpa-guice -jar james-server-jpa-app.jar`).
- OBSERVED: Dockerfile bakes Gwen in at build time (`Modelfile.gwen`: `FROM qwen3:0.6b`, temperature 0.7, num_ctx 4096, admin SYSTEM prompt) via `ollama create`; Ollama binaries are vendored from the build context (`COPY lampy-single/ollama-donor/...`), extracted byte-identical from `ollama/ollama:latest@sha256:da6e0dc5651df159e45686fd663c4dbe1624a52c44d7280eeac1551d8f865532` by `vendor-ollama.sh`.
- OBSERVED: README's "Build prerequisites" — the Dockerfile expects `wheelhouse/` (209 wheels: torch, pgai, flask, gunicorn, psycopg, etc.) and `ollama-donor/` (`/usr/bin/ollama`, `/usr/lib/ollama/`, `/usr/share/ollama/`) in the build context, NOT in this repo; the repo description says "Build deps in cosbykit-afk/lampy-deps", which now hosts them in the `build-deps-v1` release (7 split tar parts).
- OBSERVED: `build.sh` runs `docker build -f lampy-single/Dockerfile -t lampy:latest .` from the *parent* of the repo (forum-stack root); `build-wheelhouse.sh` rebuilds the wheelhouse from PyPI (`pip download`, cp310, manylinux x86_64, pinned `wheelhouse-packages.txt`, 218 lines); `pressure-test.sh` is the validation harness (Dockerfile references its phase 6 digest-pin check); README says it checks the image filesystem for required binaries, configs, symlinks, and scans for leaked secrets.
- OBSERVED: `forum-start.sh` waits up to 60s for postgres, idempotently creates the `forum` role/database, enables TimescaleDB and applies `schema.sql`, then starts gunicorn on 127.0.0.1:8000 (README: forum served at `http://localhost:8000/` directly and via Apache at `http://localhost/app/`); `pgai-worker.sh` runs `python3 -m pgai vectorizer worker --poll-interval 30s` against `postgres://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres`.
- OBSERVED: `.github/workflows/copy-to-ghcr.yml` is a manual `workflow_dispatch` job: installs crane v0.22.1, logs into GHCR with `GITHUB_TOKEN`, runs `crane copy docker.io/kitcosby/lampy-single:latest ghcr.io/cosbykit-afk/lampy-single:latest`.
- OBSERVED: `forum-app/` holds `app.py`, `config.py`, `requirements.txt`, `schema.sql`, and 11 Jinja templates. `ANNOUNCEMENT.md` is release marketing copy; `UNLICENSE`/`COMPONENT_LICENSES.md`/`FEES.md` are license/fee notes.
- OBSERVED inconsistency: README says "Place them next to the Dockerfile, then: `docker build -t lampy-single .`", but the Dockerfile `COPY`s `lampy-single/ollama-donor/...` and `lampy-single/Modelfile.gwen` (paths prefixed with `lampy-single/`), and `build.sh` cds to the repo's parent — so the real build context is the forum-stack root, not the repo root. The README instruction would fail against the committed Dockerfile.
- INFERRED: the build step is manual (Kit runs `build.sh` by hand) — no CI build workflow exists in the repo, only the GHCR copy workflow.
- INFERRED: the P1 concatenation/extraction into `wheelhouse/` and `ollama-donor/` dirs — the lampy-deps release procedure says "concatenate in order"; the tar→dir expansion matches Dockerfile expectations by name but is not spelled out in either repo.
- INFERRED: image consumers beyond Kit — public-registry pulls and the UNLICENSE imply other users may pull the image, but no consumer list was observed.
