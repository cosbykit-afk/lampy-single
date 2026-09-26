# Component Licenses

This image bundles the following major components. Their licenses apply to
their respective code; the Lampy build scripts and forum app in this repo
are public domain (see UNLICENSE).

## Verified in the image

| Component | Version | License |
|---|---|---|
| pgai | 0.12.1 | PostgreSQL License (per `METADATA` classifier) |

## Services

| Component | License |
|---|---|
| PostgreSQL 16 | PostgreSQL License |
| TimescaleDB | Timescale License (source-available; not OSI-approved) |
| pgvector | PostgreSQL License |
| Apache HTTP Server 2.4 | Apache License 2.0 |
| Ollama | MIT License |
| Apache James (mail server) | Apache License 2.0 |
| code-server | MIT License |

## Python stack

| Component | License |
|---|---|
| Python 3.10 | Python Software Foundation License |
| PyTorch 2.14 (+CUDA) | BSD 3-Clause |
| Flask 3.1 | BSD 3-Clause |
| Gunicorn | MIT License |
| psycopg (v3, binary) | LGPL-3.0 |

## Models

| Component | License |
|---|---|
| Qwen3 0.6B (`qwen3:0.6b`, `gwen:latest`) | Apache License 2.0 |

## Base

Ubuntu 24.04 — individual packages carry their own licenses (GPL, LGPL,
MIT, Apache-2.0, etc.); see `/usr/share/doc/*/copyright` in the image.

Note: the full transitive dependency tree (209 Python wheels, system
packages) contains additional licenses. The table above covers the
top-level components a rebuilder or redistributor is most likely to ask
about.
