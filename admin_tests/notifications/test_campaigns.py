import json
import pytest
from unittest import mock

from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from admin.notifications.forms import NotificationCampaignCreateForm
from admin.notifications.views import (
    NotificationCampaignCreateView,
    NotificationCampaignDetail,
    NotificationCampaignsList,
    StartNotificationCampaign,
    DeleteNotificationCampaign,
)
from admin_tests.utilities import setup_form_view
from osf.models import NotificationType
from osf.models.notification_campaign import (
    NotificationCampaign,
)
from osf_tests.factories import AuthUserFactory
from tests.base import AdminTestCase
from website import settings


def patch_messages(request):
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)


def grant_permission(user, codename):
    user.user_permissions.add(Permission.objects.get(codename=codename))
    for attr in ('_perm_cache', '_user_perm_cache', '_group_perm_cache'):
        if hasattr(user, attr):
            delattr(user, attr)


@pytest.fixture
def notification_type():
    notification_type, _ = NotificationType.objects.get_or_create(
        name='blank',
        defaults={'subject': 'Test', 'template': 'Hello {{ name }}'},
    )
    return notification_type


def _valid_form_data(notification_type, **overrides):
    data = {
        'name': 'My Campaign',
        'notification_type': notification_type.id,
        'context': '{"greeting": "hi"}',
        'filters': json.dumps({'predefined': 'active'}),
        'batch_size': settings.DEFAULT_CAMPAIGN_BATCH_SIZE,
        'max_retries': settings.DEFAULT_CAMPAIGN_MAX_RETRIES,
        'activity_threshold': settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD,
        'sendgrid_bulk': False,
        'time_window': 8 * 60 * 60,
        'max_queued_batches': settings.MAX_QUEUED_CAMPAIGN_BATCHES,
        'dispatch_interval': settings.CAMPAIGN_DISPATCH_INTERVAL,
    }
    data.update(overrides)
    return data


class TestNotificationCampaignCreateForm:

    def test_valid_form_parses_context_and_filters(self, notification_type):
        form = NotificationCampaignCreateForm(data=_valid_form_data(notification_type))
        assert form.is_valid()
        assert form.cleaned_data['context'] == {'greeting': 'hi'}
        assert form.cleaned_data['filters'] == {'predefined': 'active'}
        assert form.cleaned_data['batch_size'] == settings.DEFAULT_CAMPAIGN_BATCH_SIZE
        assert form.cleaned_data['max_retries'] == settings.DEFAULT_CAMPAIGN_MAX_RETRIES
        assert form.cleaned_data['activity_threshold'] == settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD
        assert form.cleaned_data['time_window'] == 8 * 60 * 60
        assert form.cleaned_data['sendgrid_bulk'] is False

    def test_defaults_come_from_settings(self):
        form = NotificationCampaignCreateForm()
        assert form.fields['batch_size'].initial == settings.DEFAULT_CAMPAIGN_BATCH_SIZE
        assert form.fields['max_retries'].initial == settings.DEFAULT_CAMPAIGN_MAX_RETRIES
        assert form.fields['activity_threshold'].initial == settings.DEFAULT_CAMPAIGN_ACTIVITY_THRESHOLD
        assert form.fields['time_window'].initial == 8 * 60 * 60
        assert form.fields['sendgrid_bulk'].initial is False

    def test_invalid_context_json(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, context='{not-json')
        )
        assert not form.is_valid()
        assert 'context' in form.errors

    def test_invalid_filters_json(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, filters='[1, 2,')
        )
        assert not form.is_valid()
        assert 'filters' in form.errors

    def test_empty_context_and_filters_default_to_empty_dict(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, context='', filters='')
        )
        assert form.is_valid()
        assert form.cleaned_data['context'] == {}
        assert form.cleaned_data['filters'] == {}

    def test_manual_filter_value_cannot_be_empty(self, notification_type):
        filters = json.dumps({
            'manual': {
                'operator': 'AND',
                'children': [
                    {'field': 'username', 'lookup': 'contains', 'value': ''},
                ],
            },
        })
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, filters=filters)
        )
        assert not form.is_valid()
        assert 'filters' in form.errors
        assert 'Filter value cannot be empty.' in form.errors['filters'][0]

    def test_manual_filter_value_cannot_be_none(self, notification_type):
        filters = json.dumps({
            'manual': {
                'operator': 'AND',
                'children': [
                    {'field': 'username', 'lookup': 'contains', 'value': None},
                ],
            },
        })
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, filters=filters)
        )
        assert not form.is_valid()
        assert 'filters' in form.errors
        assert 'Filter value cannot be empty.' in form.errors['filters'][0]

    def test_manual_filter_field_cannot_be_empty(self, notification_type):
        filters = json.dumps({
            'manual': {
                'operator': 'AND',
                'children': [
                    {'field': '', 'lookup': 'contains', 'value': '@'},
                ],
            },
        })
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, filters=filters)
        )
        assert not form.is_valid()
        assert 'filters' in form.errors
        assert 'Filter field cannot be empty.' in form.errors['filters'][0]

    def test_nested_manual_filter_value_cannot_be_empty(self, notification_type):
        filters = json.dumps({
            'manual': {
                'operator': 'OR',
                'children': [
                    {'field': 'username', 'lookup': 'endswith', 'value': '@cos.io'},
                    {
                        'operator': 'AND',
                        'children': [
                            {'field': 'username', 'lookup': 'not_contains', 'value': '   '},
                        ],
                    },
                ],
            },
        })
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, filters=filters)
        )
        assert not form.is_valid()
        assert 'filters' in form.errors

    def test_batch_size_must_be_at_least_one(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, batch_size=0)
        )
        assert not form.is_valid()
        assert 'batch_size' in form.errors

    def test_max_retries_cannot_be_negative(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, max_retries=-1)
        )
        assert not form.is_valid()
        assert 'max_retries' in form.errors

    def test_activity_threshold_cannot_be_negative(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, activity_threshold=-1)
        )
        assert not form.is_valid()
        assert 'activity_threshold' in form.errors

    def test_time_window_must_be_at_least_one(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, time_window=0)
        )
        assert not form.is_valid()
        assert 'time_window' in form.errors

    def test_time_window_is_accepted(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, time_window=3600)
        )
        assert form.is_valid()
        assert form.cleaned_data['time_window'] == 3600

    def test_name_is_required(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, name='')
        )
        assert not form.is_valid()
        assert 'name' in form.errors

    def test_notification_type_is_required(self):
        form = NotificationCampaignCreateForm(
            data={
                'name': 'My Campaign',
                'context': '{}',
                'filters': '{}',
                'batch_size': 10,
                'max_retries': 1,
                'activity_threshold': 5,
            }
        )
        assert not form.is_valid()
        assert 'notification_type' in form.errors

    def test_sendgrid_bulk_can_be_enabled(self, notification_type):
        form = NotificationCampaignCreateForm(
            data=_valid_form_data(notification_type, sendgrid_bulk=True)
        )
        assert form.is_valid()
        assert form.cleaned_data['sendgrid_bulk'] is True


class TestNotificationCampaignCreateView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.notification_type, _ = NotificationType.objects.get_or_create(
            name='blank',
            defaults={'subject': 'Test', 'template': 'Hello'},
        )

    def test_form_valid_persists_execution_metadata(self):
        request = RequestFactory().post(
            reverse('notifications:notification_campaigns_create'),
            data=_valid_form_data(
                self.notification_type,
                batch_size=25,
                max_retries=4,
                activity_threshold=77,
                sendgrid_bulk=True,
                time_window=28800,
                max_queued_batches=10,
                dispatch_interval=60,
            ),
        )
        request.user = self.user
        patch_messages(request)

        form = NotificationCampaignCreateForm(data=request.POST)
        assert form.is_valid()

        view = setup_form_view(
            NotificationCampaignCreateView(),
            request,
            form,
        )
        view.form_valid(form)

        campaign = NotificationCampaign.objects.get(name='My Campaign')
        assert campaign.created_by == self.user
        assert campaign.metadata['execution'] == {
            'batch_size': 25,
            'max_retries': 4,
            'activity_threshold': 77,
            'time_window': 28800,
            'max_queued_batches': 10,
            'dispatch_interval': 60,
        }
        assert campaign.metadata['sendgrid_bulk'] is True
        assert campaign.metadata['filters'] == {'predefined': 'active'}
        assert campaign.metadata['context'] == {'greeting': 'hi'}

    @mock.patch('admin.notifications.views._render_email_html', side_effect=Exception('bad template'))
    def test_form_valid_rejects_unrenderable_context(self, mock_render):
        request = RequestFactory().post(
            reverse('notifications:notification_campaigns_create'),
            data=_valid_form_data(self.notification_type),
        )
        request.user = self.user
        patch_messages(request)

        form = NotificationCampaignCreateForm(data=request.POST)
        assert form.is_valid()

        view = setup_form_view(
            NotificationCampaignCreateView(),
            request,
            form,
        )
        with mock.patch.object(view, 'form_invalid', return_value=mock.Mock(status_code=200)) as mock_invalid:
            view.form_valid(form)

        mock_invalid.assert_called_once_with(form)
        assert 'context' in form.errors
        assert 'Failed to render template' in form.errors['context'][0]
        assert not NotificationCampaign.objects.filter(name='My Campaign').exists()


class TestNotificationCampaignAdminPermissions(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.notification_type, _ = NotificationType.objects.get_or_create(
            name='blank',
            defaults={'subject': 'Test', 'template': 'Hello'},
        )
        self.campaign = NotificationCampaign.objects.create(
            name='Campaign',
            notification_type=self.notification_type,
            metadata={'filters': {}, 'context': {}, 'execution': {}},
        )

    def test_list_requires_view_permission(self):
        request = RequestFactory().get(reverse('notifications:notification_campaigns_list'))
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            NotificationCampaignsList.as_view()(request)

        grant_permission(self.user, 'view_notificationcampaign')
        response = NotificationCampaignsList.as_view()(request)
        assert response.status_code == 200

    def test_detail_requires_change_permission(self):
        request = RequestFactory().get(
            reverse('notifications:notification_campaigns_detail', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            NotificationCampaignDetail.as_view()(request, pk=self.campaign.pk)

        grant_permission(self.user, 'change_notificationcampaign')
        response = NotificationCampaignDetail.as_view()(request, pk=self.campaign.pk)
        assert response.status_code == 200

    def test_detail_allow_restart_stuck_false_when_recently_updated(self):
        grant_permission(self.user, 'change_notificationcampaign')
        request = RequestFactory().get(
            reverse('notifications:notification_campaigns_detail', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user

        response = NotificationCampaignDetail.as_view()(request, pk=self.campaign.pk)

        assert response.status_code == 200
        assert response.context_data['allow_restart_stuck'] is False

    def test_detail_allow_restart_stuck_true_when_updated_long_time_ago(self):
        grant_permission(self.user, 'change_notificationcampaign')
        NotificationCampaign.objects.filter(pk=self.campaign.pk).update(
            updated_at=timezone.now() - timedelta(minutes=16),
        )
        request = RequestFactory().get(
            reverse('notifications:notification_campaigns_detail', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user

        response = NotificationCampaignDetail.as_view()(request, pk=self.campaign.pk)

        assert response.status_code == 200
        assert response.context_data['allow_restart_stuck'] is True

    def test_start_requires_change_notificationcampaign_permission(self):

        request = RequestFactory().post(
            reverse('notifications:notification_campaigns_start', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            StartNotificationCampaign.as_view()(request, pk=self.campaign.pk)

        grant_permission(self.user, 'change_notificationcampaign')
        with mock.patch.object(NotificationCampaign, 'start') as mock_start:
            response = StartNotificationCampaign.as_view()(request, pk=self.campaign.pk)
        assert response.status_code == 302
        mock_start.assert_called_once_with(restart_failed=False, restart_stuck=False)

    def test_start_rejects_when_another_campaign_is_running(self):
        from osf.models.notification_campaign import NotificationCampaignStatus

        grant_permission(self.user, 'change_notificationcampaign')
        NotificationCampaign.objects.create(
            name='Already Running',
            notification_type=self.notification_type,
            status=NotificationCampaignStatus.RUNNING,
            metadata={'filters': {}, 'context': {}, 'execution': {}},
        )
        request = RequestFactory().post(
            reverse('notifications:notification_campaigns_start', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user
        patch_messages(request)

        with mock.patch.object(NotificationCampaign, 'start') as mock_start:
            response = StartNotificationCampaign.as_view()(request, pk=self.campaign.pk)

        assert response.status_code == 302
        mock_start.assert_not_called()
        self.campaign.refresh_from_db()
        assert self.campaign.status == NotificationCampaignStatus.CREATED

class TestNotificationCampaignDeleteView(AdminTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.notification_type, _ = NotificationType.objects.get_or_create(
            name='blank',
            defaults={'subject': 'Test', 'template': 'Hello'},
        )
        self.campaign = NotificationCampaign.objects.create(
            name='Campaign',
            notification_type=self.notification_type,
            metadata={'filters': {}, 'context': {}, 'execution': {}},
        )

    def test_delete_requires_change_notificationcampaign_permission(self):
        request = RequestFactory().post(
            reverse('notifications:notification_campaigns_delete', kwargs={'pk': self.campaign.pk})
        )
        request.user = self.user
        patch_messages(request)

        with self.assertRaises(PermissionDenied):
            DeleteNotificationCampaign.as_view()(request, pk=self.campaign.pk)

        grant_permission(self.user, 'delete_notificationcampaign')
        response = DeleteNotificationCampaign.as_view()(request, pk=self.campaign.pk)
        assert response.status_code == 302
        assert not NotificationCampaign.objects.filter(pk=self.campaign.pk).exists()
