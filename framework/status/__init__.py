# -*- coding: utf-8 -*-

from collections import namedtuple

from framework.sessions import session

Status = namedtuple('Status', ['message', 'css_class', 'dismissible', 'safe'])

#: Status_type => bootstrap css class
TYPE_MAP = {
    'warning': 'warning',
    'warn': 'warning',
    'success': 'success',
    'info': 'info',
    'error': 'danger',
    'danger': 'danger',
}

def push_status_message(message, kind='warning', dismissible=True, safe=False):
    statuses = session.data.get('status')
    if not statuses:
        statuses = []
    css_class = TYPE_MAP.get(kind, 'warning')
    statuses.append(
        Status(message=message,
               css_class=css_class,
               dismissible=dismissible,
               safe=safe,
        )
    )
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
