"""Basic Event handling for events that need subscriptions"""

from django.utils import timezone

from website.notifications import emails


event_registry = {}


def register(event_type):
    """Register classes into event_registry"""
    def decorator(cls):
        event_registry[event_type] = cls
        return cls
    return decorator


class Event:
    """Base event class for notification.

    - abstract methods set methods that should be defined by subclasses.
    To use this interface you must use the class as a Super (inherited).
     - Implement property methods in subclasses
    """
    def __init__(self, user, node, action):
        self.user = user
        self.profile_image_url = user.profile_image_url()
        self.node = node
        self.action = action
        self.timestamp = timezone.now()

    def perform(self):
        """Call NotificationSubscription.emit to notify users of an action"""
        subscription_qs = self.user.subscriptions.filter(
            notification_type__name=self.event_type
        )
        if not subscription_qs.exists():
            # If the user is not subscribed to this event type, do not send notifications
            return

        subscription = subscription_qs.first()
        context = {}

        context['message'] = self.html_message
        context['profile_image_url'] = self.profile_image_url
        context['localized_timestamp'] = emails.localize_timestamp(self.timestamp, self.user)
        context['user_fullname'] = self.user.fullname
        context['url'] = self.url

        subscription.emit(self.user, event_context=context)

    @property
    def text_message(self):
        """String: build a plain text message."""
        raise NotImplementedError

    @property
    def html_message(self):
        """String: build an html message."""
        raise NotImplementedError

    @property
    def url(self):
        """String: build a url for the message."""
        raise NotImplementedError

    @property
    def event_type(self):
        """String

        Examples:
            <waterbutler id>_file_updated"""
        raise NotImplementedError


class RegistryError(TypeError):
    pass
