from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone
from django.apps import apps

from osf.celery_stress_test import control, scenarios
from osf.celery_stress_test.presets import resolve
from osf.celery_stress_test.metrics import suite_metrics
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task

pytestmark = pytest.mark.django_db


def make_suite(kind='retry'):
    return Suite.objects.create(config=resolve(kind, {}), started_at=timezone.now(), status='running')


def test_presets_are_snapshotted():
    config = resolve('retry', {'retry_delay': 5})
    config['queue'] = 'low'
    assert resolve('retry', {})['queue'] == 'celery'
    assert config['preset_version'] == 2


def test_retry_exhaustion_is_expected_failure():
    suite = make_suite()
    task = Task.objects.create(suite=suite, queue='celery', scenario='non_retryable',
                               expected={'failures': 1, 'attempts': 1, 'status': 'failed'})
    with pytest.raises(RuntimeError):
        scenarios.scenario_task.run(test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == 'completed'
    assert suite.verdict == 'passed'
    assert task.attempts.get().outcome == 'failed'
    assert suite_metrics(suite)['failed'] == 1


def test_retry_is_nonterminal_and_cancelled():
    suite = make_suite()
    task = Task.objects.create(suite=suite, queue='celery', scenario='transient',
                               expected={'failures': 2, 'attempts': 3, 'status': 'succeeded'})
    with patch.object(scenarios.scenario_task, 'retry', side_effect=Retry()):
        with pytest.raises(Retry):
            scenarios.scenario_task.run(test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    task.refresh_from_db()
    assert task.status == 'retrying'
    assert task.attempts.get().retry_at is not None
    from unittest.mock import Mock
    control.cancel_suite(suite.id, None, Mock())
    task.refresh_from_db()
    assert task.status == 'cancelled'


def test_workflow_result_validation():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 6})
    assert scenarios.scenario_task.run([1, 2, 3], test_task_id=str(task.id)) == 6
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.verdict == 'passed'


def test_deadline_finishes_missing_work():
    suite = make_suite('workflow')
    suite.deadline_at = timezone.now() - timedelta(seconds=1)
    suite.save()
    Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 3})
    scenarios.reconcile_suites.run()
    suite.refresh_from_db()
    assert suite.verdict == 'failed'
    assert suite.finished_at
    assert 'deadline' in suite.error


def test_workflow_registers_all_steps_before_dispatch():
    suite = make_suite('workflow')
    with patch('celery.canvas.group.apply_async') as send:
        send.side_effect = lambda **kwargs: None
        scenarios.publish_scenarios(suite.id, suite.config)
    assert suite.tasks.count() == 9
    assert suite.tasks.filter(scenario__startswith='callback.').count() == 1


@pytest.mark.django_db(transaction=True, available_apps=[config.name for config in apps.get_app_configs()])
@pytest.mark.parametrize('kind', ['retry', 'workflow'])
def test_live_worker_executes_scenarios(kind):
    """Exercise real retries/canvas delivery without contacting the deployed broker."""
    import time
    from celery import Celery, current_app
    from celery.contrib.testing.worker import start_worker

    previous_app = current_app._get_current_object()
    app = Celery('suite-integration', broker='memory://', backend='cache+memory://')
    app.conf.update(task_default_queue='celery', worker_hijack_root_logger=False)
    app.task(bind=True, name='stress_testing.scenario', ignore_result=False)(
        scenarios.scenario_task.run.__func__)
    app.set_current()
    try:
        suite = make_suite(kind)
        suite.config['retry_delay'] = 1
        suite.config.update({'tasks_per_scenario': 2} if kind == 'retry' else
                            {'workflow_count': 2, 'chain_length': 4, 'group_size': 4, 'chord_size': 5})
        suite.save()
        with start_worker(app, perform_ping_check=False, pool='solo', shutdown_timeout=10):
            scenarios.publish_scenarios(suite.id, suite.config)
            control.finish_publishing(suite.id)
            until = time.monotonic() + 20
            while time.monotonic() < until:
                suite.refresh_from_db()
                if suite.finished_at:
                    break
                time.sleep(.1)
            assert suite.verdict == 'passed', (suite.error, suite.results)
    finally:
        previous_app.set_current()
        app.close()


def test_duplicate_callback_invalidates_verdict():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 3})
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    suite.refresh_from_db()
    assert suite.verdict == 'failed'
    task.refresh_from_db()
    assert task.observations['callback_count'] == 2


def test_custom_workflow_sizes_and_expected_results():
    suite = make_suite('workflow')
    suite.config.update(workflow_count=2, chain_length=5, group_size=4, chord_size=6)
    with patch('celery.canvas.group.apply_async'):
        scenarios.publish_scenarios(suite.id, suite.config)
    assert suite.tasks.count() == 32
    assert suite.tasks.get(scenario='chain.0.4').expected['result'] == 20
    assert suite.tasks.get(scenario='callback.1').expected['result'] == 15


@pytest.mark.parametrize('overrides,field', [
    ({'workflow_count': 100, 'chain_length': 100}, 'workflow_count'),
    ({'chain_length': 1}, 'chain_length'),
])
def test_workflow_form_limits(overrides, field):
    from admin.base.forms import CeleryScenarioForm
    data = resolve('workflow', {'name': 'Custom', **overrides})
    form = CeleryScenarioForm(data, suite_type='workflow')
    assert not form.is_valid()
    assert field in form.errors


def test_retry_form_requires_recoverable_transient_case():
    from admin.base.forms import CeleryScenarioForm
    form = CeleryScenarioForm(resolve('retry', {'name': 'Custom', 'transient_failures': 4}), suite_type='retry')
    assert not form.is_valid()
    assert 'transient_failures' in form.errors
