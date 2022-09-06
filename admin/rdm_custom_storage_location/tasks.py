from __future__ import absolute_import

from celery.contrib.abortable import AbortableTask

from admin.rdm_custom_storage_location.export_data.views import restore
from admin.rdm_custom_storage_location.export_data.views.export import (
    export_data_process,
    export_data_rollback_process
)
from framework.celery_tasks import app as celery_app

__all__ = [
    'run_restore_export_data_process',
    'run_restore_export_data_rollback_process',
    'run_export_data_process',
    'run_export_data_rollback_process',
]


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_restore_export_data_process(self, cookies, export_id, destination_id, export_data_restore_id):
    return restore.restore_export_data_process(self, cookies, export_id, destination_id, export_data_restore_id)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_restore_export_data_rollback_process(self, cookies, export_id, destination_id, export_data_restore_id, process_step):
    return restore.restore_export_data_rollback_process(self, cookies, export_id, destination_id, export_data_restore_id, process_step)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_process(self, cookies, export_data_id, **kwargs):
    export_data_process(self, cookies, export_data_id, **kwargs)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_rollback_process(self, cookies, export_data_id, **kwargs):
    export_data_rollback_process(cookies, export_data_id, **kwargs)
