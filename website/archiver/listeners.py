import celery
from itertools import chain

from framework.tasks.handlers import enqueue_task

from website.archiver.tasks import (
    archive,
)
from website.archiver.utils import (
    handle_archive_fail,
)
from website.archiver import utils as archiver_utils
from website.archiver import (
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_NETWORK_ERROR,
)

from website.project import signals as project_signals
from website.project import utils as project_utils

@project_signals.after_create_registration.connect
def archive_node(src, dst, user):
    """Blinker listener for registration initiations. Enqueqes an archive task

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    targets = chain([dst], dst.get_descendants_recursive())
    archive_tasks = [archive.si(t.registered_from._id, t._id, user._id) for t in targets]
    enqueue_task(
        celery.chain(*archive_tasks)
    )

def archive_node_finished(node):
    pending = [value for value in node.archived_providers.values() if value['status'] not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)]
    return False if pending else True

def archive_tree_finished(node, dir=None):
    if archive_node_finished(node):
        if not dir:
            up_ = archive_tree_finished(node.parent_node, dir='up') if node.parent_node else True
            down_ = len([ret for ret in [archive_tree_finished(child, dir='down') for child in node.nodes] if ret]) if len(node.nodes) else True
            return up_ and down_
        if dir == 'up':
            return archive_tree_finished(node.parent_node, dir='up') if node.parent_node else True
        elif dir == 'down':
            return len([ret for ret in [archive_tree_finished(child, dir='down') for child in node.nodes]]) if len(node.nodes) else True
    return False

@project_signals.archive_callback.connect
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When no tasks are
    pending, either fail the registration or send a success email

    :param dst: registration Node
    """
    if not dst.archiving:
        return
    if archive_node_finished(dst):
        dst.archiving = False
        dst.save()
    if archive_tree_finished(dst):
        dst.archiving = False
        dst.save()
        if ARCHIVER_FAILURE in [value['status'] for value in dst.archived_providers.values()]:
            handle_archive_fail(
                ARCHIVER_NETWORK_ERROR,
                dst.registered_from,
                dst,
                dst.creator,
                dst.archived_providers
            )
        else:
            if dst.pending_embargo:
                for contributor in dst.contributors:
                    project_utils.send_embargo_email(dst, contributor)
            else:
                archiver_utils.send_archiver_success_mail(dst)
