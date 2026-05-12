# Plant CPS Test Version

A minimal working prototype of the P13 web app, with **fake sensor data** so you can develop the frontend before the MQTT/sensor groups are ready.

## What this includes

- **`frontend/`** - Vue 3 + Vite + Tailwind + PrimeVue + ApexCharts, single dashboard page
- **`backend/`** - FastAPI with fake sensor generator, REST endpoints, basic JWT auth

## What this does NOT include yet

- Real MQTT integration (replaced with fake data generator - a `FakeSensorService` you swap out later)
- Real Postgres (uses in-memory storage for the prototype)
- Two view modes (simple/advanced) - only one view, add this once the basics work
- Persistent users - there's a single hardcoded test user

The goal of this version: get something running on your laptop in 10 minutes so you can see the pieces fit together. Replace fake bits one at a time.

## Quick start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Backend runs on http://localhost:8000 - visit http://localhost:8000/docs for the auto-generated Swagger UI.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on http://localhost:5173

### Test login
- Username: `viewer` / Password: `viewer123` → read-only role
- Username: `operator` / Password: `operator123` → can trigger watering

## Changes from initial scaffold

- **2026-05-07** — Pinned `vue3-apexcharts` in [frontend/package.json](frontend/package.json) from `^1.5.3` to `~1.5.3`. The floating caret was resolving to `1.11.x`, which now requires `apexcharts >= 5.10`, breaking install against the pinned `apexcharts ^3.54`. Tilde keeps it on the 1.5.x line.

## Next steps (in this order)
1. Get this running locally and click around
2. Replace `FakeSensorService` with a real `aiomqtt` subscriber once topic schema is agreed
3. Replace in-memory storage with Postgres + SQLAlchemy
4. Add the simple/advanced view toggle
5. Add proper user registration + DB-backed accounts
6. Add anomaly alerts panel (consume from anomaly detector group)
7. Polish UI, add infographics, deploy to Pi
