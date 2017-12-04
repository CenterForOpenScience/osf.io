import mock
from nose import tools as nt
from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import Permission

from tests.base import AdminTestCase
from osf.models import PreprintService
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
        nt.assert_is_instance(res, PreprintService)

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(reverse('preprints:preprint', kwargs={'guid': self.preprint._id}))
        request.user = user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, guid=self.preprint._id)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()

        view_permission = Permission.objects.get(codename='view_preprintservice')
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

        change_permission = Permission.objects.get(codename='change_preprintservice')
        view_permission = Permission.objects.get(codename='view_preprintservice')
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

        view_permission = Permission.objects.get(codename='view_preprintservice')
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
