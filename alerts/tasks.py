"""
alerts/tasks.py

Celery tasks for dispatching financing-related alerts.

Design notes
------------
- Tasks are deliberately thin: they resolve settings, call a service
  function, and record the outcome. Business logic lives in `services.py`.
- `bind=True` gives the task access to `self` for retry tracking.
- `max_retries=3` with exponential back-off handles transient gateway errors
  without hammering the SMS provider.
- All outcomes (success and failure) are persisted to `AlertAttempt` so that
  engineers and auditors can query the history without reading Celery logs.
"""

import logging
from celery import shared_task
from django.conf import settings

from .models import AlertAttempt
from .services import send_log_alert, send_sms_alert

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_financing_alert(
    self,
    financing_request_id: str,
    event: str,
    merchant_phone: str,
    new_status: str = "",
):
    """
    Queue an alert when a financing request is created or its status changes.

    Parameters
    ----------
    financing_request_id : str
        UUID string of the FinancingRequest that triggered the alert.
    event : str
        Short event label, e.g. "created" or "status_updated".
    merchant_phone : str
        Recipient phone number (E.164 preferred, e.g. +254712345678).
    new_status : str
        The new status value if this is a status_updated event.

    Non-blocking guarantee
    ----------------------
    This task is called with `.delay()` from the view layer, which enqueues
    the job without waiting for the result. The HTTP response is returned to
    the client immediately. The Celery worker picks up and executes the task
    asynchronously.
    """
    channel = getattr(settings, "ALERT_CHANNEL", "log")
    attempt = AlertAttempt.objects.create(
        financing_request_id=financing_request_id,
        event=event,
        new_status=new_status,
        channel=channel,
        recipient=merchant_phone,
        result=AlertAttempt.Result.PENDING,
    )

    try:
        if channel == "sms":
            send_sms_alert(
                phone=merchant_phone,
                event=event,
                financing_request_id=financing_request_id,
                new_status=new_status,
            )
        else:
            # Default: log channel — safe for development and testing
            send_log_alert(
                phone=merchant_phone,
                event=event,
                financing_request_id=financing_request_id,
                new_status=new_status,
            )

        attempt.result = AlertAttempt.Result.SUCCESS
        attempt.save(update_fields=["result"])
        logger.info(
            "Alert dispatched",
            extra={
                "attempt_id": str(attempt.id),
                "event": event,
                "channel": channel,
                "recipient": merchant_phone,
            },
        )

    except Exception as exc:
        attempt.result = AlertAttempt.Result.FAILURE
        attempt.error_detail = str(exc)
        attempt.save(update_fields=["result", "error_detail"])

        logger.error(
            "Alert dispatch failed — scheduling retry",
            extra={
                "attempt_id": str(attempt.id),
                "event": event,
                "error": str(exc),
                "retries": self.request.retries,
            },
        )

        # Exponential back-off: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))