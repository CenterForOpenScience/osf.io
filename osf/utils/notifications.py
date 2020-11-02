from django.utils import timezone
from website.mails import mails
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL


def get_email_template_context(resource):
    assert resource.type in ['osf.registration', 'osf.preprint'], 'This resource does not fit the template'
    return {
        'domain': DOMAIN,
        'reviewable': resource,
        'workflow': resource.provider.reviews_workflow,
        'provider_url': resource.provider.domain or f'{DOMAIN}preprints/{node.provider._id}',
        'provider_contact_email': resource.provider.email_contact or OSF_CONTACT_EMAIL,
        'provider_support_email': resource.provider.email_support or OSF_SUPPORT_EMAIL,
        'document_type': getattr(resource, 'preprint_word', 'registration')
    }


def notify_submit(resource, referrer):
    context = get_email_template_context(resource)
    context['referrer'] = referrer
    recipients = list(resource.contributors)
    reviews_signals.reviews_email_submit.send(
        context=context,
        recipients=recipients
    )
    reviews_signals.reviews_email_submit_moderators_notifications.send(
        timestamp=timezone.now(),
        context=context
    )


def notify_resubmit(resource, creator, action):
    context = get_email_template_context(resource)
    reviews_signals.reviews_email.send(
        creator=creator,
        context=context,
        template='reviews_resubmission_confirmation',
        action=action
    )


def notify_accept_reject(resource, action, machine_states, creator):
    context = get_email_template_context(resource)

    context['notify_comment'] = not resource.provider.reviews_comments_private and action.comment
    context['comment'] = action.comment
    context['is_rejected'] = action.to_state == machine_states.REJECTED.value
    context['was_pending'] = action.from_state == machine_states.PENDING.value
    reviews_signals.reviews_email.send(
        creator=creator,
        context=context,
        template='reviews_submission_status',
        action=action
    )


def notify_edit_comment(resource, action, creator):
    context = get_email_template_context(resource)

    context['comment'] = action.comment
    if not resource.provider.reviews_comments_private and action.comment:
        reviews_signals.reviews_email.send(
            creator=creator,
            context=context,
            template='reviews_update_comment',
            action=action
        )


def notify_withdraw_registration(registration, action):
    context = get_email_template_context(registration)

    for contributor in registration.contributors.all():
        context['contributor'] = contributor
        context['user'] = contributor
        context['requester'] = action.creator
        context['is_requester'] = action.creator == contributor

        mails.send_mail(
            contributor.username,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            mimetype='html',
            **context
        )


def notify_reject_withdraw_request(registration, action):
    context = get_email_template_context(registration)
    context['requester'] = action.creator

    for contributor in registration.contributors.all():
        context['contributor'] = contributor
        context['requester'] = action.creator
        context['is_requester'] = action.creator == contributor

        mails.send_mail(
            contributor.username,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            mimetype='html',
            **context
        )

def notify_moderator_registration_requests_withdrawal(registration, referrer):
    context = get_email_template_context(registration)
    context['referrer'] = referrer
    reviews_signals.reviews_withdraw_requests_notification_moderators.send(
        timestamp=timezone.now(),
        context=context
    )