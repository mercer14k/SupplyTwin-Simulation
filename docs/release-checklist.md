# Release checklist — 0.1.0 candidate

Local verification is recorded in `verification.md`. Do not mark external checks complete without evidence.

- [x] Deterministic core, sample network and nine templates implemented.
- [x] Conservation, replay, negative paths, SQLite/API and AI-isolation tests pass.
- [x] Browser workflow passes on desktop and mobile; real screenshots committed.
- [x] Measured multi-size benchmark outputs committed with hardware/config.
- [x] No-LLM default, optional local adapter, evidence-backed explanation.
- [x] Environment template, threat model, license inventory and contribution docs included.
- [x] Dockerfiles, Compose and CI build/test/security jobs provided.
- [ ] Run `docker compose up --build` and Compose smoke test on a Docker host.
- [ ] Create/push public GitHub repository using an authenticated publisher.
- [ ] Confirm the first GitHub Actions run passes on the published commit.
- [ ] Enable private vulnerability reporting and branch protection.
- [x] Production dependency audits checked; no known vulnerabilities reported at verification time.
- [ ] Tag v0.1.0 after all external gates pass.

This is a release candidate until the unchecked gates are satisfied; it is not an asserted completed production deployment.
