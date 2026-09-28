import type { Day } from "./types";
import { number } from "./api";
export default function Chart({
  baseline,
  scenario,
  field,
}: {
  baseline: Day[];
  scenario: Day[];
  field: "backlog" | "inventory" | "fill_rate";
}) {
  const max = Math.max(
    1,
    ...baseline.map((d) => d[field]),
    ...scenario.map((d) => d[field]),
  );
  const path = (rows: Day[]) =>
    rows
      .map(
        (d, i) =>
          `${i ? "L" : "M"}${40 + (i / (rows.length - 1)) * 620},${155 - (d[field] / max) * 130}`,
      )
      .join(" ");
  return (
    <svg
      className="chart"
      viewBox="0 0 690 195"
      role="img"
      aria-label={`${field} by day, baseline and scenario`}
    >
      {[0, 0.5, 1].map((x) => (
        <g key={x}>
          <line
            x1="40"
            x2="660"
            y1={155 - x * 130}
            y2={155 - x * 130}
            stroke="#253044"
            strokeDasharray="3 6"
          />
          <text x="2" y={160 - x * 130}>
            {field === "fill_rate"
              ? `${Math.round(max * x * 100)}%`
              : number(max * x)}
          </text>
        </g>
      ))}
      <path
        d={path(baseline)}
        fill="none"
        stroke="#788ba9"
        strokeWidth="2"
        strokeDasharray="5 4"
      />
      <path d={path(scenario)} fill="none" stroke="#72e5b1" strokeWidth="2.8" />
      {[0, 0.25, 0.5, 0.75, 1].map((x) => (
        <text key={x} x={40 + x * 620} y="184" textAnchor="middle">
          Day {Math.round(x * (scenario.length - 1))}
        </text>
      ))}
    </svg>
  );
}
