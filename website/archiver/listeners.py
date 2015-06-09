import celery
from itertools import chain

from framework.tasks.handlers import enqueue_task

from website.archiver.tasks import (
    archive,
)
from website.archiver import utils as archiver_utils
from website.archiver import (
    ARCHIVER_UNCAUGHT_ERROR
)

from website.project import signals as project_signals
from website.project import utils as project_utils

@project_signals.after_create_registration.connect
def after_register(src, dst, user):
    """Blinker listener for registration initiations. Enqueqes an archive task

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    archiver_utils.before_archive(dst, user)
    if dst.root != dst:  # if not top-level registration
        return
    targets = chain([dst], dst.get_descendants_recursive())
    archive_tasks = [archive.si(t.registered_from._id, t._id, user._id) for t in targets]
    enqueue_task(
        celery.chain(*archive_tasks)
    )

@project_signals.archive_callback.connect
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When no tasks are
    pending, either fail the registration or send a success email

    :param dst: registration Node
    """
    if not dst.archive_log.done:
        return
    if dst.archive_log.success:
        if dst.pending_embargo:
            for contributor in dst.contributors:
                project_utils.send_embargo_email(dst, contributor)
        else:
            archiver_utils.send_archiver_success_mail(dst.root)
    else:
        archiver_utils.handle_archive_fail(
            ARCHIVER_UNCAUGHT_ERROR,
            dst.registered_from,
            dst,
            dst.owner,
            dst.archive_log.target_addons,
        )
