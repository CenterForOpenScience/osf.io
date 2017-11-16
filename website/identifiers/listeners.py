from website.project import signals
from framework.celery_tasks.handlers import enqueue_task


@signals.node_deleted.connect
def update_status_on_delete(node):
    from website.preprints.tasks import update_ezid_metadata_on_change

    for preprint in node.preprints.all():
        enqueue_task(update_ezid_metadata_on_change.s(preprint, status='unavailable'))

    if node.get_identifier('doi'):
        enqueue_task(update_ezid_metadata_on_change.s(node, status='unavailable'))
