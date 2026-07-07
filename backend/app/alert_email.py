"""
Email notifications for critical anomaly alerts (stretch goal).

Completes the notification story: the user gets told when something critical
happens *without watching the page*. Both sensor services (real + mock) call
``notify_critical_alerts`` with their current alerts; new criticals are emailed
via ``email_util`` (Mailpit in the demo).

Best-effort by design: everything is a no-op when EMAIL_ENABLED is false, and a
per-component cooldown stops a persistent fault from flooding the inbox.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time

from .email_util import EMAIL_ENABLED, send_email

log = logging.getLogger("p13.alert_email")

# Minimum minutes between mails for the SAME component (repeat criticals from
# one fault collapse into a single mail per window).
ALERT_EMAIL_COOLDOWN_MIN = float(os.getenv("ALERT_EMAIL_COOLDOWN_MIN", "15"))

# component -> monotonic time of the last mail we sent for it.
_last_sent: dict[str, float] = {}


def notify_critical_alerts(alerts: list[dict]) -> int:
    """Fire-and-forget an email for each newly seen critical alert.

    Must be called from a running event loop (both sensor services call it
    from their async poll/generate loops). Returns how many mails were queued.
    """
    if not EMAIL_ENABLED:
        return 0
    now = time.monotonic()
    queued = 0
    for alert in alerts:
        if alert.get("severity") != "critical":
            continue
        component = alert.get("component", "unknown")
        last = _last_sent.get(component)
        if last is not None and now - last < ALERT_EMAIL_COOLDOWN_MIN * 60:
            continue
        _last_sent[component] = now
        subject = f"🚨 Plant CPS — critical alert: {component}"
        body = (
            f"A critical alert is active on your plant watering system.\n\n"
            f"Component:   {component}\n"
            f"Type:        {alert.get('alert_type', 'unknown')}\n"
            f"Observed:    {alert.get('observed_value', '—')}\n"
            f"When:        {alert.get('timestamp', '—')}\n\n"
            f"{alert.get('description', '')}\n\n"
            f"Open the dashboard for details and recent history."
        )
        asyncio.create_task(send_email(subject, body))
        queued += 1
    return queued
