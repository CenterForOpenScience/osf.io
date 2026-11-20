import time
from datetime import timedelta

from django.core.management import call_command

from celery import shared_task
from celery.signals import task_failure, task_revoked
from django.db import transaction
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task
from .control import finish_publishing, finish_task
from .load import run_load, finish_load_task
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
        if suite.deadline_at is None:
            suite.deadline_at = suite.created_at + timedelta(seconds=config.get('deadline_seconds',
                config.get('total_duration', 0) + config.get('drain_timeout', 120) + 60))
            suite.save(update_fields=['deadline_at'])

    error = ''
    try:
        if config.get('suite_type', 'load') == 'load':
            run_load(suite_id, config)
        else:
            publish_scenarios(suite_id, config)
    except Exception as exc:
        error = str(exc)
        raise
    finally:
        finish_publishing(suite_id, error)


@shared_task(bind=True, name='stress_testing.simulated_workload', ignore_result=True, store_errors_even_if_ignored=False)
def simulated_workload(self, mode='io', io_seconds=1.0, cpu_iterations=1_000_000,
                       test_task_id=None, sent_at=None, deadline=None):
    """Save task timings/outcome directly; the coordinator synchronizes suite progress."""
    received = timezone.now()
    started = time.monotonic()
    if deadline is not None and received.timestamp() >= deadline:
        if test_task_id:
            finish_load_task(test_task_id, Task.Status.FAILED, 'Task execution deadline exceeded.')
        return
    if test_task_id:
        claimed = Task.objects.filter(pk=test_task_id, status=Task.Status.QUEUED,
                                      suite__finished_at__isnull=True, suite__cancel_requested_at__isnull=True).update(
            status=Task.Status.RUNNING, started_at=received, worker=self.request.hostname or '',
            wait_seconds=max(0, received.timestamp() - (sent_at or received.timestamp())))
        if not claimed:
            Task.objects.filter(pk=test_task_id, status=Task.Status.QUEUED).update(
                status=Task.Status.CANCELLED, finished_at=timezone.now())
            return
    status, error = Task.Status.SUCCEEDED, ''
    try:
        if mode not in {'io', 'cpu', 'mixed'}:
            raise ValueError(f'Unsupported workload mode: {mode}')
        if not 0 <= io_seconds <= 30 or not 1 <= cpu_iterations <= 100_000_000:
            raise ValueError('Workload arguments exceed supported bounds.')
        if mode in {'io', 'mixed'}:
            time.sleep(io_seconds)
        if mode in {'cpu', 'mixed'}:
            sum(i * i for i in range(cpu_iterations))
    except Exception as exc:
        status, error = Task.Status.FAILED, str(exc)
        raise
    finally:
        if test_task_id:
            finish_load_task(test_task_id, status, error, runtime_seconds=time.monotonic() - started,
                             total_seconds=max(0, timezone.now().timestamp() - (sent_at or received.timestamp())))


def record_test_failure(sender=None, task_id=None, exception=None, **kwargs):
    # Covers failures reported by the worker parent, including hard timeouts and
    # lost children, where the task's finally block cannot run.
    if sender and sender.name == 'stress_testing.simulated_workload':
        finish_load_task(task_id, Task.Status.FAILED, str(exception))
    elif sender and sender.name == 'stress_testing.scenario':
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
    if task_name == 'stress_testing.scenario' and Task.objects.filter(pk=request.id).exists():
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


@shared_task(name='stress_testing.cleanup_history')
def cleanup_history():
    call_command('cleanup_celery_tests')
