# Architecture

SupplyTwin is a single-operator, local-first research and portfolio application. It is working simulation software, not a production planning system or live ERP mirror.

- `packages/supplytwin/domain.py`: strict Pydantic data contracts and acyclic graph validation.
- `data.py`: deterministic PCG64 synthetic generator, templates, and visible import reports.
- `engine.py`: pure time-stepped material simulation and paired comparison, with no HTTP, database, or AI imports.
- `store.py`: SQLite WAL repository; read-only connections for reads, bound SQL parameters, immutable network IDs, immutable run snapshots, transactional scenario versions and idempotency records.
- `ai.py`: runtime protocol, Ollama adapter, schema validation, evidence validation, bounded retry, fallback, and observable telemetry.
- `apps/api`: transport and authorization adapter. It coordinates domain and repository calls.
- `apps/web`: interactive analytical surface; model calculations remain on the server. Charts format computed values only.
- `scripts/benchmark.py`: real measured runs, replay and conservation checks, evidence faithfulness, JSON/CSV/Markdown output.

See [editable diagram](architecture.mmd). There are no remote business services in the default execution path. Model weights are a separate optional download.

## Daily event order

1. Receive shipments scheduled for the current day. Customer receipts increase cumulative delivered units.
2. Suppliers produce against inventory targets, bounded by available production capacity.
3. Draw customer demand from a run-owned seeded NumPy generator. Scenario multipliers scale common random draws only within `[start_day, end_day)`.
4. Dispatch against customer backlog, then replenish DCs from plants and plants from suppliers. Stocks cannot go negative. Plant finishing and DC handling use shared daily capacity; transport uses lane capacity.
5. Schedule arrivals at dispatch day plus the lead time in effect at dispatch. Existing shipments are never retroactively delayed.
6. Accrue holding, backlog, processing, procurement and transport cost. Reconcile material and demand balances and record ledger evidence.

SKUs are continuous equivalent units, including fractional units created by proportional allocation and demand multipliers. Plant finishing is one-to-one; this is not BOM/MRP. Supplier outages stop new production; previously held stock may still ship. Plant/DC outages stop dispatch. Customer backlog excludes allocated orders already in transit.

Order-up-to targets use a fixed baseline forecast, coverage, weighted inbound lead time and safety days. Demand shocks do not grant planners perfect foresight. Sourcing weights normalize across a target's inbound lanes; zero disables a source. Upstream forecast rates change with sourcing weights. Unfilled replenishment is retried from next day's inventory position; it is not a separate persistent purchase-order queue.

## Concurrency and persistence

One API worker serializes simulation calls with a bounded-size input contract. Each run owns its RNG and arrays. SQLite transactions serialize scenario versions and retry receipts. Runs persist full network fingerprints, parameters, engine version, daily evidence and results. The immutable network remains available under its ID. The process lock is not a distributed lock: do not launch multiple API workers. A job queue and database migration framework are future work.

SQLite schema version is recorded as `PRAGMA user_version=1`. Release 0.1 has one additive initialization schema and no destructive migrations. Keep database volume backups before upgrades. No log or run retention policy is automatic.
