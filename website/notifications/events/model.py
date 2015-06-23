# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from six import with_metaclass
from datetime import datetime
from website.notifications.emails import notify


class EventMeta(type):
    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        else:
            event_id = name.lower()
            cls.registry[event_id] = cls

        super(EventMeta, cls).__init__(name, bases, attrs)


@with_metaclass(EventMeta)
class BaseEvent:
    """
    Base notification class for building notification events and messages.
    - sets basic fields to default values.
    - abstract methods set methods that must be defined by subclasses.
    """
    def __init__(self, user, node, event):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.node_id = node._id
        self.action = event
        self.timestamp = datetime.utcnow()
        self.event = event
        self.message = "Blank message"
        self.url = None

    def perform(self):
        """Calls emails.notify"""
        notify(
            uid=self.node_id,
            event=self.event,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.message,
            gravatar_url=self.gravatar_url,
            url=self.url
        )

    def form_event(self):
        """

        """
        pass

    def form_message(self):
        """Piece together the message to be sent to subscribed users"""
        pass

    def form_url(self):
        """Build url from relevant info"""
        pass

