# Local AI design

The default is `AI_ENABLED=false`; every deterministic workflow remains available. Optional Ollama runs locally. The default suggested model is `qwen3:4b`; its upstream weights use Apache-2.0. An actual local Qwen3:8b run correctly translated the explicit Austin capacity task and selected supported evidence. This is one task, not a broad accuracy claim. The measured local model is recorded separately in `docs/benchmarks/local-ai/results.json`.

`Runtime.complete(system, user, schema)` is an injected protocol. The Ollama adapter calls local `/api/chat` with a JSON schema, temperature 0, seed 42, streaming disabled, thinking disabled, output-token bound, 60-second timeout, and one retry. Runtime adapters never receive repository credentials or mutation tools. A different local runtime can implement the protocol without changing simulation code.

Natural-language requests produce a typed parameter draft. The application adds identifiers/provenance; the model does not fabricate ingestion dates. Both structural and network-target validation run before a proposal is returned. Ambiguous or invalid requests abstain. The user reviews the proposal in the JSON editor before saving or simulating it. The AI endpoint itself never saves a scenario or runs the simulation.

Explanations are intentionally constrained: the model may select evidence IDs and change directions. The validator checks every claim against computed deltas, and deterministic templates render all numbers and wording. Unsupported claims fall back to the deterministic evidence summary. This avoids free-form causal hallucinations but limits narrative richness. It does not prove the user's natural-language intent was translated correctly, so review remains required.

Every episode records runtime/model, prompt version, source IDs, exposed token counts, configuration, latency, retry count and validation failures. There are no model tool calls; the observable list is empty. Hidden reasoning is neither exposed nor persisted. Names, imports, instructions and retrieved evidence are untrusted data, never executable instructions.

Official references: [Ollama structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx), [Qwen3 licensing](https://github.com/QwenLM/Qwen3/blob/main/README.md).
