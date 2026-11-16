import time

from celery import shared_task, current_app
from celery.signals import task_failure, task_revoked
from django.db import transaction
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task
from .control import finish_publishing, finish_task
from .scenarios import publish_scenarios  # Registers scenario tasks for signal handlers.


@shared_task(name='stress_testing.start_celery_stress_test')
def start_celery_stress_test(suite_id):
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        if suite.status != Suite.Status.QUEUED or suite.cancel_requested_at:
            return
        suite.status = Suite.Status.RUNNING
        suite.started_at = suite.heartbeat_at = timezone.now()
        suite.save(update_fields=['status', 'started_at', 'heartbeat_at'])
        config = suite.config

    error = ''
    try:
        if config.get('suite_type', 'load') == 'load':
            _publish_workloads(suite_id, config)
        else:
            publish_scenarios(suite_id, config)
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        finish_publishing(suite_id, error)


def _publish_workloads(suite_id, config):
    workloads = config['workloads']
    if not workloads:
        raise ValueError('At least one workload is required.')
    started_at = time.monotonic()
    next_run = [started_at] * len(workloads)
    next_global_run = started_at
    last_check = started_at - 1
    start_index = 0
    while time.monotonic() - started_at < config['total_duration']:
        now = time.monotonic()
        if now - last_check >= 0.25:
            # Also serves as a liveness signal while waiting between publications.
            if not Suite.objects.filter(pk=suite_id, cancel_requested_at__isnull=True).update(heartbeat_at=timezone.now()):
                return
            last_check = now
        if now < next_global_run:
            time.sleep(min(next_global_run - now, 0.01))
            continue
        published = False
        for offset in range(len(workloads)):
            index = (start_index + offset) % len(workloads)
            workload = workloads[index]
            if now < next_run[index]:
                continue
            with transaction.atomic():
                suite = Suite.objects.select_for_update().get(pk=suite_id)
                if suite.cancel_requested_at:
                    return
                task = Task.objects.create(suite=suite, workload_index=index, queue=workload['queue'])
            # The row is committed before delivery. If cancellation races with send,
            # the consumer sees its cancelled row and skips the payload.
            try:
                current_app.send_task(
                    'stress_testing.simulated_workload',
                    task_id=str(task.id),
                    kwargs={
                        'test_task_id': str(task.id),
                        'mode': workload['mode'],
                        'io_seconds': workload.get('io_seconds') or 0,
                        'cpu_iterations': workload.get('cpu_iterations') or 1_000_000,
                    },
                    queue=workload['queue'],
                    retry=False,
                )
            except Exception as exc:
                finish_task(task.id, Task.Status.FAILED, f'Publication failed: {exc}')
                raise
            Task.objects.filter(pk=task.id).update(published_at=timezone.now())
            next_run[index] = now + 1 / workload['rate']
            next_global_run = now + 1 / config['max_total_rate']
            start_index = (index + 1) % len(workloads)
            published = True
            break
        if not published:
            time.sleep(max(0.001, min(min(next_run) - now, 0.01)))


class WorkloadCancelled(Exception):
    pass


@shared_task(bind=True, name='stress_testing.simulated_workload')
def simulated_workload(self, mode='io', io_seconds=1.0, cpu_iterations=1_000_000, test_task_id=None):
    if test_task_id:
        suite_id = Task.objects.values_list('suite_id', flat=True).get(pk=test_task_id)
        with transaction.atomic():
            suite = Suite.objects.select_for_update().get(pk=suite_id)
            task = Task.objects.get(pk=test_task_id)
            if task.status != Task.Status.QUEUED:
                return
            if suite.cancel_requested_at:
                finish_task(task.id, Task.Status.CANCELLED)
                return
            task.status = Task.Status.RUNNING
            task.started_at = timezone.now()
            task.worker = self.request.hostname or ''
            task.wait_seconds = max(0, (task.started_at - task.submitted_at).total_seconds())
            task.save(update_fields=['status', 'started_at', 'worker', 'wait_seconds'])

    started = time.monotonic()
    last_check = started - 1

    def check_cancelled():
        nonlocal last_check
        now = time.monotonic()
        if test_task_id and now - last_check >= 0.25:
            if Suite.objects.filter(pk=suite_id, cancel_requested_at__isnull=False).exists():
                raise WorkloadCancelled()
            last_check = now

    status, error = Task.Status.SUCCEEDED, ''
    try:
        if mode not in {'io', 'cpu', 'mixed'}:
            raise ValueError(f'Unsupported workload mode: {mode}')
        if not 0 <= io_seconds <= 30:
            raise ValueError('io_seconds must be between 0 and 30')
        if not 1 <= cpu_iterations <= 100_000_000:
            raise ValueError('cpu_iterations must be between 1 and 100,000,000')
        check_cancelled()
        if mode in {'io', 'mixed'}:
            until = time.monotonic() + io_seconds
            while time.monotonic() < until:
                check_cancelled()
                time.sleep(min(0.1, max(0, until - time.monotonic())))
        if mode in {'cpu', 'mixed'}:
            result = 0
            for start in range(0, cpu_iterations, 10_000):
                check_cancelled()
                for i in range(start, min(start + 10_000, cpu_iterations)):
                    result += i * i
    except WorkloadCancelled:
        status = Task.Status.CANCELLED
    except Exception as exc:
        status, error = Task.Status.FAILED, str(exc)
        raise
    finally:
        if test_task_id:
            finish_task(test_task_id, status, error, runtime=time.monotonic() - started)


def record_test_failure(sender=None, task_id=None, exception=None, **kwargs):
    # Covers failures reported by the worker parent, including hard timeouts and
    # lost children, where the task's finally block cannot run.
    if sender and sender.name in ('stress_testing.simulated_workload', 'stress_testing.scenario'):
        if Task.objects.filter(pk=task_id).exists():
            finish_task(task_id, Task.Status.FAILED, str(exception))
    elif sender and sender.name == 'stress_testing.start_celery_stress_test':
        suite = Suite.objects.filter(coordinator_task_id=task_id).first()
        if suite:
            finish_publishing(suite.id, str(exception))


def record_test_revocation(sender=None, request=None, **kwargs):
    if request is None:
        return
    # Parent-process revocation may supply a Context with task, not name.
    task_name = getattr(sender, 'name', None) or getattr(request, 'task', None) or getattr(request, 'name', None)
    if task_name in ('stress_testing.simulated_workload', 'stress_testing.scenario') and Task.objects.filter(pk=request.id).exists():
        finish_task(request.id, Task.Status.CANCELLED, 'Task revoked.')
    elif task_name == 'stress_testing.start_celery_stress_test':
        suite = Suite.objects.filter(coordinator_task_id=request.id).first()
        if suite:
            finish_publishing(suite.id, '' if suite.cancel_requested_at else 'Coordinator revoked.')


@celery_app.on_after_finalize.connect
def register_test_signal_handlers(sender, **kwargs):
    # Resolve shared tasks through the finalized app's registry, not their proxies.
    for task_name in (
        'stress_testing.simulated_workload',
        'stress_testing.scenario',
        'stress_testing.start_celery_stress_test',
    ):
        task = sender.tasks[task_name]
        task_failure.connect(
            record_test_failure, sender=task,
            dispatch_uid=f'{task_name}.record_test_failure',
        )
        task_revoked.connect(
            record_test_revocation, sender=task,
            dispatch_uid=f'{task_name}.record_test_revocation',
        )


# Admin task discovery can import this module after the app has been finalized.
if celery_app.finalized:
    register_test_signal_handlers(sender=celery_app)
