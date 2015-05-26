from framework.tasks.handlers import enqueue_task

from website.archiver.tasks import archive, send_success_message
from website.archiver.utils import (
    link_archive_provider,
    handle_archive_fail,
)
from website.archiver import (
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVE_COPY_FAIL,
)

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def archive_node(src, dst, user):
    """Blinker listener for registration initiations. Enqueqes an archive task

    :param src: Node being registered
    :param dst: registration Node
    :param user: registration initiator
    """
    link_archive_provider(dst, user)
    enqueue_task(archive.si(src._id, dst._id, user._id))

@project_signals.archive_callback.connect
def archive_callback(dst):
    """Blinker listener for updates to the archive task. When no tasks are
    pending, either fail the registration or send a success email

    :param dst: registration Node
    """
    pending = [value for value in dst.archived_providers.values() if value['status'] not in (ARCHIVER_SUCCESS, ARCHIVER_FAILURE)]
    if not pending:
        dst.archiving = False
        dst.save()
        if ARCHIVER_FAILURE in [value['status'] for value in dst.archived_providers.values()]:
            handle_archive_fail(
                ARCHIVE_COPY_FAIL,
                dst.registered_from,
                dst,
                dst.creator,
                dst.archived_providers
            )
        else:
            send_success_message.delay(dst._id)
