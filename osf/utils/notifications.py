from django.utils import timezone

from osf.models.notification_type import NotificationType
from website.reviews import signals as reviews_signals
from website.settings import DOMAIN, OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL
from osf.utils.workflows import RegistrationModerationTriggers

def get_email_template_context(resource):
    is_preprint = resource.provider.type == 'osf.preprintprovider'
    url_segment = 'preprints' if is_preprint else 'registries'
    document_type = resource.provider.preprint_word if is_preprint else 'registration'
    from website.profile.utils import get_profile_image_url

    base_context = {
        'domain': DOMAIN,
        'reviewable_title': resource.title,
        'reviewable_branched_from_node': getattr(resource, 'branched_from_node', None),
        'reviewable_absolute_url': resource.absolute_url,
        'profile_image_url': get_profile_image_url(resource.creator),
        'reviewable_provider_name': resource.provider.name,
        'workflow': resource.provider.reviews_workflow,
        'provider_url': resource.provider.domain or f'{DOMAIN}{url_segment}/{resource.provider._id}',
        'provider_type': resource.provider.type,
        'provider_name': resource.provider.name,
        'provider_contact_email': resource.provider.email_contact or OSF_CONTACT_EMAIL,
        'provider_support_email': resource.provider.email_support or OSF_SUPPORT_EMAIL,
        'document_type': document_type,
        'notify_comment': not resource.provider.reviews_comments_private
    }

    if document_type == 'registration':
        base_context['draft_registration_absolute_url'] = resource.draft_registration.get().absolute_url
    else:
        base_context['draft_registration_absolute_url'] = None
    if document_type == 'registration' and resource.provider.brand:
        brand = resource.provider.brand
        base_context['logo_url'] = brand.hero_logo_image
        base_context['top_bar_color'] = brand.primary_color
        base_context['provider_name'] = resource.provider.name

    return base_context

def notify_submit(resource, user, *args, **kwargs):
    context = get_email_template_context(resource)
    recipients = list(resource.contributors)
    context['requester_fullname'] = user.fullname
    context['referrer_fullname'] = user.fullname
    context['user_fullname'] = user.fullname
    reviews_signals.reviews_email_submit.send(
        context=context,
        recipients=recipients,
        resource=resource,
        notification_type=NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION
    )
    reviews_signals.reviews_email_submit_moderators_notifications.send(
        timestamp=timezone.now(),
        context=context,
        resource=resource,

    )


def notify_resubmit(resource, user, *args, **kwargs):
    context = get_email_template_context(resource)
    context['referrer_fullname'] = user.fullname
    context['requester_fullname'] = user.fullname
    context['user_fullname'] = user.fullname

    context['resubmission'] = True
    recipients = list(resource.contributors)
    reviews_signals.reviews_email_submit.send(
        recipients=recipients,
        context=context,
        notification_type=NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION,
        resource=resource,
    )
    reviews_signals.reviews_email_submit_moderators_notifications.send(
        timestamp=timezone.now(),
        context=context,
        resource=resource,
    )


def notify_accept_reject(resource, user, action, states, *args, **kwargs):
    context = get_email_template_context(resource)
    context['user_fullname'] = user.fullname

    context['comment'] = action.comment
    context['requester_fullname'] = action.creator.fullname
    context['is_rejected'] = action.to_state == states.REJECTED.db_name
    context['was_pending'] = action.from_state == states.PENDING.db_name
    context['notify_comment'] = not resource.provider.reviews_comments_private

    reviews_signals.reviews_email.send(
        creator=user,
        context=context,
        template=NotificationType.Type.REVIEWS_SUBMISSION_STATUS,
        action=action
    )


def notify_edit_comment(resource, user, action, states, *args, **kwargs):
    if not resource.provider.reviews_comments_private and action.comment:
        context = get_email_template_context(resource)
        context['comment'] = action.comment
        context['requester_fullname'] = action.creator.fullname
        context['is_rejected'] = action.to_state == states.REJECTED.db_name
        context['was_pending'] = action.from_state == states.PENDING.db_name
        context['notify_comment'] = not resource.provider.reviews_comments_private
        reviews_signals.reviews_email.send(
            creator=user,
            context=context,
            template=NotificationType.Type.REVIEWS_SUBMISSION_STATUS,
            action=action
        )


def notify_reject_withdraw_request(resource, action, *args, **kwargs):
    context = get_email_template_context(resource)
    context['requester_fullname'] = action.creator.fullname
    context['referrer_fullname'] = action.creator.fullname
    context['force_withdrawal'] = False
    context['notify_comment'] = not resource.provider.reviews_comments_private
    context['reviewable_withdrawal_justification'] = resource.withdrawal_justification

    for contributor in resource.contributors.all():
        context['user_fullname'] = contributor.fullname
        context['contributor_fullname'] = contributor.fullname
        context['is_requester'] = action.creator == contributor
        context['comment'] = action.comment
        NotificationType.Type.NODE_WITHDRAWAl_REQUEST_APPROVED.instance.emit(
            user=contributor,
            event_context={
                'is_requester': contributor == action.creator,
                'ever_public': getattr(resource, 'ever_public', resource.is_public),
                **context
            },
        )

def notify_moderator_registration_requests_withdrawal(resource, user, *args, **kwargs):
    context = get_email_template_context(resource)
    reviews_signals.reviews_withdraw_requests_notification_moderators.send(
        timestamp=timezone.now(),
        context=context,
        resource=resource,
        user=user
    )


def notify_withdraw_registration(resource, action, *args, **kwargs):
    context = get_email_template_context(resource)

    context['force_withdrawal'] = action.trigger == RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
    context['requester_fullname'] = resource.retraction.initiated_by.fullname
    context['comment'] = action.comment
    context['force_withdrawal'] = False
    context['notify_comment'] = not resource.provider.reviews_comments_private
    context['reviewable_withdrawal_justification'] = resource.withdrawal_justification
    context['ever_public'] = getattr(resource, 'ever_public', resource.is_public)

    for contributor in resource.contributors.all():
        context['contributor_fullname'] = contributor.fullname
        context['user_fullname'] = contributor.fullname
        context['is_requester'] = resource.retraction.initiated_by == contributor

        NotificationType.Type.NODE_WITHDRAWAl_REQUEST_APPROVED.instance.emit(
            user=contributor,
            event_context=context
        )
