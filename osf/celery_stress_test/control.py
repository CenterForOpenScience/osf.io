"""Suite transitions serialize on the suite row, including cancellation and publication."""
from django.db import transaction
from django.utils import timezone

from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task


def finalize(suite):
    """Called with the suite row locked. Publication and all executions must finish."""
    if not suite.publishing_finished_at or suite.tasks.exclude(status__in=Task.TERMINAL_STATUSES).exists():
        return
    if suite.cancel_requested_at:
        suite.status = Suite.Status.CANCELLED
    elif suite.error or suite.tasks.filter(status__in=[Task.Status.FAILED, Task.Status.CANCELLED]).exists():
        suite.status = Suite.Status.FAILED
    else:
        suite.status = Suite.Status.COMPLETED
    suite.finished_at = timezone.now()
    suite.save(update_fields=['status', 'finished_at'])


def finish_publishing(suite_id, error=''):
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        if suite.publishing_finished_at:
            return
        suite.publishing_finished_at = timezone.now()
        suite.error = error[:4000]
        suite.status = Suite.Status.CANCELLING if suite.cancel_requested_at else Suite.Status.DRAINING
        suite.save(update_fields=['publishing_finished_at', 'error', 'status'])
        finalize(suite)


def finish_task(task_id, status, error='', runtime=None):
    # Always lock suite first, then update task, to avoid deadlocks with cancellation.
    suite_id = Task.objects.values_list('suite_id', flat=True).get(pk=task_id)
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        task = Task.objects.get(pk=task_id)
        if task.status in Task.TERMINAL_STATUSES:
            return
        now = timezone.now()
        task.status = Task.Status.CANCELLED if suite.cancel_requested_at else status
        task.finished_at = now
        task.runtime_seconds = runtime
        if runtime is None and task.started_at:
            task.runtime_seconds = max(0, (now - task.started_at).total_seconds())
        task.total_seconds = max(0, (now - task.submitted_at).total_seconds())
        task.error = error[:4000]
        task.save(update_fields=['status', 'finished_at', 'runtime_seconds', 'total_seconds', 'error'])
        finalize(suite)


def cancel_suite(suite_id, user, app):
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        if not suite.is_active:
            return suite, None
        if not suite.cancel_requested_at:
            suite.cancel_requested_at = timezone.now()
            suite.cancelled_by = user
        suite.status = Suite.Status.CANCELLING
        # A coordinator not yet started will never claim a cancelled suite.
        if suite.started_at is None:
            suite.publishing_finished_at = timezone.now()
        suite.save(update_fields=['cancel_requested_at', 'cancelled_by', 'status', 'publishing_finished_at'])
        suite.tasks.filter(status=Task.Status.QUEUED).update(
            status=Task.Status.CANCELLED, finished_at=timezone.now(),
        )
        finalize(suite)
    # Cooperative database checks remain authoritative if broker revocation fails.
    try:
        app.control.revoke(str(suite.coordinator_task_id), terminate=False)
        ids = suite.tasks.filter(status=Task.Status.CANCELLED).values_list('id', flat=True)
        batch = []
        for task_id in ids.iterator(chunk_size=500):
            batch.append(str(task_id))
            if len(batch) == 500:
                app.control.revoke(batch, terminate=False)
                batch = []
        if batch:
            app.control.revoke(batch, terminate=False)
    except Exception:
        return suite, 'Cancellation saved. Broker revocation failed; tasks will stop when they observe the cancellation.'
    return suite, None
