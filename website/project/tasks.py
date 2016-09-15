import datetime

import requests

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website import settings
from website.mails import mails


@celery_app.task(ignore_results=True)
def on_node_updated(node_id, user_id, first_save, saved_fields, request_headers=None):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    from website.models import Node
    node = Node.load(node_id)

    if node.is_collection or node.archiving:
        return

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search update for a new record (acceptable trade-off)
    if bool({'spam_status', 'is_deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False

    if need_update:
        node.update_search()

        if settings.SHARE_URL and settings.SHARE_API_TOKEN:
            requests.post('{}api/normalizeddata/'.format(settings.SHARE_URL), json={
                'created_at': datetime.datetime.utcnow().isoformat(),
                'normalized_data': {
                    '@graph': [{
                        '@id': '_:123',
                        '@type': 'link',
                        'type': 'provider',
                        'url': '{}{}/'.format(settings.DOMAIN, node._id),
                    }, {
                        '@id': '_:456',
                        '@type': 'throughlinks',
                        'link': {'@type': 'link', '@id': '_:123'},
                        'creative_work': {'@type': 'project', '@id': '_:789'},
                    }, {
                        '@id': '_:789',
                        '@type': 'project',
                        'is_deleted': not node.is_public or node.is_deleted or node.is_spammy,
                        'links': [{'@id': '_:456', '@type': 'throughlinks'}],
                    }]
                },
            }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN)}).raise_for_status()


@celery_app.task(ignore_results=True)
def on_user_suspension(user_id, system_tag):
    from framework.auth import User

    with TokuTransaction():
        user = User.load(user_id)
        if system_tag not in user.system_tags:
            user.system_tags.append(system_tag)
        if not user.is_disabled:
            user.disable_account()
            user.is_registered = False
            mails.send_mail(
                to_addr=user.username,
                mail=mails.SPAM_USER_BANNED,
                user=user
            )
        user.save()
