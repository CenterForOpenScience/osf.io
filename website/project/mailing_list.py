# -*- coding: utf-8 -*-

import requests

from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.exceptions import HTTPError

from website import settings


def address(node_id):
    return node_id + '@' + settings.SHORT_DOMAIN

def require_project_mailing(func):
    """ Execute function only if enable_project_mailing setting is true """
    def wrapper(*args, **kwargs):
        if settings.ENABLE_PROJECT_MAILING:
            return func(*args, **kwargs)
        return None
    return wrapper

@require_project_mailing
def send_messages(node, sender, message):
    recipients = [u for u in node.contributors
        if u not in node.mailing_unsubs
        and u != sender
        and u.is_active]
    for recipient in recipients:
        send_message(node._id, sender.fullname, recipient, message)

@queued_task
@app.task
def send_message(node_id, sender_fullname, recipient, message):
    """ Sends a message from the node through the given mailing list
    :param node_id: The id of the node in question
    :param user_fullname: The user sending the message
    :param message: Dictionary with subject and text of the email to be sent
    """
    res = requests.post(
        'https://api.mailgun.net/v3/{}/messages'.format(settings.SHORT_DOMAIN),
        auth=('api', settings.MAILGUN_API_KEY),
        data={'from': '{0} <{1}>'.format(sender_fullname, address(node_id)),
              'to': recipient.username,
              'subject': message['subject'],
              'html': '<html>{}</html>'.format(message['stripped-text'])})
    if res.status_code != 200:
        raise HTTPError(res.status_code)
