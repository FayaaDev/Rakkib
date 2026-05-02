# Rakkib Web UI Plan

## Goal

Add a browser-based setup and management UI for Rakkib while preserving Rakkib's core contract: a fresh Ubuntu server should still be installable through the one-line `install.sh` flow, without requiring Node.js, npm, pnpm, or a separate JavaScript server on the target machine.

The primary user flow is:

```bash
curl -fsSL https://raw.githubusercontent.com/FayaaDev/Rakkib/main/install.sh | bash
rakkib web --lan
```

Rakkib then prints a local URL and a LAN URL that can be opened from another device to continue the setup in a browser.

## Framework Decision

Use a React + Vite single-page app.

Do not use Next.js for the first web UI.

Reasons:

- Rakkib does not need SSR, server components, or SEO-oriented routing.
- A Vite SPA can be built ahead of time and shipped as static package data.
- The target server should not need a Node.js runtime.
- Rakkib already has a Python CLI, state model, registry, and setup engine; the web layer should expose those through a Python API rather than introduce a second backend runtime.
- The UI is primarily authenticated local/LAN administration: forms, service selection, progress, logs, diagnostics, and status.

## High-Level Architecture

```text
Browser on laptop/phone/tablet
  |
  | HTTP with setup token
  v
rakkib web process on target server
  |
  | Serves built React SPA
  | Serves JSON API
  | Streams setup events/logs
  v
Existing Rakkib Python modules
  - State
  - schema/question engine
  - registry.yaml
  - doctor checks
  - setup steps
  - service add/remove/restart
```

The web UI must not duplicate Rakkib's installer logic. It should call shared Python functions and keep the CLI and web flows aligned.

## Repository Layout

Recommended layout:

```text
web/
  package.json
  vite.config.ts
  src/
    app/
    components/
    api/
    routes/
    styles/
  dist/

src/rakkib/web/
  __init__.py
  app.py
  auth.py
  api.py
  events.py
  models.py
  runner.py
  static.py

src/rakkib/data/web/
  index.html
  assets/
```

Build output from `web/dist/` should be copied into `src/rakkib/data/web/` before packaging/release so the installed Python package can serve it.

## Runtime Command

Add a new CLI command:

```bash
rakkib web
```

Recommended options:

```bash
rakkib web
rakkib web --lan
rakkib web --host 127.0.0.1 --port 8080
rakkib web --host 0.0.0.0 --port 8080
rakkib web --no-open
rakkib web --token <token>
rakkib web --no-token
```

Default behavior:

- Bind to `127.0.0.1` by default.
- Require a token by default.
- Print a local URL.
- Do not expose on LAN unless explicitly requested.

LAN behavior:

- `rakkib web --lan` binds to `0.0.0.0`.
- Detects the primary LAN IP.
- Prints a LAN URL with the setup token.
- Keeps all execution on the target server.

Example output:

```text
Rakkib web UI is running.

Local:
  http://127.0.0.1:8080/setup?token=abc123

LAN:
  http://192.168.0.235:8080/setup?token=abc123

Keep this terminal open while using the web UI.
Press Ctrl+C to stop.
```

## Python Web Backend

Use a small Python ASGI backend.

Recommended dependency:

```text
fastapi
uvicorn[standard]
```

Alternative with fewer dependencies:

```text
starlette
uvicorn
```

FastAPI is the pragmatic choice because request/response schemas, validation, and API docs are useful for a control-plane UI.

The backend should be a thin adapter over existing Rakkib functions.

## Packaging Constraint

The target machine should not need Node.js at runtime.

Release/build flow:

```text
Developer/CI machine:
  cd web
  npm ci
  npm run build
  rsync/copy dist/ into src/rakkib/data/web/
  build Python package

Target server:
  install.sh
  rakkib web
```

Python package data must include the static web files:

```toml
[tool.setuptools.package-data]
rakkib = ["data/**/*"]
```

This already matches the current packaging pattern and should be extended to include `data/web/**/*` once the built assets are added.

## State Model

The source of truth remains `.fss-state.yaml`.

The web backend should load and save state through `rakkib.state.State`.

Important rules:

- The browser must not become the source of truth.
- Setup progress must survive browser refreshes.
- If the browser disconnects, the user should reopen the printed URL and continue.
- Secrets should never be returned by default once saved.
- Web and CLI should use the same phase completion rules.

## API Design

Initial API surface:

```text
GET  /api/health
GET  /api/session
POST /api/session/refresh-token

GET  /api/state
PATCH /api/state
GET  /api/state/resume

GET  /api/questions
GET  /api/questions/phases
GET  /api/questions/phases/{phase}
POST /api/questions/phases/{phase}/answers

GET  /api/registry
GET  /api/services
POST /api/services/selection/preview
POST /api/services/selection/apply

GET  /api/doctor
POST /api/doctor/fix/{check}

POST /api/pull/start
POST /api/pull/cancel
GET  /api/pull/status
GET  /api/pull/events

POST /api/services/{service_id}/restart
POST /api/services/restart-all

GET  /api/logs
GET  /api/logs/{name}
```

Use Server-Sent Events for setup progress first. WebSockets are optional and likely unnecessary for v1.

Recommended streaming endpoints:

```text
GET /api/pull/events
GET /api/logs/events
```

## Setup Flow

The web UI should map to the existing six Rakkib phases.

Current phases:

```text
1. Platform
2. Identity
3. Services
4. Cloudflare
5. Secrets
6. Confirm
```

The web flow should be resumable:

```text
Load state
Compute resume_phase()
Open first incomplete phase
Save each phase after valid answers
Mark confirmed only after final confirmation
Run pull only when confirmed
```

The API should expose schemas generated from `src/rakkib/data/questions/*.md`, not hardcoded frontend forms.

The frontend should render field types from schema:

```text
text
confirm
single_select
multi_select
secret_group
summary
derived
```

Derived fields should be resolved by the backend. The frontend should display results but should not run host detection commands.

## Service Selection UI

The service selection UI should be registry-driven.

It should read from `src/rakkib/data/registry.yaml` through an API endpoint.

UI requirements:

- Group services by registry category.
- Show always-installed services as locked.
- Show foundation services preselected.
- Show optional services selectable.
- Show dependency requirements before applying.
- Show destructive warnings for deselected installed services.
- Preview additions and removals before applying.
- Require explicit confirmation before removal.

This must align with current `rakkib add` behavior, where unchecked services are fully removed.

## Pull Execution

`rakkib pull` is long-running and can include privileged operations.

The web backend should not run setup directly inside a request handler.

Use a background runner:

```text
POST /api/pull/start
  - validates confirmed state
  - starts one background setup job if none is running
  - returns job id

GET /api/pull/status
  - returns idle/running/succeeded/failed/cancelled
  - returns current step
  - returns last error

GET /api/pull/events
  - streams step output and status changes
```

Only one mutating job should run at a time:

```text
pull
add/remove service
restart all
doctor auto-fix
```

Use a process-level lock for v1. A file lock can be added later if needed.

## Privilege Model

Rakkib currently runs as the installed user and uses sudo for privileged operations.

The web UI should follow the same model.

Important constraints:

- Do not run `rakkib web` as root by default.
- Do not store sudo passwords.
- Prefer existing non-interactive sudo checks where possible.
- If sudo is required and not available, show the exact command the user should run in the terminal.
- The terminal running `rakkib web` remains part of the trusted setup session.

Recommended v1 behavior:

- `rakkib web` checks whether required sudo access is currently usable.
- If sudo auth is missing, the UI instructs the user to run `rakkib auth sudo` in the terminal.
- After sudo is validated, the UI can continue.

Avoid browser prompts for sudo password in v1.

## Authentication And LAN Safety

`rakkib web` is a local setup server, not a public web app.

Security defaults:

- Bind to `127.0.0.1` by default.
- Require a high-entropy token by default.
- `--lan` must be explicit.
- Print a warning when binding to `0.0.0.0`.
- Never expose without token unless `--no-token` is explicitly passed.
- Token should be accepted via query string once, then stored in an HTTP-only cookie.
- API requests should require the session cookie or bearer token.
- Set cache-control headers to prevent sensitive state caching.

Token lifecycle:

- Generate token at process start if not provided.
- Store only in process memory for v1.
- Stop accepting old tokens when the process restarts.
- Provide `POST /api/session/refresh-token` later if needed.

## Frontend UX

The UI should feel like a guided installer, not a generic admin dashboard.

Core screens:

```text
Start / Resume
Host Check
Phase 1: Platform
Phase 2: Identity
Phase 3: Services
Phase 4: Cloudflare
Phase 5: Secrets
Phase 6: Confirm
Run Setup
Deployment Summary
Manage Services
Doctor
Logs
```

Key UX requirements:

- Show the current phase and completion state.
- Save progress after each phase.
- Make browser refresh safe.
- Clearly separate detection results from user answers.
- Show warnings before destructive service removal.
- Show live setup output.
- Surface exact recovery commands when blocked.
- Provide copyable URLs after deployment.

## Frontend Technical Plan

Recommended stack:

```text
React
Vite
TypeScript
React Router
TanStack Query
CSS Modules or Tailwind CSS
```

Avoid heavy state management in v1. Server state should come from TanStack Query, and local component state should handle unsaved form values.

Suggested frontend structure:

```text
web/src/
  main.tsx
  app/App.tsx
  app/router.tsx
  api/client.ts
  api/types.ts
  routes/Start.tsx
  routes/Phase.tsx
  routes/Services.tsx
  routes/RunSetup.tsx
  routes/Summary.tsx
  routes/Doctor.tsx
  routes/Logs.tsx
  components/FieldRenderer.tsx
  components/ServiceCard.tsx
  components/StepTimeline.tsx
  components/EventLog.tsx
  styles/tokens.css
```

Keep the frontend mostly schema-driven so new Rakkib questions do not require frontend rewrites.

## Backend Technical Plan

Suggested backend structure:

```text
src/rakkib/web/app.py
  create_app()
  static serving
  route registration

src/rakkib/web/auth.py
  token generation
  cookie/session validation

src/rakkib/web/api.py
  REST routes

src/rakkib/web/events.py
  SSE helpers

src/rakkib/web/runner.py
  background job manager
  setup step execution
  job lock

src/rakkib/web/models.py
  API response models

src/rakkib/web/static.py
  package-data static file lookup
```

The existing CLI helpers should be refactored only when needed. Prefer small shared functions over duplicating command bodies.

Candidates for shared extraction:

```text
resolve repo/state paths
load registry
validate service dependencies
apply service selection
run setup steps
summarize deployed URLs
doctor checks and auto-fixes
```

## CLI Integration

Add command to `src/rakkib/cli.py`:

```text
@cli.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8080)
@click.option("--lan", is_flag=True)
@click.option("--token")
@click.option("--no-token", is_flag=True)
@click.option("--no-open", is_flag=True)
def web(...):
    ...
```

The command should:

- Resolve `repo_dir` and `.fss-state.yaml` path.
- Generate or validate the setup token.
- Create the ASGI app with explicit settings.
- Print local/LAN URLs.
- Start uvicorn.

Do not auto-open a browser on headless Linux by default. Local development may support browser opening later.

## Data Privacy

Some state values are secrets or sensitive infrastructure details.

API responses should redact:

```text
secrets.values
password fields
tokens
Cloudflare tunnel tokens
database passwords
service secret keys
```

Use write-only fields for secrets in the UI:

- Empty means keep existing value.
- New value replaces saved value.
- API returns `configured: true` instead of returning the secret.

## Logs

Use logs to make long setup understandable and debuggable.

Recommended behavior:

- Keep an in-memory event buffer for the active `rakkib web` process.
- Also write setup logs to the existing log locations used by steps where applicable.
- Show current step, command summary, stdout/stderr tail, and failure details.
- Link failure messages to actionable commands.

Do not stream secret values.

## Development Workflow

Local frontend development:

```bash
cd web
npm install
npm run dev
```

Backend development:

```bash
rakkib web --host 127.0.0.1 --port 8080
```

During development, Vite can proxy `/api` to the Python backend.

Production/release build:

```bash
cd web
npm ci
npm run build
rm -rf ../src/rakkib/data/web
mkdir -p ../src/rakkib/data/web
cp -R dist/* ../src/rakkib/data/web/
```

The release package should include only built static assets, not `node_modules`.

## Testing Strategy

Do not rely on the current development machine as proof of bare-metal behavior. The project rule remains: install behavior must be validated on a clean Ubuntu 24.04 machine.

Test layers:

```text
Frontend:
  npm run build
  component tests for field rendering
  API client tests with mocked responses

Backend:
  unit tests for token auth
  unit tests for state redaction
  unit tests for schema-to-API serialization
  unit tests for service selection preview

Integration:
  rakkib web starts and serves static UI
  setup token required
  /api/state resumes existing .fss-state.yaml
  /api/pull/start refuses unconfirmed state
  service removal preview warns about destructive actions

Bare-metal acceptance:
  fresh Ubuntu 24.04
  install.sh succeeds
  rakkib web --lan starts
  browser on another device can complete setup
  setup survives browser refresh
```

## Milestones

### Milestone 1: Backend Skeleton

Deliverables:

- Add optional web dependencies.
- Add `src/rakkib/web/` package.
- Add `rakkib web` command.
- Serve a placeholder static page.
- Implement token guard.
- Print local and LAN URLs.

Acceptance:

- `rakkib web` starts on localhost.
- `rakkib web --lan` prints a LAN URL.
- API rejects requests without token/session.

### Milestone 2: State And Schema API

Deliverables:

- Expose redacted state.
- Expose phase schemas.
- Save answers through API.
- Compute resume phase.

Acceptance:

- Browser can complete phases 1-6 using the same `.fss-state.yaml` model.
- Refreshing the browser resumes correctly.
- Secrets are never returned in plaintext.

### Milestone 3: React Installer UI

Deliverables:

- Replace placeholder with Vite React SPA.
- Build guided phase screens.
- Implement schema-driven field renderer.
- Implement confirmation screen.

Acceptance:

- User can complete `rakkib init` equivalent from the browser.
- The resulting state can still be used by CLI `rakkib pull`.

### Milestone 4: Setup Runner

Deliverables:

- Add background job runner.
- Start setup from web UI.
- Stream setup events via SSE.
- Show success/failure state.

Acceptance:

- User can click Run Setup after confirmation.
- UI shows step-by-step progress.
- Failed setup displays actionable error and log path.

### Milestone 5: Service Management

Deliverables:

- Registry-driven service management UI.
- Add/remove preview.
- Destructive confirmation.
- Restart service actions.

Acceptance:

- Web UI supports `rakkib add` equivalent.
- Deselecting installed services warns about data removal.
- Restart actions match CLI behavior.

### Milestone 6: Doctor And Polish

Deliverables:

- Doctor screen.
- Guided fix actions where safe.
- Deployment summary with service URLs.
- Mobile layout polish.
- Accessibility pass.

Acceptance:

- UI is usable from phone/tablet on LAN.
- Common blockers show clear fix commands.
- Deployment summary matches CLI status output.

## Risks And Decisions

Open decisions:

- Whether web dependencies should be installed by default or through an extra such as `rakkib[web]`.
- Whether `rakkib web` should be part of the default `install.sh` installation immediately or gated behind a beta flag.
- Whether sudo authentication should remain terminal-only in v1.
- Whether active setup jobs need file-based locking across multiple `rakkib web` processes.

Primary risks:

- Accidentally introducing Node.js as a target runtime dependency.
- Duplicating CLI logic instead of sharing it.
- Exposing a privileged setup server on LAN without a strong token.
- Returning secrets through state APIs.
- Letting multiple mutating jobs run at once.

Recommended decisions for v1:

- Ship built static assets inside the Python package.
- Use FastAPI + Uvicorn for the web backend.
- Require token auth by default.
- Keep sudo password entry in the terminal.
- Use SSE for progress streaming.
- Use a process-level lock for mutating jobs.

## Definition Of Done

The web UI is complete when:

- `rakkib web --lan` starts on a fresh installed target.
- Another device on the same LAN can open the printed URL.
- The user can complete the Rakkib interview in the browser.
- The user can start setup from the browser after confirmation.
- Setup progress streams live and remains understandable.
- Refreshing the browser resumes from saved server-side state.
- Secrets are redacted in all API responses.
- Service selection and removal behavior matches `rakkib add`.
- The CLI remains fully usable without the web UI.
- No Node.js runtime is required on the target server.
