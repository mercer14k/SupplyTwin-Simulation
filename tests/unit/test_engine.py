import copy

import numpy as np
import pytest
from pydantic import ValidationError
from supplytwin.data import STAMP, generate, templates, validate
from supplytwin.domain import SKU, Demand, Lane, Network, Node, Scenario
from supplytwin.engine import capped, compare, simulate


def test_generator_counts_and_replay(network):
    assert network.model_dump() == generate().model_dump()
    assert len(network.nodes) == 41
    assert len(network.skus) == 60
    assert len(network.demand) == 1800
    assert len(templates()) >= 8
    assert len(generate(scale=2).demand) == 7200


def test_reproducibility_and_pure_inputs(network, scenario):
    before = copy.deepcopy((network.model_dump(), scenario.model_dump()))
    a = simulate(network, scenario)
    b = simulate(network, scenario)
    assert a == b
    assert before == (network.model_dump(), scenario.model_dump())
    changed = simulate(network, scenario.model_copy(update={"seed": 93}))
    assert a["kpis"]["demand"] != changed["kpis"]["demand"]


@pytest.mark.parametrize("index", range(9))
def test_daily_conservation_under_every_template(network, index):
    result = simulate(network, templates()[index])
    assert result["invariants"]["passed"]
    for day in result["daily"]:
        assert result["initial_inventory"] + day["sourced"] == pytest.approx(
            day["inventory"] + day["in_transit"] + day["delivered"]
        )
        assert day["total_demand"] == pytest.approx(day["total_dispatch"] + day["backlog"])
        assert 0 <= day["fill_rate"] <= 1
    for node in result["node_daily"]:
        assert 0 <= node["used_capacity"] <= node["available_capacity"] + 1e-7
    assert result["kpis"]["total_cost"] == pytest.approx(sum(result["cost_breakdown"].values()))


def test_noop_matches_baseline(network, scenario):
    scenario = Scenario(id="noop", source_id="test", ingested_at=STAMP, name="No changes")
    result = compare(network, scenario)
    assert all(v == 0 for v in result["deltas"].values())


def test_outage_has_second_order_effect(network):
    r = compare(network, templates()[2])
    assert r["deltas"]["fill_rate"] < 0
    assert max(d["backlog"] for d in r["scenario"]["daily"]) > 2000
    assert r["baseline"]["daily"][:10] == r["scenario"]["daily"][:10]
    # A lead-time lag separates upstream capacity loss from DC customer service impact.
    first_impact = next(
        i
        for i, (a, b) in enumerate(zip(r["baseline"]["daily"], r["scenario"]["daily"], strict=True))
        if a["backlog"] != b["backlog"]
    )
    assert first_impact > 10


def test_zero_demand_and_zero_capacity(network, scenario):
    raw = network.model_dump(mode="json")
    for d in raw["demand"]:
        d["daily_mean"] = 0
    zero = Network.model_validate(raw)
    r = simulate(zero, scenario)
    assert r["kpis"]["fill_rate"] == r["kpis"]["service"] == 1
    assert r["kpis"]["total_cost"] == 0
    scenario.capacity_multipliers = {n.id: 0 for n in network.nodes if n.kind != "customer"}
    r = simulate(network, scenario)
    assert r["invariants"]["passed"]
    assert all(row["used_capacity"] == 0 for row in r["node_daily"] if 10 <= row["day"] < 35)


def test_lane_capacity_and_lead_time(network):
    s = templates()[7]
    r = simulate(network, s)
    caps = {lane.id: lane.capacity for lane in network.lanes}
    for flow in r["flows"]:
        mult = (
            s.lane_capacity_multipliers.get(flow["lane_id"], 1)
            if s.start_day <= flow["day"] < s.end_day
            else 1
        )
        assert flow["units"] <= caps[flow["lane_id"]] * mult + 1e-7


def test_bad_schema_and_unknown_targets(network, scenario):
    for value in [-1, float("nan"), float("inf")]:
        raw = network.model_dump(mode="json")
        raw["nodes"][0]["capacity"] = value
        n, report = validate(raw)
        assert n is None and not report.accepted
        assert report.issues[0].path == "nodes.0.capacity"
    scenario.capacity_multipliers = {"FAKE": 0.5}
    with pytest.raises(ValueError, match="unknown"):
        simulate(network, scenario)
    with pytest.raises(ValidationError):
        Scenario(id="bad", name="Bad", source_id="test", start_day=40, end_day=20)


@pytest.mark.parametrize("mutation", ["duplicate", "cycle", "unknown", "allocation"])
def test_graph_validation(network, mutation):
    raw = network.model_dump(mode="json")
    if mutation == "duplicate":
        raw["nodes"][1]["id"] = raw["nodes"][0]["id"]
    elif mutation == "cycle":
        raw["lanes"][0]["source"] = "PLT-01"
    elif mutation == "unknown":
        raw["demand"][0]["sku"] = "FAKE"
    else:
        raw["lanes"][0]["allocation"] = 0.9
    assert not validate(raw)[1].accepted


def test_capacity_allocation():
    assert capped(np.array([20.0, 30.0]), 10).tolist() == [4, 6]
    assert capped(np.zeros(2), 0).tolist() == [0, 0]


def test_hand_audited_tiny_network():
    """Ground truth: 2 opening units, no inbound production; 1-day delivery lag."""
    p = dict(source_id="ground-truth", ingested_at=STAMP)
    nodes = [
        Node(
            id=k,
            name=k,
            kind=kind,
            latitude=0,
            longitude=0,
            capacity=100 if k == "d" else 0,
            coverage_days=0,
            safety_days=0,
            initial_days=2 if k == "d" else 0,
            **p,
        )
        for k, kind in [("s", "supplier"), ("p", "plant"), ("d", "dc"), ("c", "customer")]
    ]
    lanes = [
        Lane(id=f"{a}-{b}", source=a, target=b, lead_time=1, capacity=100, unit_cost=1, allocation=1, **p)
        for a, b in [("s", "p"), ("p", "d"), ("d", "c")]
    ]
    net = Network(
        id="tiny",
        nodes=nodes,
        lanes=lanes,
        skus=[SKU(id="sku", name="Unit", unit_cost=10, holding_cost=1, backlog_cost=2, **p)],
        demand=[Demand(id="demand", customer="c", sku="sku", daily_mean=1, **p)],
        **p,
    )
    s = Scenario(id="tiny-run", name="Tiny", horizon=2, start_day=0, end_day=2, seed=42, **p)
    r = simulate(net, s)
    # NumPy PCG64 seed 42 yields customer demand [1, 2]. Two units dispatch, one arrives by day 1.
    assert [d["demand"] for d in r["daily"]] == [1, 2]
    assert r["kpis"]["demand"] == 3
    assert r["kpis"]["dispatched"] == 2
    assert r["kpis"]["delivered"] == 1
    assert r["kpis"]["backlog"] == 1
    assert r["kpis"]["inventory"] == 0
    assert r["kpis"]["in_transit"] == 1
    assert r["kpis"]["fill_rate"] == pytest.approx(2 / 3)
    assert r["kpis"]["total_cost"] == 5  # transport 2 + holding 1 + backlog 2
