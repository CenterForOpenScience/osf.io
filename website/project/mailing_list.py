import re

from flask import request

from framework.auth.core import get_user
from framework.auth.signals import user_confirmed, node_created

from website import mails
from website import settings
from website.models import Node, NotificationSubscription
from website.notifications.utils import to_subscription_key

from website.project.model import MailingListEventLog
from website.project.signals import contributor_added
from website.util.sanitize import unescape_entities

###############################################################################
# Signalled Functions
###############################################################################

@node_created.connect
def create_mailing_list_subscription(node):
    if node.mailing_enabled:
        subscription = NotificationSubscription(
            _id=to_subscription_key(node._id, 'mailing_list_events'),
            owner=node,
            event_name='mailing_list_events'
        )
        subscription.add_user_to_subscription(node.creator, 'email_transactional', save=True)
        subscription.save()

@contributor_added.connect
def subscribe_contributor_to_mailing_list(node, contributor, auth=None):
    if node.mailing_enabled and contributor.is_active:
        subscription = NotificationSubscription.load(
            to_subscription_key(node._id, 'mailing_list_events')
        )
        subscription.add_user_to_subscription(contributor, 'email_transactional', save=True)
        subscription.save()

@user_confirmed.connect
def resubscribe_on_confirm(user):
    for node in user.contributed:
        subscribe_contributor_to_mailing_list(node, user)

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

def get_recipients(node):
    if node.mailing_enabled:
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
        return subscription.email_transactional
    return []

def get_unsubscribes(node):
    # Non-subscribed users not guaranteed to be in subscription.none
    # Safer to calculate it
    if node.mailing_enabled:
        recipients = get_recipients(node)
        return [u for u in node.contributors if u not in recipients]
    return []

def send_messages(node, sender, message):
    subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
    recipients = subscription.email_transactional
    mail = mails.DISCUSSIONS_EMAIL_ACCEPTED
    mail._subject = '{} [via OSF: {}]'.format(
        message['subject'].split(' [via OSF')[0],  # Fixes reply subj, if node.title changes
        unescape_entities(node.title)
    )
    from_addr = '{0} <{1}>'.format(sender.fullname, address(node._id))
    context = {
        'body': message['stripped-text'],
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
