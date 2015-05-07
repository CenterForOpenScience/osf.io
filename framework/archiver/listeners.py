from framework.archiver.tasks import archive

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def before_register_node(src, dst, user):
    src.archiving = True
    task = archive.delay(src._id, dst._id, user._id)
    src.archive_task_id = task.task_id
    src.save()
