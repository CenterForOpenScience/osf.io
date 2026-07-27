import celery

from framework.celery_tasks import handlers

from website.archiver import utils as archiver_utils
from website.archiver import signals as archiver_signals

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def after_register(src, dst, user):
    """Blinker listener for registration initiations. Enqueues a chain
    of archive tasks for the current node and its descendants

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    # Prevent circular import with app.py
    from website.archiver import tasks
    archiver_utils.before_archive(dst, user)
    if dst.root != dst:  # if not top-level registration
        return
    archive_tasks = [tasks.archive(job_pk=t.archive_job._id) for t in dst.node_and_primary_descendants()]
    handlers.enqueue_task(
        celery.chain(archive_tasks)
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
