import mock
import pytest
from django.core.exceptions import SuspiciousOperation, PermissionDenied
from django.http import Http404, JsonResponse
from django.test import RequestFactory
from django.urls import reverse
from nose import tools as nt

from admin.rdm_custom_storage_location.export_data.views import management
from admin_tests.utilities import setup_view
from osf.models import ExportData, ExportDataRestore
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExportDataFactory,
    RegionFactory,
    ExportDataRestoreFactory,
)
from tests.base import AdminTestCase
from admin_tests.rdm_custom_storage_location.export_data.test_utils import FAKE_DATA, FAKE_DATA_NEW


class FakeRes:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        data = FAKE_DATA
        return data


@pytest.mark.feature_202210
class TestExportBaseView(AdminTestCase):
    def setUp(self):
        super(TestExportBaseView, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = management.ExportBaseView()
        self.view.request = self.request
        self.view.kwargs = {}

    def test_load_institution(self):
        response = self.view.load_institution()
        nt.assert_equal(response, None)


@pytest.mark.feature_202210
class TestMethodGetExportData(AdminTestCase):
    def setUp(self):
        super(TestMethodGetExportData, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data.save()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    def test_method(self, mock_export_data):
        mock_export_data.filter.return_value = self.export_data.objects
        mock_export_data.order_by.return_value = [self.export_data]
        res = management.get_export_data(self.institution._id, check_delete=False)
        nt.assert_is_instance(res, list)


@pytest.mark.feature_202210
class TestExportDataListView(AdminTestCase):
    def setUp(self):
        super(TestExportDataListView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.region = RegionFactory(_id=self.institution._id, name='Storage')
        self.region._id = self.institution._id
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.institution.save()
        self.region.save()
        self.view = management.ExportDataListView()
        self.request = RequestFactory().get('/fake_path')
        self.request.GET = {'location_id': 1, 'storage_id': 1}
        self.request.user = self.user
        self.view = setup_view(self.view,
                               self.request,
                               institution_id=self.institution.id)

    def test_get(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        mock_render = mock.MagicMock()
        mock_render.return_value = None

        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportBaseView', mock_class):
            with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                res = self.view.get(self.request)
                nt.assert_equal(res, None)


@pytest.mark.feature_202210
class TestExportDataDeletedListView(AdminTestCase):
    def setUp(self):
        super(TestExportDataDeletedListView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.view = management.ExportDataDeletedListView()
        self.institution = InstitutionFactory()
        self.request = RequestFactory().get(
            reverse('custom_storage_location:export_data:export_data_deleted_list'))
        self.request.user = self.user
        self.view = setup_view(self.view,
                               self.request)

    def test_get(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        mock_render = mock.MagicMock()
        mock_render.return_value = None

        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportBaseView', mock_class):
            with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                res = self.view.get(self.request)
                nt.assert_equal(res, None)


@pytest.mark.feature_202210
class TestExportDataInformationView(AdminTestCase):
    def setUp(self):
        super(TestExportDataInformationView, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.view = management.ExportDataInformationView()
        self.export_data = ExportDataFactory()
        self.institution = InstitutionFactory(_id=self.export_data.source.guid)

    def test_get_success(self):
        mock_render = mock.MagicMock()
        mock_render.return_value = None
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request = mock.MagicMock()
        fake_res = FakeRes(200)
        mock_request.get.return_value = fake_res
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                    res = view.get(request)
                    nt.assert_equal(res, None)

    def test_get_success_not_admin(self):
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        mock_render = mock.MagicMock()
        mock_render.return_value = None
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request = mock.MagicMock()
        fake_res = FakeRes(200)
        mock_request.get.return_value = fake_res
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.render', mock_render):
                    res = view.get(request)
                    nt.assert_equal(res, None)

    @mock.patch('osf.models.export_data.requests')
    def test_get_file_info_not_valid(self, mock_request):
        fake_res = FakeRes(200)
        mock_request.get.return_value = fake_res
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        with self.assertRaises(SuspiciousOperation):
            view.get(request)

    def test_get_not_found(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=0)
        with self.assertRaises(Http404):
            view.get(request)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportDataInformationView.handle_no_permission')
    def test_get_object_permission_error_non_existent_institution(self, mock_handle_no_permission):
        test_user = AuthUserFactory()
        test_region = RegionFactory(_id='')
        test_export_data = ExportDataFactory(source=test_region)
        request = RequestFactory().get('/fake_path')
        request.user = test_user
        request.COOKIES = '213919sdasdn823193929'

        mock_handle_no_permission.side_effect = PermissionDenied()

        view = management.ExportDataInformationView()
        view = setup_view(view, request, institution_id=self.institution.id, data_id=test_export_data.id)
        with self.assertRaises(PermissionDenied):
            view.get_object()
            mock_handle_no_permission.assert_called()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportDataInformationView.handle_no_permission')
    def test_get_object_permission_error_not_related_institution(self, mock_handle_no_permission):
        test_user = AuthUserFactory()
        test_institution_id = 2 if self.institution.id != 2 else 1
        test_institution = InstitutionFactory(id=test_institution_id)
        request = RequestFactory().get('/fake_path')
        request.user = test_user
        request.COOKIES = '213919sdasdn823193929'

        mock_handle_no_permission.side_effect = PermissionDenied()

        view = management.ExportDataInformationView()
        view = setup_view(view, request, institution_id=test_institution.id, data_id=self.export_data.id)
        with self.assertRaises(PermissionDenied):
            view.get_object()
            mock_handle_no_permission.assert_called()


@pytest.mark.feature_202210
class TestCheckExportData(AdminTestCase):
    def setUp(self):
        super(TestCheckExportData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()

    def test_export_data_not_completed(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        export_data = self.export_data
        export_data.status = ExportData.STATUS_CHECKING
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    def test_cannot_connect_to_storage(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    def test_validate_fail(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = FakeRes(200)
        self.export_data.status = ExportData.STATUS_RUNNING
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.check_for_file_existent_on_export_location')
    @mock.patch.object(ExportData, 'extract_file_information_json_from_source_storage')
    def test_check_export_data_successful(self, mock_class, mock_check_exist):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'

        def side_effect(cookie):
            return '', FAKE_DATA_NEW

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_validate = mock.MagicMock()
        mock_check_exist.return_value = []
        mock_validate.return_value = True
        mock_request.get.return_value = FakeRes(200)
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
                    res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 200)


@pytest.mark.feature_202210
class TestCheckRestoreData(AdminTestCase):
    def setUp(self):
        super(TestCheckRestoreData, self).setUp()
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory()
        self.export_data_restore.export = self.export_data

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_restore_data_with_status_not_completed_and_get_from_request(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}
        export_data = self.export_data
        export_data.status = ExportData.STATUS_CHECKING

        def side_effect(destination_id=100):
            return export_data

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored')
    def test_restore_data_not_completed_and_not_from_request(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        export_data = self.export_data
        export_data.status = ExportData.STATUS_CHECKING

        def side_effect(destination_id=100):
            return export_data

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            res = view.get(request, data_id=export_data.id)
        nt.assert_equal(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_check_restore_data_cannot_connect_to_storage(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}
        export_data = self.export_data

        def side_effect(destination_id=100):
            return self.export_data_restore

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
        mock_export_data.filter.return_value.first.return_value = export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    def test_check_restore_data_with_validate_fail(self, mock_class):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}
        self.export_data_restore.status = ExportData.STATUS_RUNNING

        def side_effect(destination_id=100):
            return self.export_data_restore

        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_request.get.return_value = FakeRes(200)
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    @mock.patch.object(ExportDataRestore, 'extract_file_information_json_from_destination_storage')
    def test_check_restore_data_successful(self, mock_class_export, mock_class_restore):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}

        def side_effect_export_data(cookie):
            return '', FAKE_DATA_NEW

        def side_effect_export_data_restore(destination_id=100):
            return self.export_data_restore

        mock_class_export.side_effect = side_effect_export_data
        mock_class_restore.side_effect = side_effect_export_data_restore
        mock_export_data = mock.MagicMock()
        mock_request = mock.MagicMock()
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        mock_request.get.return_value = FakeRes(200)
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                with mock.patch('admin.rdm_custom_storage_location.export_data.views.management.validate_exported_data', mock_validate):
                    res = view.get(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 200)


@pytest.mark.feature_202210
class TestExportDataFileCSVView(AdminTestCase):
    def setUp(self):
        super(TestExportDataFileCSVView, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.export_data = ExportDataFactory()
        self.view = management.ExportDataFileCSVView()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.read_file_info_from_location')
    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportDataFileCSVView.get_object')
    def test_get(self, mock_get_object, mock_read_file_info):
        mock_get_object.return_value = self.export_data
        mock_read_file_info.return_value = FakeRes(200)
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        view = setup_view(self.view, request)
        res = view.get(request)
        nt.assert_equal(res.status_code, 200)


@pytest.mark.feature_202210
class TestDeleteExportDataView(AdminTestCase):
    def setUp(self):
        super(TestDeleteExportDataView, self).setUp()
        self.user = AuthUserFactory()
        self.export_data = ExportDataFactory()
        self.institution = InstitutionFactory()
        self.view = management.DeleteExportDataView()

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on', 'selected_source_id': ['100'], 'selected_location_id': ['100']}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_not_soure(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_with_super(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on', 'selected_source_id': ['100'], 'selected_location_id': ['100'], 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_with_super_not_source(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on', 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch('admin.rdm_custom_storage_location.export_data.views.management.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_fail(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=400)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on', 'selected_source_id': ['100'], 'selected_location_id': ['100']}
        view = setup_view(self.view, request)
        with self.assertRaises(SuspiciousOperation):
            view.post(request)

    def test_delete_not_permanently(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'selected_source_id': ['100'], 'selected_location_id': ['100']}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_delete_not_permanently_not_source(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_delete_not_permanently_super(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'selected_source_id': ['100'], 'selected_location_id': ['100'], 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_delete_not_permanently_super_not_source(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

@pytest.mark.feature_202210
class TestRevertExportData(AdminTestCase):
    def setUp(self):
        super(TestRevertExportData, self).setUp()
        self.user = AuthUserFactory()
        self.view = management.RevertExportDataView()
        self.institution = InstitutionFactory()

    def test_post(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': ['100'], 'selected_location_id': ['100']}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_not_source(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': [], 'selected_location_id': []}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_super(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': ['100'], 'selected_location_id': ['100'], 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_super_not_source(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': [], 'selected_location_id': [], 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)
