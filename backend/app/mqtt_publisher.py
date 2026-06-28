"""
WateringPublisher — the one MQTT write path: manual watering commands to P05.

Reads go through P06's HTTP query API (see p06_client.py); MQTT is used ONLY to
publish the safety-critical manual-watering command. P13 acts as a minimal
Sparkplug B node: it registers an NDEATH as its LWT, publishes an NBIRTH on
connect, and stamps every command with a wrapping sequence number.

The command is a DCMD to P05's controller device, encoded with the shared
``cps-schema`` Sparkplug codec. Topic/model come from ``schema.p05`` — never
hardcoded.

Uses paho-mqtt (the convention across the monorepo's publishers). The client
runs its own network thread (``loop_start``); ``publish_watering`` is called
from the FastAPI request thread and is safe to do so.

SECURITY: this is the security-critical path. For production it needs TLS to the
broker (from P04/P09) and an application-level signature (HMAC) on the payload
so P05 can authenticate the sender — see issue #16. Marked TODO below.
"""

from __future__ import annotations

import logging
import os

import paho.mqtt.client as mqtt
import schema.p13 as p13
from schema import codec
from schema.core import (
    BirthDeathCounter,
    DataType,
    Metric,
    SequenceCounter,
    SparkplugPayload,
    death_payload,
)
from schema.p05 import (
    ManualTriggerCommandTopic,
    ManualWateringAction,
    ManualWateringTrigger,
)

log = logging.getLogger("p13.mqtt")

BROKER = os.getenv("MQTT_HOST") or os.getenv("MQTT_BROKER") or "localhost"
PORT = int(os.getenv("MQTT_PORT", "1883"))
KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "p13-app-main")
ENABLED = os.getenv("MQTT_ENABLED", "true").lower() in ("1", "true", "yes", "on")
PUBLISH_TIMEOUT_S = float(os.getenv("MQTT_PUBLISH_TIMEOUT_S", "5"))


def _build_nbirth(seq: SequenceCounter, bd_seq: BirthDeathCounter) -> SparkplugPayload:
    """Minimal NBIRTH for a node with no domain metrics: reset seq to 0 and
    carry the bdSeq that pairs with the NDEATH LWT."""
    seq.reset()
    return SparkplugPayload(
        seq=seq.next(),
        metrics=[Metric(name="bdSeq", datatype=DataType.INT64, value=bd_seq.current)],
    )


class WateringPublisher:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._seq = SequenceCounter()
        self._bd_seq = BirthDeathCounter()
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        if not ENABLED:
            log.info("MQTT publisher disabled (MQTT_ENABLED=false)")
            return
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        # Register the LWT (NDEATH) before connecting so the broker publishes it
        # on an unexpected drop.
        client.will_set(
            p13.DeathTopic.address,
            codec.encode(death_payload(self._bd_seq)),
            qos=p13.DeathTopic.qos,
            retain=p13.DeathTopic.retain,
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
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.warning("MQTT shutdown error: %s", exc)

    # -- callbacks (run on paho's network thread) ---------------------------

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code == 0:
            self._connected = True
            client.publish(
                p13.BirthTopic.address,
                codec.encode(_build_nbirth(self._seq, self._bd_seq)),
                qos=p13.BirthTopic.qos,
                retain=p13.BirthTopic.retain,
            )
            log.info("MQTT connected to %s:%s; NBIRTH published", BROKER, PORT)
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
        # TODO(security): HMAC-sign this payload and run the broker link over TLS
        # before production. Manual watering is safety-critical (issue #16).
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
