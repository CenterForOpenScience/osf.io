import mock
from nose import tools as nt
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from osf.models import Preprint, OSFUser, PreprintLog
from osf_tests.factories import AuthUserFactory, PreprintFactory, PreprintProviderFactory
from osf.models.admin_log_entry import AdminLogEntry

from admin_tests.utilities import setup_view, setup_log_view

from admin.preprints import views
from admin.preprints.forms import ChangeProviderForm


class TestPreprintView(AdminTestCase):

    def setUp(self):
        super(TestPreprintView, self).setUp()
        self.preprint = PreprintFactory()
        self.view = views.PreprintView

    def test_no_guid(self):
        request = RequestFactory().get('/fake_path')
        view = setup_view(self.view(), request)
        preprint = view.get_object()
        nt.assert_is_none(preprint)

    def test_get_object(self):
        request = RequestFactory().get('/fake_path')
        view = setup_view(self.view(), request, guid=self.preprint._id)
        res = view.get_object()
        nt.assert_is_instance(res, Preprint)

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': self.preprint._id}))
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, guid=self.preprint._id)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()

        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': self.preprint._id}))
        request.user = user

        response = self.view.as_view()(request, guid=self.preprint._id)
        nt.assert_equal(response.status_code, 200)

    def test_change_preprint_provider_no_permission(self):
        user = AuthUserFactory()
        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': self.preprint._id}))
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, guid=self.preprint._id)

    def test_change_preprint_provider_correct_permission(self):
        user = AuthUserFactory()

        change_permission = Permission.objects.get(codename='change_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().post(reverse('preprints:preprint', kwargs={'guid': self.preprint._id}))
        request.user = user

        response = self.view.as_view()(request, guid=self.preprint._id)
        nt.assert_equal(response.status_code, 302)

    def test_change_preprint_provider_form(self):
        new_provider = PreprintProviderFactory()
        self.view.kwargs = {'guid': self.preprint._id}
        form_data = {
            'provider': new_provider.id
        }
        form = ChangeProviderForm(data=form_data, instance=self.preprint)
        self.view().form_valid(form)

        nt.assert_equal(self.preprint.provider, new_provider)


class TestPreprintFormView(AdminTestCase):

    def setUp(self):
        super(TestPreprintFormView, self).setUp()
        self.preprint = PreprintFactory()
        self.view = views.PreprintFormView
        self.user = AuthUserFactory()
        self.url = reverse('preprints:search')

    def test_no_user_permissions_raises_error(self):
        request = RequestFactory().get(self.url)
        request.user = self.user
        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request)

    def test_correct_view_permissions(self):

        view_permission = Permission.objects.get(codename='view_preprint')
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request)
        nt.assert_equal(response.status_code, 200)


class TestPreprintReindex(AdminTestCase):
    def setUp(self):
        super(TestPreprintReindex, self).setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)

    @mock.patch('website.preprints.tasks.send_share_preprint_data')
    @mock.patch('website.settings.SHARE_URL', 'ima_real_website')
    def test_reindex_preprint_share(self, mock_reindex_preprint):
        self.preprint.provider.access_token = 'totally real access token I bought from a guy wearing a trenchcoat in the summer'
        self.preprint.provider.save()

        count = AdminLogEntry.objects.count()
        view = views.PreprintReindexShare()
        view = setup_log_view(view, self.request, guid=self.preprint._id)
        view.delete(self.request)

        nt.assert_true(mock_reindex_preprint.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    @mock.patch('website.search.search.update_preprint')
    @mock.patch('website.search.elastic_search.bulk_update_nodes')
    def test_reindex_preprint_elastic(self, mock_update_search, mock_bulk_update_preprints):
        count = AdminLogEntry.objects.count()
        view = views.PreprintReindexElastic()
        view = setup_log_view(view, self.request, guid=self.preprint._id)
        view.delete(self.request)

        nt.assert_true(mock_update_search.called)
        nt.assert_true(mock_bulk_update_preprints.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)


class TestPreprintDeleteView(AdminTestCase):
    def setUp(self):
        super(TestPreprintDeleteView, self).setUp()
        self.preprint = PreprintFactory()
        self.request = RequestFactory().post('/fake_path')
        self.plain_view = views.PreprintDeleteView
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=self.preprint._id)

        self.url = reverse('preprints:remove', kwargs={'guid': self.preprint._id})

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, Preprint)

    def test_get_context(self):
        res = self.view.get_context_data(object=self.preprint)
        nt.assert_in('guid', res)
        nt.assert_equal(res.get('guid'), self.preprint._id)

    def test_remove_preprint(self):
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        self.preprint.refresh_from_db()
        nt.assert_true(self.preprint.deleted)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_restore_preprint(self):
        self.view.delete(self.request)
        self.preprint.refresh_from_db()
        nt.assert_true(self.preprint.deleted)
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        self.preprint.reload()
        nt.assert_false(self.preprint.deleted)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        guid = self.preprint._id
        request = RequestFactory().get(self.url)
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.plain_view.as_view()(request, guid=guid)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()
        guid = self.preprint._id
        change_permission = Permission.objects.get(codename='delete_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        user.user_permissions.add(change_permission)
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(self.url)
        request.user = user

        response = self.plain_view.as_view()(request, guid=guid)
        nt.assert_equal(response.status_code, 200)


class TestRemoveContributor(AdminTestCase):
    def setUp(self):
        super(TestRemoveContributor, self).setUp()
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)
        self.user_2 = AuthUserFactory()
        self.preprint.add_contributor(self.user_2)
        self.preprint.save()
        self.view = views.PreprintRemoveContributorView
        self.request = RequestFactory().post('/fake_path')
        self.url = reverse('preprints:remove_user', kwargs={'guid': self.preprint._id, 'user_id': self.user._id})

    def test_get_object(self):
        view = setup_log_view(self.view(), self.request, guid=self.preprint._id,
                              user_id=self.user._id)
        preprint, user = view.get_object()
        nt.assert_is_instance(preprint, Preprint)
        nt.assert_is_instance(user, OSFUser)

    @mock.patch('admin.preprints.views.Preprint.remove_contributor')
    def test_remove_contributor(self, mock_remove_contributor):
        user_id = self.user_2._id
        preprint_id = self.preprint._id
        view = setup_log_view(self.view(), self.request, guid=preprint_id,
                              user_id=user_id)
        view.delete(self.request)
        mock_remove_contributor.assert_called_with(self.user_2, None, log=False)

    def test_integration_remove_contributor(self):
        nt.assert_in(self.user_2, self.preprint.contributors)
        view = setup_log_view(self.view(), self.request, guid=self.preprint._id,
                              user_id=self.user_2._id)
        count = AdminLogEntry.objects.count()
        view.delete(self.request)
        nt.assert_not_in(self.user_2, self.preprint.contributors)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)

    def test_do_not_remove_last_admin(self):
        nt.assert_equal(
            len(list(self.preprint.get_admin_contributors(self.preprint.contributors))),
            1
        )
        view = setup_log_view(self.view(), self.request, guid=self.preprint._id,
                              user_id=self.user._id)
        count = AdminLogEntry.objects.count()
        view.delete(self.request)
        self.preprint.reload()  # Reloads instance to show that nothing was removed
        nt.assert_equal(len(list(self.preprint.contributors)), 2)
        nt.assert_equal(
            len(list(self.preprint.get_admin_contributors(self.preprint.contributors))),
            1
        )
        nt.assert_equal(AdminLogEntry.objects.count(), count)

    def test_no_log(self):
        view = setup_log_view(self.view(), self.request, guid=self.preprint._id,
                              user_id=self.user_2._id)
        view.delete(self.request)
        nt.assert_not_equal(self.preprint.logs.latest().action, PreprintLog.CONTRIB_REMOVED)

    def test_no_user_permissions_raises_error(self):
        guid = self.preprint._id
        request = RequestFactory().get(self.url)
        request.user = self.user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, guid=guid, user_id=self.user)

    def test_correct_view_permissions(self):
        change_permission = Permission.objects.get(codename='change_preprint')
        view_permission = Permission.objects.get(codename='view_preprint')
        self.user.user_permissions.add(change_permission)
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, guid=self.preprint._id, user_id=self.user._id)
        nt.assert_equal(response.status_code, 200)


class TestPreprintConfirmHamSpamViews(AdminTestCase):
    def setUp(self):
        super(TestPreprintConfirmHamSpamViews, self).setUp()
        self.request = RequestFactory().post('/fake_path')
        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)

    def test_confirm_node_as_ham(self):
        view = views.PreprintConfirmHamView()
        view = setup_log_view(view, self.request, guid=self.preprint._id)
        view.delete(self.request)

        self.preprint.refresh_from_db()
        nt.assert_true(self.preprint.spam_status == 4)

    def test_confirm_node_as_spam(self):
        nt.assert_true(self.preprint.is_public)
        view = views.PreprintConfirmSpamView()
        view = setup_log_view(view, self.request, guid=self.preprint._id)
        view.delete(self.request)

        self.preprint.refresh_from_db()
        nt.assert_true(self.preprint.spam_status == 2)
        nt.assert_false(self.preprint.is_public)
