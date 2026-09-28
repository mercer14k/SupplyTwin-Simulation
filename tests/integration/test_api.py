import json


def test_workflow(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").json()["status"] == "ready"
    network = client.get("/api/v1/networks/global-demo-v1").json()
    assert len(network["skus"]) == 60
    assert client.get("/api/v1/networks/global-demo-v1/validation").json()["issues"]
    scenario = client.get("/api/v1/scenarios").json()["items"][0]
    saved = client.post("/api/v1/scenarios", json=scenario, headers={"Idempotency-Key": "save-1"})
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert (
        client.post("/api/v1/scenarios", json=scenario, headers={"Idempotency-Key": "save-1"}).json()
        == saved.json()
    )
    body = {"network_id": network["id"], "scenario": saved.json()}
    response = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "run-1"})
    assert response.status_code == 200
    run = response.json()
    assert run["scenario"]["invariants"]["passed"]
    assert (
        client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "run-1"}).json()["id"] == run["id"]
    )
    assert client.get(f"/api/v1/runs/{run['id']}").json() == run
    assert client.get(f"/api/v1/runs/{run['id']}/export.csv").text.startswith("id,metric,baseline")
    assert client.post(f"/api/v1/runs/{run['id']}/explanation").json()["origin"] == "deterministic"
    assert client.get("/api/v1/runs?limit=1&offset=0").json()["total"] == 1
    body["scenario"]["seed"] += 1
    assert client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "run-1"}).status_code == 409
    assert response.headers["X-Trace-ID"]


def test_invalid_import_retained_without_mutation(client):
    network = client.get("/api/v1/networks/global-demo-v1").json()
    bad = json.loads(json.dumps(network))
    bad["nodes"][0]["capacity"] = -10
    response = client.post("/api/v1/networks/import", json=bad, headers={"X-Filename": "../../bad.json"})
    assert response.status_code == 200
    assert not response.json()["report"]["accepted"]
    assert client.get("/api/v1/networks/global-demo-v1").json() == network
    audit = client.get("/api/v1/ingestions").json()
    assert audit["total"] == 1 and audit["items"][0]["filename"] == "bad.json"


def test_valid_import_and_immutable_network(client):
    network = client.get("/api/v1/networks/global-demo-v1").json()
    network["id"] = "new-network"
    assert client.post("/api/v1/networks/import", json=network).json()["report"]["accepted"]
    network["nodes"][0]["capacity"] = 1
    assert client.post("/api/v1/networks/import", json=network).status_code == 409
    assert client.get("/api/v1/networks/new-network").json()["nodes"][0]["capacity"] != 1


def test_negative_paths(client):
    assert (
        client.post(
            "/api/v1/networks/import", content="broken", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/api/v1/networks/import", content="{broken", headers={"Content-Type": "application/json"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/networks/import",
            content="x" * (10 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert client.post("/api/v1/runs", json={}).status_code == 422
    assert client.get("/api/v1/runs/missing").status_code == 404
    response = client.get("/api/v1/runs?limit=10000")
    assert response.status_code == 422
    assert "trace_id" in response.json()["error"]


def test_authorization_and_origin_boundaries(client, monkeypatch):
    scenario = client.get("/api/v1/scenarios").json()["items"][0]
    assert (
        client.post(
            "/api/v1/scenarios", json=scenario, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    monkeypatch.setenv("API_TOKEN", "unit-test-only")
    assert client.post("/api/v1/scenarios", json=scenario).status_code == 401
    assert (
        client.post(
            "/api/v1/scenarios", json=scenario, headers={"Authorization": "Bearer unit-test-only"}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/scenarios").status_code == 200


def test_ai_disabled_and_schemas(client):
    assert not client.get("/api/v1/status").json()["ai_enabled"]
    assert (
        client.post("/api/v1/ai/propose", json={"instruction": "Reduce Austin capacity"}).json()["status"]
        == "abstained"
    )
    schema = client.get("/openapi.json").json()
    assert "/api/v1/runs" in schema["paths"]


def test_idempotency_with_server_generated_provenance(client):
    minimal = {"id": "minimal", "source_id": "test", "name": "Minimal"}
    first = client.post("/api/v1/scenarios", json=minimal, headers={"Idempotency-Key": "minimal-save"})
    second = client.post("/api/v1/scenarios", json=minimal, headers={"Idempotency-Key": "minimal-save"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    body = {"scenario": minimal}
    first = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "minimal-run"})
    second = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "minimal-run"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
