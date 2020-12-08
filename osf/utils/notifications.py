from django.utils import timezone
from website.mails import mails
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL
from osf.utils.workflows import RegistrationModerationTriggers

def get_email_template_context(resource):
    is_preprint = resource.provider.type == 'osf.preprintprovider'
    url_segment = 'preprints' if is_preprint else 'registries'
    document_type = resource.provider.preprint_word if is_preprint else 'registration'

    base_context = {
        'domain': DOMAIN,
        'reviewable': resource,
        'workflow': resource.provider.reviews_workflow,
        'provider_url': resource.provider.domain or f'{DOMAIN}{url_segment}/{resource.provider._id}',
        'provider_contact_email': resource.provider.email_contact or OSF_CONTACT_EMAIL,
        'provider_support_email': resource.provider.email_support or OSF_SUPPORT_EMAIL,
        'document_type': document_type
    }

    if document_type == 'registration':
        base_context['draft_registration'] = resource.draft_registration.get()
    if document_type == 'registration' and resource.provider.brand:
        brand = resource.provider.brand
        base_context['logo_url'] = brand.hero_logo_image
        base_context['top_bar_color'] = brand.primary_color
        base_context['provider_name'] = resource.provider.name

    return base_context

def notify_submit(resource, user, *args, **kwargs):
    context = get_email_template_context(resource)
    context['referrer'] = user
    recipients = list(resource.contributors)
    reviews_signals.reviews_email_submit.send(
        context=context,
        recipients=recipients
    )
    reviews_signals.reviews_email_submit_moderators_notifications.send(
        timestamp=timezone.now(),
        context=context
    )


def notify_resubmit(resource, user, action, *args, **kwargs):
    context = get_email_template_context(resource)
    reviews_signals.reviews_email.send(
        creator=user,
        context=context,
        template='reviews_resubmission_confirmation',
        action=action
    )


def notify_accept_reject(resource, user, action, states, *args, **kwargs):
    context = get_email_template_context(resource)

    context['notify_comment'] = not resource.provider.reviews_comments_private and action.comment
    context['comment'] = action.comment
    context['requester'] = action.creator
    context['is_rejected'] = action.to_state == states.REJECTED.db_name
    context['was_pending'] = action.from_state == states.PENDING.db_name
    reviews_signals.reviews_email.send(
        creator=user,
        context=context,
        template='reviews_submission_status',
        action=action
    )


def notify_edit_comment(resource, user, action, *args, **kwargs):
    if not resource.provider.reviews_comments_private and action.comment:
        context = get_email_template_context(resource)
        context['comment'] = action.comment
        reviews_signals.reviews_email.send(
            creator=user,
            context=context,
            template='reviews_update_comment',
            action=action
        )


def notify_reject_withdraw_request(resource, action, *args, **kwargs):
    context = get_email_template_context(resource)
    context['requester'] = action.creator

    for contributor in resource.contributors.all():
        context['contributor'] = contributor
        context['requester'] = action.creator
        context['is_requester'] = action.creator == contributor

        mails.send_mail(
            contributor.username,
            mails.WITHDRAWAL_REQUEST_DECLINED,
            **context
        )


def notify_moderator_registration_requests_withdrawal(resource, user, *args, **kwargs):
    context = get_email_template_context(resource)
    context['referrer'] = user
    reviews_signals.reviews_withdraw_requests_notification_moderators.send(
        timestamp=timezone.now(),
        context=context
    )


def notify_withdraw_registration(resource, action, *args, **kwargs):
    context = get_email_template_context(resource)

    context['force_withdrawal'] = action.trigger == RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
    context['requester'] = resource.retraction.initiated_by
    context['comment'] = action.comment
    context['notify_comment'] = not resource.provider.reviews_comments_private and action.comment

    for contributor in resource.contributors.all():
        context['contributor'] = contributor
        context['is_requester'] = context['requester'] == contributor
        mails.send_mail(
            contributor.username,
            mails.WITHDRAWAL_REQUEST_GRANTED,
            **context
        )
