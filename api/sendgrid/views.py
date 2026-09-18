import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView

from api.sendgrid.permissions import RequestComesFromSendGrid
from osf.email.notification_campaign import (
    CAMPAIGN_CUSTOM_ARG_KEYS,
    process_sendgrid_campaign_events,
)

logger = logging.getLogger(__name__)


def _is_campaign_related_event(event):
    """SendGrid flattens personalization ``custom_args`` onto each event object."""
    if not isinstance(event, dict):
        return False
    return all(event.get(key) for key in CAMPAIGN_CUSTOM_ARG_KEYS)


class SendGridEventWebhook(APIView):
    """Receive SendGrid Event Webhook POSTs and enqueue campaign event handling.

    Mounted under the ``_/`` namespace (no user auth). Non-campaign events are
    ignored; campaign-tagged events are processed asynchronously.

    Local testing
    -------------
    Requests must be ECDSA-signed by SendGrid (see ``RequestComesFromSendGrid``),
    so plain ``curl`` posts are rejected unless you forge a valid signature or
    disable the signature check. Use a public tunnel and a real SendGrid Event Webhook
    instead:

    1. Run the API (``localhost:8000``) and a Celery worker (events are enqueued
       to ``email.process_sendgrid_campaign_events``).
    2. Expose the API, e.g. ``ngrok http 8000``. Add ``*.ngrok-free.dev`` in
       ``ALLOWED_HOSTS`` in the settings. See https://ngrok.com/docs/share-localhost/overview
        for more details.
    3. In SendGrid → Mail Settings → Event Webhook:
       - POST URL: ``https://<ngrok-host>/_/sendgrid/events/``
       - Enable Signed Event Webhook; copy the verification key into
         ``SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY`` (``website/settings/local.py``).
       - Subscribe at least to ``delivered``, ``bounce``, and ``dropped``.
    4. Send a notification campaign email (personalization ``custom_args`` must
       include ``campaign_id``, ``campaign_recipient_id``, and ``run_id``).
       SendGrid's "Test Your Integration" payload lacks those keys, so this view
       accepts it with 200 but does not update campaign recipients.
    """

    view_name = 'sendgrid_event_webhook'
    view_category = 'sendgrid'

    authentication_classes = ()
    permission_classes = (
        RequestComesFromSendGrid,
    )

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_serializer_class(self):
        return None

    def post(self, request):
        try:
            events = json.loads(request.body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return HttpResponse('Invalid JSON', status=400)

        if isinstance(events, dict):
            events = [events]
        if not isinstance(events, list):
            return HttpResponse('Expected a JSON array of events', status=400)

        # Process only campaign-related events
        # TODO: add handling for non-campaign events here if required
        campaign_events = [event for event in events if _is_campaign_related_event(event)]

        if campaign_events:
            process_sendgrid_campaign_events.delay(campaign_events)
            logger.info(f'Enqueued {len(campaign_events)} campaign-related SendGrid event(s) of {len(events)} received')

        return HttpResponse('Events received', status=200)
