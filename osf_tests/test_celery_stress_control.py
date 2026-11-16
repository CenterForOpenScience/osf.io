from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task
from osf.celery_stress_test import control, tasks
from osf.celery_stress_test.metrics import suite_metrics

pytestmark = pytest.mark.django_db


@pytest.fixture
def suite():
    return Suite.objects.create(config={
        'name': 'Test suite', 'total_duration': 1, 'max_total_rate': 10,
        'workloads': [{'name': 'I/O', 'mode': 'io', 'queue': 'celery', 'rate': 10,
                       'io_seconds': 0, 'cpu_iterations': None}],
    })


def make_task(suite, **kwargs):
    return Task.objects.create(suite=suite, workload_index=0, queue='celery', **kwargs)


def test_queued_cancellation_prevents_coordinator_and_workload_execution(suite):
    task = make_task(suite)
    app = Mock()
    control.cancel_suite(suite.id, None, app)
    tasks.start_celery_stress_test.run(str(suite.id))
    with patch.object(tasks.time, 'sleep') as sleep:
        tasks.simulated_workload.run(test_task_id=str(task.id))
    sleep.assert_not_called()
    suite.refresh_from_db()
    task.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert task.status == Task.Status.CANCELLED
    app.control.revoke.assert_any_call(str(suite.coordinator_task_id), terminate=False)
    app.control.revoke.assert_any_call([str(task.id)], terminate=False)


def test_cancellation_waits_for_running_tasks_and_coordinator(suite):
    suite.status, suite.started_at = Suite.Status.RUNNING, timezone.now()
    suite.save()
    task = make_task(suite, status=Task.Status.RUNNING, started_at=timezone.now())
    queued = make_task(suite)
    control.cancel_suite(suite.id, None, Mock())
    suite.refresh_from_db()
    queued.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLING
    assert queued.status == Task.Status.CANCELLED
    control.finish_task(task.id, Task.Status.SUCCEEDED, runtime=.5)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLING
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    task.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert task.status == Task.Status.CANCELLED
    assert task.runtime_seconds == .5


def test_no_new_publications_after_cancel_during_send(suite):
    def cancel_during_send(*args, **kwargs):
        assert Task.objects.filter(pk=kwargs['task_id']).exists()
        control.cancel_suite(suite.id, None, Mock())
    with patch.object(tasks.current_app, 'send_task', side_effect=cancel_during_send) as send:
        tasks.start_celery_stress_test.run(str(suite.id))
    assert send.call_count == 1
    suite.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert suite.tasks.count() == 1


def test_broker_failure_does_not_lose_cancel_request(suite):
    app = Mock()
    app.control.revoke.side_effect = OSError('Broker unavailable')
    _, warning = control.cancel_suite(suite.id, None, app)
    suite.refresh_from_db()
    assert warning
    assert suite.cancel_requested_at is not None
    assert suite.status == Suite.Status.CANCELLED


def test_running_io_task_observes_cancellation(suite):
    real_sleep = tasks.time.sleep
    requested = False

    def cancel_then_sleep(seconds):
        nonlocal requested
        if not requested:
            requested = True
            control.cancel_suite(suite.id, None, Mock())
        real_sleep(min(seconds, .05))
    task = make_task(suite)
    with patch.object(tasks.time, 'sleep', side_effect=cancel_then_sleep):
        tasks.simulated_workload.run(io_seconds=10, test_task_id=str(task.id))
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert task.runtime_seconds < 2


def test_running_cpu_task_observes_cancellation(suite):
    task = make_task(suite)
    # Let CPU work start, then cancel at the next polling interval.
    original_filter = Suite.objects.filter
    checks = 0

    def cancel_before_check(*args, **kwargs):
        nonlocal checks
        if kwargs.get('cancel_requested_at__isnull') is False:
            checks += 1
            if checks == 2:
                control.cancel_suite(suite.id, None, Mock())
        return original_filter(*args, **kwargs)
    with patch.object(Suite.objects, 'filter', side_effect=cancel_before_check):
        tasks.simulated_workload.run(mode='cpu', cpu_iterations=100_000_000, test_task_id=str(task.id))
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert checks == 2
    assert task.runtime_seconds < 2


def test_publishing_finish_drains_before_completing(suite):
    task = make_task(suite)
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.DRAINING
    control.finish_task(task.id, Task.Status.SUCCEEDED, runtime=.1)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.COMPLETED
    finished_at = suite.finished_at
    control.finish_task(task.id, Task.Status.FAILED, 'Duplicate delivery')
    suite.refresh_from_db()
    assert suite.finished_at == finished_at
    assert suite.status == Suite.Status.COMPLETED


def test_publication_failure_is_persisted(suite):
    with patch.object(tasks.current_app, 'send_task', side_effect=OSError('offline')):
        with pytest.raises(OSError):
            tasks.start_celery_stress_test.run(str(suite.id))
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED
    assert suite.error == 'offline'
    assert suite.tasks.get().status == Task.Status.FAILED


def test_worker_failure_signal_finishes_orphaned_task(suite):
    task = make_task(suite, status=Task.Status.RUNNING, started_at=timezone.now())
    control.finish_publishing(suite.id)
    tasks.task_failure.send(
        sender=tasks.celery_app.tasks['stress_testing.simulated_workload'],
        task_id=str(task.id), exception=RuntimeError('lost child'),
    )
    task.refresh_from_db()
    suite.refresh_from_db()
    assert task.status == Task.Status.FAILED
    assert suite.status == Suite.Status.FAILED


def test_coordinator_revoked_before_start(suite):
    tasks.record_test_revocation(request=Mock(name='unused', **{
        'id': str(suite.coordinator_task_id),
    }))  # Unknown task names do not affect the suite.
    request = Mock()
    request.name = 'stress_testing.start_celery_stress_test'
    request.id = str(suite.coordinator_task_id)
    tasks.task_revoked.send(
        sender=tasks.celery_app.tasks['stress_testing.start_celery_stress_test'], request=request,
    )
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED


def test_invalid_workload_is_recorded_as_failed(suite):
    task = make_task(suite)
    with pytest.raises(ValueError):
        tasks.simulated_workload.run(mode='invalid', test_task_id=str(task.id))
    task.refresh_from_db()
    assert task.status == Task.Status.FAILED
    assert 'Unsupported' in task.error


def test_metrics_use_successful_samples_and_full_elapsed_time(suite):
    now = timezone.now()
    suite.started_at = now - timedelta(seconds=20)
    suite.publishing_finished_at = now - timedelta(seconds=10)
    suite.finished_at = now
    suite.status = Suite.Status.COMPLETED
    suite.save()
    for value in range(1, 21):
        make_task(suite, status=Task.Status.SUCCEEDED, wait_seconds=value, runtime_seconds=value / 10,
                  total_seconds=value * 2, published_at=now)
    make_task(suite, status=Task.Status.FAILED, runtime_seconds=1000)
    make_task(suite, status=Task.Status.CANCELLED, runtime_seconds=1000)
    result = suite_metrics(suite)
    assert result['total'] == 22
    assert result['published'] == 20
    assert result['publish_rate'] == 2
    assert result['throughput'] == 1
    assert result['wait']['p95'] == 19
    assert result['runtime']['mean'] == pytest.approx(1.05)
    assert result['runtime']['samples'] == 20
    assert result['failure_percent'] == pytest.approx(100 / 21)


def test_empty_metrics_and_repeated_cancellation(suite):
    assert suite_metrics(suite)['failure_percent'] is None
    assert suite_metrics(suite)['runtime']['p95'] is None
    control.cancel_suite(suite.id, None, Mock())
    suite.refresh_from_db()
    timestamp = suite.cancel_requested_at
    app = Mock()
    control.cancel_suite(suite.id, None, app)
    suite.refresh_from_db()
    assert suite.cancel_requested_at == timestamp
    app.control.revoke.assert_not_called()


@pytest.fixture
def admin_views(settings):
    from django.urls import path
    from admin.base import celery_panel

    settings.ROOT_URLCONF = __name__
    global urlpatterns
    urlpatterns = [
        path('suites/', celery_panel.celery_stress_suites, name='celery_stress_test'),
        path('suites/new/', celery_panel.celery_stress_test_view, name='celery_stress_test_new'),
        path('suites/<uuid:suite_id>/', celery_panel.celery_stress_suite_detail, name='celery_stress_suite_detail'),
        path('suites/<uuid:suite_id>/cancel/', celery_panel.celery_stress_suite_cancel, name='celery_stress_suite_cancel'),
    ]
    return celery_panel


def admin_request(method='get', data=None):
    from django.test import RequestFactory

    request = getattr(RequestFactory(), method)('/suites/', data or {})
    request.user = Mock(is_authenticated=True, is_staff=True, is_active=True, is_superuser=True)
    return request


def render_fragment(request, template, context):
    from pathlib import Path
    from django.http import HttpResponse
    from django.template import Engine, Context

    engine = Engine(
        dirs=[str(Path(__file__).parents[1] / 'admin/templates')],
        libraries={'i18n': 'django.templatetags.i18n', 'static': 'django.templatetags.static'},
        loaders=[
            ('django.template.loaders.locmem.Loader', {
                'admin/dj_celery_panel/base.html': '{% block panel_page_content %}{% endblock %}',
            }),
            'django.template.loaders.filesystem.Loader',
        ],
    )
    return HttpResponse(engine.get_template(template).render(Context(context)))


def test_dashboard_lists_active_before_finished_and_renders_actions(suite, admin_views):
    Suite.objects.create(name='Finished suite', config=suite.config, status=Suite.Status.COMPLETED)
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views, 'render', side_effect=render_fragment):
        response = admin_views.celery_stress_suites(admin_request())
    html = response.content.decode()
    assert html.index('Celery load test') < html.index('Finished suite')
    assert 'Cancel suite' in html
    assert 'New test suite' in html


def test_detail_renders_config_outcomes_latency_and_errors(suite, admin_views):
    make_task(suite, status=Task.Status.FAILED, error='<script>error</script>')
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views, 'render', side_effect=render_fragment):
        response = admin_views.celery_stress_suite_detail(admin_request(), suite.id)
    html = response.content.decode()
    assert 'Successful task latency' in html
    assert 'Submission to start' in html
    assert 'I/O / io / celery' in html
    assert '&lt;script&gt;error&lt;/script&gt;' in html
    assert '<script>error</script>' not in html


def test_cancel_is_post_only_and_permission_protected(suite, admin_views):
    from django.core.exceptions import PermissionDenied

    request = admin_request()
    assert admin_views.celery_stress_suite_cancel(request, suite.id).status_code == 405
    request = admin_request('post')
    request.user.is_superuser = request.user.is_staff = False
    with pytest.raises(PermissionDenied):
        admin_views.celery_stress_suite_cancel(request, suite.id)
    suite.refresh_from_db()
    assert suite.cancel_requested_at is None


def test_create_committed_suite_before_broker_dispatch(admin_views):
    request = admin_request('post', {
        'name': 'New suite', 'total_duration': 1, 'max_total_rate': 10,
        'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '0',
        'form-0-name': 'I/O', 'form-0-mode': 'io', 'form-0-queue': 'celery',
        'form-0-rate': '1', 'form-0-io_seconds': '0',
    })
    request.user = None  # The auth decorator is bypassed only for this handler test.

    def dispatch(*args, **kwargs):
        assert Suite.objects.filter(pk=kwargs['args'][0]).exists()
        return Mock()
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views.start_celery_stress_test, 'apply_async', side_effect=dispatch) as publish, \
            patch.object(admin_views.messages, 'success'):
        response = admin_views.celery_stress_test_view.__wrapped__.__wrapped__(request)
    assert response.status_code == 302
    assert publish.call_count == 1
    assert 'default' in admin_views.celery_stress_test_view._non_atomic_requests
    assert 'default' in admin_views.celery_stress_suite_cancel._non_atomic_requests


def test_create_form_renders_name_and_contiguous_form_prefix(admin_views):
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views, 'render', side_effect=render_fragment):
        response = admin_views.celery_stress_test_view(admin_request())
    html = response.content.decode()
    assert 'name="name"' in html
    assert 'name="form-0-mode"' in html
    assert 'value.replace(/form-' in html


@pytest.mark.parametrize('signal,receiver', [
    (tasks.task_failure, tasks.record_test_failure),
    (tasks.task_revoked, tasks.record_test_revocation),
])
def test_stress_signal_handlers_ignore_unrelated_tasks(signal, receiver):
    app = tasks.celery_app
    app.finalize()
    unrelated = app.tasks['celery.backend_cleanup']
    responses = signal.send(sender=unrelated, task_id='unrelated-id', request=None)
    assert receiver not in [handler for handler, _ in responses]


@pytest.mark.parametrize('task_name', [
    'stress_testing.simulated_workload', 'stress_testing.start_celery_stress_test',
])
@pytest.mark.parametrize('signal,receiver', [
    (tasks.task_failure, tasks.record_test_failure),
    (tasks.task_revoked, tasks.record_test_revocation),
])
def test_concrete_stress_senders_are_registered_once(task_name, signal, receiver):
    app = tasks.celery_app
    app.finalize()
    # Covers the late-import path as well as duplicate registration attempts.
    tasks.register_test_signal_handlers(sender=app)
    tasks.register_test_signal_handlers(sender=app)
    task = app.tasks[task_name]
    responses = signal.send(sender=task, task_id=None, request=None)
    assert [handler for handler, _ in responses].count(receiver) == 1
    assert not [response for handler, response in responses if handler == receiver and isinstance(response, Exception)]


def test_signal_registration_runs_after_app_finalization():
    from celery import Celery

    app = Celery('stress-signal-registration', set_as_current=False)
    app.on_after_finalize.connect(tasks.register_test_signal_handlers)
    assert not app.finalized
    try:
        app.finalize()
        for name in ('stress_testing.simulated_workload', 'stress_testing.start_celery_stress_test'):
            task = app.tasks[name]
            assert tasks.record_test_failure in tasks.task_failure._live_receivers(task)
            assert tasks.record_test_revocation in tasks.task_revoked._live_receivers(task)
    finally:
        for name in ('stress_testing.simulated_workload', 'stress_testing.start_celery_stress_test'):
            task = app.tasks[name]
            tasks.task_failure.disconnect(sender=task, dispatch_uid=f'{name}.record_test_failure')
            tasks.task_revoked.disconnect(sender=task, dispatch_uid=f'{name}.record_test_revocation')
        app.close()
