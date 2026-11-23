from django import forms
from django.core.validators import validate_email


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
    queue = forms.ChoiceField(choices=[])

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        allowed_queues = ('high', 'med', 'low', 'celery')  # TODO: Replace with settings.CELERY_QUEUES

        self.fields['queue'].choices = [
            (queue, queue) for queue in allowed_queues
        ]

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('mode')

        if mode in {'io', 'mixed'} and cleaned_data.get('io_seconds') is None:
            self.add_error('io_seconds', 'Specify the I/O duration.')

        if mode in {'cpu', 'mixed'} and cleaned_data.get('cpu_iterations') is None:
            self.add_error('cpu_iterations', 'Specify the CPU iteration count.')

        return cleaned_data
