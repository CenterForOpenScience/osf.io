import celery
import itertools

from framework.tasks import handlers

from website.archiver.tasks import archive
from website.archiver import utils as archiver_utils
from website.archiver import (
    ARCHIVER_UNCAUGHT_ERROR,
)
from website.archiver.decorators import fail_archive_on_error
from website.archiver import signals as archiver_signals

from website.project import signals as project_signals
from website.project import utils as project_utils

def node_and_primary_descendants(node):
    """Gets an iterator for a node and all of its visible descendants

    :param node Node: target Node
    """
    return itertools.chain([node], node.get_descendants_recursive(lambda n: n.primary))

@project_signals.after_create_registration.connect
def after_register(src, dst, user):
    """Blinker listener for registration initiations. Enqueqes a chain
    of archive tasks for the current node and its descendants

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    archiver_utils.before_archive(dst, user)
    if dst.root != dst:  # if not top-level registration
        return
    archive_tasks = [archive.si(job_pk=t.archive_job._id) for t in node_and_primary_descendants(dst)]
    handlers.enqueue_task(
        celery.chain(*archive_tasks)
    )

@project_signals.archive_callback.connect
@fail_archive_on_error
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When the tree of ArchiveJob
    instances is complete, proceed to send success or failure mails

    :param dst: registration Node
    """
    root = dst.root
    root_job = root.archive_job
    if not root_job.archive_tree_finished():
        return
    if root_job.sent:
        return
    root_job.sent = True
    root_job.save()
    if root_job.success:
        archiver_utils.archive_success(root, root.registered_user)
        if dst.pending_embargo:
            for contributor in root.active_contributors():
                project_utils.send_embargo_email(
                    root,
                    contributor,
                    urls=root_job.meta['embargo_urls'].get(contributor._id),
                )
        else:
            archiver_utils.send_archiver_success_mail(root)
        for node in node_and_primary_descendants(root):
            node.update_search()  # update search if public
    else:
        archiver_utils.handle_archive_fail(
            ARCHIVER_UNCAUGHT_ERROR,
            root.registered_from,
            root,
            root.registered_user,
            dst.archive_job.target_addons,
        )

@archiver_signals.archive_fail.connect
def archive_fail(dst, errors):
    reason = dst.archive_status
    root_job = dst.root.archive_job
    if root_job.sent:
        return
    root_job.sent = True
    root_job.save()
    archiver_utils.handle_archive_fail(
        reason,
        dst.root.registered_from,
        dst.root,
        dst.root.registered_user,
        errors
    )
