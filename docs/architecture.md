Living document — update these diagrams when adding features.

# lampy-single — Architecture

The lampy-single repo is the Docker single-container build for the Lampy forum stack: a Dockerfile, supervisord config, the Flask forum app source, build and validation scripts, and a GitHub Actions workflow that copies the published image from Docker Hub to GHCR.

## 1. Context diagram (level 0)

```mermaid
flowchart LR
    E1["Kit"]
    S0("lampy-single repo")
    E2["External build context"]
    E3["Docker Hub"]
    E4["GHCR"]
    E5["Image users"]

    E1 -->|"runs build.sh"| S0
    E2 -->|"wheelhouse and ollama-donor dirs"| S0
    S0 -->|"publishes kitcosby slash lampy-single latest"| E3
    E3 -->|"crane copy workflow"| E4
    E3 -->|"pulls image"| E5
    E4 -->|"pulls image"| E5
```

## 2. Level-1 data flow diagram

```mermaid
flowchart LR
    E1["Kit"]
    E2["External build context"]
    E3["Image users"]
    P1("1.0 Build image")
    P2("2.0 Validate image")
    P3("3.0 Publish image")
    P4("4.0 Copy to GHCR")
    D1[("D1 Repo source files")]
    D2[("D2 Built image artifact")]
    D3[("D3 Docker Hub")]
    D4[("D4 GHCR")]

    E1 -->|"runs build.sh"| P1
    D1 -->|"Dockerfile forum-app supervisord conf scripts"| P1
    E2 -->|"wheelhouse and ollama-donor dirs"| P1
    P1 -->|"lampy-single latest"| D2
    D2 -->|"image under test"| P2
    P2 -->|"pass fail report"| E1
    P2 -->|"passed image"| P3
    P3 -->|"pushes kitcosby lampy-single"| D3
    D3 -->|"copy workflow dispatch"| P4
    P4 -->|"crane copies image"| D4
    D3 -->|"pulls"| E3
    D4 -->|"pulls"| E3
```

## 3. Entity–relationship diagram

No persistent data model observed — the repo is a build recipe; there is no database or schema of its own. The forum-app schema.sql in the repo belongs to the Flask app's runtime database, not to this repo. The only persisted artifacts are container image records in the registries:

```mermaid
erDiagram
    IMAGE {
        string registry
        string repository
        string tag
        string digest
    }
```

## Grounding notes

- OBSERVED: README.md states the image runs the full Lampy forum stack (PostgreSQL with TimescaleDB and pgvector, Apache, Ollama with Gwen, James mail server, code-server, pgai-vectorizer worker, Flask forum app), pullable from Docker Hub `kitcosby/lampy-single:latest` and GHCR `ghcr.io/cosbykit-afk/lampy-single:latest`, both pointing to digest `sha256:69a30fb52d664e31105972d88b1d243d923e2bb8474e2c531e08a55e004455` (first 64 hex chars of the digest shown verbatim in README).
- OBSERVED: the Dockerfile header lists the seven supervisord services and says the Dockerfile expects `wheelhouse/` and `ollama-donor/` directories in the build context, explicitly noted as NOT in this repo.
- OBSERVED: `build.sh`, `build-cloud.sh`, `build-wheelhouse.sh`, `pressure-test.sh` exist at repo root; README says pressure-test.sh checks the image filesystem for required binaries, configs, symlinks, and scans for leaked secrets.
- OBSERVED: `.github/workflows/copy-to-ghcr.yml` is a manual workflow-dispatch job that uses crane to copy `docker.io/kitcosby/lampy-single:latest` to `ghcr.io/cosbykit-afk/lampy-single:latest`.
- OBSERVED: `forum-app/` contains `app.py`, `config.py`, `requirements.txt`, `schema.sql`, and 11 Jinja templates — the Flask forum source bundled into the image at build time.
- INFERRED: the exact build trigger (Kit runs build.sh by hand vs a scheduled run) — no CI build workflow exists in the repo, only the GHCR copy workflow, so the build step is manual.
- INFERRED: image consumers beyond Kit — the public-registry pulls and the LICENSE/unlicense files imply other users may pull the image, but no consumer list was observed.
