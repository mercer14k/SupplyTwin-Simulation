# Verification record

Verified locally on 2026-09-27, Apple M5 / macOS 26.6.2 arm64, Python 3.12.14, Node from the local development runtime, with the committed dependency locks.

| Check | Evidence / status |
|---|---|
| Backend Ruff lint and formatting | Passed |
| Backend unit and integration suite | 37 tests passed; detailed coverage report in `verification-backend.txt` |
| Frontend ESLint / TypeScript | Passed |
| Frontend Vitest | 2 tests passed |
| Production frontend bundle | Built successfully; network renderer split from the main interface |
| Playwright desktop/mobile workflows | 2 tests passed in installed Chrome |
| Deterministic benchmark | 3 sizes × 3 timed repeats; conservation and replay passed |
| Actual local model | Ollama Qwen3:8b; one explicit proposal correct, supported evidence selection accepted; raw metadata and telemetry committed |
| Python production dependency audit | No known vulnerabilities reported; `security-audits/python.json` |
| Frontend production dependency audit | No known vulnerabilities reported; `security-audits/frontend.json` |
| Mermaid architecture | Canonical schema and static lint passed; not a claim of renderer acceptance |
| Docker Compose | Not executed here: Docker runtime is absent. CI smoke job is provided |
| GitHub publishing | Not executed: no local Git publishing credential; in-app GitHub browser is signed out |
| Hosted CI | Not observed; requires repository publication |

Audits are point-in-time checks, not guarantees. Current Starlette emits a deprecation notice for its HTTPX TestClient adapter; tests pass, and the warning is retained rather than hidden. No CI badge claims a remote pass.

The project's intended source is public, but no public repository URL is claimed before a successful authenticated push. A source ZIP and initialized local Git repository are provided. After signing in with GitHub CLI, publish from the repository root using:

```sh
gh repo create supplytwin --public --source . --remote origin --push
gh run list
```

Review the Actions result, enable private vulnerability reporting, then complete the release checklist before tagging. If a repository named `supplytwin` already exists, inspect it before choosing a different name; do not force-push over unrelated work.
