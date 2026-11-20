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
        help_text='Maximum time to wait for load tasks after publication ends.')
    total_duration = forms.IntegerField(
        label='Duration (seconds)',
        min_value=1,
        max_value=3600,
        initial=120,
    )
    max_total_rate = forms.IntegerField(
        label='Maximum total task rate (tasks/second)',
        min_value=1,
        max_value=1000,
        initial=20,
    )


def stress_test_queue_choices():
    declared_queues = {queue.name for queue in celery_app.conf.task_queues}
    return [(name, name) for name in settings.CELERY_STRESS_TEST_QUEUES if name in declared_queues]


class WorkloadForm(forms.Form):
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
    name = forms.CharField(max_length=100, initial='Celery correctness test')
    queue = forms.ChoiceField(choices=stress_test_queue_choices)
    deadline_seconds = forms.IntegerField(min_value=10, max_value=3600, initial=120)
    retry_delay = forms.IntegerField(min_value=1, max_value=60, initial=2)
    max_retries = forms.IntegerField(min_value=2, max_value=10, initial=3)
    tasks_per_scenario = forms.IntegerField(min_value=1, max_value=100, initial=1,
        help_text='Number of tasks for each of the three retry scenarios (3 × this value total).')
    transient_failures = forms.IntegerField(min_value=1, max_value=10, initial=2,
        help_text='Failures before a transient task succeeds; must not exceed maximum retries.')
    workflow_count = forms.IntegerField(min_value=1, max_value=100, initial=1,
        help_text='Number of independent chain, group and chord sets.')
    chain_length = forms.IntegerField(min_value=2, max_value=100, initial=2)
    group_size = forms.IntegerField(min_value=2, max_value=100, initial=3)
    chord_size = forms.IntegerField(min_value=2, max_value=100, initial=3,
        help_text='Header task count; each chord also has one final callback.')

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
        total = data.get('workflow_count', 0) * (data.get('chain_length', 0) + data.get('group_size', 0) + data.get('chord_size', 0) + 1)
        if total > 500:
            self.add_error('workflow_count', 'Choose sizes producing at most 500 tasks in total.')
        return data
