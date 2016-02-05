# -*- coding: utf-8 -*-
"""Basic Event handling for events that need subscriptions"""

from datetime import datetime

from website.notifications import emails


event_registry = {}


def register(event_type):
    """Register classes into event_registry"""
    def decorator(cls):
        event_registry[event_type] = cls
        return cls
    return decorator


class Event(object):
    """Base event class for notification.

    - abstract methods set methods that should be defined by subclasses.
    To use this interface you must use the class as a Super (inherited).
     - Implement property methods in subclasses
    """
    def __init__(self, user, node, action):
        self.user = user
        self.gravatar_url = user.profile_image_url()
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
            url=self.url
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


class RegistryError(TypeError):
    pass
