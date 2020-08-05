import logging

from django.apps import apps
from framework.celery_tasks import app as celery_app

from website import settings
from api.share.utils import update_share

logger = logging.getLogger(__name__)


@celery_app.task(ignore_results=True)
def on_node_updated(node_id, user_id, first_save, saved_fields, request_headers=None):
    # WARNING: Only perform Read-Only operations in an asynchronous task, until Repeatable Read/Serializable
    # transactions are implemented in View and Task application layers.
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)

    if node.is_collection or node.archiving or node.is_quickfiles:
        return

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search update for a new record (acceptable trade-off)
    if bool({'spam_status', 'is_deleted', 'deleted'}.intersection(saved_fields)):
        need_update = True
    elif not node.is_public and 'is_public' not in saved_fields:
        need_update = False

    if need_update:
        node.update_search()
        if settings.SHARE_ENABLED:
            update_share(node)
        update_collecting_metadata(node, saved_fields)

    if node.get_identifier_value('doi') and bool(node.IDENTIFIER_UPDATE_FIELDS.intersection(saved_fields)):
        node.request_identifier_update(category='doi')


def update_collecting_metadata(node, saved_fields):
    from website.search.search import update_collected_metadata
    if node.is_collected:
        if node.is_public:
            update_collected_metadata(node._id)
        else:
            update_collected_metadata(node._id, op='delete')
