# Production Readiness Checklist — Omnyxnet

This document breaks the full work required to take the repository to production readiness into small, actionable steps. All automated tests and verification steps should run inside containers (Docker or other OCI-compatible runtimes) to ensure reproducible, hermetic execution.

Goals
- Provide a repeatable, container-first workflow for code quality, security, testing, and deployment.
- Produce CI that builds and validates artifacts inside containers.
- Ensure observable, secure, and resilient production deployments.

Assumptions
- You have Docker available locally and in CI.
- The repo contains Python services (adjust commands if other languages exist).
- The default branch is `main`; new work should be merged via PRs.

How to use this file
- Follow each numbered section in order. Each section contains small steps and example Docker commands.

1) Repo hygiene (quick) — Completed. See the **Completed** section at the end of this document.

2) Static analysis & formatting
 - Add `ruff` (or `flake8`), `black` and a pre-commit config.
 - Run these inside a test container and fix issues; enforce in CI.

Commands (containerized)
```bash
docker run --rm -v "$PWD":/app -w /app omnyxnet:dev ruff .
docker run --rm -v "$PWD":/app -w /app omnyxnet:dev black --check .
```

Status: attempted
- I attempted to build `omnyxnet:dev` and run these checks inside Docker, but the Docker daemon is not available in this environment ("Cannot connect to the Docker daemon").
- Next steps for you or CI:
  - Start the Docker daemon locally and run the example commands above, or
  - If you prefer I can run the equivalent checks outside containers (directly on the runner) and report findings.


3) Type checks
 - Add `mypy` or appropriate type checker. Run in container and resolve type issues.

4) Tests — unit, integration, e2e (container-first strategy)
 - Unit tests: run in lightweight test image.
 - Integration tests: run in docker-compose with dependent services (DB, Redis, etc.).
 - E2E: run against a staging deployment composed of containers.

Example docker-compose test flow
```bash
# start dependencies and the app in compose (compose file under /docker or repo root)
docker-compose -f docker/docker-compose.test.yml up -d --build

# run tests in an ephemeral test container that has network access to the services
docker run --rm --network host -v "$PWD":/app -w /app omnyxnet:dev pytest tests/integration -q

# tear down
docker-compose -f docker/docker-compose.test.yml down
```

5) Coverage and gating
 - Collect coverage inside containers and fail CI if coverage < target (e.g., 80%).

6) Dependency management & security audits
 - Produce a lockfile (`requirements.txt` with pinned versions or `poetry.lock`).
 - Run `pip-audit` or `safety` inside a container and remediate vulnerabilities.

Containerized audit example
```bash
docker run --rm -v "$PWD":/app -w /app omnyxnet:dev bash -lc "pip install pip-audit && pip-audit --format=json > audit.json"
```

7) Build artifacts and container images
 - Add a production `Dockerfile` (multi-stage, minimal base, non-root user).
 - Build and scan images in CI using tools like `trivy`.

8) CI / CD (container-first)
 - Add CI workflows that:
   - Build `omnyxnet:ci` image.
   - Run linters, mypy, tests, security scans inside the image.
   - Build and push artifacts/images only after PR checks pass.
 - Example jobs: `lint`, `unit-tests`, `integration-tests`, `security-scan`, `build-image`.

9) Configuration & secrets
 - Do NOT store secrets in repo. Provide `env.example` and require env validation on startup.
 - Use GitHub Secrets / Vault for CI and deployments.

10) Runtime hardening
 - Run containers as non-root, drop unnecessary capabilities, and set resource limits.
 - Add healthchecks and readiness/liveness checks.

11) Observability & alerts
 - Add structured logs and metrics exporters. Run a Prometheus scrape and Grafana dashboard in staging containers.
 - Add smoke checks executed by CI or a synthetic job.

12) Database migrations & backups
 - Put migrations under version control (Alembic). Run them as part of container start in a controlled manner.
 - Create backup containers and test restores in staging.

13) Performance testing
 - Create a load-testing container (locust/jmeter) and run against staging; iterate to meet SLOs.

14) Release, canaries & rollback
 - Build images with immutable tags, deploy via orchestrator (Kubernetes/Helm recommended).
 - Use canary or blue/green by limiting traffic and running health checks.

15) Final security review & compliance
 - Run threat model and, if needed, external penetration testing once staging is clean.

16) Docs & runbooks
 - Add ops runbooks that show the exact container commands for deploying, rollback, and debugging.

Example minimal commands to include in runbooks
```bash
# build image locally
docker build -t ghcr.io/<org>/omnyxnet:$(git rev-parse --short HEAD) -f Dockerfile .

# run a one-off migration
docker run --rm -e ENV=staging ghcr.io/<org>/omnyxnet:tag alembic upgrade head

# run smoke test container
docker run --rm --network host ghcr.io/<org>/omnyxnet:tag pytest tests/smoke -q
```

Next actions (pick one)
- I can start by running linters and tests inside a container locally and report results.
- I can add a `Dockerfile.dev` and `docker/docker-compose.test.yml` (if missing) to make tests reproducible.
- I can scaffold CI workflows that run the containerized checks on every PR.

If you want me to start executing steps, tell me which of the three options above to run first.

## Completed

### Repo hygiene (completed)

- Actions performed:
  - Added `Dockerfile.dev` at the repository root to provide a reproducible dev/test image.
  - Added `docker/docker-compose.test.yml` to standardize integration/test compose flows.

- How to use the artifacts:
  - Build the dev image locally:
    ```bash
    docker build -t omnyxnet:dev -f Dockerfile.dev .
    ```
  - Run unit tests inside the image:
    ```bash
    docker run --rm -v "$PWD":/app -w /app omnyxnet:dev pytest -q
    ```
  - Run the docker-compose test flow (compose will wait for `.tests-ready` file):
    ```bash
    docker-compose -f docker/docker-compose.test.yml up --build -d
    # create indicator file to trigger test run in the composed app service
    touch .tests-ready
    docker-compose -f docker/docker-compose.test.yml logs -f --tail=100
    docker-compose -f docker/docker-compose.test.yml down
    ```

Files added:
- `Dockerfile.dev`
- `docker/docker-compose.test.yml`

### Static analysis & formatting (checks run)

- Actions performed:
  - Ran `ruff check .`, `black --check .`, and `mypy` inside the `omnyxnet:dev` container.

- Summary of findings:
  - `ruff` reported 256 issues across the codebase; 177 are fixable with `ruff --fix`.
  - Common `ruff` problems: extraneous `f` prefix on print/f-string literals, unused imports, unused local variables, bare `except:` usages, ambiguous short names.
  - `black` would reformat 55 files (style differences detected).
  - `mypy` reported a blocking error: "Duplicate module named 'main'" (conflicting paths: `services/python-ai-client/app/main.py` and `python/main.py`). This requires adjusting module layout or `mypy` config.

- Commands to reproduce locally (containerized):
  ```bash
  docker build -t omnyxnet:dev -f Dockerfile.dev .
  docker run --rm -u testuser -v "$PWD":/app -w /app omnyxnet:dev bash -lc \
    "python -m pip install --user ruff black mypy pytest >/dev/null 2>&1 && python -m ruff check . || true && python -m black --check . || true && python -m mypy --ignore-missing-imports . || true"
  ```

- Recommended next actions to address findings:
  1. Auto-fix style & many lint issues:
     - `ruff --fix .` then `python -m black .` to apply formatting and safe fixes.
  2. Manually inspect and fix remaining `ruff` issues (unused variables/imports, bare `except`, logic gaps).
  3. Resolve `mypy` duplicate-module error by either:
     - Removing or renaming one of the `main.py` files, or
     - Adding `__init__.py` to create explicit packages, or
     - Configuring `mypy` with `--exclude` or `--explicit-package-bases`.
  4. Re-run the checks inside the container until clean.

- Status: checks executed; fixes required (see recommended next actions).
 - Status: auto-fixes applied (see repo commit). Remaining issues listed below.

### Auto-fix results

- Actions taken:
  - Ran `ruff --fix .` and `black .` and committed the changes in branch `copilot/rebase-fixes-2025-12-22`.
  - Commit message: "style: apply ruff --fix and black formatting" (58 files changed).

- Remaining issues after auto-fix:
  - `ruff`/format auto-fixes addressed 177 fixable issues; 78 lint/type issues remain that require manual attention (unused imports/variables, bare `except`, ambiguous names, undefined variables, and duplicate definitions in CLI).
  - `mypy` still reports a blocking error: duplicate module named `main` (`services/python-ai-client/app/main.py` and `python/main.py`).

- Recommended manual fixes (next):
  1. Resolve duplicate `main` modules by renaming or introducing packages (`__init__.py`) or adjusting `mypy` config.
  2. For each remaining `ruff` issue, fix code as appropriate (remove unused imports/variables, avoid bare `except`, fix undefined names like `e`).
  3. Re-run `mypy` and targeted unit tests inside the container.


