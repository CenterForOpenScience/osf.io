from django import forms
from osf.models import NotificationType, NotificationCampaign
from website import settings
import json

# SendGrid Mail Send accepts at most 1000 personalizations (one per recipient in bulk mode) per request.
SENDGRID_MAX_PERSONALIZATIONS = 1000


class NotificationTypeForm(forms.ModelForm):
    class Meta:
        model = NotificationType
        fields = '__all__'


class NotificationCampaignCreateForm(forms.ModelForm):
    # Execution values the create page switches to when "SendGrid Bulk" is selected.
    BULK_EXECUTION_DEFAULTS = {
        'batch_size': settings.DEFAULT_CAMPAIGN_BULK_BATCH_SIZE,
        'max_queued_batches': settings.DEFAULT_CAMPAIGN_BULK_MAX_QUEUED_BATCHES,
        'dispatch_interval': settings.DEFAULT_CAMPAIGN_BULK_DISPATCH_INTERVAL,
    }

    context = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 8}),
        initial='{}',
    )

    filters = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial='{}',
    )

    batch_size = forms.IntegerField(
        min_value=1,
        initial=settings.DEFAULT_CAMPAIGN_BATCH_SIZE,
    )

    max_retries = forms.IntegerField(
        min_value=0,
        initial=settings.DEFAULT_CAMPAIGN_MAX_RETRIES,
    )

    activity_threshold = forms.IntegerField(
        min_value=0,
        initial=settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD,
        help_text='Non-spam users at or above this activity total are sent in the high-activity phase.',
    )

    time_window = forms.IntegerField(
        min_value=1,
        initial=settings.DEFAULT_CAMPAIGN_WINDOW_TIME,
        help_text='The time in seconds before the developer reminder is sent.',
    )

    sendgrid_bulk = forms.BooleanField(
        required=False,
        initial=False,
        help_text=(
            f'Send each batch as a single SendGrid request (max {SENDGRID_MAX_PERSONALIZATIONS} recipients) '
            'and track delivery via the SendGrid webhook. Selecting it switches Batch Size, Max Queued Batches '
            'and Dispatch Interval to bulk defaults that avoid SendGrid rate limiting.'
        ),
    )

    max_queued_batches = forms.IntegerField(
        min_value=1,
        initial=settings.MAX_QUEUED_CAMPAIGN_BATCHES,
        help_text='Maximum number of queued campaign batches allowed before new batches are rejected.',
    )

    dispatch_interval = forms.IntegerField(
        min_value=1,
        initial=settings.CAMPAIGN_DISPATCH_INTERVAL,
        help_text='The time in seconds between dispatches of campaign batches.',
    )

    log_email_recipients = forms.CharField(
        required=False,
        initial='',
        help_text='List of email addresses to receive campaign log emails, separated by commas.',
    )

    class Meta:
        model = NotificationCampaign
        fields = (
            'name',
            'notification_type',
        )

    def clean(self):
        cleaned_data = super().clean()
        batch_size = cleaned_data.get('batch_size')
        if cleaned_data.get('sendgrid_bulk') and batch_size and batch_size > SENDGRID_MAX_PERSONALIZATIONS:
            self.add_error(
                'batch_size',
                f'Batch Size cannot exceed {SENDGRID_MAX_PERSONALIZATIONS} for SendGrid bulk requests.',
            )
        return cleaned_data

    def clean_context(self):
        value = self.cleaned_data['context'] or '{}'
        try:
            return json.loads(value)
        except Exception as e:
            raise forms.ValidationError(e)

    def clean_filters(self):
        value = self.cleaned_data['filters'] or '{}'
        try:
            data = json.loads(value)
        except Exception as e:
            raise forms.ValidationError(e)

        if isinstance(data, dict) and 'manual' in data:
            self._validate_filter_node(data['manual'])

        return data

    def _validate_filter_node(self, node):
        if not isinstance(node, dict):
            raise forms.ValidationError('Invalid filter structure.')

        if 'field' in node:
            if not str(node.get('field') or '').strip():
                raise forms.ValidationError('Filter field cannot be empty.')
            if not str(node.get('lookup') or '').strip():
                raise forms.ValidationError('Filter lookup cannot be empty.')
            value = node.get('value')
            if value is None or (isinstance(value, str) and not value.strip()):
                raise forms.ValidationError('Filter value cannot be empty.')
            return

        for child in node.get('children') or []:
            self._validate_filter_node(child)
