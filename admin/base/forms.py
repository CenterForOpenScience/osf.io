from django import forms
from django.core.validators import validate_email
from framework.celery_tasks import app as celery_app
from website import settings


class GuidForm(forms.Form):
    guid = forms.CharField(label='Guid', min_length=5, max_length=10, required=True)


class MultiEmailField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        return [r.strip().lower() for r in value.split(',')]

    def validate(self, value):
        super().validate(value)
        for email in value:
            validate_email(email)


class ImportFileForm(forms.Form):
    file = forms.FileField()


class ArchiveRegistrationWithPigeonForm(forms.Form):
    guid_to_archive = forms.CharField(label='guid_to_archive', min_length=5, max_length=1024, required=False)


class CeleryStressTestForm(forms.Form):
    name = forms.CharField(max_length=100, initial='Celery load test')
    drain_timeout = forms.IntegerField(min_value=10, max_value=3600, initial=120,
        help_text='Time budgeted for published tasks to finish. The execution deadline is set at submission using the publishing duration, this budget, and a 60-second buffer.')
    total_duration = forms.IntegerField(
        label='Duration (seconds)',
        min_value=1,
        max_value=3600,
        initial=120,
        help_text='How long the coordinator publishes tasks after it starts. Already-published tasks can finish afterward.',
    )
    max_total_rate = forms.IntegerField(
        label='Maximum total task rate (tasks/second)',
        min_value=1,
        max_value=1000,
        initial=20,
        help_text='Combined publishing ceiling across all workloads. Each workload also has its own publishing rate.',
    )


def stress_test_queue_choices():
    """Offer only queues that are both configured in Celery and allowed for stress tests."""
    declared_queues = {queue.name for queue in celery_app.conf.task_queues}
    return [(name, name) for name in settings.CELERY_STRESS_TEST_QUEUES if name in declared_queues]


class WorkloadForm(forms.Form):
    """Configure the queue, publishing rate, and synthetic work for one workload."""
    name = forms.CharField(
        max_length=100,
        initial='Workload',
    )
    mode = forms.ChoiceField(
        choices=[
            ('io', 'I/O-bound'),
            ('cpu', 'CPU-bound'),
            ('mixed', 'Mixed'),
        ],
        initial='io',
    )
    queue = forms.ChoiceField(choices=stress_test_queue_choices)

    rate = forms.IntegerField(
        label='Task rate (tasks/second)',
        min_value=1,
        max_value=1000,
        initial=10,
    )
    io_seconds = forms.FloatField(
        label='I/O duration (seconds)',
        min_value=0,
        max_value=30,
        initial=1,
        required=False,
    )
    cpu_iterations = forms.IntegerField(
        label='CPU iterations',
        min_value=1,
        max_value=100_000_000,
        initial=1_000_000,
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')

        if mode in {'io', 'mixed'} and cleaned_data.get('io_seconds') is None:
            self.add_error('io_seconds', 'Specify the I/O duration.')

        if mode in {'cpu', 'mixed'} and cleaned_data.get('cpu_iterations') is None:
            self.add_error('cpu_iterations', 'Specify the CPU iteration count.')

        return cleaned_data


class CeleryScenarioForm(forms.Form):
    """Expose the fields and validate the task budget for the selected scenario preset."""

    name = forms.CharField(max_length=100, initial='Celery correctness test')
    queue = forms.ChoiceField(choices=stress_test_queue_choices,
        help_text='Workers consuming this queue execute the scenario tasks and workflow callbacks.')
    deadline_seconds = forms.IntegerField(min_value=10, max_value=3600, initial=120,
        label='Execution time budget (seconds)',
        help_text='Starts when you submit the suite. Includes queue wait, execution, retry delays, and callbacks.')
    retry_delay = forms.IntegerField(min_value=1, max_value=60, initial=2,
        help_text='Seconds Celery schedules between a retryable failure and the next attempt.')
    max_retries = forms.IntegerField(min_value=2, max_value=10, initial=3,
        help_text='Number of retries allowed after the initial attempt.')
    tasks_per_scenario = forms.IntegerField(min_value=1, max_value=100, initial=1,
        help_text='Number of tasks for each of the three retry scenarios (3 * this value total).')
    transient_failures = forms.IntegerField(min_value=1, max_value=10, initial=2,
        help_text='Failures simulated before a transient task succeeds. Must be within the retry limit.')
    workflow_count = forms.IntegerField(min_value=1, max_value=100, initial=1,
        help_text='Number of independent chain, group and chord sets.')
    chain_length = forms.IntegerField(min_value=2, max_value=100, initial=2,
        help_text='Sequential steps per chain. Each step receives the previous result.')
    group_size = forms.IntegerField(min_value=2, max_value=100, initial=3,
        help_text='Independent tasks in each group.')
    chord_size = forms.IntegerField(min_value=2, max_value=100, initial=3,
        help_text='Tasks that must finish before the chord runs its final callback.')

    def __init__(self, *args, suite_type, **kwargs):
        super().__init__(*args, **kwargs)
        excluded = (('workflow_count', 'chain_length', 'group_size', 'chord_size') if suite_type == 'retry'
                    else ('tasks_per_scenario', 'transient_failures', 'retry_delay', 'max_retries'))
        for name in excluded:
            del self.fields[name]

    def clean(self):
        data = super().clean()
        if 'max_retries' in data and data.get('deadline_seconds', 0) <= data['max_retries'] * data.get('retry_delay', 0):
            self.add_error('deadline_seconds', 'Allow more time than the configured retry delays.')
        if data.get('transient_failures', 0) > data.get('max_retries', 0):
            self.add_error('transient_failures', 'Must not exceed maximum retries.')
        tasks_per_workflow = data.get('chain_length', 0) + data.get('group_size', 0) + data.get('chord_size', 0) + 1
        if data.get('workflow_count', 0) * tasks_per_workflow > 500:
            self.add_error('workflow_count', 'Choose sizes producing at most 500 tasks in total.')
        return data
