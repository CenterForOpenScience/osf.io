import mock
from nose import tools as nt
from django.test import RequestFactory

from admin.preprints.views import PreprintReindexShare
from admin_tests.utilities import setup_log_view
from osf.models.admin_log_entry import AdminLogEntry
from osf_tests.factories import AuthUserFactory, ProjectFactory, PreprintFactory
from tests.base import AdminTestCase


class TestPreprintReindex(AdminTestCase):
    def setUp(self):
        super(TestPreprintReindex, self).setUp()
        self.request = RequestFactory().post('/fake_path')

        self.user = AuthUserFactory()
        self.preprint = PreprintFactory(creator=self.user)

    @mock.patch('admin.preprints.views.on_preprint_updated')
    def test_reindex_preprint_share(self, mock_reindex_preprint):
        count = AdminLogEntry.objects.count()
        view = PreprintReindexShare()
        view = setup_log_view(view, self.request, guid=self.preprint._id)
        view.delete(self.request)

        nt.assert_true(mock_reindex_preprint.called)
        nt.assert_equal(AdminLogEntry.objects.count(), count + 1)
