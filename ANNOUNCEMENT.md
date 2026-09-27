# Lampy — Announcement

**Lampy is here!** 🎉

A single-container, self-hosted forum stack that packs an entire platform
into one Docker image.

## What's inside

- 🗄️ **PostgreSQL 16** with TimescaleDB + pgvector (vector search built in)
- 🌐 **Apache** web server
- 🤖 **Ollama** with Qwen3 — local LLM, no API keys needed
- 📧 **Apache James** mail server
- 💻 **code-server** — VS Code in your browser
- 🔍 **pgai** vectorizer worker for AI-powered search
- 💬 **Flask** forum app ready to go

One container. One command. Your own forum with AI search, email, and
code editing.

## Get it

It's public domain ([UNLICENSE](UNLICENSE)) — build it yourself or pull
the image:

- 📦 Docker Hub: `kitcosby/lampy-single:latest`
- 📦 GitHub Container Registry: `ghcr.io/cosbykit-afk/lampy-single:latest`
- 💻 Source: https://github.com/cosbykit-afk/lampy-single

```bash
docker run -d --name lampy -p 80:80 -p 443:443 kitcosby/lampy-single:latest
```

Default credentials are `password` / `password` (override with
`-e PASSWORD=... -e POSTGRES_PASSWORD=...` at runtime).
