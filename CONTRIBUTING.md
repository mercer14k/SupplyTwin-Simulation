# Contributing

Use Python 3.12+, Node 22+, and pnpm 11.25.0. Install the locked dependencies described in README. Keep business rules in `packages/supplytwin`, HTTP behavior in `apps/api`, and display behavior in `apps/web`.

Before submitting: `ruff check .`, `ruff format --check .`, `pytest`, then `cd apps/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build && pnpm e2e`. Run the benchmark for engine changes and include machine/configuration metadata. Do not compare timings from different hardware as if they were equivalent.

A bug report should include the smallest synthetic network/scenario, seed, engine version, expected behavior, trace ID, and result fingerprint. Do not upload credentials or confidential company data. Changes to cost or KPI definitions require docs and independent regression cases. New dependencies require a license entry. Never replace deterministic calculations with model output.

Contributions are licensed under Apache-2.0. Open a focused issue or pull request with the observed problem, change, evidence and limitations. Security reports follow SECURITY.md.
