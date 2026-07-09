#!/usr/bin/env bash
# scripts/start.sh — start the whole P13 stack with one command.
#
#   ./scripts/start.sh              # DEMO: mock data + Mailpit email demo
#   ./scripts/start.sh --real       # REAL: broker + our backend; P06 runs elsewhere
#   ./scripts/start.sh --full       # REAL + local P06 stack (InfluxDB, logger,
#                                   #   query API, aggregator) from ../monorepo
#   ./scripts/start.sh --no-email   # any mode without Mailpit/email
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
#
# Division of responsibility: on the Pi, P06 runs InfluxDB + logger/API
# themselves — use --real there. --full exists so ONE person on ONE laptop can
# run the entire real pipeline without P06 around (we temporarily "play P06").

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
# Each service runs in its OWN process group (setsid), so cleanup can kill the
# whole tree (uv -> uvicorn -> reload worker, npm -> sh -> node). Killing just
# the top pid orphans the grandchildren, which then keep ports 8000/5173 and
# serve STALE data on the next start.
cleanup() {
  echo ""
  echo "==> Stopping ..."
  for pid in "${PIDS[@]}"; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  sleep 1
  for pid in "${PIDS[@]}"; do kill -KILL -- "-$pid" 2>/dev/null || true; done
  # Fallback: pattern-kill anything that escaped its process group (uv/npm
  # re-spawn children); a survivor here keeps :8000/:5173 and serves stale data.
  pkill -f 'uvicorn app.main' 2>/dev/null || true
  pkill -f 'vite --host' 2>/dev/null || true
  pkill -f 'p06_data_logging_visualisation' 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

port_up() { nc -z localhost "$1" 2>/dev/null; }

# Refuse to start over a stale instance — otherwise the new backend can't bind
# and the browser keeps talking to the OLD one (frozen alerts, old code).
for p in 8000 5173; do
  if port_up "$p"; then
    echo "ERROR: port $p is already in use — a previous run is still alive." >&2
    echo "       Stop it first:  pkill -f 'uvicorn app.main' ; pkill -f vite" >&2
    exit 1
  fi
done

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
    echo "==> Starting InfluxDB ..."
    if docker compose version >/dev/null 2>&1; then
      (cd "$MONOREPO" && docker compose up -d influxdb >/dev/null)
    elif command -v docker-compose >/dev/null; then
      (cd "$MONOREPO" && docker-compose up -d influxdb >/dev/null)
    else
      # No compose installed — replicate the monorepo's influxdb service.
      # Named volumes keep the data across restarts, same as compose.
      docker run -d --name cps-influxdb -p 8086:8086 \
        -e DOCKER_INFLUXDB_INIT_MODE=setup \
        -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
        -e DOCKER_INFLUXDB_INIT_PASSWORD=changeme123 \
        -e DOCKER_INFLUXDB_INIT_ORG="${INFLUX_ORG:-cps}" \
        -e DOCKER_INFLUXDB_INIT_BUCKET="${INFLUX_BUCKET:-cps_raw}" \
        -e DOCKER_INFLUXDB_INIT_RETENTION=7d \
        -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN="${INFLUX_TOKEN:-dev-token-change-me}" \
        -v cps_influxdb_data:/var/lib/influxdb2 \
        -v cps_influxdb_config:/etc/influxdb2 \
        influxdb:2.7 >/dev/null \
        || docker start cps-influxdb >/dev/null   # container exists from a previous run
    fi
  fi
  # The port opens before Influx finishes first-run setup — wait for health.
  echo -n "    waiting for InfluxDB to be ready "
  until curl -fsS http://localhost:8086/health >/dev/null 2>&1; do echo -n "."; sleep 1; done
  echo " ok"

  echo "==> Starting P06 logger + query API + aggregator ..."
  (cd "$MONOREPO" && exec setsid env "${P06_ENV[@]}" MQTT_BROKER=localhost \
     uv run --package p06_data_logging_visualisation p06-logger) & PIDS+=($!)
  (cd "$MONOREPO" && exec setsid env "${P06_ENV[@]}" API_HOST=0.0.0.0 API_PORT=8088 \
     uv run --package p06_data_logging_visualisation p06-api) & PIDS+=($!)
  (cd "$MONOREPO" && exec setsid env "${P06_ENV[@]}" \
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
  exec setsid env "${BACKEND_ENV[@]}" uv run uvicorn app.main:app --reload
) &
PIDS+=($!)

# --- Frontend ------------------------------------------------------------------
echo "==> Starting frontend (:5173) ..."
(
  cd "$REPO_ROOT/frontend"
  # --host: reachable from phones on the same WiFi
  exec setsid npm run dev -- --host
) &
PIDS+=($!)

sleep 3
echo ""
echo "────────────────────────────────────────────────────────"
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "  App:      http://localhost:5173"
[ -n "$LAN_IP" ] && echo "  Phone:    http://$LAN_IP:5173  (same WiFi)"
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
