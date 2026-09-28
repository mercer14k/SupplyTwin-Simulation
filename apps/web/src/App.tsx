import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Box,
  CheckCircle2,
  ChevronRight,
  Database,
  FileJson,
  FlaskConical,
  GitBranch,
  Globe2,
  Info,
  Layers3,
  LoaderCircle,
  Play,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { api, post, download, number, metric, delta } from "./api";
import type {
  Evidence,
  Explanation,
  Network,
  Report,
  Run,
  Scenario,
} from "./types";
import { lazy, Suspense } from "react";
const NetworkMap = lazy(() => import("./NetworkMap"));
import Chart from "./Chart";

type Page = "workspace" | "scenarios" | "data" | "about";
const labels: Record<string, string> = {
  fill_rate: "Immediate fill rate",
  backlog: "Open backlog",
  average_inventory: "Average inventory",
  total_cost: "Modeled cost",
  service: "Delivered service",
  utilization: "Capacity utilization",
  stockouts: "Stockout SKU-days",
  inventory: "Closing inventory",
};
const describe = (s: Scenario) =>
  `${s.horizon} days · Seed ${s.seed} · Active days ${s.start_day}–${s.end_day - 1}`;
export default function App() {
  const [page, setPage] = useState<Page>("workspace");
  const [network, setNetwork] = useState<Network>();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenario, setScenario] = useState<Scenario>();
  const [run, setRun] = useState<Run>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [day, setDay] = useState(20);
  const [selected, setSelected] = useState("PLT-01");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState({
    ai_enabled: false,
    auth_required: false,
    engine: "",
  });
  const [report, setReport] = useState<Report>();
  const [evidence, setEvidence] = useState<Evidence>();
  const [explanation, setExplanation] = useState<Explanation>();
  const [instruction, setInstruction] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [json, setJson] = useState("");
  const [chartField, setChartField] = useState<
    "backlog" | "inventory" | "fill_rate"
  >("backlog");
  const [history, setHistory] = useState<
    { id: string; name: string; created_at: string }[]
  >([]);
  const [versions, setVersions] = useState<Scenario[]>([]);
  const selectNode = useCallback((id: string) => setSelected(id), []);
  useEffect(() => {
    if (!evidence && !advanced) return;
    const previous = document.activeElement as HTMLElement;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setEvidence(undefined);
        setAdvanced(false);
      }
      if (e.key === "Tab") {
        const items = Array.from(
          document.querySelectorAll<HTMLElement>(
            "[role=dialog] button,[role=dialog] textarea,[role=dialog] a[href]",
          ),
        );
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [evidence, advanced]);
  const refreshHistory = () =>
    api<{ items: { id: string; name: string; created_at: string }[] }>(
      "/runs",
    ).then((r) => setHistory(r.items));
  useEffect(() => {
    Promise.all([
      api<Network>("/networks/global-demo-v1"),
      api<{ items: Scenario[] }>("/scenarios"),
      api<typeof status>("/status"),
      api<Report>("/networks/global-demo-v1/validation"),
    ])
      .then(([n, s, st, r]) => {
        setNetwork(n);
        setScenarios(s.items);
        setScenario(
          s.items.find((x) => x.id === "plant-constraint") || s.items[0],
        );
        setStatus(st);
        setReport(r);
      })
      .catch((e) => setError(e.message));
    refreshHistory().catch(() => {});
  }, []);
  const execute = async (s = scenario) => {
    if (!s || !network) return;
    setBusy(true);
    setError("");
    setExplanation(undefined);
    try {
      const result = await post<Run>("/runs", {
        scenario: s,
        network_id: network.id,
      });
      setRun(result);
      setDay(Math.min(20, s.horizon - 1));
      setNotice("Simulation complete. Every day passed conservation checks.");
      await refreshHistory();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const update = (patch: Partial<Scenario>) => {
    if (scenario) setScenario({ ...scenario, ...patch });
  };
  const save = async () => {
    if (!scenario) return;
    try {
      const saved = await post<Scenario>("/scenarios", scenario);
      setScenario(saved);
      setScenarios((await api<{ items: Scenario[] }>("/scenarios")).items);
      setNotice(`Saved ${saved.name}, version ${saved.version}.`);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const selectScenario = (s: Scenario) => {
    setScenario(s);
    setVersions([]);
    setPage("workspace");
    setNotice("Scenario loaded. Run comparison to compute its outcomes.");
  };
  const importScenario = async (file?: File) => {
    if (!file) return;
    try {
      if (file.size > 100000)
        throw Error("Scenario files must be smaller than 100 KB.");
      const raw = JSON.parse(await file.text());
      const saved = await post<Scenario>("/scenarios", raw);
      setScenario(saved);
      setScenarios((await api<{ items: Scenario[] }>("/scenarios")).items);
      setNotice("Scenario imported and versioned.");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const importNetwork = async (file?: File) => {
    if (!file) return;
    setBusy(true);
    try {
      if (file.size > 10 * 1024 * 1024)
        throw Error("Network files must be smaller than 10 MiB.");
      const result = await api<{ report: Report; network_id: string }>(
        "/networks/import",
        {
          method: "POST",
          body: await file.text(),
          headers: { "X-Filename": file.name },
        },
      );
      setReport(result.report);
      if (result.report.accepted) {
        setNetwork(await api<Network>(`/networks/${result.network_id}`));
        setRun(undefined);
        setNotice("Network imported. Validation report is available below.");
      } else setNotice("Import rejected. Every detected error is shown below.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const propose = async () => {
    if (!network) return;
    setBusy(true);
    try {
      const p = await post<{
        status: string;
        reason: string;
        scenario: Scenario | null;
      }>("/ai/propose", { instruction, network_id: network.id });
      if (p.scenario) {
        setJson(JSON.stringify(p.scenario, null, 2));
        setAdvanced(true);
        setNotice(
          "AI proposal ready for review. Apply it to the editor before running.",
        );
      } else setNotice(p.reason);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const explain = async () => {
    if (!run) return;
    setBusy(true);
    try {
      setExplanation(
        await post<Explanation>(`/runs/${run.id}/explanation`, {}),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const node = network?.nodes.find((n) => n.id === selected);
  const nodeDay = run?.scenario.node_daily.find(
    (n) => n.node_id === selected && n.day === day,
  );
  const canonical = (v: unknown): string =>
    JSON.stringify(v, (_key, value) =>
      value && typeof value === "object" && !Array.isArray(value)
        ? Object.fromEntries(
            Object.entries(value).sort(([a], [b]) => a.localeCompare(b)),
          )
        : value,
    );
  const stale = !!(
    run &&
    scenario &&
    canonical(run.scenario.scenario) !== canonical(scenario)
  );
  const nav = [
    { id: "workspace", title: "Scenario workspace", icon: Layers3 },
    { id: "scenarios", title: "Scenario library", icon: GitBranch },
    { id: "data", title: "Network & data", icon: Database },
    { id: "about", title: "Architecture", icon: Info },
  ] as const;
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          href="#workspace"
          onClick={() => setPage("workspace")}
          className="brand"
        >
          <span className="brand-icon">
            <Box size={23} />
          </span>
          <span>
            SupplyTwin<span className="brand-sub">SUPPLY CHAIN SIMULATION</span>
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(({ id, title, icon: Icon }) => (
            <button
              key={id}
              className={page === id ? "nav active" : "nav"}
              onClick={() => setPage(id)}
            >
              <Icon size={18} />
              {title}
              {page === id && <ChevronRight size={15} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <ShieldCheck size={18} />
            <div>
              Local by design<small>No cloud AI required</small>
            </div>
          </div>
          <div className="build-label">
            ENGINE {status.engine || "…"} <span>OPEN SOURCE</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            SupplyTwin <ChevronRight size={14} />
            <span>{nav.find((n) => n.id === page)?.title}</span>
          </div>
          <div className="topbar-right">
            <span className="badge">SYNTHETIC DATA</span>
            <span className="local-status">
              <span /> Local workspace
            </span>
          </div>
        </header>
        <div className="page">
          <div className="page-heading">
            <div>
              <div className="eyebrow">PLAN WITH EVIDENCE</div>
              <h1>
                {page === "workspace"
                  ? "See the ripple effect."
                  : page === "scenarios"
                    ? "Reusable disruptions."
                    : page === "data"
                      ? "Every record, traceable."
                      : "Simulation first. AI second."}
              </h1>
              <p>
                {page === "workspace"
                  ? "Test a decision before it reaches your supply chain."
                  : page === "scenarios"
                    ? "Start from a template. Save changes as immutable versions."
                    : page === "data"
                      ? "Inspect the network, provenance, and validation findings."
                      : "A local, open-source digital twin with auditable material balances."}
              </p>
            </div>
            {page === "workspace" && (
              <button
                className="primary"
                disabled={busy || !scenario}
                onClick={() => execute()}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Play size={17} />
                )}{" "}
                {busy ? "Simulating…" : "Run comparison"}
              </button>
            )}
          </div>
          {error && (
            <div className="alert error" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert" role="status">
              {notice}
              <button aria-label="Dismiss notice" onClick={() => setNotice("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {status.auth_required && (
            <label className="token-field">
              Workspace access token{" "}
              <input
                type="password"
                placeholder="Bearer token"
                onChange={(e) =>
                  sessionStorage.setItem("supplytwin-token", e.target.value)
                }
              />
            </label>
          )}
          {!network || !scenario ? (
            <div className="empty">
              <LoaderCircle size={24} className="spin" /> Loading local network…
            </div>
          ) : (
            <>
              {page === "workspace" && (
                <>
                  <div className="network-strip">
                    <div>
                      <Globe2 size={16} />
                      <strong>Global reference network</strong>
                      <span>{network.nodes.length} nodes</span>
                      <span>{network.lanes.length} lanes</span>
                      <span>{network.skus.length} SKUs</span>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setPage("data")}
                    >
                      Inspect data <ArrowRight size={14} />
                    </button>
                  </div>
                  <div className="kpis">
                    {[
                      "fill_rate",
                      "backlog",
                      "average_inventory",
                      "total_cost",
                    ].map((key) => (
                      <button
                        className="kpi"
                        key={key}
                        disabled={!run}
                        onClick={() =>
                          setEvidence(
                            run?.evidence.find((e) => e.metric === key),
                          )
                        }
                      >
                        <span>
                          {labels[key]}
                          <ArrowRight size={14} />
                        </span>
                        <strong>
                          {run ? metric(key, run.scenario.kpis[key]) : "—"}
                        </strong>
                        <div>
                          {run ? (
                            <>
                              <span
                                className={
                                  ["fill_rate"].includes(key)
                                    ? run.deltas[key] < 0
                                      ? "adverse"
                                      : "positive"
                                    : run.deltas[key] > 0
                                      ? "adverse"
                                      : "positive"
                                }
                              >
                                {delta(key, run.deltas[key])}
                              </span>
                              <small>
                                {" "}
                                vs baseline{" "}
                                {metric(key, run.baseline.kpis[key])}
                              </small>
                            </>
                          ) : (
                            <small>Run a comparison to compute</small>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                  {run && (
                    <div className="run-caption">
                      <span className="computed">COMPUTED</span>{" "}
                      {run.scenario.scenario.name} ·{" "}
                      {describe(run.scenario.scenario)}{" "}
                      {stale && (
                        <span className="stale">
                          Editor changed · run to refresh
                        </span>
                      )}
                      <button
                        className="text-button"
                        onClick={() => execute(run.scenario.scenario)}
                        disabled={busy}
                      >
                        <RefreshCw size={13} /> Replay seed
                      </button>
                    </div>
                  )}
                  <div className="workspace-grid">
                    <section className="panel network-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Network flow</h2>
                          <span>
                            Geographic view · daily dispatched material
                          </span>
                        </div>
                        <span className="badge">
                          {run ? `DAY ${day}` : "AWAITING RUN"}
                        </span>
                      </div>
                      <Suspense
                        fallback={
                          <div className="empty map-host">
                            Loading network view…
                          </div>
                        }
                      >
                        <NetworkMap
                          network={network}
                          result={run?.scenario}
                          day={day}
                          onSelect={selectNode}
                        />
                      </Suspense>
                      <div className="map-caption">
                        <span>180° W</span>
                        <span>
                          EQUIRECTANGULAR NETWORK · NOT ROUTE GEOMETRY
                        </span>
                        <span>180° E</span>
                      </div>
                      <div className="legend">
                        {["supplier", "plant", "dc", "customer"].map((k) => (
                          <span key={k}>
                            <i className={k} />
                            {k === "dc"
                              ? "Distribution center"
                              : k.charAt(0).toUpperCase() + k.slice(1)}
                          </span>
                        ))}
                      </div>
                      <div className="timeline">
                        <label htmlFor="day">
                          Day <strong>{day}</strong>
                        </label>
                        <input
                          id="day"
                          type="range"
                          min="0"
                          max={(run?.scenario.horizon || scenario.horizon) - 1}
                          value={day}
                          onChange={(e) => setDay(+e.target.value)}
                          disabled={!run}
                        />
                        <span>
                          {(run?.scenario.horizon || scenario.horizon) - 1}
                        </span>
                      </div>
                      <div className="facility">
                        <div className="facility-select">
                          <label htmlFor="facility">Inspect facility</label>
                          <select
                            id="facility"
                            value={selected}
                            onChange={(e) => setSelected(e.target.value)}
                          >
                            {network.nodes.map((n) => (
                              <option key={n.id} value={n.id}>
                                {n.name}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <small>Inventory</small>
                          <strong>
                            {nodeDay ? number(nodeDay.inventory) : "—"}{" "}
                            <em>units</em>
                          </strong>
                        </div>
                        <div>
                          <small>Utilization</small>
                          <strong>
                            {nodeDay
                              ? metric("utilization", nodeDay.utilization)
                              : "—"}
                          </strong>
                        </div>
                        <div>
                          <small>Daily capacity</small>
                          <strong>
                            {number(
                              nodeDay?.available_capacity ??
                                node?.capacity ??
                                0,
                            )}
                          </strong>
                        </div>
                      </div>
                    </section>
                    <aside className="panel scenario-editor">
                      <div className="panel-heading">
                        <div>
                          <h2>
                            <Settings2 size={17} /> Scenario controls
                          </h2>
                          <span>Typed inputs · deterministic outcomes</span>
                        </div>
                      </div>
                      <div className="editor-body">
                        <label>
                          Disruption template
                          <select
                            value={
                              scenarios.some((s) => s.id === scenario.id)
                                ? scenario.id
                                : ""
                            }
                            onChange={(e) => {
                              const s = scenarios.find(
                                (s) => s.id === e.target.value,
                              );
                              if (s) setScenario(s);
                            }}
                          >
                            <option value="" disabled>
                              Custom scenario
                            </option>
                            {scenarios.map((s) => (
                              <option value={s.id} key={s.id}>
                                {s.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <p className="scenario-description">
                          {scenario.description}
                        </p>
                        <label>
                          Scenario name
                          <input
                            value={scenario.name}
                            onChange={(e) => update({ name: e.target.value })}
                          />
                        </label>
                        <div className="form-pair">
                          <label>
                            Horizon, days
                            <input
                              type="number"
                              min="2"
                              max="365"
                              value={scenario.horizon}
                              onChange={(e) =>
                                update({ horizon: +e.target.value })
                              }
                            />
                          </label>
                          <label>
                            Random seed
                            <input
                              type="number"
                              min="0"
                              value={scenario.seed}
                              onChange={(e) =>
                                update({ seed: +e.target.value })
                              }
                            />
                          </label>
                        </div>
                        <div className="form-pair">
                          <label>
                            Start day
                            <input
                              type="number"
                              min="0"
                              value={scenario.start_day}
                              onChange={(e) =>
                                update({ start_day: +e.target.value })
                              }
                            />
                          </label>
                          <label>
                            End day, exclusive
                            <input
                              type="number"
                              min="1"
                              value={scenario.end_day}
                              onChange={(e) =>
                                update({ end_day: +e.target.value })
                              }
                            />
                          </label>
                        </div>
                        <label className="range-label">
                          Demand multiplier{" "}
                          <strong>
                            {scenario.demand_multiplier.toFixed(2)}×
                          </strong>
                          <input
                            type="range"
                            min="0"
                            max="3"
                            step=".05"
                            value={scenario.demand_multiplier}
                            onChange={(e) =>
                              update({ demand_multiplier: +e.target.value })
                            }
                          />
                        </label>
                        <label className="range-label">
                          Safety stock multiplier{" "}
                          <strong>
                            {scenario.safety_stock_multiplier.toFixed(2)}×
                          </strong>
                          <input
                            type="range"
                            min="0"
                            max="3"
                            step=".1"
                            value={scenario.safety_stock_multiplier}
                            onChange={(e) =>
                              update({
                                safety_stock_multiplier: +e.target.value,
                              })
                            }
                          />
                        </label>
                        <div className="override-list">
                          {Object.entries(scenario.capacity_multipliers).map(
                            ([id, v]) => (
                              <label key={id}>
                                {id} capacity multiplier
                                <input
                                  type="number"
                                  min="0"
                                  max="3"
                                  step=".1"
                                  value={v}
                                  onChange={(e) =>
                                    update({
                                      capacity_multipliers: {
                                        ...scenario.capacity_multipliers,
                                        [id]: +e.target.value,
                                      },
                                    })
                                  }
                                />
                              </label>
                            ),
                          )}
                        </div>
                        <button
                          className="text-button"
                          onClick={() => {
                            setJson(JSON.stringify(scenario, null, 2));
                            setAdvanced(true);
                          }}
                        >
                          <FileJson size={15} /> Edit all typed parameters{" "}
                          <ArrowRight size={14} />
                        </button>
                        <div className="editor-actions">
                          <button onClick={save}>
                            <GitBranch size={15} /> Save version
                          </button>
                          <button
                            title="Export scenario JSON"
                            aria-label="Export scenario JSON"
                            onClick={() =>
                              download(`${scenario.id}.json`, scenario)
                            }
                          >
                            <ArrowDownToLine size={16} />
                          </button>
                          <label
                            className="button"
                            title="Import scenario JSON"
                          >
                            <Upload size={16} />
                            <span className="sr-only">
                              Import scenario JSON
                            </span>
                            <input
                              type="file"
                              accept="application/json,.json"
                              className="sr-only"
                              onChange={(e) =>
                                importScenario(e.target.files?.[0])
                              }
                            />
                          </label>
                        </div>
                      </div>
                    </aside>
                  </div>
                  <div className="lower-grid">
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <h2>How the impact unfolds</h2>
                          <span>Daily simulation ledger</span>
                        </div>
                        <select
                          aria-label="Chart metric"
                          value={chartField}
                          onChange={(e) =>
                            setChartField(e.target.value as typeof chartField)
                          }
                        >
                          <option value="backlog">Open backlog</option>
                          <option value="inventory">Inventory</option>
                          <option value="fill_rate">Fill rate</option>
                        </select>
                      </div>
                      {run ? (
                        <>
                          <div className="chart-legend">
                            <span>— Scenario</span>
                            <span>┄ Baseline</span>
                          </div>
                          <Chart
                            baseline={run.baseline.daily}
                            scenario={run.scenario.daily}
                            field={chartField}
                          />
                        </>
                      ) : (
                        <div className="empty chart-empty">
                          <Activity size={24} />
                          <p>
                            Run a comparison to see how the disruption
                            propagates.
                          </p>
                        </div>
                      )}
                    </section>
                    <section className="panel evidence-panel">
                      <div className="panel-heading">
                        <div>
                          <h2>
                            <ShieldCheck size={17} /> Evidence & integrity
                          </h2>
                          <span>Every value has a computed source</span>
                        </div>
                      </div>
                      {run ? (
                        <div className="evidence-body">
                          <div className="integrity">
                            <CheckCircle2 size={17} />
                            {run.scenario.invariants.passed
                              ? "Conservation checks passed"
                              : "Conservation check failed"}
                          </div>
                          <p>
                            Max material residual{" "}
                            <code>
                              {run.scenario.invariants.max_mass_error.toExponential(
                                2,
                              )}
                            </code>{" "}
                            units
                          </p>
                          <p>
                            Run fingerprint{" "}
                            <code>{run.scenario.result_hash.slice(0, 16)}</code>
                          </p>
                          <div className="action-row">
                            <button onClick={explain} disabled={busy}>
                              <Sparkles size={15} /> Explain deltas
                            </button>
                            <a
                              className="button"
                              href={`/api/v1/runs/${run.id}/export.csv`}
                            >
                              <ArrowDownToLine size={15} /> KPI CSV
                            </a>
                          </div>
                        </div>
                      ) : (
                        <div className="empty">
                          <ShieldCheck size={25} />
                          <p>
                            Inventory balances, demand reconciliation, and run
                            fingerprints appear after simulation.
                          </p>
                        </div>
                      )}
                    </section>
                  </div>
                  {run && (
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <h2>Baseline vs. scenario</h2>
                          <span>
                            Identical seed and demand draws · changes apply only
                            within the active window
                          </span>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => download(`run-${run.id}.json`, run)}
                        >
                          Export full evidence <ArrowDownToLine size={15} />
                        </button>
                      </div>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Measure</th>
                              <th>Baseline</th>
                              <th>Scenario</th>
                              <th>Delta</th>
                              <th>Evidence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.keys(labels).map((key) => (
                              <tr key={key}>
                                <td>{labels[key]}</td>
                                <td>{metric(key, run.baseline.kpis[key])}</td>
                                <td>{metric(key, run.scenario.kpis[key])}</td>
                                <td>{delta(key, run.deltas[key])}</td>
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() =>
                                      setEvidence(
                                        run.evidence.find(
                                          (e) => e.metric === key,
                                        ),
                                      )
                                    }
                                  >
                                    Inspect <ChevronRight size={14} />
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  )}
                  {explanation && (
                    <section className="panel narrative">
                      <div className="panel-heading">
                        <h2>
                          {explanation.origin === "local-ai-selection"
                            ? "AI-selected evidence"
                            : "Computed explanation"}
                        </h2>
                        <span className="badge">
                          {explanation.origin.toUpperCase()}
                        </span>
                      </div>
                      <div className="evidence-body">
                        <p>{explanation.reason}</p>
                        {explanation.claims.map((c) => (
                          <button
                            className="claim"
                            key={c.id}
                            onClick={() => setEvidence(c)}
                          >
                            {c.text} <strong>{delta(c.metric, c.delta)}</strong>
                            <code>{c.id}</code>
                          </button>
                        ))}
                        <details>
                          <summary>Observable model telemetry</summary>
                          <pre>
                            {JSON.stringify(explanation.telemetry, null, 2)}
                          </pre>
                        </details>
                      </div>
                    </section>
                  )}
                  <section className="panel ai-panel">
                    <div>
                      <h2>
                        <Sparkles size={17} /> Natural-language scenario
                      </h2>
                      <p>
                        {status.ai_enabled
                          ? "Local model proposals require review before simulation."
                          : "Optional local AI is off. All simulation and evidence features work without it."}
                      </p>
                    </div>
                    <div className="ai-input">
                      <input
                        aria-label="Scenario instruction"
                        placeholder="Reduce Austin capacity by 50% from day 10 to day 35…"
                        value={instruction}
                        onChange={(e) => setInstruction(e.target.value)}
                      />
                      <button
                        onClick={propose}
                        disabled={busy || instruction.length < 5}
                      >
                        Propose <ArrowRight size={16} />
                      </button>
                    </div>
                  </section>
                </>
              )}
              {page === "scenarios" && (
                <>
                  <div className="template-grid">
                    {scenarios.map((s) => (
                      <article className="panel template" key={s.id}>
                        <div className="template-top">
                          <FlaskConical size={22} />
                          <span className="badge">VERSION {s.version}</span>
                        </div>
                        <h2>{s.name}</h2>
                        <p>{s.description}</p>
                        <small>{describe(s)}</small>
                        <button onClick={() => selectScenario(s)}>
                          Open scenario <ArrowRight size={15} />
                        </button>
                        <button
                          className="text-button"
                          onClick={async () => {
                            setVersions(
                              (
                                await api<{ items: Scenario[] }>(
                                  `/scenarios/${s.id}/versions`,
                                )
                              ).items,
                            );
                          }}
                        >
                          View versions
                        </button>
                      </article>
                    ))}
                  </div>
                  {versions.length > 0 && (
                    <section className="panel evidence-body">
                      <h2>Version history</h2>
                      {versions.map((v) => (
                        <button
                          className="version"
                          key={v.version}
                          onClick={() => selectScenario(v)}
                        >
                          {v.name} · v{v.version} <span>{describe(v)}</span>
                        </button>
                      ))}
                    </section>
                  )}
                  <section className="panel">
                    <div className="panel-heading">
                      <h2>Recent simulation runs</h2>
                      <span>{history.length} recent runs</span>
                    </div>
                    {history.length ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Scenario</th>
                              <th>Created</th>
                              <th>Replay evidence</th>
                            </tr>
                          </thead>
                          <tbody>
                            {history.map((h) => (
                              <tr key={h.id}>
                                <td>{h.name}</td>
                                <td>
                                  {new Date(h.created_at).toLocaleString()}
                                </td>
                                <td>
                                  <button
                                    onClick={async () => {
                                      const r = await api<Run>(`/runs/${h.id}`);
                                      setRun(r);
                                      setScenario(r.scenario.scenario);
                                      setNetwork(
                                        await api<Network>(
                                          `/networks/${r.scenario.network_id}`,
                                        ),
                                      );
                                      setPage("workspace");
                                    }}
                                  >
                                    Open run
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="empty">
                        Your simulation history will appear here.
                      </div>
                    )}
                  </section>
                </>
              )}
              {page === "data" && (
                <>
                  <div className="data-actions">
                    <label className="search">
                      <Search size={17} />
                      <input
                        placeholder="Search facilities, IDs, or types"
                        aria-label="Search network"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                    </label>
                    <button onClick={() => download("network.json", network)}>
                      <ArrowDownToLine size={16} /> Export network
                    </button>
                    <label className="button">
                      <Upload size={16} /> Import network
                      <input
                        type="file"
                        className="sr-only"
                        accept=".json,application/json"
                        onChange={(e) => importNetwork(e.target.files?.[0])}
                      />
                    </label>
                  </div>
                  <div className="provenance">
                    <span className="badge">RAW DATA</span>
                    <span>
                      Source <code>{network.source_id}</code>
                    </span>
                    <span>
                      Ingested{" "}
                      {new Date(network.ingested_at).toISOString().slice(0, 10)}
                    </span>
                    <span>{network.demand.length} demand records</span>
                  </div>
                  <section className="panel">
                    <div className="panel-heading">
                      <h2>Facilities</h2>
                      <span>{network.nodes.length} records</span>
                    </div>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>ID</th>
                            <th>Facility</th>
                            <th>Type</th>
                            <th>Capacity / day</th>
                            <th>Safety days</th>
                            <th>Initial days</th>
                          </tr>
                        </thead>
                        <tbody>
                          {network.nodes
                            .filter((n) =>
                              `${n.id} ${n.name} ${n.kind}`
                                .toLowerCase()
                                .includes(search.toLowerCase()),
                            )
                            .map((n) => (
                              <tr key={n.id}>
                                <td>
                                  <code>{n.id}</code>
                                </td>
                                <td>{n.name}</td>
                                <td>
                                  <span className={`type ${n.kind}`}>
                                    {n.kind}
                                  </span>
                                </td>
                                <td>{number(n.capacity)}</td>
                                <td>{n.safety_days}</td>
                                <td>{n.initial_days}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                  <section className="panel">
                    <div className="panel-heading">
                      <h2>Validation report</h2>
                      <span className="badge">
                        {report?.accepted
                          ? "ACCEPTED WITH FINDINGS"
                          : "REVIEW REQUIRED"}
                      </span>
                    </div>
                    <div className="evidence-body">
                      <p>
                        {report?.record_count} valid records. Invalid imports
                        are retained in the ingestion audit and do not replace
                        the active network.
                      </p>
                      {report?.issues.map((i, index) => (
                        <div className={`validation ${i.severity}`} key={index}>
                          <code>{i.path}</code>
                          <span>{i.message}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                  {run && (
                    <section className="panel">
                      <div className="panel-heading">
                        <h2>SKU outcomes</h2>
                        <span className="computed">COMPUTED</span>
                      </div>
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>SKU</th>
                              <th>Demand</th>
                              <th>Dispatched</th>
                              <th>Backlog</th>
                              <th>Inventory</th>
                            </tr>
                          </thead>
                          <tbody>
                            {run.scenario.skus.map((s) => (
                              <tr key={s.sku_id}>
                                <td>{s.sku_id}</td>
                                <td>{number(s.demand)}</td>
                                <td>{number(s.dispatched)}</td>
                                <td>{number(s.backlog)}</td>
                                <td>{number(s.inventory)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                  )}
                </>
              )}
              {page === "about" && (
                <div className="about-grid">
                  <section className="panel evidence-body">
                    <span className="eyebrow">A REPRODUCIBLE DIGITAL TWIN</span>
                    <h2>
                      From an operational question to inspectable evidence.
                    </h2>
                    <p>
                      SupplyTwin models material moving from suppliers through
                      plants and distribution centers to customers. Daily
                      inventory decisions compete for shared production,
                      handling, and lane capacity.
                    </p>
                    <div className="architecture">
                      {[
                        "Validated network + typed scenario",
                        "Seeded time-step simulation",
                        "Immutable run + balance ledger",
                        "Comparison + cited explanation",
                      ].map((s, i) => (
                        <div key={s}>
                          <span>0{i + 1}</span>
                          {s}
                          {i < 3 && <ArrowRight size={18} />}
                        </div>
                      ))}
                    </div>
                    <p>
                      Local AI can propose typed parameters and select verified
                      evidence. It has no database tools, shell access, or
                      ability to supply KPI values.
                    </p>
                    <a
                      className="button"
                      href="/docs"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Explore API documentation <ArrowRight size={16} />
                    </a>
                  </section>
                  <section className="panel evidence-body">
                    <h2>Model boundaries</h2>
                    <ul>
                      <li>
                        Daily time steps with continuous equivalent units and
                        one-to-one plant finishing.
                      </li>
                      <li>
                        Fixed demand forecasts and order-up-to inventory
                        policies; no BOM explosion or optimization.
                      </li>
                      <li>
                        Immediate fill measures same-day dispatch. Delivered
                        service excludes material still in transit at the
                        horizon.
                      </li>
                      <li>
                        Stockout counts are internal node–SKU–days. Cost
                        excludes initial inventory acquisition, tax, and fixed
                        overhead.
                      </li>
                      <li>
                        Shared capacity uses proportional SKU allocation and
                        daily rotating lane priority.
                      </li>
                      <li>
                        Single local operator. Multi-user tenancy is outside
                        this release.
                      </li>
                    </ul>
                    <h2>Open-source components</h2>
                    <p>
                      Python · FastAPI · Pydantic · NumPy · SQLite · React ·
                      TypeScript · Three.js · Ollama (optional).
                    </p>
                    <span className="badge">APACHE-2.0 PROJECT LICENSE</span>
                  </section>
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              SupplyTwin <span> / </span> An interactive open-source digital
              twin
            </span>
            <span>Reproducible by design. Decisions remain yours.</span>
          </footer>
        </div>
      </main>
      {evidence && (
        <div className="modal-backdrop" onClick={() => setEvidence(undefined)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-title"
            className="modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-heading">
              <h2 id="evidence-title">Computed evidence</h2>
              <button
                autoFocus
                aria-label="Close evidence"
                onClick={() => setEvidence(undefined)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="evidence-body">
              <span className="computed">DETERMINISTIC SIMULATION</span>
              <h3>{labels[evidence.metric] || evidence.metric}</h3>
              <div className="evidence-values">
                <div>
                  Baseline
                  <strong>{metric(evidence.metric, evidence.baseline)}</strong>
                </div>
                <div>
                  Scenario
                  <strong>{metric(evidence.metric, evidence.scenario)}</strong>
                </div>
                <div>
                  Delta<strong>{delta(evidence.metric, evidence.delta)}</strong>
                </div>
              </div>
              <p>
                Evidence ID: <code>{evidence.id}</code>
              </p>
              <p>
                Engine {run?.scenario.engine_version} · seed{" "}
                {run?.scenario.seed}
              </p>
              <p className="break">
                Network hash: <code>{run?.scenario.network_hash}</code>
              </p>
              <p>
                This value was computed by the simulation engine. No language
                model contributed numerical values.
              </p>
            </div>
          </section>
        </div>
      )}
      {advanced && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="parameters-title"
            className="modal wide"
          >
            <div className="panel-heading">
              <h2 id="parameters-title">Review typed scenario parameters</h2>
              <button
                aria-label="Close parameters"
                onClick={() => setAdvanced(false)}
              >
                <X size={18} />
              </button>
            </div>
            <div className="evidence-body">
              <p>
                Capacity, lane capacity, lead time, and sourcing changes are
                keyed by network IDs. Zero sourcing weights disable that source;
                remaining weights normalize.
              </p>
              <textarea
                aria-label="Scenario JSON"
                autoFocus
                value={json}
                onChange={(e) => setJson(e.target.value)}
              />
              <div className="action-row">
                <button
                  className="primary"
                  onClick={async () => {
                    try {
                      const parsed = JSON.parse(json);
                      const validated = await post<Scenario>(
                        "/scenarios",
                        parsed,
                      );
                      setScenario(validated);
                      setScenarios(
                        (await api<{ items: Scenario[] }>("/scenarios")).items,
                      );
                      setAdvanced(false);
                      setNotice(
                        "Parameters validated and saved as a new version. Run to compute outcomes.",
                      );
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  Validate & apply
                </button>
                <button onClick={() => setAdvanced(false)}>Cancel</button>
              </div>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
