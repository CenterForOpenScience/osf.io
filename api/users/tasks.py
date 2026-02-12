import logging

from framework import sentry
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='api.users.tasks.merge_users')
def merge_users(merger_guid: str, mergee_guid: str):
    """
    Background task to merge one user into another.

    :param merger_guid: GUID of the primary user that will receive content
    :param mergee_guid: GUID of the user being merged into the primary user
    """
    from osf.models import OSFUser

    try:
        merger = OSFUser.load(merger_guid)
        mergee = OSFUser.load(mergee_guid)

        if not merger or not mergee:
            sentry.log_message(f'User merge task received invalid users: merger={merger_guid}, mergee={mergee_guid}')
            return

        if merger == mergee:
            sentry.log_message(f'User merge task attempted to merge a user into itself: {merger_guid}')
            return

        merger.merge_user(mergee)
    except Exception as exc:
        logger.exception(f'Unexpected error during background user merge: merger={merger_guid}, mergee={mergee_guid}')
        sentry.log_exception(exc)
