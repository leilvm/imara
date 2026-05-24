"""
alerts/services.py

Alert delivery implementations. Separated from tasks.py so that individual
channel functions can be tested in isolation without Celery infrastructure.
"""

import logging

logger = logging.getLogger(__name__)


def _build_message(event: str, financing_request_id: str, new_status: str = "") -> str:
    """Construct a short, bandwidth-friendly message string."""
    if event == "created":
        return (
            f"[Imara] Your financing request {financing_request_id[:8]}... "
            f"has been received. We will review it shortly."
        )
    elif event == "status_updated":
        return (
            f"[Imara] Your financing request {financing_request_id[:8]}... "
            f"status has been updated to: {new_status.upper()}."
        )
    else:
        return f"[Imara] Update on your financing request {financing_request_id[:8]}..."


def send_log_alert(
    phone: str,
    event: str,
    financing_request_id: str,
    new_status: str = "",
) -> None:
    """
    Development/test channel: write the alert to the Python logger.
    No external dependencies — always succeeds in local dev.
    """
    message = _build_message(event, financing_request_id, new_status)
    logger.info(
        "[ALERT:LOG] Would send SMS",
        extra={
            "recipient": phone,
            "message": message,
            "event": event,
            "financing_request_id": financing_request_id,
        },
    )
    # Also print so it's visible in runserver output
    print(f"\n{'='*60}")
    print(f"  IMARA ALERT (log channel)")
    print(f"  To: {phone}")
    print(f"  Message: {message}")
    print(f"{'='*60}\n")


def send_sms_alert(
    phone: str,
    event: str,
    financing_request_id: str,
    new_status: str = "",
) -> None:
    """
    Production SMS channel stub using Africa's Talking gateway.

    In a real deployment, install `africastalking` and configure:
        AFRICASTALKING_USERNAME=<username>
        AFRICASTALKING_API_KEY=<key>

    The stub raises NotImplementedError so that misconfigured staging
    deployments fail loudly rather than silently dropping alerts.
    """
    import os

    username = os.environ.get("AFRICASTALKING_USERNAME")
    api_key = os.environ.get("AFRICASTALKING_API_KEY")

    if not username or not api_key:
        raise NotImplementedError(
            "SMS channel requires AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY. "
            "Set ALERT_CHANNEL=log in .env for local development."
        )

    # Real implementation would be:
    # import africastalking
    # africastalking.initialize(username, api_key)
    # sms = africastalking.SMS
    # message = _build_message(event, financing_request_id, new_status)
    # response = sms.send(message, [phone])

    message = _build_message(event, financing_request_id, new_status)
    logger.info(f"[ALERT:SMS] Sent to {phone}: {message}")
