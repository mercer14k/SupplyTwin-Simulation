"""Versioned HTTP adapter. Computation and persistence live in packages/supplytwin."""

import csv
import io
import json
import logging
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from supplytwin.ai import AIService, OllamaRuntime
from supplytwin.data import generate, templates, validate
from supplytwin.domain import AIRequest, Network, RunRequest, Scenario
from supplytwin.engine import compare, digest
from supplytwin.store import Conflict, Store

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("supplytwin.api")
ROOT = Path(__file__).resolve().parents[2]
MAX_UPLOAD = 10 * 1024 * 1024


def create_app(db_path=None, ai=None):
    @asynccontextmanager
    async def lifespan(app):
        store = Store(db_path or os.getenv("DATABASE_PATH", str(ROOT / ".local/supplytwin.db")))
        sample = ROOT / "data/sample/network.json"
        if not store.network("global-demo-v1"):
            store.put_network(
                json.loads(sample.read_text()) if sample.exists() else generate().model_dump(mode="json")
            )
        if not store.scenarios():
            for scenario in templates():
                store.save_scenario(scenario.model_dump(mode="json"))
        app.state.store = store
        app.state.ai = ai or AIService(
            OllamaRuntime(
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            )
            if os.getenv("AI_ENABLED", "false").lower() == "true"
            else None
        )
        yield

    app = FastAPI(title="SupplyTwin", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def trace(request: Request, call_next):
        request.state.trace_id = str(uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        log.info(
            json.dumps(
                dict(
                    event="request",
                    trace_id=request.state.trace_id,
                    method=request.method,
                    path=request.url.path,
                    status=response.status_code,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                )
            )
        )
        return response

    def error(request, status, code, message, details=None):
        return JSONResponse(
            status_code=status,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "trace_id": getattr(request.state, "trace_id", None),
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def schema_error(request, exc):
        return error(
            request,
            422,
            "invalid_request",
            "Request failed schema validation",
            [{"path": list(e["loc"]), "message": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return error(request, 409, "conflict", str(exc))

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return error(request, 422, "invalid_value", str(exc))

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        log.exception(
            json.dumps(dict(event="unexpected_error", trace_id=getattr(request.state, "trace_id", None)))
        )
        return error(
            request, 500, "internal_error", "Request failed; use the trace ID to inspect server logs"
        )

    def store(request: Request):
        return request.app.state.store

    def authorize(request: Request, authorization: str | None = Header(default=None)):
        expected = os.getenv("API_TOKEN")
        if expected and not secrets.compare_digest(authorization or "", f"Bearer {expected}"):
            raise HTTPException(401, "Valid bearer token required for mutations")
        origin = request.headers.get("origin")
        allowed = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin and origin not in allowed:
            raise HTTPException(403, "Origin is not allowed to mutate local state")

    def network_for(repo, identifier):
        raw = repo.network(identifier)
        if not raw:
            raise HTTPException(404, "Network not found")
        return Network.model_validate(raw)

    def run_for(repo, identifier):
        run = repo.run(identifier)
        if not run:
            raise HTTPException(404, "Run not found")
        return run

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready(repo=Depends(store)):
        with repo.connection(True) as db:
            db.execute("SELECT 1").fetchone()
        return {"status": "ready", "engine": "1.0.0"}

    @app.get("/api/v1/status")
    def status(request: Request):
        return dict(
            ai_enabled=request.app.state.ai.runtime is not None,
            engine="1.0.0",
            auth_required=bool(os.getenv("API_TOKEN")),
            mode="single-operator-local",
        )

    @app.get("/api/v1/networks")
    def networks(repo=Depends(store)):
        return {"items": repo.list_networks()}

    @app.get("/api/v1/networks/{identifier}", response_model=Network)
    def network(identifier: str, repo=Depends(store)):
        return network_for(repo, identifier)

    @app.get("/api/v1/networks/{identifier}/validation")
    def validation(identifier: str, repo=Depends(store)):
        return validate(network_for(repo, identifier).model_dump(mode="json"))[1]

    @app.post("/api/v1/networks/import", dependencies=[Depends(authorize)])
    async def import_network(request: Request, repo=Depends(store)):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "Use application/json")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_UPLOAD:
                raise HTTPException(413, "Network upload exceeds 10 MiB")
        try:
            raw = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(422, "Malformed JSON") from None
        network, report = validate(raw)
        filename = re.sub(
            r"[^A-Za-z0-9_.-]",
            "_",
            request.headers.get("x-filename", "network.json").replace("\\", "/").split("/")[-1],
        )[:100]
        ingestion_id = repo.ingestion(raw, filename, report.model_dump())
        if network:
            repo.put_network(network.model_dump(mode="json"))
        return {"ingestion_id": ingestion_id, "report": report, "network_id": network.id if network else None}

    @app.get("/api/v1/ingestions")
    def ingestions(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), repo=Depends(store)):
        return repo.ingestions(limit, offset)

    @app.get("/api/v1/scenarios")
    def scenarios(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), repo=Depends(store)):
        rows = repo.scenarios()
        return dict(items=rows[offset : offset + limit], total=len(rows), offset=offset, limit=limit)

    @app.get("/api/v1/scenarios/{identifier}/versions")
    def versions(identifier: str, repo=Depends(store)):
        return {"items": repo.scenarios(identifier)}

    @app.post("/api/v1/scenarios", response_model=Scenario, dependencies=[Depends(authorize)])
    def save_scenario(
        scenario: Scenario, idempotency_key: str | None = Header(None, max_length=128), repo=Depends(store)
    ):
        return repo.save_scenario(
            scenario.model_dump(mode="json"),
            idempotency_key,
            digest(scenario.model_dump(mode="json", exclude_unset=True)),
        )

    @app.post("/api/v1/runs", dependencies=[Depends(authorize)])
    def run(
        body: RunRequest, idempotency_key: str | None = Header(None, max_length=128), repo=Depends(store)
    ):
        network = network_for(repo, body.network_id)
        fingerprint = digest(body.model_dump(mode="json", exclude_unset=True))
        # One local worker, serialized compute: protects memory and retry idempotency.
        with repo.run_lock:
            previous = repo.existing_run(idempotency_key, fingerprint)
            if previous:
                return previous
            return repo.save_run(compare(network, body.scenario), idempotency_key, fingerprint)

    @app.get("/api/v1/runs")
    def runs(limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0), repo=Depends(store)):
        return repo.runs(limit, offset)

    @app.get("/api/v1/runs/{identifier}")
    def read_run(identifier: str, repo=Depends(store)):
        return run_for(repo, identifier)

    @app.get("/api/v1/runs/{identifier}/export.csv")
    def export(identifier: str, repo=Depends(store)):
        result = run_for(repo, identifier)
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["id", "metric", "baseline", "scenario", "delta", "source"]
        )
        writer.writeheader()
        writer.writerows(result["evidence"])
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="supplytwin-comparison.csv"'},
        )

    @app.post("/api/v1/ai/propose", dependencies=[Depends(authorize)])
    def propose(body: AIRequest, request: Request, repo=Depends(store)):
        return request.app.state.ai.propose(body.instruction, network_for(repo, body.network_id))

    @app.post("/api/v1/runs/{identifier}/explanation", dependencies=[Depends(authorize)])
    def explain(identifier: str, request: Request, repo=Depends(store)):
        return request.app.state.ai.explain(run_for(repo, identifier))

    return app


app = create_app()
