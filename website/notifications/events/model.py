# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from website.notifications.emails import notify

class BaseEvent:
    """
    Base notification class for building notification events and messages.
    - sets basic fields to default values.
    - abstract methods set methods that must be defined by subclasses.
    """
    __metaclass__ = ABCMeta

    def __init__(self, user, node, event):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.node_id = node._id
        self.event = event
        self.timestamp = datetime.utcnow()
        self.event_sub = event
        self.message = "Blank message"
        self.url = None

    def perform(self):
        """Calls emails.notify"""
        notify(
            uid=self.node_id,
            event=self.event_sub,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.message,
            gravatar_url=self.gravatar_url,
            url=self.url
        )

    @abstractmethod
    def form_event(self):
        """
        Use NODE_SUBSCRIPTIONS_AVAILABLE and USER_SUBSCRIPTIONS_AVAILABLE plus UIDs
        where available to denote individual subscriptions.
        """
        pass

    @abstractmethod
    def form_message(self):
        """Piece together the message to be sent to subscribed users"""
        pass

    @abstractmethod
    def form_url(self):
        """Build url from relevant info"""
        pass

