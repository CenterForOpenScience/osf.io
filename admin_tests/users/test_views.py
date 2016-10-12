from django.test import RequestFactory
from django.http import Http404
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from nose import tools as nt
import mock
import csv
import os
from datetime import datetime

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
        self.user_2 = AuthUserFactory()
        self.user_3 = AuthUserFactory()
        self.data = [
            ['none', 'date', 'thing', 'more', 'less', 'email', 'none'],
            [None, '9/1/16', None, None, None, self.user_1.username, None],
            [None, '9/1/16', None, None, None, self.user_2.username, None],
            [None, '9/1/16', None, None, None, self.user_3.username, None],
        ]
        with open('test.csv', 'w') as fp:
            writer = csv.writer(fp)
            for row in self.data:
                writer.writerow(row)
        self.view = UserWorkshopFormView()

    def test_no_extra_info(self):
        with file('test.csv') as fp:
            final = self.view.parse(fp)
        nt.assert_equal(len(self.data[0]) + 3, len(final[0]))

    def test_one_node(self):
        node = ProjectFactory(creator=self.user_1)
        node.add_log(
            'log_added',
            params={'project': node.pk},
            auth=self.auth_1,
            log_date=datetime.utcnow(),
            save=True
        )
        with file('test.csv') as fp:
            final = self.view.parse(fp)
        nt.assert_equal(1, final[1][-2])
        nt.assert_equal(2, final[1][-3])
        nt.assert_equal(self.user_1.pk, final[1][-4])

    def test_unicode_error(self):
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'unicode.csv')
        with file(path, mode='U') as fp:
            final = self.view.parse(fp)
        nt.assert_in('Unable to parse line:', final[1][0])

    def test_form_valid(self):
        request = RequestFactory().post('/fake_path')
        with file('test.csv', mode='rb') as fp:
            uploaded = SimpleUploadedFile(fp.name, fp.read(), content_type='text/csv')
        form = WorkshopForm(data={'document': uploaded})
        form.is_valid()
        form.cleaned_data['document'] = uploaded
        view = setup_form_view(self.view, request, form)

    def tearDown(self):
        os.remove('test.csv')
