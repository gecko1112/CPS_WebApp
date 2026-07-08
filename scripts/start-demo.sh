#!/usr/bin/env bash
# scripts/start-demo.sh — start the whole P13 stack with one command.
#
#   ./scripts/start-demo.sh              # DEMO: mock data + Mailpit email demo
#   ./scripts/start-demo.sh --real       # REAL: broker + our backend; P06 runs elsewhere
#   ./scripts/start-demo.sh --full       # REAL + local P06 stack (InfluxDB, logger,
#                                        #   query API, aggregator) from ../monorepo
#   ./scripts/start-demo.sh --no-email   # any mode without Mailpit/email
#
# Always starts (foreground, Ctrl+C stops everything):
#   * backend  — uvicorn on :8000  (MOCK_DATA=true in demo mode)
#   * frontend — Vite dev server on :5173
#   * Mailpit (docker) unless already running / --no-email
# --real adds:  Mosquitto broker :1883 (docker, if not running)
# --full adds:  InfluxDB :8086 (docker compose) + P06 logger/api/aggregator (uv)
#
# NOTE (--full): P06 logs whatever is published on the bus — actual sensor DATA
# still needs the other groups' publishers (run them via mprocs in ../monorepo).
# For the Pi/monorepo single-process deployment use mprocs there instead.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONOREPO="${MONOREPO:-$REPO_ROOT/../monorepo}"
MODE=demo
EMAIL=true

for arg in "$@"; do
  case "$arg" in
    --real) MODE=real ;;
    --full) MODE=full ;;
    --no-email) EMAIL=false ;;
    *) echo "unknown argument: $arg (use --real | --full | --no-email)" >&2; exit 1 ;;
  esac
done

PIDS=()
cleanup() {
  echo ""
  echo "==> Stopping ..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

port_up() { nc -z localhost "$1" 2>/dev/null; }

# --- Mailpit (email demo) ----------------------------------------------------
if $EMAIL; then
  if port_up 8025; then
    echo "==> Mailpit already running (http://localhost:8025)"
  elif command -v docker >/dev/null; then
    echo "==> Starting Mailpit ..."
    docker run --rm -d --name p13-mailpit -p 1025:1025 -p 8025:8025 axllent/mailpit >/dev/null \
      || echo "    (couldn't start Mailpit — email demo disabled)"
  else
    echo "==> docker not found — skipping Mailpit (email demo disabled)"
  fi
fi

# --- Broker (real/full) ------------------------------------------------------
if [ "$MODE" != demo ]; then
  if port_up 1883; then
    echo "==> MQTT broker already running (:1883)"
  else
    echo "==> Starting Mosquitto broker ..."
    docker run --rm -d --name cps-mqtt -p 1883:1883 \
      -v "$MONOREPO/docker/mosquitto.conf":/mosquitto/config/mosquitto.conf \
      eclipse-mosquitto:2 >/dev/null || echo "    (broker start failed — watering will 503)"
  fi
fi

# --- Local P06 stack (full only) ----------------------------------------------
if [ "$MODE" = full ]; then
  if [ ! -d "$MONOREPO" ]; then
    echo "ERROR: monorepo not found at $MONOREPO (set MONOREPO=/path)"; exit 1
  fi
  P06_ENV=(INFLUX_URL=http://localhost:8086 INFLUX_ORG="${INFLUX_ORG:-cps}"
           INFLUX_BUCKET="${INFLUX_BUCKET:-cps_raw}"
           INFLUX_TOKEN="${INFLUX_TOKEN:-dev-token-change-me}")

  if port_up 8086; then
    echo "==> InfluxDB already running (:8086)"
  else
    echo "==> Starting InfluxDB (docker compose, monorepo) ..."
    (cd "$MONOREPO" && docker compose up -d influxdb >/dev/null)
  fi
  until port_up 8086; do sleep 1; done

  echo "==> Starting P06 logger + query API + aggregator ..."
  (cd "$MONOREPO" && env "${P06_ENV[@]}" MQTT_BROKER=localhost \
     uv run --package p06_data_logging_visualisation p06-logger) & PIDS+=($!)
  (cd "$MONOREPO" && env "${P06_ENV[@]}" API_HOST=0.0.0.0 API_PORT=8088 \
     uv run --package p06_data_logging_visualisation p06-api) & PIDS+=($!)
  (cd "$MONOREPO" && env "${P06_ENV[@]}" \
     uv run --package p06_data_logging_visualisation p06-aggregator) & PIDS+=($!)
fi

if [ "$MODE" = real ]; then
  echo "    NOTE: expecting P06's query API on :8088 (start it separately, or use --full)."
fi

# --- Backend -------------------------------------------------------------------
echo "==> Starting backend (:8000, mode: $MODE) ..."
BACKEND_ENV=()
[ "$MODE" = demo ] && BACKEND_ENV+=("MOCK_DATA=true")
$EMAIL && BACKEND_ENV+=("EMAIL_ENABLED=true")
(
  cd "$REPO_ROOT/backend"
  env "${BACKEND_ENV[@]}" uv run uvicorn app.main:app --reload
) &
PIDS+=($!)

# --- Frontend ------------------------------------------------------------------
echo "==> Starting frontend (:5173) ..."
(
  cd "$REPO_ROOT/frontend"
  npm run dev
) &
PIDS+=($!)

sleep 3
echo ""
echo "────────────────────────────────────────────────────────"
echo "  App:      http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
$EMAIL && echo "  Mailpit:  http://localhost:8025"
[ "$MODE" = full ] && echo "  P06 API:  http://localhost:8088/health"
echo ""
echo "  Logins:   operator@example.com / operator123"
echo "            viewer@example.com   / viewer123"
if [ "$MODE" = demo ]; then
  echo ""
  echo "  Demo story: healthy → 1 warning (~40s) → 1 critical (~2min, emailed)"
else
  echo ""
  echo "  Real mode: dashboard fills as groups publish on the bus."
fi
echo ""
echo "  Ctrl+C stops everything."
echo "────────────────────────────────────────────────────────"

wait
