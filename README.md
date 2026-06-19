# Plant CPS Web App

A phone-friendly dashboard for the P13 autonomous balcony plant watering CPS (TU Berlin, CPS SoSe 2026). Displays system status, sensor data, anomaly alerts, and weather forecasts in non-expert language. Supports manual watering with a confirmation step.

## What this includes

- **`frontend/`** — Vue 3 + Vite + Tailwind + PrimeVue + ApexCharts + vue-router. Dark glassmorphism theme (green/white/black). Pages: Welcome (video bg), Dashboard, Settings, Login.
- **`backend/`** — FastAPI + **fastapi-users** (auth) + **fastapi-mail** (notifications, planned). SQLite user database, JWT auth, fake sensor + alert generators matching Sparkplug B payload shapes.

## What this does NOT include yet

- Real MQTT integration — fake generators stand in for now; swap for `aiomqtt` + monorepo `schema` package later
- Real Postgres — SQLite is used today; change `DATABASE_URL` env var when ready
- Two view modes (simple/advanced)
- Admin user-management UI (endpoints exist via fastapi-users; the page is open as issue #5)
- Notification dispatch (Mailpit + browser toast — issue #15)
- Signed/encrypted manual watering commands (issue #16)

## Quick start

### Backend

The backend uses **uv** (not pip) to match the course monorepo.

```bash
# Install uv once if you don't have it:
curl -LsSf https://astral.sh/uv/install.sh | sh

cd backend
cp .env.example .env       # then edit .env to set ADMIN_EMAIL/ADMIN_PASSWORD and JWT_SECRET
uv sync                    # installs all Python deps into backend/.venv
uv run uvicorn app.main:app --reload
```

Backend runs on http://localhost:8000 — Swagger UI at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on http://localhost:5173

### Test login

Email-based login (fastapi-users). Default seeded accounts on first run:

- `viewer@example.com / viewer123` — read-only
- `operator@example.com / operator123` — can trigger watering
- Admin account from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/login` | Login | Dark themed with glassmorphism card |
| `/` | Welcome | Landing page with 4K video background, at-a-glance status cards, CTAs |
| `/dashboard` | Dashboard | Full sensor data, alerts panel, live charts, manual watering |
| `/settings` | Settings | Choose preferred landing page after login |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/jwt/login` | Form-encoded login → JWT |
| POST | `/api/auth/register` | Self-service signup (creates viewer) |
| GET | `/api/users/me` | Current user (incl. role) |
| GET | `/api/sensors/latest` | All sensor data (soil, controller, weather, tank, power) |
| GET | `/api/sensors/history` | Historical data for a sensor |
| GET | `/api/system/status` | High-level system health |
| GET | `/api/alerts/active` | Currently firing anomaly alerts |
| GET | `/api/alerts/recent` | Last N alerts with timestamps |
| POST | `/api/commands/water` | Manual watering (operator+, requires confirmation) |

## Deployment

The web app is intended to run on the Raspberry Pi inside the local WiFi network, alongside P04's Mosquitto broker. Phones and laptops on the same WiFi access the dashboard at the Pi's local IP (e.g. `http://192.168.x.x:8000`). No public internet hosting — see issue #13.

## Tracking

Work items live as GitHub issues: <https://github.com/gecko1112/CPS_WebApp/issues>

## Changes from initial scaffold

- **2026-05-07** — Pinned `vue3-apexcharts` in [frontend/package.json](frontend/package.json) from `^1.5.3` to `~1.5.3`. The floating caret was resolving to `1.11.x`, which now requires `apexcharts >= 5.10`, breaking install against the pinned `apexcharts ^3.54`. Tilde keeps it on the 1.5.x line.
- **2026-06-11** — Backend rewritten to use **uv** (not pip), **SQLite + SQLAlchemy** user database, and **fastapi-users** for auth (email-based login, JWT, automatic registration endpoint). **fastapi-mail** added for upcoming notification work. Hosting decision: Pi-only LAN, no public hosting.
