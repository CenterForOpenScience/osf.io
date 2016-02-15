# -*- coding: utf-8 -*-

import requests

from framework.tasks import app
from framework.tasks.handlers import queued_task
from framework.exceptions import HTTPError

from website import settings
from website.mails.mails import render_message

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
    subject = message['subject']
    context = {
        'body': message['stripped-text'][0],
        'cat': node.category,
        'node_url': '{}{}'.format(settings.DOMAIN.rstrip('/'), node.url),
        'node_title': node.title,
        'url': '{}{}settings/#discussionsSettings'.format(settings.DOMAIN.rstrip('/'), node.url)
    }
    rendered_message = render_message('discussions_email_accepted.html.mako', **context)
    for recipient in recipients:
        send_message(node._id, sender.fullname, recipient.username, subject, rendered_message)

@queued_task
@app.task
def send_message(node_id, sender_fullname, recipient_email, subject, message):
    """ Sends a message from the node through the given mailing list
    :param node_id: The id of the node in question
    :param sender_fullname: The user sending the message
    :param recipient_email: The user receiving the message
    :param subject: email subject
    :param message: Rendered email content from template
    """
    res = requests.post(
        'https://api.mailgun.net/v3/{}/messages'.format(settings.SHORT_DOMAIN),
        auth=('api', settings.MAILGUN_API_KEY),
        data={'from': '{0} <{1}>'.format(sender_fullname, address(node_id)),
              'to': recipient_email,
              'subject': subject,
              'html': message})
    if res.status_code != 200:
        raise HTTPError(res.status_code)
