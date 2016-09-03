from framework.celery_tasks import app as celery_app
from website.project import spam

@celery_app.task(ignore_results=True)
def on_node_updated(node_id, saved_fields, request_headers):
    from website.models import Node
    node = Node.load(node_id)

    is_spam = spam.check_node_for_spam(node, request_headers)

    if not is_spam:
        first_save = not node._is_loaded
        need_update = bool(node.SOLR_UPDATE_FIELDS.intersection(saved_fields))
        if not node.is_public:
            if first_save or 'is_public' not in saved_fields:
                need_update = False
        if node.is_collection or node.archiving:
            need_update = False
        if need_update:
            node.update_search()
