# -*- coding: utf-8 -*-
from __future__ import absolute_import

from celery.contrib.abortable import AbortableTask

from admin.rdm_custom_storage_location.export_data.views import export
from admin.rdm_custom_storage_location.export_data.views import restore
from framework.celery_tasks import app as celery_app

__all__ = [
    'run_export_data_process',
    'run_export_data_rollback_process',
    'run_restore_export_data_process',
    'run_restore_export_data_rollback_process',
]


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_process(
        self, cookies, export_data_id, location_id, source_id, **kwargs):
    return export.export_data_process(
        self, cookies, export_data_id, location_id, source_id, **kwargs)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_export_data_rollback_process(
        self, cookies, export_data_id, location_id, source_id, **kwargs):
    return export.export_data_rollback_process(
        self, cookies, export_data_id, location_id, source_id, **kwargs)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_restore_export_data_process(
        self, cookies, export_id, export_data_restore_id, list_project_id, **kwargs):
    return restore.restore_export_data_process(
        self, cookies, export_id, export_data_restore_id, list_project_id, **kwargs)


@celery_app.task(bind=True, base=AbortableTask, track_started=True)
def run_restore_export_data_rollback_process(
        self, cookies, export_id, export_data_restore_id, process_step, **kwargs):
    return restore.restore_export_data_rollback_process(
        self, cookies, export_id, export_data_restore_id, process_step, **kwargs)
