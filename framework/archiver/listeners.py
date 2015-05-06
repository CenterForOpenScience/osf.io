from framework.archiver import ArchiveTask

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def _before_register_node(src, dst, user):
    src.archiving = True
    task = ArchiveTask().delay(src._id, dst._id, user._id)
    src.archive_task_id = task.task_id
