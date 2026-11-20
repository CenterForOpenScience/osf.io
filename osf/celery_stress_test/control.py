"""Suite transitions serialize on the suite row, including cancellation and publication."""
import time

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .load import load_progress, sync_load_progress
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task


def scenario_progress(suite):
    fields = {'total': Count('id'), 'published': Count('id', filter=Q(published_at__isnull=False))}
    fields.update({status: Count('id', filter=Q(status=status)) for status in Task.Status.values})
    summary = suite.tasks.aggregate(**fields)
    summary['active'] = summary['queued'] + summary['running'] + summary['retrying']
    return summary


def sync_progress(suite):
    if suite.config.get('suite_type', 'load') == 'load':
        return sync_load_progress(suite)
    summary = scenario_progress(suite)
    Suite.objects.filter(pk=suite.id, finished_at__isnull=True).update(
        results={**suite.results, 'progress': summary}, heartbeat_at=timezone.now())
    return summary


def wait_for_tasks(suite_id, publication_error=None):
    """Suite handlers poll results and drain already-sent tasks after publication errors."""
    if publication_error is not None:
        Suite.objects.filter(pk=suite_id, finished_at__isnull=True).update(error=str(publication_error)[:4000])
    Suite.objects.filter(pk=suite_id, finished_at__isnull=True, publishing_finished_at__isnull=True).update(
        publishing_finished_at=timezone.now())
    Suite.objects.filter(pk=suite_id, finished_at__isnull=True, cancel_requested_at__isnull=True).update(
        status=Suite.Status.DRAINING)
    suite = Suite.objects.get(pk=suite_id)
    while True:
        suite.refresh_from_db()
        if suite.finished_at:
            break
        if suite.cancel_requested_at:
            suite.tasks.filter(status__in=[Task.Status.QUEUED, Task.Status.RETRYING]).update(
                status=Task.Status.CANCELLED, finished_at=timezone.now())
        if sync_progress(suite)['active'] == 0:
            break
        remaining = (suite.deadline_at - timezone.now()).total_seconds()
        if remaining <= 0:
            error = 'Execution deadline exceeded; tasks or callbacks did not finish.'
            suite.tasks.exclude(status__in=Task.TERMINAL_STATUSES).update(
                status=Task.Status.FAILED, finished_at=timezone.now(), error=error)
            if publication_error is not None:
                error = f'Publication failed: {publication_error}; {error}'
            raise RuntimeError(error) from publication_error
        time.sleep(min(5, remaining))
    if publication_error is not None:
        raise publication_error


def finalize(suite):
    """Called with the suite row locked. Publication and all executions must finish."""
    if suite.finished_at:
        return
    if not suite.publishing_finished_at or suite.tasks.exclude(status__in=Task.TERMINAL_STATUSES).exists():
        return
    if suite.config.get('suite_type', 'load') == 'load':
        suite.results = {'load': load_progress(suite.id, len(suite.config.get('workloads', [])))}
    else:
        suite.results = {**suite.results, 'progress': scenario_progress(suite)}
    if suite.cancel_requested_at:
        suite.status = Suite.Status.CANCELLED
    elif suite.config.get('suite_type', 'load') != 'load':
        from .scenarios import evaluate
        results, passed = evaluate(suite)
        suite.results = {**suite.results, **results}
        suite.verdict = Suite.Verdict.PASSED if passed and not suite.error else Suite.Verdict.FAILED
        suite.status = Suite.Status.COMPLETED if suite.verdict == Suite.Verdict.PASSED else Suite.Status.FAILED
    elif suite.error or suite.tasks.filter(status__in=[Task.Status.FAILED, Task.Status.CANCELLED]).exists():
        suite.status = Suite.Status.FAILED
    else:
        suite.status = Suite.Status.COMPLETED
    if suite.cancel_requested_at:
        suite.verdict = Suite.Verdict.CANCELLED
    elif suite.config.get('suite_type', 'load') == 'load':
        suite.verdict = Suite.Verdict.PASSED if suite.status == Suite.Status.COMPLETED else Suite.Verdict.FAILED
    suite.finished_at = timezone.now()
    suite.save(update_fields=['status', 'finished_at', 'verdict', 'results'])


def finish_publishing(suite_id, error=''):
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        if suite.finished_at:
            return
        suite.publishing_finished_at = suite.publishing_finished_at or timezone.now()
        suite.error = (error or suite.error)[:4000]
        suite.status = Suite.Status.CANCELLING if suite.cancel_requested_at else Suite.Status.DRAINING
        suite.save(update_fields=['publishing_finished_at', 'error', 'status'])
        finalize(suite)


def finish_task(task_id, status, error='', runtime=None, result=None):
    """Finish one scenario task and its attempt, without locking/updating its suite."""
    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=task_id)
        suite = task.suite
        if suite.finished_at or task.status in Task.TERMINAL_STATUSES:
            return
        now = timezone.now()
        task.status = Task.Status.CANCELLED if suite.cancel_requested_at else status
        task.finished_at = now
        task.runtime_seconds = runtime
        if runtime is None and task.started_at:
            task.runtime_seconds = max(0, (now - task.started_at).total_seconds())
        task.total_seconds = max(0, (now - task.submitted_at).total_seconds())
        task.error = error[:4000]
        if result is not None:
            task.observations['result'] = result
        task.save(update_fields=['status', 'finished_at', 'runtime_seconds', 'total_seconds', 'error', 'observations'])
        task.attempts.filter(finished_at__isnull=True).update(
            finished_at=now, outcome=task.status, error=task.error)


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
        suite.tasks.filter(status__in=[Task.Status.QUEUED, Task.Status.RETRYING]).update(
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
        return suite, 'Cancellation saved. Broker revocation failed; load payloads expire at their deadline and running work finishes naturally.'
    return suite, None
