"""Transport-neutral domain contracts. No HTTP, persistence or AI dependencies."""

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Record(StrictModel):
    id: Identifier
    source_id: Identifier
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: Literal["valid", "warning"] = "valid"
    lineage: dict[str, str] = Field(default_factory=dict)


class Node(Record):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["supplier", "plant", "dc", "customer"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: Nonnegative
    coverage_days: float = Field(ge=0, le=90)
    safety_days: float = Field(ge=0, le=60)
    initial_days: float = Field(ge=0, le=90)
    process_cost: Nonnegative = 0


class SKU(Record):
    name: str = Field(max_length=100)
    unit_cost: Nonnegative
    holding_cost: Nonnegative
    backlog_cost: Nonnegative


class Lane(Record):
    source: Identifier
    target: Identifier
    lead_time: int = Field(ge=1, le=60)
    capacity: Nonnegative
    unit_cost: Nonnegative
    allocation: float = Field(gt=0, le=1)


class Demand(Record):
    customer: Identifier
    sku: Identifier
    daily_mean: Nonnegative


class Network(Record):
    nodes: list[Node] = Field(min_length=4, max_length=2000)
    skus: list[SKU] = Field(min_length=1, max_length=1000)
    lanes: list[Lane] = Field(min_length=3, max_length=10000)
    demand: list[Demand] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def check_network(self):
        for label, records in [
            ("nodes", self.nodes),
            ("skus", self.skus),
            ("lanes", self.lanes),
            ("demand", self.demand),
        ]:
            if len({r.id for r in records}) != len(records):
                raise ValueError(f"duplicate identifier in {label}")
        nodes = {n.id: n for n in self.nodes}
        sku_ids = {s.id for s in self.skus}
        allowed = {("supplier", "plant"), ("plant", "dc"), ("dc", "customer")}
        incoming: dict[str, list[Lane]] = {}
        pairs = set()
        for lane in self.lanes:
            if lane.source not in nodes or lane.target not in nodes:
                raise ValueError(f"lane {lane.id} has an unknown endpoint")
            if (nodes[lane.source].kind, nodes[lane.target].kind) not in allowed:
                raise ValueError(
                    f"lane {lane.id} violates the acyclic supplier → plant → dc → customer graph"
                )
            pair = (lane.source, lane.target)
            if pair in pairs:
                raise ValueError("duplicate source-target lane")
            pairs.add(pair)
            incoming.setdefault(lane.target, []).append(lane)
        for node in self.nodes:
            lanes = incoming.get(node.id, [])
            if node.kind != "supplier" and not lanes:
                raise ValueError(f"node {node.id} is disconnected")
            if lanes and abs(sum(x.allocation for x in lanes) - 1) > 1e-8:
                raise ValueError(f"incoming allocations for {node.id} must sum to one")
            if node.kind == "customer" and len(lanes) != 1:
                raise ValueError("each customer requires exactly one serving DC")
        seen = set()
        for d in self.demand:
            if d.customer not in nodes or nodes[d.customer].kind != "customer" or d.sku not in sku_ids:
                raise ValueError(f"demand {d.id} has invalid references")
            key = (d.customer, d.sku)
            if key in seen:
                raise ValueError("duplicate customer-SKU demand")
            seen.add(key)
        if len(self.nodes) * len(self.skus) > 100000:
            raise ValueError("network exceeds the 100000 node-SKU safety limit")
        return self


class ScenarioParameters(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    horizon: int = Field(default=60, ge=2, le=365)
    seed: int = Field(default=42, ge=0, le=2147483647)
    start_day: int = Field(default=10, ge=0, le=364)
    end_day: int = Field(default=35, ge=1, le=365)
    demand_multiplier: float = Field(default=1, ge=0, le=5)
    capacity_multipliers: dict[Identifier, Annotated[float, Field(ge=0, le=3)]] = Field(default_factory=dict)
    lane_capacity_multipliers: dict[Identifier, Annotated[float, Field(ge=0, le=3)]] = Field(
        default_factory=dict
    )
    lead_time_overrides: dict[Identifier, Annotated[int, Field(ge=1, le=90)]] = Field(default_factory=dict)
    sourcing_weights: dict[Identifier, Annotated[float, Field(ge=0, le=1)]] = Field(default_factory=dict)
    safety_stock_multiplier: float = Field(default=1, ge=0, le=5)

    @model_validator(mode="after")
    def check_window(self):
        if not 0 <= self.start_day < self.end_day <= self.horizon:
            raise ValueError("require 0 <= start_day < end_day <= horizon")
        return self


class Scenario(Record, ScenarioParameters):
    version: int = Field(default=1, ge=1)
    parent_id: Identifier | None = None

    def check_targets(self, network: Network) -> None:
        nodes = {n.id: n for n in network.nodes}
        lanes = {lane.id for lane in network.lanes}
        if set(self.capacity_multipliers) - nodes.keys():
            raise ValueError("unknown capacity node")
        if any(nodes[n].kind == "customer" for n in self.capacity_multipliers):
            raise ValueError("customer capacity cannot be changed")
        for values in [self.lane_capacity_multipliers, self.lead_time_overrides, self.sourcing_weights]:
            if set(values) - lanes:
                raise ValueError("unknown lane")
        for node in network.nodes:
            incoming = [x for x in network.lanes if x.target == node.id]
            if incoming and sum(self.sourcing_weights.get(x.id, x.allocation) for x in incoming) <= 0:
                raise ValueError(f"all sourcing weights are zero for {node.id}")
        if len(nodes) * len(network.skus) * self.horizon > 12000000:
            raise ValueError("run exceeds the 12000000 node-SKU-day safety limit")


class Issue(StrictModel):
    path: str
    severity: Literal["error", "warning"]
    message: str


class ValidationReport(StrictModel):
    accepted: bool
    issues: list[Issue]
    record_count: int


class RunRequest(StrictModel):
    scenario: Scenario
    network_id: Identifier = "global-demo-v1"


class AIRequest(StrictModel):
    instruction: str = Field(min_length=5, max_length=2000)
    network_id: Identifier = "global-demo-v1"
