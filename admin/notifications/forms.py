from django import forms
from osf.models import NotificationType, NotificationCampaign
from website import settings
import json


class NotificationTypeForm(forms.ModelForm):
    class Meta:
        model = NotificationType
        fields = '__all__'


class NotificationCampaignCreateForm(forms.ModelForm):
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
        initial=8 * 60 * 60,  # 8 hours
        help_text='The time in seconds before the developer reminder is sent.',
    )

    sendgrid_bulk = forms.BooleanField(
        required=False,
        initial=False,
    )

    class Meta:
        model = NotificationCampaign
        fields = (
            'name',
            'notification_type',
        )

    def clean_context(self):
        value = self.cleaned_data['context'] or '{}'
        try:
            return json.loads(value)
        except Exception as e:
            raise forms.ValidationError(e)

    def clean_filters(self):
        value = self.cleaned_data['filters'] or '{}'
        try:
            return json.loads(value)
        except Exception as e:
            raise forms.ValidationError(e)
