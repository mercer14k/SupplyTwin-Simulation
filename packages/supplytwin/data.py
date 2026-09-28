"""Synthetic, reproducible data with provenance and visible validation."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from .domain import SKU, Demand, Issue, Lane, Network, Node, Scenario, ValidationReport

STAMP = datetime(2026, 1, 1, tzinfo=timezone.utc)


def generate(seed: int = 17, scale: int = 1) -> Network:
    if not 1 <= scale <= 4:
        raise ValueError("scale must be 1..4")
    rng = np.random.default_rng(seed)
    source = f"synthetic-{seed}-x{scale}"
    provenance = {
        "source_id": source,
        "ingested_at": STAMP,
        "lineage": {"generator": "1.0.0", "seed": str(seed)},
    }
    places = [
        ("SUP-01", "Osaka Components", "supplier", 34.69, 135.5),
        ("SUP-02", "Kaohsiung Materials", "supplier", 22.63, 120.3),
        ("SUP-03", "Monterrey Supply", "supplier", 25.67, -100.3),
        ("SUP-04", "Brno Precision", "supplier", 49.2, 16.61),
        ("PLT-01", "Austin Assembly", "plant", 30.27, -97.74),
        ("PLT-02", "Rotterdam Assembly", "plant", 51.92, 4.48),
        ("DC-01", "Los Angeles", "dc", 34.05, -118.24),
        ("DC-02", "Chicago", "dc", 41.88, -87.63),
        ("DC-03", "Frankfurt", "dc", 50.11, 8.68),
        ("DC-04", "Singapore", "dc", 1.35, 103.82),
        ("DC-05", "São Paulo", "dc", -23.55, -46.63),
    ]
    nodes = []
    for ident, name, kind, lat, lon in places:
        capacity = {"supplier": 700, "plant": 1600, "dc": 700}[kind] * scale**2
        nodes.append(
            Node(
                id=ident,
                name=name,
                kind=kind,
                latitude=lat,
                longitude=lon,
                capacity=capacity,
                coverage_days=3 if kind == "dc" else 5,
                safety_days=2,
                initial_days=5 if kind == "dc" else 7,
                process_cost={"supplier": 0, "plant": 2.5, "dc": 0.3}[kind],
                **provenance,
            )
        )
    for i in range(30 * scale):
        dc = nodes[6 + i % 5]
        nodes.append(
            Node(
                id=f"CUS-{i + 1:03}",
                name=f"{dc.name} customer {i // 5 + 1:02}",
                kind="customer",
                latitude=float(np.clip(dc.latitude + rng.normal(0, 4), -85, 85)),
                longitude=float(np.clip(dc.longitude + rng.normal(0, 5), -175, 175)),
                capacity=0,
                coverage_days=0,
                safety_days=0,
                initial_days=0,
                **provenance,
            )
        )
    skus = [
        SKU(
            id=f"SKU-{i + 1:03}",
            name=f"Module {i + 1:03}",
            unit_cost=round(float(rng.uniform(8, 45)), 2),
            holding_cost=0.015,
            backlog_cost=0.8,
            **provenance,
        )
        for i in range(60 * scale)
    ]
    lanes = []

    def lane(a, b, days, cap, cost, weight):
        lanes.append(
            Lane(
                id=f"{a}--{b}",
                source=a,
                target=b,
                lead_time=days,
                capacity=cap * scale**2,
                unit_cost=cost,
                allocation=weight,
                **provenance,
            )
        )

    for s in range(4):
        for p in range(2):
            lane(f"SUP-{s + 1:02}", f"PLT-{p + 1:02}", 3 + (s + p) % 4, 350, 0.8, 0.25)
    for p in range(2):
        for d in range(5):
            lane(
                f"PLT-{p + 1:02}",
                f"DC-{d + 1:02}",
                2 + (p + d) % 3,
                420,
                1.2,
                0.65 if (d < 2) == (p == 0) else 0.35,
            )
    for i in range(30 * scale):
        lane(f"DC-{i % 5 + 1:02}", f"CUS-{i + 1:03}", 1, 180, 0.5, 1)
    demand = []
    for i in range(30 * scale):
        for s in range(60 * scale):
            # Known edge case: zero-demand tail SKU. Low-volume and asymmetric demand are intentional.
            mean = 0 if s == 59 * scale else round(float(rng.uniform(0.35, 2.05)), 3)
            demand.append(
                Demand(
                    id=f"DEM-{i + 1:03}-{s + 1:03}",
                    customer=f"CUS-{i + 1:03}",
                    sku=f"SKU-{s + 1:03}",
                    daily_mean=mean,
                    **provenance,
                )
            )
    return Network(
        id="global-demo-v1" if scale == 1 else f"global-x{scale}",
        nodes=nodes,
        lanes=lanes,
        skus=skus,
        demand=demand,
        **provenance,
    )


def templates() -> list[Scenario]:
    common = {"source_id": "disruption-library-v1", "ingested_at": STAMP}
    specs = [
        (
            "demand-surge",
            "Demand surge",
            "Demand rises 40% across all customer markets.",
            {"demand_multiplier": 1.4},
        ),
        (
            "supplier-outage",
            "Osaka supplier outage",
            "Osaka stops production for 25 days.",
            {"capacity_multipliers": {"SUP-01": 0}},
        ),
        (
            "plant-constraint",
            "Austin capacity reduction",
            "Austin loses 80% of finishing capacity.",
            {"capacity_multipliers": {"PLT-01": 0.2}},
        ),
        (
            "ocean-delay",
            "Ocean freight delay",
            "Inbound transit to Austin extends to 14 days.",
            {"lead_time_overrides": {f"SUP-{i:02}--PLT-01": 14 for i in range(1, 5)}},
        ),
        (
            "dc-outage",
            "Chicago DC outage",
            "Chicago cannot dispatch material during the disruption.",
            {"capacity_multipliers": {"DC-02": 0}},
        ),
        (
            "lean-stock",
            "Lean inventory policy",
            "Safety-stock targets fall to zero for the disruption window.",
            {"safety_stock_multiplier": 0},
        ),
        (
            "sourcing-shift",
            "Diversify Austin sourcing",
            "Shift Austin's orders away from Osaka; remaining weights normalize.",
            {"sourcing_weights": {"SUP-01--PLT-01": 0, "SUP-03--PLT-01": 0.75}},
        ),
        (
            "transport-crunch",
            "Transatlantic lane constraint",
            "Rotterdam–Chicago capacity falls 90%.",
            {"lane_capacity_multipliers": {"PLT-02--DC-02": 0.1}},
        ),
        (
            "compound-shock",
            "Compound disruption",
            "Demand rises 30% while Austin loses half its capacity.",
            {"demand_multiplier": 1.3, "capacity_multipliers": {"PLT-01": 0.5}},
        ),
    ]
    return [
        Scenario(id=ident, name=name, description=desc, **changes, **common)
        for ident, name, desc, changes in specs
    ]


def validate(raw: dict) -> tuple[Network | None, ValidationReport]:
    try:
        network = Network.model_validate(raw)
    except ValidationError as exc:
        issues = [
            Issue(path=".".join(map(str, e["loc"])) or "$", severity="error", message=e["msg"])
            for e in exc.errors()
        ]
        return None, ValidationReport(accepted=False, issues=issues, record_count=0)
    issues = []
    zero = sum(d.daily_mean == 0 for d in network.demand)
    if zero:
        issues.append(
            Issue(path="demand", severity="warning", message=f"{zero} zero-demand records retained")
        )
    for node in network.nodes:
        if node.kind != "customer" and node.capacity == 0:
            issues.append(
                Issue(path=node.id, severity="warning", message="Zero capacity: node cannot dispatch")
            )
    return network, ValidationReport(
        accepted=True,
        issues=issues,
        record_count=1 + len(network.nodes) + len(network.skus) + len(network.lanes) + len(network.demand),
    )


def write_sample(directory: Path, seed: int = 17, scale: int = 1):
    directory.mkdir(parents=True, exist_ok=True)
    network = generate(seed, scale)
    (directory / "network.json").write_text(network.model_dump_json(indent=2))
    (directory / "scenarios.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in templates()], indent=2)
    )
    invalid = network.model_dump(mode="json")
    invalid["nodes"][0]["capacity"] = -10
    invalid["lanes"][0]["lead_time"] = 0
    (directory / "invalid-network.json").write_text(json.dumps(invalid, indent=2))
