from website.project import signals
from framework.celery_tasks.handlers import enqueue_task


@signals.node_deleted.connect
def update_status_on_delete(node):
    from website.identifiers.tasks import update_doi_metadata_on_change

    for preprint in node.preprints.all():
        enqueue_task(update_doi_metadata_on_change.s(preprint._id, status='unavailable'))

    if node.get_identifier('doi'):
        enqueue_task(update_doi_metadata_on_change.s(node._id, status='unavailable'))
