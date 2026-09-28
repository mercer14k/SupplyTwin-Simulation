# Measured SupplyTwin benchmark

This is an actual local measurement, not a performance guarantee.

Recorded: 2026-09-27T20:46:51.308749+00:00
Hardware: Apple M5; 10 logical CPUs; macOS-26.6.2-arm64-arm-64bit
Python 3.12.14; NumPy 2.5.3; engine 1.0.0; model disabled.

Timing excludes generation, HTTP and serialization. Python allocation peak is a separate traced run; it is not process RSS.

| Nodes | SKUs | Demand records | Days | Median seconds | Python peak MiB | Replay | Balance |
|---:|---:|---:|---:|---:|---:|---|---|
| 41 | 60 | 1800 | 60 | 0.0312 | 3.05 | True | True |
| 71 | 120 | 7200 | 60 | 0.0620 | 9.38 | True | True |
| 131 | 240 | 28800 | 60 | 0.1604 | 33.53 | True | True |

Evidence faithfulness: 1.0 over 3 claims (deterministic).
Measures supported evidence and numeric/directional fidelity of constrained claims, not natural-language semantic quality.

No-LLM results do not measure a language model. Local-model failures and fallback are retained in the JSON telemetry.

Regenerate: `python scripts/benchmark.py --output .local/benchmarks`.
