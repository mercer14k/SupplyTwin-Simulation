import { describe, it, expect } from "vitest";
import { metric, delta } from "./api";
describe("analytical display semantics", () => {
  it("distinguishes percentage points from relative percent", () => {
    expect(delta("fill_rate", -0.05)).toBe("-5.0 pp");
    expect(metric("service", 0.95)).toBe("95.0%");
  });
  it("formats negative cost and zero values", () => {
    expect(delta("total_cost", -100)).toBe("$-100");
    expect(metric("backlog", 0)).toBe("0");
  });
});
