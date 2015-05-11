from framework.archiver.tasks import archive

from website.project import signals as project_signals


@project_signals.after_create_registration.connect
def archive_node(src, dst, user):
    dst.archiving = True
    task = archive(src._id, dst._id, user._id)
    dst.archive_task_id = task.task_id
    dst.save()
