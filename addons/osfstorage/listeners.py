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
        Guid = apps.get_model('osf.Guid')
        OsfStorageFolder = apps.get_model('osf.OsfStorageFolder')
        guid = Guid.objects.filter(_id=node_id).values('content_type_id', 'object_id').get()
        OsfStorageFolder.objects.get(
            target_object_id=guid['object_id'],
            target_content_type=guid['content_type_id'],
            is_root=True
        ).delete(save=True)
