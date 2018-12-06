
from website import mails, settings
from website.osf_groups.signals import unreg_member_added, member_added

@member_added.connect
def notify_added_group_member(group, user, permission, auth=None, throttle=None, email_template='default', *args, **kwargs):
    if email_template == 'false':
        return

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

    else:
        unreg_member_added.send(group, user=user, permission=permission, auth=auth, email_template=email_template)


def send_claim_member_email(email, user, group, permission, auth=None, email_template='default'):
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

    return claimer_email


@unreg_member_added.connect
def finalize_invitation(group, user, permission, auth, email_template='default'):
    email_template = mails.GROUP_MEMBER_UNREGISTERED_ADDED

    try:
        record = user.get_unclaimed_record(group._id)
    except ValueError:
        pass
    else:
        if record['email']:
            send_claim_member_email(record['email'], user, group, permission, auth=auth, email_template=email_template)
