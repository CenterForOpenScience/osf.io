"""Bounded synthetic scenarios using real Celery retries and canvas primitives."""
from datetime import timedelta

from celery import chain, chord, group, shared_task
from celery.exceptions import Ignore
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task, CeleryTestTaskAttempt as Attempt
from .control import finish_task, wait_for_tasks


def signature(task):
    """Build a Celery signature with the stored task ID and target queue."""
    return scenario_task.s(test_task_id=str(task.id)).set(task_id=str(task.id), queue=task.queue)


def publish_scenarios(suite_id, config):
    """Store expected outcomes, submit the Celery canvas, and wait for its tasks."""
    with transaction.atomic():
        suite = Suite.objects.select_for_update().get(pk=suite_id)
        if suite.cancel_requested_at:
            return
        suite.deadline_at = suite.deadline_at or timezone.now() + timedelta(seconds=config['deadline_seconds'])
        suite.save(update_fields=['deadline_at'])

        def create_scenario(name, **expected):
            return Task.objects.create(suite=suite, queue=config['queue'], scenario=name, expected=expected)

        if config['suite_type'] == 'retry':
            retry_limit = config['max_retries']
            failures = config.get('transient_failures', 2)
            scenario_tasks = []
            for index in range(config.get('tasks_per_scenario', 1)):
                scenario_tasks.extend([
                    create_scenario(f'transient.{index}', failures=failures, attempts=failures + 1, status='succeeded'),
                    create_scenario(f'exhausted.{index}', failures=retry_limit + 1, attempts=retry_limit + 1, status='failed'),
                    create_scenario(f'non_retryable.{index}', failures=1, attempts=1, status='failed'),
                ])
            canvas = group(signature(task) for task in scenario_tasks)
        else:
            workflows = []
            for index in range(config.get('workflow_count', 1)):
                steps = [create_scenario(f'chain.{index}.{step_index}', value=step_index + 2, result=sum(range(2, step_index + 3)))
                         for step_index in range(config.get('chain_length', 2))]
                branches = [create_scenario(f'group.{index}.{step_index}', value=step_index, result=step_index)
                            for step_index in range(config.get('group_size', config.get('width', 3)))]
                chord_size = config.get('chord_size', config.get('width', 3))
                headers = [create_scenario(f'chord.{index}.{step_index}', value=step_index, result=step_index) for step_index in range(chord_size)]
                callback = create_scenario(f'callback.{index}', result=sum(range(chord_size)))
                workflows.extend([chain(*(signature(task) for task in steps)),
                                  group(signature(task) for task in branches),
                                  chord([signature(task) for task in headers], signature(callback))])
            canvas = group(workflows)
    # All control rows are committed before the canvas can be consumed.
    # If only part of the canvas is published, the deadline closes out steps that never run.
    publication_error = None
    try:
        canvas.apply_async()
        Task.objects.filter(suite_id=suite_id).update(published_at=timezone.now())
    except Exception as exc:
        publication_error = exc
    wait_for_tasks(suite_id, publication_error)


@shared_task(bind=True, name='stress_testing.scenario', ignore_result=False)
def scenario_task(self, previous=None, test_task_id=None):
    """Record an attempt and simulate a retry outcome or compute a workflow result."""
    attempt_number = self.request.retries + 1
    with transaction.atomic():
        task = Task.objects.select_for_update().get(pk=test_task_id)
        suite = task.suite
        if task.scenario_name == 'callback':
            task.observations['callback_count'] = task.observations.get('callback_count', 0) + 1
            task.save(update_fields=['observations'])
        if suite.cancel_requested_at or suite.finished_at or task.status in Task.TERMINAL_STATUSES:
            return task.observations.get('result')
        attempt, created = Attempt.objects.get_or_create(task=task, number=attempt_number,
                                                        defaults={'worker': self.request.hostname or ''})
        if not created:
            raise Ignore()
        task.status = Task.Status.RUNNING
        task.started_at = task.started_at or timezone.now()
        task.worker = self.request.hostname or ''
        task.wait_seconds = max(0, (task.started_at - task.submitted_at).total_seconds())
        task.save(update_fields=['status', 'started_at', 'worker', 'wait_seconds'])
    if suite.config['suite_type'] == 'retry' and attempt_number <= task.expected['failures']:
        retry = task.scenario_name != 'non_retryable' and attempt_number <= suite.config['max_retries']
        now = timezone.now()
        Attempt.objects.filter(pk=attempt.pk).update(
            finished_at=now, outcome='retry' if retry else 'failed', error='Synthetic failure',
            retry_at=now + timedelta(seconds=suite.config['retry_delay']) if retry else None)
        if retry:
            retrying = Task.objects.filter(pk=task.id, status=Task.Status.RUNNING,
                                           suite__cancel_requested_at__isnull=True,
                                           suite__finished_at__isnull=True).update(status=Task.Status.RETRYING)
            if not retrying:
                finish_task(task.id, Task.Status.CANCELLED)
                return
            raise self.retry(exc=RuntimeError('Synthetic transient failure'),
                             countdown=suite.config['retry_delay'], max_retries=suite.config['max_retries'])
        finish_task(task.id, Task.Status.FAILED, 'Synthetic failure: no further retries')
        raise RuntimeError('Synthetic failure: no further retries')
    value = (sum(previous) if task.scenario_name == 'callback' else
             (previous or 0) + task.expected.get('value', 0))
    finish_task(task.id, Task.Status.SUCCEEDED, result=value)
    return value


def evaluate(suite):
    """Compare recorded outcomes, retry timing, and workflow results with expectations."""
    checks = []
    for task in suite.tasks.prefetch_related('attempts').order_by('scenario'):
        attempts = list(task.attempts.order_by('number'))
        expected = task.expected
        passed = task.status == expected.get('status', 'succeeded')
        if 'attempts' in expected:
            passed = passed and len(attempts) == expected['attempts']
        if 'result' in expected:
            passed = passed and task.observations.get('result') == expected['result']
        if task.scenario_name == 'callback':
            passed = passed and task.observations.get('callback_count') == 1
        observed_retry_delays = [
            (next_attempt.started_at - prior_attempt.finished_at).total_seconds()
            for prior_attempt, next_attempt in zip(attempts, attempts[1:])
            if prior_attempt.finished_at
        ]
        scheduled_retry_delay = suite.config.get('retry_delay', 0)
        passed = passed and all(delay >= scheduled_retry_delay - .25 for delay in observed_retry_delays)
        checks.append({'scenario': task.scenario, 'passed': passed, 'expected': expected,
                       'actual_status': task.status, 'observations': task.observations,
                       'attempts': len(attempts), 'observed_retry_delays': observed_retry_delays,
                       'scheduled_retry_delay': scheduled_retry_delay,
                       'duration_seconds': task.total_seconds,
                       'recovery_seconds': task.total_seconds if task.scenario_name == 'transient' and task.status == 'succeeded' else None,
                       'exhausted_retries': task.scenario_name == 'exhausted' and task.status == 'failed' and len(attempts) == expected.get('attempts')})
    duration = (timezone.now() - suite.started_at).total_seconds() if suite.started_at else None
    return {'checks': checks, 'duration_seconds': duration}, bool(checks) and all(check['passed'] for check in checks)


@shared_task(name='stress_testing.sync_overdue_suites')
def sync_overdue_suites():
    """Finalize overdue active suites and fail their remaining nonterminal tasks."""
    from .control import finalize
    now = timezone.now()
    # Older suites without a stored deadline use a two-hour cutoff from submission.
    overdue = Suite.objects.filter(status__in=Suite.ACTIVE_STATUSES).filter(
        Q(deadline_at__lte=now) | Q(deadline_at__isnull=True, created_at__lte=now - timedelta(hours=2)),
    )
    for suite_id in overdue.values_list('id', flat=True):
        with transaction.atomic():
            suite = Suite.objects.select_for_update().get(pk=suite_id)
            # The coordinator may have finalized the suite since the overdue query.
            if not suite.is_active:
                continue
            suite.error = 'Execution deadline exceeded; required tasks or callbacks did not finish.'
            # An interrupted coordinator may have left publication open.
            suite.publishing_finished_at = suite.publishing_finished_at or timezone.now()
            suite.tasks.exclude(status__in=Task.TERMINAL_STATUSES).update(
                status=Task.Status.FAILED, finished_at=timezone.now(), error=suite.error)
            suite.save(update_fields=['error', 'publishing_finished_at'])
            finalize(suite)
