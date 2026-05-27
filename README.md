# Plant CPS Web App

A phone-friendly dashboard for the P13 autonomous balcony plant watering CPS (TU Berlin, CPS SoSe 2026). Displays system status, sensor data, anomaly alerts, and weather forecasts in non-expert language. Supports manual watering with a confirmation step.

## What this includes

- **`frontend/`** — Vue 3 + Vite + Tailwind + PrimeVue + ApexCharts + vue-router. Dark glassmorphism theme (green/white/black). Pages: Welcome (video bg), Dashboard, Settings, Login.
- **`backend/`** — FastAPI with fake sensor generator matching Sparkplug B payload shapes, REST endpoints, JWT auth, anomaly alert simulation.

## What this does NOT include yet

- Real MQTT integration (replaced with `FakeSensorService` — swap out later with `aiomqtt` + monorepo `schema` package)
- Real Postgres (uses in-memory storage for the prototype)
- Two view modes (simple/advanced)
- Persistent users — hardcoded test accounts only

## Quick start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
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
- `viewer / viewer123` → read-only role
- `operator / operator123` → can trigger watering

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
| POST | `/api/auth/login` | Returns JWT |
| GET | `/api/sensors/latest` | All sensor data (soil, controller, weather, tank, power) |
| GET | `/api/sensors/history` | Historical data for a sensor |
| GET | `/api/system/status` | High-level system health |
| GET | `/api/alerts/active` | Currently firing anomaly alerts |
| GET | `/api/alerts/recent` | Last N alerts with timestamps |
| POST | `/api/commands/water` | Manual watering (operator only, requires confirmation) |

## Next steps
1. Add P07 + P08 subscriptions to monorepo `p13.py` schema file
2. Replace `FakeSensorService` with real `aiomqtt` + Sparkplug B subscriber
3. Replace in-memory storage with Postgres
4. Add simple/advanced view toggle
5. Add proper user registration + DB-backed accounts
6. Deploy to Pi
