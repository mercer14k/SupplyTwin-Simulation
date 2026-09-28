"""Daily, capacity-constrained multi-echelon inventory simulation.

Material uses equivalent SKU units end-to-end (one-to-one plant finishing).
No AI is imported here. Each call owns its RNG and mutable state.
"""

import hashlib
import json
from collections import defaultdict

import numpy as np

from .domain import Network, Scenario

ENGINE_VERSION = "1.0.0"


def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capped(quantities: np.ndarray, capacity: float) -> np.ndarray:
    total = float(quantities.sum())
    return quantities * min(1, max(0, capacity) / total) if total > 0 else quantities.copy()


def simulate(network: Network, scenario: Scenario) -> dict:
    scenario.check_targets(network)
    nodes, skus, lanes = network.nodes, network.skus, network.lanes
    ni, si = {n.id: i for i, n in enumerate(nodes)}, {s.id: i for i, s in enumerate(skus)}
    internal = [i for i, n in enumerate(nodes) if n.kind != "customer"]
    incoming = defaultdict(list)
    for li, lane in enumerate(lanes):
        incoming[ni[lane.target]].append(li)
    means = np.zeros((len(nodes), len(skus)))
    for d in network.demand:
        means[ni[d.customer], si[d.sku]] = d.daily_mean
    base_caps = np.array([n.capacity for n in nodes])
    costs = np.array([s.unit_cost for s in skus])
    holding = np.array([s.holding_cost for s in skus])
    penalty = np.array([s.backlog_cost for s in skus])

    def rates_and_weights(active):
        rates = means.copy()
        weights = np.array(
            [
                scenario.sourcing_weights.get(lane.id, lane.allocation) if active else lane.allocation
                for lane in lanes
            ]
        )
        for indexes in incoming.values():
            weights[indexes] /= weights[indexes].sum()
        for kind in ["customer", "dc", "plant"]:
            for i, node in enumerate(nodes):
                if node.kind == kind:
                    for li in incoming[i]:
                        rates[ni[lanes[li].source]] += rates[i] * weights[li]
        return rates, weights

    rates, _ = rates_and_weights(False)
    stock = rates * np.array([n.initial_days for n in nodes])[:, None]
    initial = float(stock.sum())
    backlog = np.zeros_like(stock)
    pipeline = np.zeros_like(stock)
    arrivals: dict[int, list] = defaultdict(list)
    rng = np.random.default_rng(scenario.seed)
    daily, node_daily, flows = [], [], []
    total_demand = total_dispatch = delivered = sourced = immediate = 0.0
    cost_parts = dict(procurement=0.0, processing=0.0, transport=0.0, holding=0.0, backlog=0.0)
    sku_demand = np.zeros(len(skus))
    sku_dispatch = np.zeros(len(skus))
    lane_total = np.zeros(len(lanes))
    stockout_days = 0
    max_mass_error = max_demand_error = 0.0
    for day in range(scenario.horizon):
        active = scenario.start_day <= day < scenario.end_day
        rates, weights = rates_and_weights(active)
        cap = base_caps * np.array(
            [scenario.capacity_multipliers.get(n.id, 1) if active else 1 for n in nodes]
        )
        remaining = cap.copy()
        for target, qty in arrivals.pop(day, []):
            pipeline[target] -= qty
            if nodes[target].kind == "customer":
                delivered += float(qty.sum())
            else:
                stock[target] += qty
        # Suppliers produce against a fixed-forecast base-stock target, constrained by daily capacity.
        for i, node in enumerate(nodes):
            if node.kind == "supplier":
                target = rates[i] * (
                    node.coverage_days
                    + node.safety_days * (scenario.safety_stock_multiplier if active else 1)
                )
                qty = capped(np.maximum(0, target - stock[i]), remaining[i])
                stock[i] += qty
                remaining[i] -= qty.sum()
                sourced += float(qty.sum())
                cost_parts["procurement"] += float(qty @ costs)
        demand = rng.poisson(means).astype(float)
        if active:
            demand *= scenario.demand_multiplier
        old_backlog = backlog.copy()
        backlog += demand
        total_demand += float(demand.sum())
        sku_demand += demand.sum(axis=0)
        day_dispatch = 0.0
        day_flows = np.zeros(len(lanes))

        def dispatch(li, request):
            nonlocal total_dispatch, immediate, day_dispatch
            lane = lanes[li]
            a, b = ni[lane.source], ni[lane.target]
            lane_cap = lane.capacity * (scenario.lane_capacity_multipliers.get(lane.id, 1) if active else 1)
            # Supplier capacity constrains source production; plant/DC capacity constrains dispatch.
            available_cap = lane_cap if nodes[a].kind == "supplier" else min(lane_cap, remaining[a])
            qty = capped(np.minimum(np.maximum(request, 0), stock[a]), available_cap)
            amount = float(qty.sum())
            if amount < 1e-10:
                return
            stock[a] -= qty
            pipeline[b] += qty
            if nodes[a].kind != "supplier":
                remaining[a] -= amount
            lead = scenario.lead_time_overrides.get(lane.id, lane.lead_time) if active else lane.lead_time
            arrivals[day + lead].append((b, qty.copy()))
            day_flows[li] += amount
            cost_parts["transport"] += amount * lane.unit_cost
            cost_parts["processing"] += amount * nodes[a].process_cost
            if nodes[b].kind == "customer":
                backlog[b] -= qty
                total_dispatch += amount
                day_dispatch += amount
                sku_dispatch[:] += qty
                # Old backlog gets priority; only today's demand filled today enters immediate fill.
                immediate += float(np.maximum(0, qty - old_backlog[b]).sum())

        # Rotate stable lane order each day to distribute shared node capacity without random bias.
        for kind in ["customer", "dc", "plant"]:
            selected = [li for li, lane in enumerate(lanes) if nodes[ni[lane.target]].kind == kind]
            offset = day % len(selected) if selected else 0
            selected = selected[offset:] + selected[:offset]
            # Fix each target's request before assigning its sourcing shares.
            requests = {}
            for li in selected:
                b = ni[lanes[li].target]
                if b not in requests:
                    if kind == "customer":
                        requests[b] = backlog[b].copy()
                    else:
                        node = nodes[b]
                        avg_lead = sum(
                            weights[j]
                            * (
                                scenario.lead_time_overrides.get(lanes[j].id, lanes[j].lead_time)
                                if active
                                else lanes[j].lead_time
                            )
                            for j in incoming[b]
                        )
                        target = rates[b] * (
                            node.coverage_days
                            + avg_lead
                            + node.safety_days * (scenario.safety_stock_multiplier if active else 1)
                        )
                        # Customer backlog pulls DC replenishment; upstream shortage travels through stock targets.
                        downstream_backlog = sum(
                            (
                                backlog[ni[lane.target]]
                                for lane in lanes
                                if lane.source == node.id and nodes[ni[lane.target]].kind == "customer"
                            ),
                            start=np.zeros(len(skus)),
                        )
                        requests[b] = np.maximum(0, target + downstream_backlog - stock[b] - pipeline[b])
                dispatch(li, requests[b] * weights[li])
        lane_total += day_flows
        unmet = float(backlog.sum())
        stockout_days += int(((stock[internal] < 1e-8) & (rates[internal] > 0)).sum())
        cost_parts["holding"] += float(stock.sum(axis=0) @ holding)
        cost_parts["backlog"] += float(backlog.sum(axis=0) @ penalty)
        mass_error = initial + sourced - float(stock.sum()) - float(pipeline.sum()) - delivered
        demand_error = total_demand - total_dispatch - unmet
        max_mass_error = max(max_mass_error, abs(mass_error))
        max_demand_error = max(max_demand_error, abs(demand_error))
        if abs(mass_error) > 1e-6 * max(1, initial + sourced) or abs(demand_error) > 1e-6 * max(
            1, total_demand
        ):
            raise ArithmeticError("conservation invariant failed")
        if stock.min() < -1e-7 or pipeline.min() < -1e-7 or backlog.min() < -1e-7:
            raise ArithmeticError("negative inventory state")
        utilized = cap - remaining
        daily.append(
            dict(
                day=day,
                demand=float(demand.sum()),
                dispatched=day_dispatch,
                backlog=unmet,
                inventory=float(stock.sum()),
                in_transit=float(pipeline.sum()),
                delivered=delivered,
                sourced=sourced,
                total_demand=total_demand,
                total_dispatch=total_dispatch,
                modeled_cost=sum(cost_parts.values()),
                mass_error=mass_error,
                demand_error=demand_error,
                fill_rate=immediate / total_demand if total_demand else 1,
            )
        )
        for i in internal:
            node_daily.append(
                dict(
                    day=day,
                    node_id=nodes[i].id,
                    inventory=float(stock[i].sum()),
                    in_transit=float(pipeline[i].sum()),
                    used_capacity=float(utilized[i]),
                    available_capacity=float(cap[i]),
                    utilization=float(utilized[i] / cap[i]) if cap[i] else 0,
                )
            )
        flows.extend(
            dict(day=day, lane_id=lanes[i].id, units=float(q)) for i, q in enumerate(day_flows) if q > 0
        )
    capacity_sum = sum(n["available_capacity"] for n in node_daily)
    result = dict(
        engine_version=ENGINE_VERSION,
        seed=scenario.seed,
        horizon=scenario.horizon,
        network_id=network.id,
        network_hash=digest(network.model_dump(mode="json")),
        scenario=scenario.model_dump(mode="json"),
        initial_inventory=initial,
        kpis=dict(
            fill_rate=immediate / total_demand if total_demand else 1,
            service=delivered / total_demand if total_demand else 1,
            backlog=float(backlog.sum()),
            inventory=float(stock.sum()),
            average_inventory=float(np.mean([d["inventory"] for d in daily])),
            utilization=sum(n["used_capacity"] for n in node_daily) / capacity_sum if capacity_sum else 0,
            stockouts=stockout_days,
            total_cost=sum(cost_parts.values()),
            demand=total_demand,
            dispatched=total_dispatch,
            delivered=delivered,
            in_transit=float(pipeline.sum()),
        ),
        cost_breakdown=cost_parts,
        daily=daily,
        node_daily=node_daily,
        flows=flows,
        lanes=[dict(lane_id=lane.id, units=float(lane_total[i])) for i, lane in enumerate(lanes)],
        skus=[
            dict(
                sku_id=s.id,
                demand=float(sku_demand[i]),
                dispatched=float(sku_dispatch[i]),
                backlog=float(backlog[:, i].sum()),
                inventory=float(stock[:, i].sum()),
            )
            for i, s in enumerate(skus)
        ],
        invariants=dict(
            max_mass_error=max_mass_error,
            max_demand_error=max_demand_error,
            passed=max_mass_error < 1e-5 and max_demand_error < 1e-5,
        ),
    )
    result["result_hash"] = digest(result)
    return result


def compare(network: Network, scenario: Scenario) -> dict:
    baseline = Scenario(
        id="baseline",
        source_id=network.source_id,
        ingested_at=scenario.ingested_at,
        name="Baseline",
        horizon=scenario.horizon,
        seed=scenario.seed,
        start_day=scenario.start_day,
        end_day=scenario.end_day,
    )
    base, changed = simulate(network, baseline), simulate(network, scenario)
    deltas = {k: changed["kpis"][k] - v for k, v in base["kpis"].items()}
    return dict(
        baseline=base,
        scenario=changed,
        deltas=deltas,
        evidence=[
            dict(
                id=f"kpi:{k}",
                metric=k,
                baseline=base["kpis"][k],
                scenario=changed["kpis"][k],
                delta=v,
                source="deterministic-simulation",
            )
            for k, v in deltas.items()
        ],
    )
