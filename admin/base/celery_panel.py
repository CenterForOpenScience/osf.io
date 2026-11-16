from collections import defaultdict
from fnmatch import fnmatchcase
from functools import cache

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from dj_celery_panel import views
from dj_celery_panel.celery_utils import CeleryQueuesInspectBackend, QueueDetailPage, QueueListPage
from dj_celery_panel.conf import panel_config

from framework.celery_tasks import app as celery_app
from osf.models.celery_test import CeleryTestSuite, CeleryTestTask
from osf.celery_stress_test.control import cancel_suite, finish_publishing
from osf.celery_stress_test.metrics import suite_metrics
from osf.celery_stress_test.tasks import start_celery_stress_test
from .forms import CeleryStressTestForm, WorkloadForm, CeleryScenarioForm
from osf.celery_stress_test.presets import PRESETS, resolve


WorkloadFormSet = formset_factory(
    WorkloadForm,
    extra=1,
    can_delete=True,
    max_num=10,
    min_num=1,
    validate_max=True,
)


@cache
def import_task_modules():
    # Register the tasks from CeleryConfig.imports like the worker does on start. Not in AppConfig.ready():
    # some task modules call django.setup() on import, which can't run while Django is loading apps
    celery_app.loader.import_default_modules()


def overview(request):
    # The overview lists the tasks registered in this process
    import_task_modules()
    return views.index(request)


class RoutedTasksQueuesBackend(CeleryQueuesInspectBackend):
    """dj-celery-panel queues backend that also lists the tasks routed to each queue, the
    CeleryConfig routing entries that match no task, and the configured queues that no active worker consumes.

    Routes are resolved the same way Celery does when sending a task, so explicit
    queue= overrides passed to apply_async() at call time are not reflected.
    """

    BACKEND_DESCRIPTION = 'Queue bindings, routing configuration, routed tasks, unmatched routing entries and unconsumed queues'

    def get_queues(self):
        page = super().get_queues()
        # Workers report only the queues they consume, so a configured queue nobody consumes
        # would be missing from the list while tasks routed to it pile up
        listed = {queue['name'] for queue in page.queues}
        unconsumed = [
            self.describe_unconsumed_queue(queue)
            for name, queue in sorted(self.app.amqp.queues.items())
            if name not in listed
        ]
        routed_tasks = self.get_routed_tasks_by_queue()
        unmatched_entries = self.get_unmatched_routing_entries_by_queue()
        return QueueListPage(
            queues=[
                {
                    **queue,
                    'routed_tasks_count': len(routed_tasks[queue['name']]),
                    'unmatched_routing_entries': unmatched_entries[queue['name']],
                }
                for queue in page.queues + unconsumed
            ],
            error=page.error,
        )

    def get_queue_detail(self, queue_name):
        page = super().get_queue_detail(queue_name)
        queue = page.queue
        if queue is None:
            # membership check first: indexing Queues creates missing ones
            if queue_name not in self.app.amqp.queues:
                return page
            queue = self.describe_unconsumed_queue(self.app.amqp.queues[queue_name])
        return QueueDetailPage(
            queue={**queue, 'routed_tasks': self.get_routed_tasks(queue_name)},
            error=page.error,
        )

    def describe_unconsumed_queue(self, queue):
        broker_info = self._get_queue_length_from_broker(queue.name)
        return {
            'name': queue.name,
            'exchange': queue.exchange.name,
            'exchange_type': queue.exchange.type,
            'routing_key': queue.routing_key,
            'durable': queue.durable,
            'auto_delete': queue.auto_delete,
            'exclusive': queue.exclusive,
            'arguments': queue.queue_arguments,
            'workers': [],
            'worker_details': [],
            'message_count': broker_info.get('length'),
            'consumer_count': broker_info.get('consumer_count'),
            'broker_query_error': broker_info.get('error'),
        }

    def get_routed_tasks(self, queue_name):
        return self.get_routed_tasks_by_queue()[queue_name]

    def get_registered_tasks(self):
        # Every task the worker registers, not only the ones this process happened to import
        import_task_modules()
        return {name: task for name, task in self.app.tasks.items() if not name.startswith('celery.')}

    def get_routed_tasks_by_queue(self):
        router = self.app.amqp.router
        routed_tasks = defaultdict(list)
        for name, task in sorted(self.get_registered_tasks().items()):
            routed_tasks[router.route(dict(task._get_exec_options()), name)['queue'].name].append(name)
        return routed_tasks

    def get_unmatched_routing_entries_by_queue(self):
        # Celery matches task_routes entries against task names as fnmatch globs, so an entry
        # that matches no registered task name routes nothing: the task is gone, renamed,
        # or its module isn't in the celery app's include.
        # Entries routed to queues outside task_queues (osf.*, website.*) are for OSF tasks
        # sent by name with send_task(), which are never registered here, so they are skipped
        task_names = self.get_registered_tasks()
        router = self.app.amqp.router
        unmatched_entries = defaultdict(list)
        for entry, route in sorted(self.app.conf.task_routes.items()):
            queue_name = router.expand_destination(dict(route))['queue'].name
            if queue_name in self.app.amqp.queues and not any(
                fnmatchcase(name, entry) for name in task_names
            ):
                unmatched_entries[queue_name].append(entry)
        return unmatched_entries


@transaction.non_atomic_requests
@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET', 'POST'])
def celery_stress_test_view(request):
    """
    Configure and start a Celery stress test.
    """
    context = panel_config.get_context(
        request,
        current_tab='celery_stress_test',
    )
    preset = request.POST.get('preset', request.GET.get('preset', 'load'))
    if preset not in PRESETS:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest('Unknown suite preset.')
    if preset != 'load':
        form = CeleryScenarioForm(request.POST if request.method == 'POST' else None,
                                  suite_type=preset, initial=PRESETS[preset]['defaults'])
        if request.method == 'POST' and form.is_valid():
            config = resolve(preset, form.cleaned_data)
            if preset == 'workflow':
                try:
                    celery_app.backend.ensure_chords_allowed()
                except (NotImplementedError, AttributeError) as exc:
                    form.add_error(None, f'This result backend does not support chords: {exc}')
            if not form.errors:
                from datetime import timedelta
                from django.utils import timezone
                suite = CeleryTestSuite.objects.create(name=config['name'], config=config, created_by=request.user,
                    deadline_at=timezone.now() + timedelta(seconds=config['deadline_seconds']))
                try:
                    start_celery_stress_test.apply_async(args=[str(suite.id)],
                        task_id=str(suite.coordinator_task_id), retry=False)
                except Exception as exc:
                    finish_publishing(suite.id, f'Coordinator publication failed: {exc}')
                    messages.error(request, 'Failed to submit the suite.')
                return redirect('celery_stress_suite_detail', suite_id=suite.id)
        context.update({'form': form, 'presets': PRESETS, 'selected_preset': preset})
        return render(request, 'admin/dj_celery_panel/scenario_testing.html', context)
    context.update({'presets': PRESETS, 'selected_preset': preset})

    if request.method == 'POST':
        form = CeleryStressTestForm(request.POST)
        workload_formset = WorkloadFormSet(request.POST)

        if form.is_valid() and workload_formset.is_valid():
            config = {
                **form.cleaned_data,
                'suite_type': 'load',
                'preset_version': 1,
                'workloads': [
                    workload_form.cleaned_data
                    for workload_form in workload_formset
                    if workload_form.cleaned_data
                    and not workload_form.cleaned_data.get('DELETE', False)
                ],
            }

            if not config['workloads']:
                messages.error(
                    request,
                    'Please configure at least one workload.',
                )
            else:
                suite = CeleryTestSuite.objects.create(
                    name=config['name'], config=config, created_by=request.user,
                )
                try:
                    start_celery_stress_test.apply_async(
                        args=[str(suite.id)], task_id=str(suite.coordinator_task_id), retry=False,
                    )
                except Exception as error:
                    finish_publishing(suite.id, f'Coordinator publication failed: {error}')
                    messages.error(
                        request,
                        'Failed to start the stress test. Please try again.',
                    )
                else:
                    messages.success(
                        request,
                        f"Stress test submitted successfully: {suite.name}",
                    )
                    return redirect('celery_stress_suite_detail', suite_id=suite.id)
    else:
        form = CeleryStressTestForm()
        workload_formset = WorkloadFormSet()

    context.update({
        'form': form,
        'workload_formset': workload_formset,
    })

    return render(
        request,
        'admin/dj_celery_panel/celery_stress_testing.html',
        context,
    )


@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET'])
def celery_stress_suites(request):
    context = panel_config.get_context(request, current_tab='celery_stress_test')
    suites = CeleryTestSuite.objects.annotate(
        task_count=Count('tasks'),
        succeeded_count=Count('tasks', filter=Q(tasks__status=CeleryTestTask.Status.SUCCEEDED)),
        failed_count=Count('tasks', filter=Q(tasks__status=CeleryTestTask.Status.FAILED)),
    )
    context.update({
        'active_suites': suites.filter(status__in=CeleryTestSuite.ACTIVE_STATUSES),
        'history': Paginator(suites.exclude(status__in=CeleryTestSuite.ACTIVE_STATUSES), 25).get_page(request.GET.get('page')),
    })
    return render(request, 'admin/dj_celery_panel/stress_suites.html', context)


@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET'])
def celery_stress_suite_detail(request, suite_id):
    suite = get_object_or_404(CeleryTestSuite, pk=suite_id)
    context = panel_config.get_context(request, current_tab='celery_stress_test')
    context.update({
        'suite': suite,
        'metrics': suite_metrics(suite),
        'task_page': Paginator(suite.tasks.order_by('-submitted_at', '-id'), 50).get_page(request.GET.get('page')),
    })
    return render(request, 'admin/dj_celery_panel/stress_suite_detail.html', context)


@transaction.non_atomic_requests
@panel_config.permission_required('celery_stress_test')
@require_http_methods(['POST'])
def celery_stress_suite_cancel(request, suite_id):
    get_object_or_404(CeleryTestSuite, pk=suite_id)
    suite, warning = cancel_suite(suite_id, request.user, celery_app)
    if warning:
        messages.warning(request, warning)
    elif suite.cancel_requested_at:
        messages.success(request, 'Cancellation requested. Queued tasks are revoked; running tasks and the coordinator stop cooperatively.')
    else:
        messages.info(request, 'This suite has already finished.')
    return redirect('celery_stress_suite_detail', suite_id=suite.id)
