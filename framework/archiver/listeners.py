from framework.tasks.handlers import enqueue_task
from framework.archiver.tasks import archive

from framework.archiver.utils import (
    link_archive_provider,
)

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def archive_node(src, dst, user):
    link_archive_provider(dst, user)
    enqueue_task(archive.si(src._id, dst._id, user._id))
