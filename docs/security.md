# Threat model

Assets: imported network data, scenario history, computed evidence, API token, model endpoint configuration. Trust boundaries: browser/API, imported JSON/domain schema, application/SQLite, and application/local model. Default deployment is one trusted operator on loopback. It provides no multi-tenant separation, Internet-ready identity layer, or enterprise integration claim.

| Threat | Implemented control | Residual limit |
|---|---|---|
| Malformed/oversized network | JSON MIME check, 10 MiB streamed limit, strict finite numeric schemas, graph constraints, validation audit | JSON object materialization still consumes bounded memory |
| Expensive simulation | node/SKU/day work limit, horizon limits, serialized run lock | No distributed job queue; authorized calls can consume local CPU |
| Cross-site mutation | Origin allowlist, optional constant-time bearer-token check | Loopback binding is the default operator boundary; read endpoints intentionally public locally |
| Filename traversal | Strip both separator forms and non-safe characters; filenames are audit metadata only | No uploaded code or filesystem extraction occurs |
| SQL injection | Bound parameters, fixed SQL, query-only read connections | Local users with filesystem access can read the database |
| Prompt injection | Treat all model inputs as data; structured schemas; no model tools, SQL or shell | Semantic mistranslation remains possible and requires review |
| Fabricated explanation | Validate cited IDs/directions; render values from immutable evidence | Constrained explanation has limited causal depth |
| Runtime outage | Bounded timeout/retry; deterministic fallback; no state mutation by AI | Request may wait for two model attempts |
| Secrets in logs | No auth header or raw prompt logging; `.env` ignored | Imported data and run snapshots are plaintext on disk |
| Browser injection | React text escaping, no dynamic HTML, self-only production CSP | API docs viewer uses FastAPI's upstream CDN assets |

Compose exposes only loopback ports, runs app containers without root application processes, and sets no-new-privileges. The Ollama endpoint is operator configuration, not model-controlled. Never expose these services directly to the Internet. For shared environments add TLS, authentication on reads, tenant scoping, rate limits, model endpoint policy and a job queue before deployment.

Set `API_TOKEN` to a unique value to protect mutations; the browser stores a supplied token in session storage for the tab session. Read routes use SQLite `mode=ro` and `query_only`. DB files and local model prompts never go to paid/cloud AI. All model downloads and package installations remain external network actions.

Audit and run retention are manual. Back up the data volume before upgrades and remove imported sensitive data when no longer needed. Reports and example datasets committed here contain synthetic information only.
