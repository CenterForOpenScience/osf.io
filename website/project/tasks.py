import logging

import requests

from framework.celery_tasks import app as celery_app

from website import settings


logger = logging.getLogger(__name__)


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

        if settings.SHARE_URL:
            if not settings.SHARE_API_TOKEN:
                return logger.warning('SHARE_API_TOKEN not set. Could not send %s to SHARE.'.format(node))

            resp = requests.post('{}api/normalizeddata/'.format(settings.SHARE_URL), json={
                'data': {
                    'type': 'NormalizedData',
                    'attributes': {
                        'tasks': [],
                        'raw': None,
                        'data': {'@graph': [{
                            '@id': '_:123',
                            '@type': 'workidentifier',
                            'creative_work': {'@id': '_:789', '@type': 'project'},
                            'uri': '{}{}/'.format(settings.DOMAIN, node._id),
                        }, {
                            '@id': '_:789',
                            '@type': 'project',
                            'is_deleted': not node.is_public or node.is_deleted or node.is_spammy,
                        }]}
                    }
                }
            }, headers={'Authorization': 'Bearer {}'.format(settings.SHARE_API_TOKEN), 'Content-Type': 'application/vnd.api+json'})
            logger.debug(resp.content)
            resp.raise_for_status()
