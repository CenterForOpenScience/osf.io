# -*- coding: utf-8 -*-

import re

from flask import request

from framework.auth.decorators import collect_auth
from framework.auth.core import get_user
from framework.auth.signals import user_confirmed

from website import mails
from website import settings
from website.models import Node
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
    must_be_contributor
)
from website.project.model import MailingListEventLog
from website.util.permissions import ADMIN
from website.util.sanitize import unescape_entities


###############################################################################
# Internal Calls
###############################################################################


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def enable_discussions(node, **kwargs):
    node.mailing_enabled = True
    node.save()


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable_discussions(node, **kwargs):
    node.mailing_enabled = False
    node.save()


@must_be_valid_project
@collect_auth
@must_be_contributor
@must_not_be_registration
def set_subscription(node, auth, **kwargs):
    subscription = request.json.get('discussionsSub')
    subscribed = True if subscription == 'subscribed' else False
    user = auth.user

    if subscribed and user in node.mailing_unsubs:
        node.mailing_unsubs.remove(user)
    elif not subscribed and user not in node.mailing_unsubs:
        node.mailing_unsubs.append(user)

    node.save()


###############################################################################
# Signalled Functions
###############################################################################


@user_confirmed.connect
def resubscribe_on_confirm(user):
    for node in user.contributed:
        try:
            node.mailing_unsubs.remove(user)
            node.save()
        except ValueError:
            # Nodes created via OSF4M
            pass

###############################################################################
# Mailing List Functions
###############################################################################

def address(node_id):
    return node_id + '@' + settings.SHORT_DOMAIN

def find_email(long_email):
    # allow for both "{email}" syntax and "{name} <{email}>" syntax
    if ' ' in long_email:
        email = re.search(r'<\S*>$', long_email).group(0)[1:-1]
        return email
    else:
        return long_email


def route_message(**kwargs):
    """ Recieves messages sent through Mailgun, validates them, and warns the
    user if they are not valid"""
    message = request.form
    target = find_email(message['To'])
    node_id = re.search(r'[a-z0-9]*@', target).group(0)[:-1]
    node = Node.load(node_id)

    sender_email = find_email(message['From'])
    sender = get_user(email=sender_email)

    user_is_admin = 'admin' in node.get_permissions(sender)\
        if sender and node else False

    mail_params = {
        'to_addr': sender_email,
        'mail': mails.DISCUSSIONS_EMAIL_REJECTED,
        'target_address': target,
        'user': sender,
        'node_type': node.project_or_component if node else '',
        'node_url': node.absolute_url if node else '',
        'is_admin': user_is_admin
    }

    if not sender:
        reason = MailingListEventLog.UNAUTHORIZED
    elif not node:
        reason = MailingListEventLog.NOT_FOUND
    elif node.is_deleted:
        reason = MailingListEventLog.DELETED
    elif sender not in node.contributors:
        reason = MailingListEventLog.FORBIDDEN
    elif not node.mailing_enabled:
        reason = MailingListEventLog.DISABLED
    else:
        reason = ''

    if reason:
        mails.send_mail(reason=reason, **mail_params)
    else:
        send_messages(node, sender, message)

    # Create a log of this mailing event
    reason = reason if reason else MailingListEventLog.OK
    MailingListEventLog.create_from_event(
        content=message,
        status=reason,
        node=node,
        email=sender_email,
        user=sender,
    )

def send_messages(node, sender, message):
    recipients = [u for u in node.contributors
        if u not in node.mailing_unsubs
        and u != sender
        and u.is_active]
    mail = mails.DISCUSSIONS_EMAIL_ACCEPTED
    mail.subject = '{} [via OSF: {}]'.format(
        message['subject'].split(' [via OSF')[0],  # Fixes reply subj, if node.title changes
        unescape_entities(node.title)
    )
    from_addr = '{0} <{1}>'.format(sender.fullname, address(node._id))
    context = {
        'body': message['stripped-text'][0],
        'cat': node.category,
        'node_url': '{}{}'.format(settings.DOMAIN.rstrip('/'), node.url),
        'node_title': node.title,
        'url': '{}{}settings/#configureNotificationsAnchor'.format(settings.DOMAIN.rstrip('/'), node.url)
    }

    for recipient in recipients:
        mails.send_mail(
            to_addr=recipient.username,
            mail=mail,
            from_addr=from_addr,
            **context
        )
