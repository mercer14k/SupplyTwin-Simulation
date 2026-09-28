export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = sessionStorage.getItem("supplytwin-token");
  const response = await fetch("/api/v1" + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message || `Request failed (${response.status})`,
    );
  }
  return response.json();
}
export const post = <T>(path: string, body: unknown): Promise<T> =>
  api<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "Idempotency-Key": crypto.randomUUID() },
  });
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
export const number = (v: number) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(v);
export const metric = (key: string, v: number) =>
  ["fill_rate", "service", "utilization"].includes(key)
    ? `${(v * 100).toFixed(1)}%`
    : key.includes("cost")
      ? `$${number(v)}`
      : number(v);
export const delta = (key: string, raw: number) => {
  const v = Math.abs(raw) < 1e-8 ? 0 : raw;
  return `${v > 0 ? "+" : ""}${["fill_rate", "service", "utilization"].includes(key) ? `${(v * 100).toFixed(1)} pp` : metric(key, v)}`;
};
