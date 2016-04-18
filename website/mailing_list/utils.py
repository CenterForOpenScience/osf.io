import re

from flask import request
from modularodm import Q

from framework.auth.core import get_user
from framework.auth.signals import user_confirmed

from website import mails
from website import settings
from website.notifications.utils import to_subscription_key

from website.mailing_list.model import MailingListEventLog
from website.project.signals import contributor_added
from website.util.sanitize import unescape_entities

ANGLE_BRACKETS_REGEX = re.compile(r'<(.*?)>')

###############################################################################
# Signalled Functions
###############################################################################

@contributor_added.connect
def subscribe_contributor_to_mailing_list(node, contributor, auth=None):
    if node.mailing_enabled and contributor.is_active:
        subscription = node.get_or_create_mailing_list_subscription()
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
    if '<' in long_email:
        email = ANGLE_BRACKETS_REGEX.search(long_email).groups[0]
        return email
    elif '@' in long_email:
        return long_email
    return None

def reason_for_rejection(sender, node, message):
    if 'multipart/report' in message['Content-Type'] and 'delivery-status' in message['Content-Type']:
        return MailingListEventLog.BOUNCED
    if not sender:
        return MailingListEventLog.UNAUTHORIZED
    elif not node:
        return MailingListEventLog.NOT_FOUND
    elif node.is_deleted:
        return MailingListEventLog.DELETED
    elif sender not in node.contributors:
        return MailingListEventLog.FORBIDDEN
    elif not node.mailing_enabled:
        return MailingListEventLog.DISABLED
    elif not get_recipients(node, sender):
        return MailingListEventLog.NO_RECIPIENTS

    p = re.compile('auto[- ]{0,1}reply', re.IGNORECASE)
    if p.match(message['subject']):
        return MailingListEventLog.AUTOREPLY
    try:
        last_sender_msg = MailingListEventLog.find(Q('sending_user', 'eq', sender) & Q('destination_node', 'eq', node))[0].content
    except IndexError:
        pass
    else:
        if len(message['stripped-text']) > 10 and message['stripped-text'] == last_sender_msg['stripped-text']:
            return MailingListEventLog.AUTOREPLY
    return

def route_message(**kwargs):
    """ Acquires messages sent through Mailgun, validates them, and warns the
    user if they are not valid"""
    from website.models import Node  # avoid circular imports
    message = request.form
    target = find_email(message['To'])
    # node_id = re.search(r'[a-z0-9]*@', target).group(0)[:-1]
    node = Node.load(re.search(r'[a-z0-9]*@', target).group(0)[:-1])

    sender_email = find_email(message['From'])
    sender = get_user(email=sender_email)

    reason = reason_for_rejection(sender, node, message)

    if reason:
        if reason not in (MailingListEventLog.BOUNCED, MailingListEventLog.AUTOREPLY):
            send_rejection(node, sender, sender_email, target, message, reason)
        recipients = []
    else:
        reason = MailingListEventLog.OK
        recipients = get_recipients(node, sender=sender)
        send_acception(node, sender, recipients, message)

    # Create a log of this mailing event
    MailingListEventLog(
        content=message,
        status=reason,
        destination_node=node,
        sending_email=sender_email,
        sending_user=sender,
        intended_recipients=recipients
    ).save()

def get_recipients(node, sender=None):
    if node.mailing_enabled:
        from website.models import NotificationSubscription  # avoid circular import
        subscription = NotificationSubscription.load(to_subscription_key(node._id, 'mailing_list_events'))
        return [u for u in subscription.email_transactional if not u == sender]
    return []

def get_unsubscribes(node):
    # Non-subscribed users not guaranteed to be in subscription.none
    # Safer to calculate it
    if node.mailing_enabled:
        recipients = get_recipients(node)
        return [u for u in node.contributors if u not in recipients]
    return []

def send_acception(node, sender, recipients, message):
    mail = mails.MAILING_LIST_EMAIL_ACCEPTED
    mail._subject = '{} [via OSF: {}]'.format(
        message['subject'].split(' [via OSF')[0],  # Fixes reply subj, if node.title changes
        unescape_entities(node.title)
    )
    from_addr = '{0} <{1}>'.format(sender.fullname, address(node._id))
    context = {
        'body': message['stripped-text'],
        'cat': node.category,
        'node_url': '{}{}'.format(settings.DOMAIN.rstrip('/'), node.url),
        'node_title': unescape_entities(node.title),
        'url': '{}{}settings/#configureNotificationsAnchor'.format(settings.DOMAIN.rstrip('/'), node.url)
    }

    for recipient in recipients:
        mails.send_mail(
            to_addr=recipient.username,
            mail=mail,
            from_addr=from_addr,
            **context
        )

def send_rejection(node, sender, sender_email, target, message, reason):
    user_is_admin = 'admin' in node.get_permissions(sender)\
        if sender and node else False

    mail_params = {
        'to_addr': sender_email,
        'mail': mails.MAILING_LIST_EMAIL_REJECTED,
        'target_address': target,
        'user': sender,
        'node_type': node.project_or_component if node else '',
        'node_url': node.absolute_url if node else '',
        'is_admin': user_is_admin,
        'mail_log_class': MailingListEventLog
    }

    mails.send_mail(reason=reason, **mail_params)
