import logging

from framework.utils import get_timestamp
from osf.models import NotificationType

from website import settings
logger = logging.getLogger(__name__)

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

    NotificationType.objects.get(
        name=email_template.tpl_prefix
    ).emit(
        user=user,
        event_context={
            'group_name': group.name,
            'referrer_name': auth.user.fullname if auth else '',
            'permission': permission,
            'claim_url': claim_url,
            'osf_contact_email': settings.OSF_CONTACT_EMAIL,
        }
    )
    user.member_added_email_records[group._id]['last_sent'] = get_timestamp()
    user.save()

    return claimer_email
