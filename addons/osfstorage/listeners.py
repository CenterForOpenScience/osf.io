"""
Listens for actions to be done to OSFstorage file nodes specifically.
"""
from django.apps import apps

from website.project.signals import contributor_removed, node_deleted
from framework.celery_tasks import app
from framework.celery_tasks.handlers import enqueue_task


@contributor_removed.connect
def checkin_files_by_user(node, user):
    """ Listens to a contributor being removed to check in all of their files
    """
    node.files.filter(checkout=user).update(checkout=None)


@node_deleted.connect
def delete_files(node):
    enqueue_task(delete_files_task.s(node._id))


@app.task(max_retries=5, default_retry_delay=60)
def delete_files_task(node_id):
    AbstractNode = apps.get_model('osf.AbstractNode')
    node = AbstractNode.load(node_id)
    for osfstorage_file in node.files.all():
        osfstorage_file.delete()
