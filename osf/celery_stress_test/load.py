"""Rate-limited publication and periodic progress sync from task result rows."""
import time

from django.db.models import Count, Q
from django.utils import timezone

from framework.celery_tasks import app
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task


def load_progress(suite_id, workload_count):
    """Count task outcomes for the suite and each configured workload."""
    fields = {'total': Count('id'), 'published': Count('id', filter=Q(published_at__isnull=False))}
    fields.update({status: Count('id', filter=Q(status=status)) for status in Task.Status.values})
    counts = list(Task.objects.filter(suite_id=suite_id).values('workload_index').annotate(**fields))
    workloads = [{key: 0 for key in fields} for _ in range(workload_count)]
    for row in counts:
        if row['workload_index'] is not None and row['workload_index'] < workload_count:
            workloads[row['workload_index']] = {key: row[key] for key in fields}
    summary = {key: sum(row[key] for row in workloads) for key in fields}
    summary['active'] = summary['queued'] + summary['running'] + summary['retrying']
    summary['workloads'] = workloads
    return summary


def sync_load_progress(suite):
    """Save the latest workload counters and coordinator heartbeat."""
    summary = load_progress(suite.id, len(suite.config['workloads']))
    Suite.objects.filter(pk=suite.id, finished_at__isnull=True).update(
        results={'load': summary}, heartbeat_at=timezone.now())
    return summary


def finish_load_task(task_id, status, error='', **timings):
    """Record a load task outcome unless the task is already terminal."""
    Task.objects.filter(pk=task_id).exclude(status__in=Task.TERMINAL_STATUSES).update(
        status=status, error=error[:4000], finished_at=timezone.now(), **timings)


def run_load(suite_id, config):
    """Publish paced load tasks, then wait for published work even if a send failed."""
    # Control imports the load progress helpers; defer this import to avoid a cycle.
    from .control import wait_for_tasks

    suite = Suite.objects.get(pk=suite_id)
    publication_error = None
    try:
        publish(suite, config)
    except Exception as exc:
        publication_error = exc
    finally:
        sync_load_progress(suite)
    wait_for_tasks(suite_id, publication_error)


def publish(suite, config):
    """Publish workloads in rotation using per-workload rates and a shared rate cap."""
    started = time.monotonic()
    next_workload_due = [started] * len(config['workloads'])
    next_suite_due = started
    last_check = started - 5  # force immediate progress sync on first iteration
    rotation_start_index = 0
    while time.monotonic() - started < config['total_duration']:
        now = time.monotonic()
        # run periodic progress sync and deadline check at most once every 5 seconds
        if now - last_check >= 5:
            suite.refresh_from_db()
            if suite.finished_at or suite.cancel_requested_at:
                return
            if timezone.now() >= suite.deadline_at:
                raise RuntimeError('Load deadline exceeded while publishing.')
            sync_load_progress(suite)
            last_check = now
        now = time.monotonic()
        if now < next_suite_due:
            time.sleep(min(next_suite_due - now, .01))
            continue
        for offset in range(len(next_workload_due)):
            index = (rotation_start_index + offset) % len(next_workload_due)
            if now < next_workload_due[index]:
                continue
            workload = config['workloads'][index]

            task = Task.objects.create(suite_id=suite.id, workload_index=index, queue=workload['queue'])
            try:
                app.send_task('stress_testing.simulated_workload', task_id=str(task.id),
                              kwargs={'mode': workload['mode'], 'io_seconds': workload.get('io_seconds') or 0,
                                      'cpu_iterations': workload.get('cpu_iterations') or 1000000,
                                      'test_task_id': str(task.id), 'sent_at': task.submitted_at.timestamp(),
                                      'deadline': suite.deadline_at.timestamp()},
                              queue=workload['queue'], expires=suite.deadline_at, retry=False, ignore_result=True)
            except Exception as exc:
                finish_load_task(task.id, Task.Status.FAILED, f'Publication failed: {exc}')
                raise
            Task.objects.filter(pk=task.id).update(published_at=timezone.now())
            next_workload_due[index] = now + 1 / workload['rate']
            next_suite_due = now + 1 / config['max_total_rate']
            rotation_start_index = (index + 1) % len(next_workload_due)
            break
        else:
            time.sleep(.001)
