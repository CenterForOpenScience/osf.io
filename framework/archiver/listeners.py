from celery.contrib import rdb

from framework.archiver import ArchiveNodeTask

from website.project import signals as project_signals

@project_signals.after_create_registration.connect
def _before_register_node(src, dst, user):
    ArchiveNodeTask().delay(src, dst, user)
