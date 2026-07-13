# Plant CPS Web App

A phone-friendly dashboard for the P13 autonomous balcony plant watering CPS (TU Berlin, CPS SoSe 2026). Displays system status, sensor data, anomaly alerts, and weather forecasts in non-expert language. Supports manual watering with a confirmation step, two view modes (simple / advanced), and email alerts for critical events.

## Architecture

```
other groups → MQTT broker → P06 logger (InfluxDB + HTTP query API)
                                   ↓  (polled every 10 s)
                             FastAPI backend ── REST/JSON ──> Vue 3 SPA
                                   ↑                          (polls every 3 s)
        manual watering: Sparkplug B DCMD → MQTT → P05 controller
```

- **Reads** come from P06's HTTP query API (`P06_API_URL`, default `:8088`) — not from MQTT directly.
- **The one write** is the manual watering command: Sparkplug B protobuf (via the shared `cps-schema` package) published to P05's command topic. The backend acts as a minimal Sparkplug node (NBIRTH / NDEATH / sequence counter).
- **Demo mode** (`MOCK_DATA=true`) swaps the sensor service for a self-contained mock — no broker, no P06, no schema needed. Same REST shapes, same frontend.

## What this includes

- **`frontend/`** — Vue 3 + Vite + Tailwind + PrimeVue + ApexCharts + vue-router. Dark glassmorphism theme. Pages: Welcome (video bg), Dashboard, Settings, Login.
  - Simple / advanced view toggle (UI preference, independent of roles)
  - Plant-health headline, status banner, stat cards with hover explainers + normal ranges
  - System-overview SVG (live tank fill, animated pump while watering)
  - Soil-moisture & temperature charts (1h / 12h / 24h) with 💧 watering-event markers
  - Alert panel + in-app toasts + best-effort browser notifications
  - Editable plant watering profiles (operator), watering history (advanced view)
- **`backend/`** — FastAPI + **fastapi-users** (JWT auth, roles viewer/operator/admin, SQLite) + **fastapi-mail** (email on manual watering and on critical anomaly alerts, with per-component cooldown; demo via Mailpit) + **httpx** (P06 client) + **paho-mqtt** (watering publisher, TLS/credentials-ready for P09).
- **`scripts/export-to-monorepo.sh`** — one-command source sync into the course monorepo: cuts `p13/sync` fresh from the monorepo's `origin/main` (integration team's work is always the base), rsyncs only our source areas (`backend/app/`, `frontend/src|public/` + configs), commits; `--push` for an MR. Never touches workspace-managed files (`backend/pyproject.toml`, `bun.lock`). In the monorepo, P13 runs via P10's `scripts/run.sh` (backend :8000 + vite :5173).

## Not included (by design / blocked)

- Real plant-health score — P16 (Plant Health Model) is vacant this term; the headline is a placeholder derived from system status
- Plant-profile edits in real mode — waiting on a P05 command path (demo mode is fully editable)
- Secured broker connection is wired but **off by default** — waiting on P09's TLS cert + credentials
- Postgres — SQLite is sufficient for users-only relational data (sensor history lives in P06's InfluxDB); swap via `DATABASE_URL` if ever needed

## Quick start

### One command (recommended)

```bash
./scripts/start.sh              # DEMO: mock data + Mailpit email demo
./scripts/start.sh --real       # REAL: broker + backend; P06 expected on :8088
./scripts/start.sh --full       # REAL + local P06 stack (InfluxDB, logger, query API, aggregator)
./scripts/start.sh --no-email   # any mode without Mailpit/email
```

Windows: `.\scripts\start.ps1` with the same modes as switches (`-Real`, `-Full`, `-NoEmail`).

Starts backend (`:8000`), frontend (`:5173`), and Mailpit (`:8025`); `--real`/`--full` add the Mosquitto broker (`:1883`) and, for `--full`, the monorepo's P06 pipeline (`:8086`/`:8088`). Skips anything already running; Ctrl+C stops everything it started. Note: `--full` provides the pipeline — actual sensor *data* still needs the other groups' publishers (run `uv run mprocs` in the monorepo for a full simulation).

The manual equivalents:

### Demo mode (no broker / P06 / schema needed — the reliable path)

```bash
cd backend
uv sync
MOCK_DATA=true uv run uvicorn app.main:app --reload   # http://localhost:8000

cd frontend
npm install
npm run dev                                           # http://localhost:5173
```

Demo alert story: starts healthy → one warning (~40 s) → one critical (~2 min, emailed if email is enabled). Manual watering updates moisture, tank, and the chart markers optimistically.

### Real mode

```bash
cd backend
cp .env.example .env       # set ADMIN_EMAIL / ADMIN_PASSWORD / JWT_SECRET; see the env knobs inside
uv sync                    # installs deps + editable cps-schema from ../monorepo
uv run uvicorn app.main:app --reload
```

Requires P06's query API running (`P06_API_URL`) for data and an MQTT broker (`MQTT_HOST` / `MQTT_PORT`) for the watering command. Everything degrades gracefully when a dependency is down.

### Email notifications (stretch, demo via Mailpit)

```bash
docker run --rm -d -p 1025:1025 -p 8025:8025 axllent/mailpit
# set EMAIL_ENABLED=true, then open http://localhost:8025
```

### Test login

- `viewer@example.com / viewer123` — read-only
- `operator@example.com / operator123` — can trigger watering + edit profiles
- Admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env` (seeded users need `SEED_DEV_USERS=true`)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/jwt/login` | Form-encoded login → JWT |
| POST | `/api/auth/register` | Self-service signup (creates viewer) |
| GET | `/api/users/me` | Current user (incl. role) |
| GET | `/api/sensors/latest` | All sensor data (soil, controller, weather, tank, power) |
| GET | `/api/sensors/history` | Historical data (`sensor`, `hours`, downsampled) |
| GET | `/api/system/status` | High-level health + plant-health headline |
| GET | `/api/alerts/active` · `/api/alerts/recent` | Anomaly alerts (P08 shape) |
| GET | `/api/components/health` | Per-group liveness strip |
| GET | `/api/watering/history` | Past watering events (chart markers) |
| GET/PATCH | `/api/config/watering` | Plant watering profiles (PATCH: operator) |
| POST | `/api/commands/water` | Manual watering (operator + confirmation; start/stop) |
| POST | `/api/commands/auto-watering` | Enable/disable P05 automatic watering (operator) |

## Deployment

Runs on the Raspberry Pi inside the local WiFi, alongside the broker and P06. A single FastAPI process serves both the API and the built frontend (monorepo package, port 8000 via mprocs). Phones on the same WiFi use `http://<pi-ip>:8000`. No public hosting.

## Tracking

Work items live as GitHub issues: <https://github.com/gecko1112/CPS_WebApp/issues>

## Changes from initial scaffold

- **2026-05-07** — Pinned `vue3-apexcharts` in [frontend/package.json](frontend/package.json) from `^1.5.3` to `~1.5.3`. The floating caret was resolving to `1.11.x`, which now requires `apexcharts >= 5.10`, breaking install against the pinned `apexcharts ^3.54`. Tilde keeps it on the 1.5.x line.
- **2026-06-11** — Backend rewritten to use **uv** (not pip), **SQLite + SQLAlchemy** user database, and **fastapi-users** for auth (email-based login, JWT, automatic registration endpoint). **fastapi-mail** added for upcoming notification work. Hosting decision: Pi-only LAN, no public hosting.
- **2026-07-08** — README rewritten to match the shipped state (it still described the June scaffold): real data wiring (P06 HTTP reads + Sparkplug B MQTT watering command), demo mode, view modes, plant profiles, watering history + chart markers, email notifications (incl. critical-alert mails), component health, system SVG, monorepo export pipeline, updated endpoint table.
