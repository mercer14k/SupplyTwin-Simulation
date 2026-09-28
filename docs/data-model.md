# Data dictionary and provenance

Every domain record has `id` (stable identifier), `source_id`, `ingested_at` (ISO datetime), `validation_status` and optional string-valued `lineage`. The sample uses a fixed generation timestamp to remain byte-reproducible; real import attempts have a separate actual ingestion timestamp in the audit database. Dataset content is synthetic, not observed market or company data.

| Entity | Fields | Units / rules |
|---|---|---|
| Network | nodes, lanes, skus, demand | Unique record IDs and validated references |
| Node | kind, latitude, longitude | supplier, plant, dc, customer; geographic degrees |
| Node | capacity | Equivalent SKU units/day shared across all SKUs |
| Node | coverage_days, safety_days, initial_days | Fixed forecast days of supply |
| Node | process_cost | Modeled currency/unit dispatched from a plant or DC |
| SKU | unit_cost | Modeled procurement currency/unit newly produced by supplier |
| SKU | holding_cost, backlog_cost | Currency/unit/day, no financial valuation claim |
| Lane | source, target, lead_time, capacity | Directed adjacent echelon, 1–60 days, units/day |
| Lane | allocation, unit_cost | Inbound shares sum to 1; currency/unit shipped |
| Demand | customer, sku, daily_mean | One record per customer/SKU; Poisson baseline mean |
| Scenario | horizon, seed, start_day, end_day | 0-based days; end is exclusive; 2–365-day horizon |
| Scenario | demand_multiplier, capacity_multipliers | Bounded numeric controls; unknown targets rejected on run |
| Scenario | lane_capacity_multipliers, lead_time_overrides | Lane IDs; lead time is an absolute day count |
| Scenario | sourcing_weights, safety_stock_multiplier | Nonnegative weights normalize; every target needs positive total weight |
| Scenario | version, parent_id | Server-generated version; optional fork lineage |

JSON schemas: `data/schemas/network.schema.json`, `scenario.schema.json`. They are generated from the actual models. Graph rules are additional semantic validation.

## Validation and known cases

The committed network has 41 nodes, 48 lanes, 60 SKUs, and 1,800 customer–SKU demand records. `SKU-060` intentionally has 30 zero-demand records: they are accepted with a visible warning. The graph has dual plant sourcing and shared capacities. The invalid fixture contains exactly two field errors: negative supplier capacity and zero lane lead time. It must be rejected; the original payload and all detected errors remain in the ingestion audit.

The generator supports scales 1–4. Scale 4 produces 131 nodes, 138 lanes, 240 SKUs, 28,800 demand records. Capacity grows quadratically with scale to keep load comparable. Generate into `.local/large` instead of committing performance data.

## KPI definitions

- **Fill rate:** today's demand dispatched today / total demand; old backlog receives priority. No-demand convention: 1.
- **Delivered service:** cumulative customer receipts / cumulative demand at the horizon. This includes late receipts; it is not OTIF. No-demand convention: 1.
- **Backlog:** customer demand not yet dispatched at the horizon. Full daily series exposes peaks and recovery.
- **Inventory:** internal on-hand units at horizon; average inventory is the arithmetic mean of daily closing stock.
- **Utilization:** sum of used supplier production and plant/DC dispatch capacity / sum of available capacity across days. Zero-capacity days contribute zero denominator, so compare alongside outages.
- **Stockouts:** internal node–SKU–days with positive forecast and effectively zero closing inventory, not unique customers or unfilled orders.
- **Modeled cost:** new supplier production × unit cost + dispatch processing + lane freight + closing inventory holding + daily backlog penalty. Opening stock acquisition, fixed costs, taxes, lost sales, terminal inventory valuation and currency conversion are excluded. Lower cost can reflect depletion rather than an economically superior policy.

Material invariant: opening stock + supplier production = closing on-hand + all in-transit units + customer deliveries. Demand invariant: cumulative demand = cumulative dispatch + open backlog. Customer transit plus deliveries equals customer dispatch. Replay hashes include engine version and network content.
