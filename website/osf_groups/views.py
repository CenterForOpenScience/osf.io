import logging

from framework.utils import get_timestamp, throttle_period_expired

from website import mails, settings
from website.notifications.exceptions import InvalidSubscriptionError
from website.notifications.utils import (
    check_if_all_global_subscriptions_are_none,
    subscribe_user_to_notifications,
)
from website.osf_groups.signals import (
    unreg_member_added,
    member_added,
    group_added_to_node,
)
logger = logging.getLogger(__name__)


@member_added.connect
def notify_added_group_member(group, user, permission, auth=None, throttle=None, email_template='default', *args, **kwargs):
    if email_template == 'false':
        return

    throttle = throttle or settings.GROUP_MEMBER_ADDED_EMAIL_THROTTLE

    member_record = user.member_added_email_records.get(group._id, {})
    if member_record:
        timestamp = member_record.get('last_sent', None)
        if timestamp:
            if not throttle_period_expired(timestamp, throttle):
                return
    else:
        user.member_added_email_records[group._id] = {}

    if user.is_registered:
        email_template = mails.GROUP_MEMBER_ADDED
        mails.send_mail(
            to_addr=user.username,
            mail=email_template,
            mimetype='html',
            user=user,
            group_name=group.name,
            permission=permission,
            referrer_name=auth.user.fullname if auth else '',
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
        )
        user.member_added_email_records[group._id]['last_sent'] = get_timestamp()
        user.save()

    else:
        unreg_member_added.send(group, user=user, permission=permission, auth=auth, throttle=throttle, email_template=email_template)


def send_claim_member_email(email, user, group, permission, auth=None, throttle=None, email_template='default'):
    """
    Unregistered user claiming a user account as a group member of an OSFGroup. Send an email for claiming the account.
    Sends to the given email

    :param str email: The address given in the claim user form
    :param User user: The User record to claim.
    :param OSFGroup group: The group where the user claimed their account.
    :return

    """

    claimer_email = email.lower().strip()
    claim_url = user.get_claim_url(group._id, external=True)

    throttle = throttle or settings.GROUP_MEMBER_ADDED_EMAIL_THROTTLE

    mails.send_mail(
        to_addr=claimer_email,
        mail=email_template,
        mimetype='html',
        user=user,
        group_name=group.name,
        referrer_name=auth.user.fullname if auth else '',
        permission=permission,
        claim_url=claim_url,
        osf_contact_email=settings.OSF_CONTACT_EMAIL,
    )
    user.member_added_email_records[group._id]['last_sent'] = get_timestamp()
    user.save()

    return claimer_email


@unreg_member_added.connect
def finalize_invitation(group, user, permission, auth, throttle, email_template='default'):
    email_template = mails.GROUP_MEMBER_UNREGISTERED_ADDED

    try:
        record = user.get_unclaimed_record(group._id)
    except ValueError:
        pass
    else:
        if record['email']:
            send_claim_member_email(record['email'], user, group, permission, auth=auth, throttle=throttle, email_template=email_template)


@group_added_to_node.connect
def notify_added_node_group_member(group, node, user, permission, auth, throttle=None):
    throttle = throttle or settings.GROUP_CONNECTED_EMAIL_THROTTLE

    node_group_record = user.group_connected_email_records.get(group._id, {})
    if node_group_record:
        timestamp = node_group_record.get('last_sent', None)
        if timestamp:
            if not throttle_period_expired(timestamp, throttle):
                return
    else:
        user.group_connected_email_records[group._id] = {}

    if (not auth or auth.user != user) and user.is_registered:
        email_template = mails.GROUP_ADDED_TO_NODE
        mails.send_mail(
            to_addr=user.username,
            mail=email_template,
            mimetype='html',
            user=user,
            node=node,
            all_global_subscriptions_none=check_if_all_global_subscriptions_are_none(user),
            group_name=group.name,
            permission=permission,
            referrer_name=auth.user.fullname if auth else '',
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
        )

        user.group_connected_email_records[group._id]['last_sent'] = get_timestamp()
        user.save()

@group_added_to_node.connect
def subscribe_group_member(group, node, user, permission, auth, throttle=None):
    try:
        subscribe_user_to_notifications(node, user)
    except InvalidSubscriptionError as err:
        logger.warn('Skipping subscription of user {} to node {}'.format(user, node._id))
        logger.warn('Reason: {}'.format(str(err)))
