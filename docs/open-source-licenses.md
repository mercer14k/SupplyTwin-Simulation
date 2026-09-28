# Open-source and model licenses

SupplyTwin's original source and synthetic dataset are released under Apache-2.0 (root `LICENSE`). Model weights and dependencies are not relicensed by this project. Keep upstream notices when redistributing dependencies. No proprietary hosted AI service or paid credential is in the default dependency path.

The machine-readable [dependency inventory](dependency-inventory.json) records installed versions and package-declared licenses for backend and frontend, including development packages. `requirements.lock`, `requirements-dev.lock`, and `apps/web/pnpm-lock.yaml` pin the evaluated versions. Distribution metadata can contain multiple licenses or missing fields; the upstream license files remain authoritative. Audit the exact binary wheels/images you redistribute, including platform-specific bundled libraries.

| Material dependency | License | Use / upstream notice |
|---|---|---|
| Python | PSF-2.0 | Interpreter; https://docs.python.org/3/license.html |
| FastAPI / Pydantic | MIT | API and validation; upstream distribution notices |
| Starlette / Uvicorn / HTTPX | BSD-3-Clause | HTTP stack and local runtime transport |
| NumPy 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Numerical arrays; binary distributions can bundle additional permissively licensed libraries |
| SQLite | Public domain | Local store; https://www.sqlite.org/copyright.html |
| React / React DOM | MIT | User interface |
| Three.js | MIT | Network flow rendering |
| Vite / Vitest | MIT | Build and frontend unit tests |
| TypeScript | Apache-2.0 | Static types |
| Lucide | ISC | Interface icons |
| pytest / Ruff | MIT | Backend verification |
| Playwright | Apache-2.0 | Browser tests; browser engines retain their own licenses |
| ESLint / typescript-eslint | MIT | Frontend linting |
| pnpm | MIT | Package manager |
| pip-audit | Apache-2.0 | Dependency advisory scan |
| Nginx | BSD-2-Clause | Local reverse proxy; container includes other OS packages |
| Docker Engine / Compose | Apache-2.0 | Local containers; Docker Desktop is not required |
| Ollama | MIT | Optional local runtime; https://github.com/ollama/ollama/blob/main/LICENSE |
| Qwen3-4B / Qwen3-8B | Apache-2.0 | Optional open-weight models; https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE and https://huggingface.co/Qwen/Qwen3-8B/blob/main/LICENSE |
| GitHub Actions checkout/setup/upload actions | MIT | Open-source workflow actions; hosted GitHub service is optional infrastructure, not a runtime dependency |

Container base images include Debian or Alpine packages under their respective licenses. The Python image, Node build image and Nginx image must retain upstream notices. This inventory documents material dependencies; it is not legal advice or a certification of every future dependency update.

There are no commercial stock images, remote map tiles, paid fonts, copied enterprise datasets or bundled model weights. The network view draws project data; UI icons are Lucide. Qwen model downloads must remain lawful under their upstream license and any applicable distribution restrictions. A user may supply a different local model, but is responsible for reviewing that model's terms before redistribution.
