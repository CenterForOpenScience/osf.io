# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from datetime import datetime

from website.notifications import emails


event_register = {}


def register(event_type):
    """Register classes into event_register"""
    def decorator(cls):
        event_register[event_type] = cls
        return cls
    return decorator


class Event(object):
    """Base event class for notification.

    - abstract methods set methods that must be defined by subclasses.
    To use this interface you must use the class as a Super (inherited).
     - Implement property methods in subclasses
     - All subclasses must be in this file for the meta class to list them
     - Name the subclasses you will be calling as such:
      - event (the type of event from _SUBSCRIPTIONS_AVAILABLE or specific cases)
      - class
      example: event = file_added, class = FileAdded
     - Call Event.parse_event() with the correct event name
    """
    def __init__(self, user, node, action):
        self.user = user
        self.gravatar_url = user.gravatar_url
        self.node = node
        self.action = action
        self.timestamp = datetime.utcnow()

    def perform(self):
        """Call emails.notify to notify users of an action"""
        emails.notify(
            event=self.event_type,
            user=self.user,
            node=self.node,
            timestamp=self.timestamp,
            message=self.html_message,
            gravatar_url=self.gravatar_url,
            url=self.url.url
        )

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
