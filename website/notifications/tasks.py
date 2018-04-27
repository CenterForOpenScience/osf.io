"""
Tasks for making even transactional emails consolidated.
"""
import itertools

from django.db import connection

from framework.celery_tasks import app as celery_app
from framework.sentry import log_exception
from osf.models import OSFUser, AbstractNode, AbstractProvider
from osf.models import NotificationDigest
from website import mails, settings
from website.notifications.utils import NotificationsDict
from api.preprint_providers.permissions import GroupHelper


@celery_app.task(name='website.notifications.tasks.send_users_email', max_retries=0)
def send_users_email(send_type):
    """Send pending emails.

    :param send_type
    :return:
    """
    _send_global_and_node_emails(send_type)
    _send_reviews_moderator_emails(send_type)


def _send_global_and_node_emails(send_type):
    """
    Called by `send_users_email`. Send all global and node-related notification emails.
    """
    grouped_emails = get_users_emails(send_type)
    for group in grouped_emails:
        user = OSFUser.load(group['user_id'])
        if not user:
            log_exception()
            continue
        info = group['info']
        notification_ids = [message['_id'] for message in info]
        sorted_messages = group_by_node(info)
        if sorted_messages:
            if not user.is_disabled:
                # If there's only one node in digest we can show it's preferences link in the template.
                notification_nodes = sorted_messages['children'].keys()
                node = AbstractNode.load(notification_nodes[0]) if len(
                    notification_nodes) == 1 else None
                mails.send_mail(
                    to_addr=user.username,
                    mimetype='html',
                    can_change_node_preferences=bool(node),
                    node=node,
                    mail=mails.DIGEST,
                    name=user.fullname,
                    message=sorted_messages,
                )
            remove_notifications(email_notification_ids=notification_ids)


def _send_reviews_moderator_emails(send_type):
    """
    Called by `send_users_email`. Send all reviews triggered emails.
    """
    grouped_emails = get_moderators_emails(send_type)
    for group in grouped_emails:
        user = OSFUser.load(group['user_id'])
        info = group['info']
        notification_ids = [message['_id'] for message in info]
        if not user.is_disabled:
            provider = AbstractProvider.objects.get(id=group['provider_id'])
            mails.send_mail(
                to_addr=user.username,
                mimetype='html',
                mail=mails.DIGEST_REVIEWS_MODERATORS,
                name=user.fullname,
                message=info,
                provider_name=provider.name,
                reviews_submissions_url='{}reviews/preprints/{}'.format(settings.DOMAIN, provider._id),
                notification_settings_url='{}reviews/preprints/{}/notifications'.format(settings.DOMAIN, provider._id),
                is_reviews_moderator_notificaiton=True,
                is_admin=GroupHelper(provider).get_group('admin').user_set.filter(id=user.id).exists()
            )
        remove_notifications(email_notification_ids=notification_ids)


def get_moderators_emails(send_type):
    """Get all emails for reviews moderators that need to be sent, grouped by users AND providers.
    :param send_type: from NOTIFICATION_TYPES, could be "email_digest" or "email_transactional"
    :return Iterable of dicts of the form:
        [
            'user_id': 'se8ea',
            'provider_id': '1',
            'info': [
                {
                    'message': 'Hana Xie submitted Gravity',
                    '_id': NotificationDigest._id,
                }
            ],
        ]
    """
    sql = """
        SELECT json_build_object(
                'user_id', osf_guid._id,
                'provider_id', nd.provider_id,
                'info', json_agg(
                    json_build_object(
                        'message', nd.message,
                        '_id', nd._id
                    )
                )
            )
        FROM osf_notificationdigest AS nd
          LEFT JOIN osf_guid ON nd.user_id = osf_guid.object_id
        WHERE send_type = %s AND event = 'new_pending_submissions'
        AND osf_guid.content_type_id = (SELECT id FROM django_content_type WHERE model = 'osfuser')
        GROUP BY osf_guid.id, nd.provider_id
        ORDER BY osf_guid.id ASC
        """

    with connection.cursor() as cursor:
        cursor.execute(sql, [send_type, ])
        return itertools.chain.from_iterable(cursor.fetchall())


def get_users_emails(send_type):
    """Get all emails that need to be sent.
    NOTE: These do not include reviews triggered emails for moderators.

    :param send_type: from NOTIFICATION_TYPES
    :return: Iterable of dicts of the form:
        {
            'user_id': 'se8ea',
            'info': [{
                'message': {
                    'message': 'Freddie commented on your project Open Science',
                    'timestamp': datetime object
                },
                'node_lineage': ['parent._id', 'node._id'],
                '_id': NotificationDigest._id
            }, ...
            }]
            {
            'user_id': ...
            }
        }
    """

    sql = """
    SELECT json_build_object(
            'user_id', osf_guid._id,
            'info', json_agg(
                json_build_object(
                    'message', nd.message,
                    'node_lineage', nd.node_lineage,
                    '_id', nd._id
                )
            )
        )
    FROM osf_notificationdigest AS nd
      LEFT JOIN osf_guid ON nd.user_id = osf_guid.object_id
    WHERE send_type = %s AND event != 'new_pending_submissions'
    AND osf_guid.content_type_id = (SELECT id FROM django_content_type WHERE model = 'osfuser')
    GROUP BY osf_guid.id
    ORDER BY osf_guid.id ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [send_type, ])
        return itertools.chain.from_iterable(cursor.fetchall())


def group_by_node(notifications, limit=15):
    """Take list of notifications and group by node.

    :param notifications: List of stored email notifications
    :return:
    """
    emails = NotificationsDict()
    for notification in notifications[:15]:
        emails.add_message(notification['node_lineage'], notification['message'])
    return emails


def remove_notifications(email_notification_ids=None):
    """Remove sent emails.

    :param email_notification_ids:
    :return:
    """
    if email_notification_ids:
        NotificationDigest.objects.filter(_id__in=email_notification_ids).delete()
