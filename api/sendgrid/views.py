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
