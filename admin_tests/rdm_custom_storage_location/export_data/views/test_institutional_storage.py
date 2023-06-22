import mock
import pytest
from django.test import RequestFactory
from nose import tools as nt

from admin.rdm_custom_storage_location.export_data.views import institutional_storage
from admin_tests.utilities import setup_view
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    RegionFactory,
)
from tests.base import AdminTestCase


@pytest.mark.feature_202210
class TestExportDataInstitutionListView(AdminTestCase):

    def setUp(self):
        super(TestExportDataInstitutionListView, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = institutional_storage.ExportDataInstitutionListView()
        self.view.request = self.request

    def test_func(self):
        res = self.view.test_func()
        nt.assert_equal(res, True)

    def test_get_queryset(self):
        mock_institution = mock.MagicMock()
        mock_institution.all.return_value.order_by.return_value = self.institution
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.institutional_storage.Institution.objects', mock_institution):
            res = self.view.get_queryset()
            nt.assert_equal(res.id, self.institution.id)

    def test_get_context_data(self):
        view = institutional_storage.ExportDataInstitutionListView()
        view = setup_view(view, self.request)
        view.object_list = view.get_queryset()
        res = view.get_context_data()
        nt.assert_is_not_none(res)


@pytest.mark.feature_202210
class TestExportDataInstitutionalStorageListView(AdminTestCase):

    def setUp(self):
        super(TestExportDataInstitutionalStorageListView, self).setUp()
        self.institution = InstitutionFactory()
        self.region = RegionFactory()
        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = institutional_storage.ExportDataInstitutionalStorageListView()
        self.view.request = self.request
        self.view.kwargs = {
            'institution_id': self.institution.id
        }

    def test_get(self):
        mock_institution = mock.MagicMock()
        mock_institution.get.return_value = self.institution
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.institutional_storage.Institution.objects', mock_institution):
            res = self.view.get(self.request)
            nt.assert_equal(res.status_code, 200)

    def test_get_queryset(self):
        mock_region = mock.MagicMock()
        mock_region.return_value = self.region
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.institutional_storage.Institution.get_institutional_storage', mock_region):
            res = self.view.get_queryset()
            nt.assert_equal(res.id, self.region.id)

    def test_get_context_data(self):
        view = institutional_storage.ExportDataInstitutionalStorageListView()
        view = setup_view(view, self.request)
        mock_institution = mock.MagicMock()
        mock_institution.get.return_value = self.institution
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.institutional_storage.Institution.objects', mock_institution):
            view.object_list = view.get_queryset()
            view.get(self.request)
            res = view.get_context_data()
        nt.assert_is_not_none(res)

@pytest.mark.feature_202210
class TestExportDataListInstitutionListView(AdminTestCase):

    def setUp(self):
        super(TestExportDataListInstitutionListView, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = institutional_storage.ExportDataListInstitutionListView()
        self.view.request = self.request

    def test_func(self):
        res = self.view.test_func()
        nt.assert_equal(res, True)

    def test_get_queryset(self):
        mock_institution = mock.MagicMock()
        mock_institution.all.return_value.order_by.return_value = self.institution
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.institutional_storage.Institution.objects', mock_institution):
            res = self.view.get_queryset()
            nt.assert_equal(res.id, self.institution.id)

    def test_get_context_data(self):
        view = institutional_storage.ExportDataListInstitutionListView()
        view = setup_view(view, self.request)
        view.object_list = view.get_queryset()
        res = view.get_context_data()
        nt.assert_is_not_none(res)
