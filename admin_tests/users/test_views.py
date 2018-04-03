import mock
import csv
import furl
import pytz
import pytest
from datetime import datetime, timedelta

from nose import tools as nt
from django.test import RequestFactory
from django.http import Http404
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from website import settings
from framework.auth import Auth
from osf.models.user import OSFUser
from osf.models.tag import Tag
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory,
    ProjectFactory,
    TagFactory,
    UnconfirmedUserFactory
)
from admin_tests.utilities import setup_view, setup_log_view, setup_form_view

from admin.users import views
from admin.users.forms import WorkshopForm, UserSearchForm, MergeUserForm
from osf.models.admin_log_entry import AdminLogEntry

pytestmark = pytest.mark.django_db


class TestUserView(AdminTestCase):
    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request)
        with nt.assert_raises(AttributeError):
            view.get_object()

    def test_load_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request, guid=guid)
        res = view.get_object()
        nt.assert_is_instance(res, dict)

    def test_name_data(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get('/fake_path')
        view = views.UserView()
        view = setup_view(view, request, guid=guid)
        temp_object = view.get_object()
        view.object = temp_object
        res = view.get_context_data()
        nt.assert_equal(res[views.UserView.context_object_name], temp_object)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.UserView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('users:user', kwargs={'guid': guid}))
        request.user = user

        response = views.UserView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestResetPasswordView(AdminTestCase):
    def setUp(self):
        super(TestResetPasswordView, self).setUp()
        self.user = UserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.plain_view = views.ResetPasswordView
        self.view = setup_view(self.plain_view(), self.request, guid=self.user._id)

    def test_get_initial(self):
        self.view.user = self.user
        self.view.get_initial()
        res = self.view.initial
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['guid'], self.user._id)
        nt.assert_equal(res['emails'], [(r, r) for r in self.user.emails.values_list('address', flat=True)])

    def test_reset_password_context(self):
        self.view.user = self.user
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in((self.user.emails.first().address, self.user.emails.first().address), self.view.initial['emails'])

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()

        guid = user._id
        request = RequestFactory().get(reverse('users:reset_password', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            views.ResetPasswordView.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:reset_password', kwargs={'guid': guid}))
        request.user = user

        response = views.ResetPasswordView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestDisableUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.UserDeleteView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view().get_object()
        nt.assert_is_instance(obj, OSFUser)

    def test_get_context(self):
        res = self.view().get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_reactivate_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        self.view().delete(self.request)
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        nt.assert_false(self.user.is_disabled)
        nt.assert_false(self.user.requested_deactivation)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_no_user(self):
        view = setup_view(views.UserDeleteView(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:disable', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestHamUserRestore(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.HamUserRestoreView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

        self.spam_confirmed, created = Tag.objects.get_or_create(name='spam_confirmed')
        self.ham_confirmed, created = Tag.objects.get_or_create(name='ham_confirmed')

    def test_get_object(self):
        obj = self.view().get_object()
        nt.assert_is_instance(obj, OSFUser)

    def test_get_context(self):
        res = self.view().get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_enable_user(self):
        self.user.disable_account()
        self.user.save()
        nt.assert_true(self.user.is_disabled)
        self.view().delete(self.request)
        self.user.reload()

        nt.assert_false(self.user.is_disabled)
        nt.assert_false(self.user.all_tags.filter(name=self.spam_confirmed.name).exists())
        nt.assert_true(self.user.all_tags.filter(name=self.ham_confirmed.name).exists())


class TestDisableSpamUser(AdminTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.public_node = ProjectFactory(creator=self.user, is_public=True)
        self.private_node = ProjectFactory(creator=self.user, is_public=False)
        self.request = RequestFactory().post('/fake_path')
        self.view = views.SpamUserDeleteView
        self.view = setup_log_view(self.view, self.request, guid=self.user._id)

    def test_get_object(self):
        obj = self.view().get_object()
        nt.assert_is_instance(obj, OSFUser)

    def test_get_context(self):
        res = self.view().get_context_data(object=self.user)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.user._id)

    def test_disable_spam_user(self):
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
        count = AdminLogEntry.objects.count()
        self.view().delete(self.request)
        self.user.reload()
        self.public_node.reload()
        nt.assert_true(self.user.is_disabled)
        nt.assert_true(self.user.all_tags.filter(name='spam_confirmed').exists())
        nt.assert_false(self.public_node.is_public)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 3)

    def test_no_user(self):
        view = setup_view(self.view(), self.request, guid='meh')
        with nt.assert_raises(Http404):
            view.delete(self.request)

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(reverse('users:spam_disable', kwargs={'guid': guid}))
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('users:spam_disable', kwargs={'guid': guid}))
        request.user = user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class SpamUserListMixin(object):
    def setUp(self):

        spam_flagged = TagFactory(name='spam_flagged')
        spam_confirmed = TagFactory(name='spam_confirmed')
        ham_confirmed = TagFactory(name='ham_confirmed')

        self.flagged_user = UserFactory()
        self.flagged_user.tags.add(spam_flagged)
        self.flagged_user.save()

        self.spam_user = UserFactory()
        self.spam_user.tags.add(spam_confirmed)
        self.spam_user.save()

        self.ham_user = UserFactory()
        self.ham_user.tags.add(ham_confirmed)
        self.ham_user.save()

        self.request = RequestFactory().post('/fake_path')

    def test_no_user_permissions_raises_error(self):
        user = UserFactory()
        guid = user._id
        request = RequestFactory().get(self.url)
        request.user = user

        with self.assertRaises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        spam_permission = Permission.objects.get(codename='view_spam')
        user.user_permissions.add(view_permission)
        user.user_permissions.add(spam_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)

class TestFlaggedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestFlaggedSpamUserList, self).setUp()
        self.plain_view = views.UserFlaggedSpamList
        self.view = setup_log_view(self.plain_view(), self.request)
        self.url = reverse('users:flagged-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.flagged_user._id)


class TestConfirmedSpamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestConfirmedSpamUserList, self).setUp()
        self.plain_view = views.UserKnownSpamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-spam')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.spam_user._id)


class TestConfirmedHamUserList(SpamUserListMixin, AdminTestCase):
    def setUp(self):
        super(TestConfirmedHamUserList, self).setUp()
        self.plain_view = views.UserKnownHamList
        self.view = setup_log_view(self.plain_view(), self.request)

        self.url = reverse('users:known-ham')

    def test_get_queryset(self):
        qs = self.view.get_queryset()
        nt.assert_equal(qs.count(), 1)
        nt.assert_equal(qs[0]._id, self.ham_user._id)


class TestRemove2Factor(AdminTestCase):
    def setUp(self):
        super(TestRemove2Factor, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = views.User2FactorDeleteView
        self.setup_view = setup_log_view(self.view(), self.request, guid=self.user._id)

        self.url = reverse('users:remove2factor', kwargs={'guid': self.user._id})

    @mock.patch('osf.models.user.OSFUser.delete_addon')
    def test_remove_two_factor_get(self, mock_delete_addon):
        self.setup_view.delete(self.request)
        mock_delete_addon.assert_called_with('twofactor')

    def test_integration_delete_two_factor(self):
        user_addon = self.user.get_or_add_addon('twofactor')
        nt.assert_not_equal(user_addon, None)
        user_settings = self.user.get_addon('twofactor')
        nt.assert_not_equal(user_settings, None)
        count = AdminLogEntry.objects.count()
        self.setup_view.delete(self.request)
        post_addon = self.user.get_addon('twofactor')
        nt.assert_equal(post_addon, None)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_no_user_permissions_raises_error(self):
        guid = self.user._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with self.assertRaises(PermissionDenied):
            self.view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        guid = self.user._id

        change_permission = Permission.objects.get(codename='change_osfuser')
        self.user.user_permissions.add(change_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)


class TestUserWorkshopFormView(AdminTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.view = views.UserWorkshopFormView()
        self.node = ProjectFactory(creator=self.user)

        self.mock_data = mock.patch.object(
            csv,
            'reader',
            # parse data into the proper format handling None values as csv reader would
            side_effect=(lambda values: [[item or '' for item in value] for value in values])
        )
        self.mock_data.start()

    def tearDown(self):
        self.mock_data.stop()

    def _setup_workshop(self, date):
        self.workshop_date = date
        self.data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, None, self.user.username, None],
        ]

        self.user_exists_by_name_data = [
            ['number', 'date', 'location', 'topic', 'name', 'email', 'other'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, self.user.fullname, 'unknown@example.com', None],
        ]

        self.user_not_found_data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, self.workshop_date.strftime('%m/%d/%y'), None, None, None, 'fake@example.com', None],
        ]

    def _add_log(self, date):
        self.node.add_log('log_added', params={'project': self.node._id}, auth=self.auth, log_date=date, save=True)

    def test_correct_number_of_columns_added(self):
        self._setup_workshop(self.node.created)
        added_columns = ['OSF ID', 'Logs Since Workshop', 'Nodes Created Since Workshop', 'Last Log Data']
        result_csv = self.view.parse(self.data)
        nt.assert_equal(len(self.data[0]) + len(added_columns), len(result_csv[0]))

    def test_user_activity_day_of_workshop_and_before(self):
        self._setup_workshop(self.node.created)
        # add logs 0 to 48 hours back
        for time_mod in range(9):
            self._add_log(self.node.created - timedelta(hours=(time_mod * 6)))
        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_activity_after_workshop(self):
        self._setup_workshop(self.node.created - timedelta(hours=25))
        self._add_log(self.node.created)

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        # 1 node created, 1 node log
        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

        # Test workshop 30 days ago
        self._setup_workshop(self.node.created - timedelta(days=30))

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

        # Test workshop a year ago
        self._setup_workshop(self.node.created - timedelta(days=365))

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_logs_since_workshop, 2)
        nt.assert_equal(user_nodes_created_since_workshop, 1)

    # Regression test for OSF-8089
    def test_utc_new_day(self):
        node_date = self.node.created
        date = datetime(node_date.year, node_date.month, node_date.day, 0, tzinfo=pytz.utc) + timedelta(days=1)
        self._setup_workshop(date)
        self._add_log(self.workshop_date + timedelta(hours=25))

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        nt.assert_equal(user_logs_since_workshop, 1)

    # Regression test for OSF-8089
    def test_utc_new_day_plus_hour(self):
        node_date = self.node.created
        date = datetime(node_date.year, node_date.month, node_date.day, 0, tzinfo=pytz.utc) + timedelta(days=1, hours=1)
        self._setup_workshop(date)
        self._add_log(self.workshop_date + timedelta(hours=25))

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        nt.assert_equal(user_logs_since_workshop, 1)

    # Regression test for OSF-8089
    def test_utc_new_day_minus_hour(self):
        node_date = self.node.created
        date = datetime(node_date.year, node_date.month, node_date.day, 0, tzinfo=pytz.utc) + timedelta(days=1) - timedelta(hours=1)
        self._setup_workshop(date)
        self._add_log(self.workshop_date + timedelta(hours=25))

        result_csv = self.view.parse(self.data)
        user_logs_since_workshop = result_csv[1][-3]
        nt.assert_equal(user_logs_since_workshop, 1)

    def test_user_osf_account_not_found(self):
        self._setup_workshop(self.node.created)
        result_csv = self.view.parse(self.user_not_found_data)
        user_id = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_id, '')
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_user_found_by_name(self):
        self._setup_workshop(self.node.created)
        result_csv = self.view.parse(self.user_exists_by_name_data)
        user_id = result_csv[1][-4]
        last_log_date = result_csv[1][-1]
        user_logs_since_workshop = result_csv[1][-3]
        user_nodes_created_since_workshop = result_csv[1][-2]

        nt.assert_equal(user_id, self.user._id)
        nt.assert_equal(last_log_date, '')
        nt.assert_equal(user_logs_since_workshop, 0)
        nt.assert_equal(user_nodes_created_since_workshop, 0)

    def test_form_valid(self):
        request = RequestFactory().post('/fake_path')
        data = [
            ['none', 'date', 'none', 'none', 'none', 'email', 'none'],
            [None, '9/1/16', None, None, None, self.user.username, None],
        ]

        uploaded = SimpleUploadedFile('test_name', bytes(csv.reader(data)), content_type='text/csv')

        form = WorkshopForm(data={'document': uploaded})
        form.is_valid()
        form.cleaned_data['document'] = uploaded
        setup_form_view(self.view, request, form)


class TestUserSearchView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_3 = AuthUserFactory(fullname='Reby Sky')
        self.user_4 = AuthUserFactory(fullname='King Maxel Hardy')

        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.UserFormView()
        self.view = setup_form_view(self.view, self.request, form=UserSearchForm())

    def test_search_user_by_guid(self):
        form_data = {
            'guid': self.user_1.guids.first()._id
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_1.guids.first()._id))

    def test_search_user_by_name(self):
        form_data = {
            'name': 'Hardy'
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/search/Hardy/')

    def test_search_user_by_name_with_punctuation(self):
        form_data = {
            'name': '~Dr. Sportello-Fay, PI'
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, furl.quote('/users/search/~Dr. Sportello-Fay, PI/', safe='/.,~'))

    def test_search_user_by_username(self):
        form_data = {
            'email': self.user_1.username
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_1.guids.first()._id))

    def test_search_user_by_alternate_email(self):
        form_data = {
            'email': self.user_2_alternate_email
        }
        form = UserSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(self.view.success_url, '/users/{}/'.format(self.user_2.guids.first()._id))

    def test_search_user_list(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'Hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)

    def test_search_user_list_case_insensitive(self):
        view = views.UserSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)


class TestGetLinkView(AdminTestCase):

    def test_get_user_confirmation_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        user_token = user.email_verifications.keys()[0]
        ideal_link_path = '/confirm/{}/{}/'.format(user._id, user_token)
        link = view.get_link(user)
        link_path = str(furl.furl(link).path)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_user_confirmation_link_with_expired_token(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetUserConfirmationLink()
        view = setup_view(view, request, guid=user._id)

        old_user_token = user.email_verifications.keys()[0]
        user.email_verifications[old_user_token]['expiration'] = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(hours=24)
        user.save()

        link = view.get_link(user)
        new_user_token = user.email_verifications.keys()[0]

        link_path = str(furl.furl(link).path)
        ideal_link_path = '/confirm/{}/{}/'.format(user._id, new_user_token)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_password_reset_link(self):
        user = UnconfirmedUserFactory()
        request = RequestFactory().get('/fake_path')
        view = views.GetPasswordResetLink()
        view = setup_view(view, request, guid=user._id)

        link = view.get_link(user)

        user_token = user.verification_key_v2.get('token')
        nt.assert_is_not_none(user_token)

        ideal_link_path = '/resetpassword/{}/{}'.format(user._id, user_token)
        link_path = str(furl.furl(link).path)

        nt.assert_equal(link_path, ideal_link_path)

    def test_get_unclaimed_node_links(self):
        project = ProjectFactory()
        unregistered_contributor = project.add_unregistered_contributor(fullname='Brother Nero', email='matt@hardyboyz.biz', auth=Auth(project.creator))
        project.save()

        request = RequestFactory().get('/fake_path')
        view = views.GetUserClaimLinks()
        view = setup_view(view, request, guid=unregistered_contributor._id)

        links = view.get_claim_links(unregistered_contributor)
        unclaimed_records = unregistered_contributor.unclaimed_records

        nt.assert_equal(len(links), 1)
        nt.assert_equal(len(links), len(unclaimed_records.keys()))
        link = links[0]

        nt.assert_in(project._id, link)
        nt.assert_in(unregistered_contributor.unclaimed_records[project._id]['token'], link)


class TestUserReindex(AdminTestCase):
    def setUp(self):
        super(TestUserReindex, self).setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()

    @mock.patch('website.search.search.update_user')
    def test_reindex_user_elastic(self, mock_reindex_elastic):
        count = AdminLogEntry.objects.count()
        view = views.UserReindexElastic()
        view = setup_log_view(view, self.request, guid=self.user._id)
        view.delete(self.request)

        nt.assert_true(mock_reindex_elastic.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

class TestUserMerge(AdminTestCase):
    def setUp(self):
        super(TestUserMerge, self).setUp()
        self.request = RequestFactory().post('/fake_path')

    @mock.patch('osf.models.user.OSFUser.merge_user')
    def test_merge_user(self, mock_merge_user):
        user = UserFactory()
        user_merged = UserFactory()

        view = views.UserMergeAccounts()
        view = setup_log_view(view, self.request, guid=user._id)

        invalid_form = MergeUserForm(data={'user_guid_to_be_merged': 'Not a valid Guid'})
        valid_form = MergeUserForm(data={'user_guid_to_be_merged': user_merged._id})

        nt.assert_false(invalid_form.is_valid())
        nt.assert_true(valid_form.is_valid())

        view.form_valid(valid_form)
        nt.assert_true(mock_merge_user.called_with())
