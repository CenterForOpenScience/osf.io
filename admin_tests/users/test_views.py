from django.test import RequestFactory
from django.http import Http404
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from nose import tools as nt
import mock
import csv
import os
from datetime import timedelta

from tests.base import AdminTestCase
from website import settings
from framework.auth import User, Auth
from tests.factories import (
    UserFactory,
    AuthUserFactory,
    ProjectFactory,
)
from admin_tests.utilities import setup_view, setup_log_view, setup_form_view

from admin.users.views import (
    UserView,
    ResetPasswordView,
    User2FactorDeleteView,
    UserDeleteView,
    SpamUserDeleteView,
    UserFlaggedSpamList,
    UserKnownSpamList,
    UserKnownHamList,
    UserWorkshopFormView,
)
from admin.users.forms import WorkshopForm
from admin.common_auth.logs import OSFLogEntry


class TestUserView(AdminTestCase):
    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = UserView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[UserView.context_object_name], temp_object)


class TestResetPasswordView(AdminTestCase):
    def test_reset_password_context(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = ResetPasswordView()
        view = setup_view(view, request, guid=guid)
        res = view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in((user.emails[0], user.emails[0]), view.initial['emails'])


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = UserDeleteView()
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, User)

    def test_get_context(self):
        res = self.view.get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        self.user.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)

    def test_reactivate_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view.delete(self.request)
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        self.user.reload()
        nt.assert_false(self.user.is_disabled)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)

    def test_no_user(self):
        view = setup_view(UserDeleteView(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)


class TestDisableSpamUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.public_node = ProjectFactory(creator=self.user, is_public=True)
        self.public_node = ProjectFactory(creator=self.user, is_public=False)
        self.request = RequestFactory().post('/fake_path')
        self.view = SpamUserDeleteView()
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, User)

    def test_get_context(self):
        res = self.view.get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_spam_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        self.user.reload()
        self.public_node.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_false(self.public_node.is_public)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 3)

    def test_no_user(self):
        view = setup_view(UserDeleteView(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)


class SpamUserListMixin(AdminTestCase):
    def setUp(self):
        self.flagged_user = UserFactory(system_tags=['spam_flagged'])
        self.spam_user = UserFactory(system_tags=['spam_confirmed'])
        self.ham_user = UserFactory(system_tags=['ham_confirmed'])
        self.request = RequestFactory().post('/fake_path')


class TestFlaggedSpamUserList(SpamUserListMixin):
    def setUp(self):
        super(TestFlaggedSpamUserList, self).setUp()
        self.view = UserFlaggedSpamList()
        self.view = setup_log_view(self.view, self.request)

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.flagged_user._id)


class TestConfirmedSpamUserList(SpamUserListMixin):
    def setUp(self):
        super(TestConfirmedSpamUserList, self).setUp()
        self.view = UserKnownSpamList()
        self.view = setup_log_view(self.view, self.request)

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.spam_user._id)


class TestConfirmedHamUserList(SpamUserListMixin):
    def setUp(self):
        super(TestConfirmedHamUserList, self).setUp()
        self.view = UserKnownHamList()
        self.view = setup_log_view(self.view, self.request)

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.ham_user._id)


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super(TestRemove2Factor, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = User2FactorDeleteView()
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    @mock.patch('admin.users.views.User.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        self.view.delete(self.request)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        user_addon = self.user.get_or_add_addon('twofactor')
        nt.assert_not_equal(user_addon, None)
        user_settings = self.user.get_addon('twofactor')
        nt.assert_not_equal(user_settings, None)
        count = OSFLogEntry.objects.count()
        self.view.delete(self.request)
        post_addon = self.user.get_addon('twofactor')
        nt.assert_equal(post_addon, None)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)


class TestUserWorkshopFormView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory()
        self.auth_1 = Auth(self.user_1)
        self.view = UserWorkshopFormView()
        self.workshop_date = timezone.now()
        self.data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, None, self.user_1.username, None],
        ]

        self.user_exists_by_name_data = [
            ['number', 'date', 'location', 'topic', 'name', 'email', 'other'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, self.user_1.fullname, 'unknown@example.com', None],
        ]

        self.user_not_found_data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, None, 'fake@example.com', None],
        ]

    def _create_and_parse_test_file(self, data):
        with open('test.csv', 'w') as fp:
            writer = csv.writer(fp)
            for row in data:
                writer.writerow(row)

        with file('test.csv') as fp:
            result_csv = self.view.parse(fp)

        return result_csv

    def _create_nodes_and_add_logs(self, first_activity_date, second_activity_date=None):
        node_one = ProjectFactory(creator=self.user_1, date_created=first_activity_date)
        node_one.add_log(
            'log_added', params={'project': node_one._id}, auth=self.auth_1, log_date=first_activity_date, save=True
        )

        if second_activity_date:
            node_two = ProjectFactory(creator=self.user_1, date_created=second_activity_date)
            node_two.add_log(
                'log_added', params={'project': node_two._id}, auth=self.auth_1, log_date=second_activity_date, save=True
            )

    def test_correct_number_of_columns_added(self):
        added_columns = ['OSF ID', 'Logs Since Workshop', 'Nodes Created Since Workshop', 'Last Log Data']
        result_csv = self._create_and_parse_test_file(self.data)
        nt.assert_equal(len(self.data[0]) + len(added_columns), len(result_csv[0]))

    def test_user_activity_day_of_workshop_only(self):
        self._create_nodes_and_add_logs(first_activity_date=self.workshop_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_before_workshop_only(self):
        activity_date = timezone.now() - timedelta(days=1)
        self._create_nodes_and_add_logs(first_activity_date=activity_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_after_workshop_only(self):
        activity_date = timezone.now() + timedelta(days=1)
        self._create_nodes_and_add_logs(first_activity_date=activity_date)

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_activity_day_of_workshop_and_before(self):
        activity_date = timezone.now() - timedelta(days=1)
        self._create_nodes_and_add_logs(
            first_activity_date=self.workshop_date,
            second_activity_date=activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_day_of_workshop_and_after(self):
        activity_date = timezone.now() + timedelta(days=1)
        self._create_nodes_and_add_logs(
            first_activity_date=self.workshop_date,
            second_activity_date=activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_activity_before_workshop_and_after(self):
        before_activity_date = timezone.now() - timedelta(days=1)
        after_activity_date = timezone.now() + timedelta(days=1)
        self._create_nodes_and_add_logs(
            first_activity_date=before_activity_date,
            second_activity_date=after_activity_date
        )

        result_csv = self._create_and_parse_test_file(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    def test_user_osf_account_not_found(self):
        result_csv = self._create_and_parse_test_file(self.user_not_found_data)
        user_guid = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_guid, '')
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_found_by_name(self):
        result_csv = self._create_and_parse_test_file(self.user_exists_by_name_data)
        user_guid = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_guid, self.user_1._id)
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_form_valid(self):
        request = RequestFactory().post('/fake_path')
        data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, '9/1/16', None, None, None, self.user_1.username, None],
        ]

        with open('test.csv', 'w') as fp:
            writer = csv.writer(fp)
            for row in data:
                writer.writerow(row)

        with file('test.csv', mode='rb') as fp:
            uploaded = SimpleUploadedFile(fp.name, fp.read(), content_type='text/csv')

        form = WorkshopForm(data={'document': uploaded})
        form.is_valid()
        form.cleaned_data['document'] = uploaded
        setup_form_view(self.view, request, form)

    def tearDown(self):
        if os.path.isfile('test.csv'):
            os.remove('test.csv')
