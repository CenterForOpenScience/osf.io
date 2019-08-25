"""
Listens for actions to be done to OSFstorage file nodes specifically.
"""
from django.apps import apps
from django.db import transaction

from website.project.signals import contributor_removed, node_deleted
from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import enqueue_postcommit_task


@contributor_removed.connect
def checkin_files_by_user(node, user):
    """ Listens to a contributor or group member being removed to check in all of their files
    """
    enqueue_postcommit_task(checkin_files_task, (node._id, user._id, ), {}, celery=True)


@app.task(max_retries=5, default_retry_delay=60)
def checkin_files_task(node_id, user_id):
    with transaction.atomic():
        AbstractNode = apps.get_model('osf.AbstractNode')
        Preprint = apps.get_model('osf.Preprint')
        Guid = apps.get_model('osf.Guid')
        OSFUser = apps.get_model('osf.OSFUser')

        node = Guid.load(node_id).referent
        assert isinstance(node, (AbstractNode, Preprint))
        user = OSFUser.load(user_id)

        # If user doesn't have any permissions through their OSF group or through contributorship,
        # check their files back in
        if not node.is_contributor_or_group_member(user):
            node.files.filter(checkout=user).update(checkout=None)


@node_deleted.connect
def delete_files(node):
    enqueue_postcommit_task(delete_files_task, (node._id, ), {}, celery=True)


@app.task(max_retries=5, default_retry_delay=60)
def delete_files_task(node_id):
    with transaction.atomic():
        AbstractNode = apps.get_model('osf.AbstractNode')
        node = AbstractNode.objects.get(guids___id=node_id)
        node.root_folder.delete(save=True)
