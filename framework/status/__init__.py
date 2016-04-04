# -*- coding: utf-8 -*-

from collections import namedtuple

from framework.sessions import session

Status = namedtuple('Status', ['message', 'jumbotron', 'css_class', 'dismissible', 'trust'])  # trust=True displays msg as raw HTML

#: Status_type => bootstrap css class
TYPE_MAP = {
    'warning': 'warning',
    'warn': 'warning',
    'success': 'success',
    'info': 'info',
    'error': 'danger',
    'danger': 'danger',
    'default': 'default',
}

def push_status_message(message, kind='warning', dismissible=True, trust=True, jumbotron=False):
    """
    Push a status message that will be displayed as a banner on the next page loaded by the user.

    :param message: Text of the message to display
    :param kind: The type of alert message to use; translates into a bootstrap CSS class of `alert-<kind>`
    :param dismissible: Whether the status message can be dismissed by the user
    :param trust: Whether the text is safe to insert directly into HTML as given. (useful if the message includes
        custom code, eg links) If false, the message will be automatically escaped as an HTML-safe string.
    :param jumbotron: Should this be in a jumbotron element rather than an alert
    """
    # TODO: Change the default to trust=False once conversion to markupsafe rendering is complete
    try:
        statuses = session.data.get('status')
    except RuntimeError:
        # Working outside of request context, so should be a DRF issue. Status messages are not appropriate there.
        # If it's any kind of notification, then it doesn't make sense to send back to the API routes.
        if kind == 'error':
            #  If it's an error, then the call should fail with the error message. I do not know of any cases where
            # this branch will be hit, but I'd like to avoid a silent failure.
            from rest_framework.exceptions import ValidationError
            raise ValidationError(message)
        return
    if not statuses:
        statuses = []
    css_class = TYPE_MAP.get(kind, 'warning')
    statuses.append(Status(message=message,
                           jumbotron=jumbotron,
                           css_class=css_class,
                           dismissible=dismissible,
                           trust=trust))
    session.data['status'] = statuses

def pop_status_messages(level=0):
    messages = session.data.get('status')
    session.status_prev = messages
    if 'status' in session.data:
        del session.data['status']
    return messages

def pop_previous_status_messages(level=0):
    messages = session.data.get('status_prev')
    if 'status_prev' in session.data:
        del session.data['status_prev']
    return messages
