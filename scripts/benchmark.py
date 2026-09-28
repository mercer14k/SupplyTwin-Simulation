"""One command: python scripts/benchmark.py --output docs/benchmarks/example

Actual measurements only; network generation excluded from timed simulation runs.
"""

import argparse
import csv
import json
import os
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

from supplytwin.ai import AIService, OllamaRuntime, direction
from supplytwin.data import generate, templates
from supplytwin.engine import ENGINE_VERSION, compare, simulate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".local/benchmarks"))
    parser.add_argument("--scales", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--model", help="Optional installed Ollama model; never downloaded by this script")
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be >= 1")
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = dict(
        timestamp=datetime.now(timezone.utc).isoformat(),
        os=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        logical_cpus=os.cpu_count(),
        python=sys.version.split()[0],
        engine=ENGINE_VERSION,
        numpy=__import__("numpy").__version__,
        model=args.model or "disabled",
        seed=42,
        generator_seed=17,
        repeats=args.repeats,
        protocol="Timing excludes generation, HTTP and serialization. Python allocation peak is a separate traced run; it is not process RSS.",
    )
    if sys.platform == "darwin":
        import subprocess

        metadata["hardware"] = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
        ).strip()
        metadata["physical_memory_bytes"] = int(
            subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
        )
    if args.model:
        import httpx

        with httpx.Client(timeout=5, trust_env=False) as client:
            try:
                metadata["ollama_version"] = client.get("http://localhost:11434/api/version").json()
                metadata["model_artifact"] = next(
                    (
                        m
                        for m in client.get("http://localhost:11434/api/tags").json().get("models", [])
                        if m["name"] == args.model
                    ),
                    None,
                )
            except (httpx.HTTPError, ValueError):
                metadata["ollama_version"] = "unavailable"
    rows = []
    for scale in args.scales:
        network = generate(scale=scale)
        scenario = templates()[2]
        durations, hashes = [], []
        for _ in range(args.repeats):
            start = time.perf_counter()
            result = simulate(network, scenario)
            durations.append(time.perf_counter() - start)
            hashes.append(result["result_hash"])
        tracemalloc.start()
        simulate(network, scenario)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        row = dict(
            scale=scale,
            nodes=len(network.nodes),
            lanes=len(network.lanes),
            skus=len(network.skus),
            demand_records=len(network.demand),
            horizon=scenario.horizon,
            median_seconds=statistics.median(durations),
            min_seconds=min(durations),
            max_seconds=max(durations),
            python_peak_mib=peak / 1024 / 1024,
            reproducible=len(set(hashes)) == 1,
            conservation_passed=result["invariants"]["passed"],
            max_mass_error=result["invariants"]["max_mass_error"],
            result_hash=hashes[0],
        )
        rows.append(row)
        print(json.dumps(row), flush=True)
    comparison = compare(generate(), templates()[2])
    service = AIService(OllamaRuntime(model=args.model) if args.model else None)
    explanation = service.explain(comparison)
    evidence = {e["id"]: e for e in comparison["evidence"]}
    faithful = [
        c["id"] in evidence
        and c["delta"] == evidence[c["id"]]["delta"]
        and c["direction"] == direction(evidence[c["id"]]["delta"])
        for c in explanation["claims"]
    ]
    ai = dict(
        mode=explanation["origin"],
        model=args.model or "disabled",
        claims=len(faithful),
        evidence_faithfulness=sum(faithful) / len(faithful) if faithful else None,
        missing_evidence_abstains=service.explain(None)["status"] == "abstained",
        telemetry=explanation["telemetry"],
        limitation="Measures supported evidence and numeric/directional fidelity of constrained claims, not natural-language semantic quality.",
    )
    if args.model:
        proposal = service.propose(
            "Reduce Austin Assembly capacity to 20% of normal from day 10 through day 34, inclusive. Keep a 60-day horizon and seed 42.",
            generate(),
        )
        candidate = proposal.get("scenario") or {}
        ai["proposal"] = dict(
            status=proposal["status"],
            correct=candidate.get("capacity_multipliers") == {"PLT-01": 0.2}
            and candidate.get("start_day") == 10
            and candidate.get("end_day") == 35,
            telemetry=proposal["telemetry"],
        )
    report = dict(
        metadata=metadata,
        measurements=rows,
        ai_evaluation=ai,
        comparison_kpis={
            "baseline": comparison["baseline"]["kpis"],
            "scenario": comparison["scenario"]["kpis"],
            "deltas": comparison["deltas"],
        },
    )
    (args.output / "results.json").write_text(json.dumps(report, indent=2))
    with (args.output / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Measured SupplyTwin benchmark",
        "",
        "This is an actual local measurement, not a performance guarantee.",
        "",
        f"Recorded: {metadata['timestamp']}",
        f"Hardware: {metadata.get('hardware', metadata['machine'])}; {metadata['logical_cpus']} logical CPUs; {metadata['os']}",
        f"Python {metadata['python']}; NumPy {metadata['numpy']}; engine {ENGINE_VERSION}; model {metadata['model']}.",
        "",
        metadata["protocol"],
        "",
        "| Nodes | SKUs | Demand records | Days | Median seconds | Python peak MiB | Replay | Balance |",
        "|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    lines += [
        f"| {r['nodes']} | {r['skus']} | {r['demand_records']} | {r['horizon']} | {r['median_seconds']:.4f} | {r['python_peak_mib']:.2f} | {r['reproducible']} | {r['conservation_passed']} |"
        for r in rows
    ]
    lines += [
        "",
        f"Evidence faithfulness: {ai['evidence_faithfulness']} over {ai['claims']} claims ({ai['mode']}).",
        ai["limitation"],
        "",
        "No-LLM results do not measure a language model. Local-model failures and fallback are retained in the JSON telemetry.",
        "",
        "Regenerate: `python scripts/benchmark.py --output .local/benchmarks`.",
    ]
    if args.model:
        lines += [
            "",
            f"Explicit proposal task: {ai['proposal']['status']}; expected parameters matched: {ai['proposal']['correct']}. This is one test case.",
        ]
    (args.output / "summary.md").write_text("\n".join(lines) + "\n")
    if not all(r["conservation_passed"] and r["reproducible"] for r in rows) or not all(faithful):
        raise SystemExit("Evaluation failed")


if __name__ == "__main__":
    main()
