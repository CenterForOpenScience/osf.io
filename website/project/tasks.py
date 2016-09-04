from framework.celery_tasks import app as celery_app
from website import settings


@celery_app.task(ignore_results=True)
def on_node_updated(node_id, saved_fields, request_headers=None):
    from website.models import Node
    node = Node.load(node_id)

    if request_headers and settings.SPAM_CHECK_ENABLED:
        if node.check_spam(saved_fields, request_headers):
            node.save()

    need_update = bool(node.SEARCH_UPDATE_FIELDS.intersection(saved_fields))
    # due to async nature of call this can issue a search delete for a new record (acceptable trade-off)
    if not node.is_public and 'is_public' not in saved_fields:
        need_update = False
    # short circuit unneeded celery task for search update
    if node.is_collection or node.archiving:
        need_update = False
    if need_update:
        node.update_search()
