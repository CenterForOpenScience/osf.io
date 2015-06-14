import celery
import itertools

from framework.tasks import handlers

from website.archiver.tasks import (
    archive,
)
from website.archiver import utils as archiver_utils
from website.archiver import (
    ARCHIVER_UNCAUGHT_ERROR,
)
from website.archiver.decorators import fail_archive_on_error

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
    targets = itertools.chain([dst], dst.get_descendants_recursive())
    archive_tasks = [archive.si(t.archive_job._id) for t in targets if t.primary]
    handlers.enqueue_task(
        celery.chain(*archive_tasks)
    )

@project_signals.archive_callback.connect
@fail_archive_on_error
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When no tasks are
    pending, either fail the registration or send a success email

    :param dst: registration Node
    """
    root_job = dst.root.archive_job
    if root_job.sent or not root_job.archive_tree_finished():
        return
    root_job.sent = True
    root_job.save()
    if dst.archive_job.success:
        if dst.pending_embargo:
            for contributor in dst.contributors:
                project_utils.send_embargo_email(
                    dst.root,
                    contributor,
                    urls=root_job.meta.get('embargo_urls')
                )
        else:
            archiver_utils.send_archiver_success_mail(dst.root)
    else:
        archiver_utils.handle_archive_fail(
            ARCHIVER_UNCAUGHT_ERROR,
            dst.registered_from,
            dst,
            dst.registered_user,
            dst.archive_job.target_addons,
        )
