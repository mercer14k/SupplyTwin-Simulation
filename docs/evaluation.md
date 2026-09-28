# Evaluation

Run `python scripts/benchmark.py --output .local/benchmarks` after installing the backend. The command writes `results.json`, `results.csv`, and `summary.md`; it fails on conservation, replay or supported-claim faithfulness failures. Default generator seed is 17; simulation seed is 42; horizons are 60 days; scales are 1, 2 and 4; each is timed three times. Generation, HTTP and serialization are excluded. A separate tracemalloc run reports Python allocation peak, which must not be described as RSS or total process memory.

Committed example results are measured on the hardware/configuration printed inside each report. They are not universal performance claims. `docs/benchmarks/example` measures the deterministic engine. `docs/benchmarks/local-ai` adds an actual installed model; inspect origin and failures to distinguish model acceptance from deterministic fallback.

To benchmark a different installed model: `python scripts/benchmark.py --model qwen3:8b --scales 1 --output .local/qwen-eval`. The script never downloads weights. This small harness checks evidence IDs, numerical/directional fidelity, missing-evidence abstention, and one explicit natural-language parameter task. It is not a broad language-understanding leaderboard; a 1.0 rendered-claim score with fallback is not a perfect LLM score.

Tests include all disruption templates, nonnegative balances, capacity bounds, common random numbers, fixed-seed repeatability, pure input immutability, invalid graphs, zero demand, zero capacity, and a hand-audited four-node case with 2 opening units, demand [1, 2], dispatch 2, deliveries 1, transit 1, backlog 1 and cost 5. This is independent closed-form ground truth.

API tests use an actual temporary SQLite database. Browser tests exercise baseline/scenario comparison, evidence inspection, replay, version save, export, network search, malformed import, architecture content, and mobile overflow. Model tests inject unavailable, invalid, unsupported and valid outputs and assert deterministic state remains unchanged.

## Screenshot reproduction

1. Start native backend and frontend, or use Compose.
2. Open the scenario workspace at 1512×1050.
3. Select **Austin capacity reduction**, horizon 60, seed 42, active days 10–34, capacity multiplier 0.2.
4. Click **Run comparison**; set displayed day 20.
5. Capture a full-page image. The committed image is `docs/screenshots/workspace.png`.
6. Repeat at 390×844 for responsive behavior.

Automated: `cd apps/web && pnpm e2e`. Screenshots are written under `output/playwright`. With an already running app set `E2E_BASE_URL`; with installed Chrome set `PLAYWRIGHT_CHANNEL=chrome`. CI uses Playwright Chromium.
