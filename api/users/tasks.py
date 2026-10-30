import logging

from framework import sentry
from framework.celery_tasks import app as celery_app

from osf.models import OSFUser
from osf.models.notification_type import NotificationTypeEnum

logger = logging.getLogger(__name__)


@celery_app.task(name='api.users.tasks.merge_users')
def merge_users(merger_guid: str, mergee_guid: str, initiator_guid: str | None = None):
    """
    Background task to merge one user into another.

    :param merger_guid: GUID of the primary user that will receive content
    :param mergee_guid: GUID of the user being merged into the primary user
    :param initiator_guid: GUID of the user who started the merge, notified if it fails
    """
    merger = OSFUser.load(merger_guid)
    mergee = OSFUser.load(mergee_guid)

    if not merger or not mergee:
        message = f'User merge task received invalid users: merger={merger_guid}, mergee={mergee_guid}'
        sentry.log_message(message)
        _notify_merge_failed(initiator_guid, merger_guid, mergee_guid, message)
        return

    if merger == mergee:
        message = f'User merge task attempted to merge a user into itself: {merger_guid}'
        sentry.log_message(message)
        _notify_merge_failed(initiator_guid, merger_guid, mergee_guid, message)
        return

    try:
        merger.merge_user(mergee)
    except Exception as exc:
        _notify_merge_failed(initiator_guid, merger_guid, mergee_guid, repr(exc))


def _notify_merge_failed(initiator_guid: str | None, merger_guid: str, mergee_guid: str, error: str):
    if not initiator_guid:
        return
    try:
        initiator = OSFUser.load(initiator_guid)
        if not initiator:
            return
        NotificationTypeEnum.USER_MERGE_FAILED_REPORT.instance.emit(
            user=initiator,
            message_frequency='instantly',
            event_context={
                'merger_guid': merger_guid,
                'mergee_guid': mergee_guid,
                'error': error,
            },
            save=False,
        )
    except Exception as exc:
        logger.exception('Failed to send user merge failure email')
        sentry.log_exception(exc)


@celery_app.task(bind=True, name='api.users.tasks.confirm_user_ham')
def confirm_user_ham(self, user_guid: str, initiator_guid: str | None = None):
    initiator_user = OSFUser.load(initiator_guid) if initiator_guid else None
    failed_ham = []
    try:
        user = OSFUser.objects.get(guids___id=user_guid)
    except OSFUser.DoesNotExist as exc:
        sentry.log_exception(exc)
        return str(exc)
    else:
        try:
            user.is_registered = True  # back in the day spam users were de-registered
            failed_ham = user.confirm_ham(save=True, train_spam_services=False)
        except Exception as exc:
            sentry.log_exception(exc)

    try:
        if initiator_user:
            NotificationTypeEnum.USER_CONFIRM_HAM_REPORT.instance.emit(
                user=initiator_user,
                message_frequency='instantly',
                event_context={
                    'user_guid': user._id,
                    'failed_ham': ', '.join(failed_ham),
                },
                save=False,
            )
    except Exception as exc:
        logger.exception('Failed to send HAM confirmation report email')
        sentry.log_exception(exc)

    return True
