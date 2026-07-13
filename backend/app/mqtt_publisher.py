"""
WateringPublisher — the one MQTT write path: manual watering commands to P05.

Reads go through P06's HTTP query API (see p06_client.py); MQTT is used ONLY to
publish the safety-critical manual-watering command. P13 acts as a minimal
Sparkplug B node: it registers an NINFO last-will, publishes NINFO online on
connect, and stamps every command with a wrapping sequence number.

The command is a DCMD to P05's controller device, encoded with the shared
``cps-schema`` Sparkplug codec. Topic/model come from ``schema.p05`` — never
hardcoded.

Uses paho-mqtt (the convention across the monorepo's publishers). The client
runs its own network thread (``loop_start``); ``publish_watering`` is called
from the FastAPI request thread and is safe to do so.

SECURITY (issue #16, per P09): the broker secures this path — MQTT over TLS +
our per-component P13 credentials + a broker ACL that only lets P13 publish to
the watering topic. Username/password come from P13's own auth.env (see
scripts/setup-workspace.sh, which bootstraps it) via
schema.mqtt.create_client(); TLS is configured via env (MQTT_TLS*), off by
default so the local/demo broker works; fill in with P09's values. P09's
model uses no app-layer payload signing.
"""

from __future__ import annotations

import logging
import os

import paho.mqtt.client as mqtt
from schema.core import SequenceCounter
from schema.p05 import (
    ManualTriggerCommandTopic,
    ManualWateringAction,
    ManualWateringTrigger,
)
from schema.p13 import InfoTopic
from schema.utils import package_root

from schema import codec
from schema import mqtt as schema_mqtt

log = logging.getLogger("p13.mqtt")

BROKER = os.getenv("MQTT_HOST") or os.getenv("MQTT_BROKER") or "localhost"
PORT = int(os.getenv("MQTT_PORT", "1883"))
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "p13-app-main")
ENABLED = os.getenv("MQTT_ENABLED", "true").lower() in ("1", "true", "yes", "on")
PUBLISH_TIMEOUT_S = float(os.getenv("MQTT_PUBLISH_TIMEOUT_S", "5"))
AUTH_ENV = package_root(__file__) / "auth.env"

# --- Broker security (issue #16, per P09) ----------------------------------
# P09's model is broker-centric: MQTT over TLS + per-component credentials +
# per-component ACLs (the broker enforces that only P13 may publish to the
# watering DCMD topic). Username/password come from AUTH_ENV via
# create_client(); all off by default (no password set) so the local/demo
# broker still works.
USE_TLS = os.getenv("MQTT_TLS", "false").lower() in ("1", "true", "yes", "on")
TLS_CA = os.getenv("MQTT_TLS_CA") or None  # CA cert to trust (from P09)
TLS_CERT = os.getenv("MQTT_TLS_CERT") or None  # client cert (only if mTLS)
TLS_KEY = os.getenv("MQTT_TLS_KEY") or None
TLS_INSECURE = os.getenv("MQTT_TLS_INSECURE", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)  # skip server-hostname verification — testing only


class WateringPublisher:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._seq = SequenceCounter()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        if not ENABLED:
            log.info("MQTT publisher disabled (MQTT_ENABLED=false)")
            return
        client = schema_mqtt.create_client(
            "p13", auth_env=AUTH_ENV, client_id=CLIENT_ID
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect

        # MQTT over TLS (P09's secured broker). tls_set() with ca_certs=None uses
        # the system trust store; pass P09's CA via MQTT_TLS_CA. certfile/keyfile
        # enable mTLS if P09 requires client certificates.
        if USE_TLS:
            try:
                client.tls_set(ca_certs=TLS_CA, certfile=TLS_CERT, keyfile=TLS_KEY)
                if TLS_INSECURE:
                    client.tls_insecure_set(True)
                log.info("MQTT TLS enabled (ca=%s, mtls=%s)", TLS_CA, bool(TLS_CERT))
            except Exception as exc:  # noqa: BLE001 — degrade gracefully
                log.error("MQTT TLS setup failed: %s", exc)

        # Register the LWT on NINFO before connecting so the broker publishes it
        # on an unexpected drop.
        client.will_set(
            InfoTopic.address,
            codec.encode(InfoTopic.model.will().to_data(self._seq)),
            qos=InfoTopic.qos,
            retain=InfoTopic.retain,
        )
        # connect_async + loop_start: non-blocking, auto-retries, so app startup
        # never blocks or crashes when the broker is down.
        try:
            client.connect_async(BROKER, PORT, keepalive=KEEPALIVE)
            client.loop_start()
            log.info("MQTT publisher connecting to %s:%s", BROKER, PORT)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            log.warning("MQTT connect_async failed: %s", exc)
        self._client = client

    def stop(self) -> None:
        if self._client is None:
            return
        try:
            if self._connected:
                self._client.publish(
                    InfoTopic.address,
                    codec.encode(InfoTopic.model.death().to_data(self._seq)),
                    qos=InfoTopic.qos,
                    retain=InfoTopic.retain,
                )
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.warning("MQTT shutdown error: %s", exc)

    # -- callbacks (run on paho's network thread) ---------------------------

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code == 0:
            self._connected = True
            client.publish(
                InfoTopic.address,
                codec.encode(InfoTopic.model.birth().to_data(self._seq)),
                qos=InfoTopic.qos,
                retain=InfoTopic.retain,
            )
            log.info("MQTT connected to %s:%s; NINFO birth published", BROKER, PORT)
        else:
            self._connected = False
            log.warning("MQTT connection refused: %s", reason_code)

    def _on_disconnect(
        self, _client, _userdata, _flags, reason_code, _properties
    ) -> None:
        self._connected = False
        log.warning("MQTT disconnected: %s", reason_code)

    # -- publish ------------------------------------------------------------

    def publish_watering(self, action: str, duration_s: int | None) -> dict:
        """Publish a manual watering command (DCMD) to P05. Raises RuntimeError
        when the broker is not connected or the publish is not acknowledged."""
        if self._client is None or not self._connected:
            raise RuntimeError("not connected to the MQTT broker")

        trigger = ManualWateringTrigger(
            action=ManualWateringAction(action), duration_s=duration_s
        )
        seq_used = self._seq.current
        # Security (per P09): authentication + integrity come from the broker —
        # TLS + our P13 credentials + an ACL that only lets P13 publish here (all
        # configured in start()). No app-layer payload signing in P09's model.
        payload = codec.encode(trigger.to_data(self._seq))
        info = self._client.publish(
            ManualTriggerCommandTopic.address,
            payload,
            qos=ManualTriggerCommandTopic.qos,
            retain=ManualTriggerCommandTopic.retain,
        )
        info.wait_for_publish(timeout=PUBLISH_TIMEOUT_S)
        if not info.is_published():
            raise RuntimeError("publish timed out — broker did not acknowledge")
        log.info(
            "manual watering published: action=%s duration_s=%s seq=%s",
            action,
            duration_s,
            seq_used,
        )
        return {"topic": ManualTriggerCommandTopic.address, "seq": seq_used}


watering_publisher = WateringPublisher()
