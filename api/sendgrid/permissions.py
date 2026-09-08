from rest_framework import permissions
from rest_framework import exceptions
from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader

from framework import sentry
from website import settings


class RequestComesFromSendGrid(permissions.BasePermission):
    """Verify that the request comes from SendGrid via signed Event Webhook.

    Uses ECDSA signature verification against the raw request body as documented at:
    https://www.twilio.com/docs/sendgrid/for-developers/tracking-events/getting-started-event-webhook-security-features
    """

    def has_permission(self, request, view):
        if request.method != 'POST':
            raise exceptions.MethodNotAllowed(method=request.method)

        public_key = settings.SENDGRID_EVENT_WEBHOOK_PUBLIC_KEY
        if not public_key:
            sentry.log_message('SendGrid Event Webhook public key is not configured')
            return False

        signature = request.headers.get(EventWebhookHeader.SIGNATURE)
        timestamp = request.headers.get(EventWebhookHeader.TIMESTAMP)
        if not signature or not timestamp:
            error_message = 'SendGrid Event Webhook signature headers required'
            sentry.log_message(error_message)
            raise exceptions.ParseError(error_message)

        # Must verify the raw body; re-serializing parsed JSON breaks the signature.
        payload = request.body.decode('utf-8')
        event_webhook = EventWebhook(public_key)
        if not event_webhook.verify_signature(payload, signature, timestamp):
            raise exceptions.ParseError('Invalid SendGrid Event Webhook signature')

        return True
