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
    targets = itertools.chain([dst], dst.get_descendants_recursive(lambda n: n.primary))
    archive_tasks = [archive.si(job_pk=t.archive_job._id) for t in targets]
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
    if not root_job.archive_tree_finished():
        return
    if root_job.sent:
        return
    root_job.sent = True
    root_job.save()
    if root_job.success:
        archiver_utils.archive_success(dst, dst.registered_user)
        if dst.pending_embargo:
            for contributor in dst.contributors:
                if contributor.is_active:
                    project_utils.send_embargo_email(
                        dst.root,
                        contributor,
                        urls=root_job.meta['embargo_urls'].get(contributor._id),
                    )
        else:
            archiver_utils.send_archiver_success_mail(dst.root)
    else:
        archiver_utils.handle_archive_fail(
            ARCHIVER_UNCAUGHT_ERROR,
            dst.root.registered_from,
            dst.root,
            dst.root.registered_user,
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
