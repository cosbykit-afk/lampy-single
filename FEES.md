# Fees and Commercial Licensing

What it costs to run Lampy commercially, per component. See
COMPONENT_LICENSES.md for the license of each part; this file is about
money.

## The one hard rule: TimescaleDB

TimescaleDB ships under two licenses. The core (hypertables, basic
time-series) is Apache 2.0. The advanced features this image uses —
columnar compression, continuous aggregates, retention policies — are
under the **Timescale License (TSL)**, a source-available license.

The TSL is **free for self-hosted use at any scale**, including
commercial and internal production use. There is exactly one thing it
forbids:

> **You may not offer TimescaleDB itself as a hosted database service
> (DBaaS) to third parties.**

Running Lampy for your own forum, your company's forum, or your SaaS
product's forum is fine. Selling "TimescaleDB-as-a-service" to the
public is not — that requires a commercial agreement with Tiger Data
(the company behind TimescaleDB).

This is why AWS RDS and similar services ship only the Apache-2.0
subset of TimescaleDB features.

## License fees per component: $0

Every constituent part of this stack is **free to use commercially**.
There are no license fees to pay, at any company size, for:

| Component | License | Commercial license fee |
|---|---|---|
| PostgreSQL 16 | PostgreSQL License | $0 |
| TimescaleDB (self-hosted) | Apache 2.0 + Timescale License | $0 |
| pgvector | PostgreSQL License | $0 |
| pgvectorscale | PostgreSQL License | $0 |
| pgai | PostgreSQL License | $0 |
| Apache HTTP Server 2.4 | Apache License 2.0 | $0 |
| Apache James (mail) | Apache License 2.0 | $0 |
| Ollama | MIT License | $0 |
| code-server | MIT License | $0 |
| Python 3.10 | PSF License | $0 |
| PyTorch | BSD 3-Clause | $0 |
| Flask | BSD 3-Clause | $0 |
| Gunicorn | MIT License | $0 |
| Qwen3 0.6B (model weights) | Apache License 2.0 | $0 |

The Apache License 2.0 already permits commercial and corporate use.
There is no "commercial Apache license" to buy from the Apache Software
Foundation — the license you have *is* the commercial license. The same
holds for the MIT, BSD, PSF, and PostgreSQL licenses above.

Note: the Ollama *software* is MIT (free). Individual *model weights*
you run through it carry their own licenses — check the model card.
The bundled Qwen3 0.6B weights are Apache 2.0.

## Where money actually goes at enterprise scale

If you take Lampy corporate, the costs are operational, not licensing:

**Self-hosted (any size).** License fees: $0. You pay for hardware or
cloud VMs, bandwidth, and whoever operates it. The TSL permits this.

**Commercial support (optional).** If you want a vendor to answer the
phone:
- TimescaleDB: Tiger Data sells TimescaleDB Enterprise (commercially
  supported self-managed TimescaleDB, priced on compute capacity) and
  offers support for self-managed deployments. Tiger Cloud is their
  fully managed offering (pay-as-you-go).
- PostgreSQL: support contracts from vendors such as EDB or Crunchy
  Data (pricing is per-engagement — contact the vendor).
- Apache HTTP Server / James: no vendor sells licenses; third-party
  support firms offer Apache httpd support contracts.

**Managed database (instead of self-hosting).** Tiger Cloud
(pay-as-you-go, compute + storage) if you want TimescaleDB run for you.
Note the TSL restriction above runs the other direction: *you* cannot
be the one selling managed TimescaleDB.

## Summary

- Going corporate changes nothing about what you owe for the software:
  **$0** in license fees across the whole stack.
- The single legal boundary is the Timescale License: do not resell
  TimescaleDB as a hosted database service.
- Budget for servers, operators, and optional support contracts — not
  licenses.
