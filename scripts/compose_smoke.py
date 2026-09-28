"""Stdlib-only check against the actual Compose web proxy and persisted API."""

import json
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8080"


def read(path, body=None):
    request = Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=120) as response:
        return json.load(response)


assert read("/ready")["status"] == "ready"
scenario = read("/api/v1/scenarios")["items"][0]
result = read("/api/v1/runs", {"network_id": "global-demo-v1", "scenario": scenario})
assert result["scenario"]["invariants"]["passed"]
assert read(f"/api/v1/runs/{result['id']}")["scenario"]["result_hash"] == result["scenario"]["result_hash"]
print("Compose workflow: readiness, simulation, conservation, persistence passed")
