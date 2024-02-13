import copy
import json
import mock
import pytest
import uuid
from django.core.exceptions import PermissionDenied
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
    ExportDataLocationFactory,
)
from tests.base import AdminTestCase
from django.contrib.auth.models import AnonymousUser
from admin_tests.rdm_custom_storage_location.export_data.test_utils import FAKE_DATA, FAKE_DATA_NEW, gen_file
from django.http import HttpResponseBadRequest

MANAGEMENT_EXPORT_DATA_PATH = 'admin.rdm_custom_storage_location.export_data.views.management'


class FakeRes:
    def __init__(self, status_code, data=FAKE_DATA):
        self.status_code = status_code
        self._content_data = data

    def json(self):
        return self._content_data


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

    def test_load_institution_not_exist(self):
        self.view.kwargs = {'institution_id': '0'}
        with nt.assert_raises(Http404):
            self.view.load_institution()


@pytest.mark.feature_202210
class TestMethodGetExportData(AdminTestCase):
    def setUp(self):
        super(TestMethodGetExportData, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.export_data = ExportDataFactory()
        self.export_data.save()

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
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
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportBaseView', mock_class):
            mock_render = mock.MagicMock()
            mock_render.return_value = None
            with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render', mock_render):
                res = self.view.get(self.request, institution_id=self.institution.id)
                nt.assert_equal(res, None)

    def test_get_super_not_institution_id(self):
        mock_class = mock.MagicMock()
        mock_class.handle_no_permission.return_value = True
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportBaseView', mock_class):
            mock_render = mock.MagicMock()
            mock_render.return_value = None
            with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render', mock_render):
                res = self.view.get(self.request)
                nt.assert_equal(res.status_code, 302)


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
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportBaseView', mock_class):
            mock_render = mock.MagicMock()
            mock_render.return_value = None
            with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render', mock_render):
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
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_render = mock.MagicMock()
                mock_render.return_value = None
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render', mock_render):
                    request = RequestFactory().get('/fake_path')
                    request.user = self.user
                    request.COOKIES = '213919sdasdn823193929'
                    view = management.ExportDataInformationView()
                    view = setup_view(view, request,
                                    institution_id=self.institution.id, data_id=self.export_data.id)
                    res = view.get(request)
                    nt.assert_equal(res, None)

    def test_get_success_not_admin(self):
        mock_validate = mock.MagicMock()
        mock_validate.return_value = True
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_render = mock.MagicMock()
                mock_render.return_value = None
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render', mock_render):
                    self.user.is_superuser = False
                    self.user.affiliated_institutions.add(self.institution)
                    request = RequestFactory().get('/fake_path')
                    request.user = self.user
                    request.COOKIES = '213919sdasdn823193929'
                    view = management.ExportDataInformationView()
                    view = setup_view(view, request,
                                    institution_id=self.institution.id, data_id=self.export_data.id)
                    res = view.get(request)
                    nt.assert_equal(res, None)

    @mock.patch('osf.models.export_data.requests')
    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render_bad_request_response')
    def test_get_file_info_not_valid(self, mock_render, mock_request):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        mock_request.get.return_value = FakeRes(200)
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        view = management.ExportDataInformationView()
        view = setup_view(view, request,
                          institution_id=self.institution.id, data_id=self.export_data.id)
        res = view.get(request)
        nt.assert_equal(res.status_code, 400)

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

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportDataInformationView.handle_no_permission')
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

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportDataInformationView.handle_no_permission')
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

        self.institution01 = InstitutionFactory(name='inst01')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_01_location = ExportDataLocationFactory(institution_guid=self.institution01._id)

        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.export_data_02_location = ExportDataLocationFactory(institution_guid=self.institution02._id)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    def test_export_data_not_completed(self):
        export_data = self.export_data
        export_data.status = ExportData.STATUS_CHECKING
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            request = RequestFactory().get('/fake_path')
            request.user = self.user
            request.COOKIES = '213919sdasdn823193929'
            view = management.CheckExportData()
            view.export_data = export_data
            view = setup_view(view, request, data_id=export_data.id)
            res = view.get(request, data_id=export_data.id)
            nt.assert_equal(res.status_code, 400)

    def test_cannot_connect_to_storage(self):
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
            with mock.patch('osf.models.export_data.requests', mock_request):
                request = RequestFactory().get('/fake_path')
                request.user = self.user
                request.COOKIES = '213919sdasdn823193929'
                view = management.CheckExportData()
                view = setup_view(view, request, data_id=self.export_data.id)
                view.export_data = self.export_data
                res = view.get(request, data_id=self.export_data.id)
                nt.assert_equals(res.status_code, 400)

    def test_validate_fail(self):
        mock_export_data = mock.MagicMock()
        self.export_data.status = ExportData.STATUS_RUNNING
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                request = RequestFactory().get('/fake_path')
                request.user = self.user
                request.COOKIES = '213919sdasdn823193929'
                view = management.CheckExportData()
                view = setup_view(view, request, data_id=self.export_data.id)
                view.export_data = self.export_data
                res = view.get(request, data_id=self.export_data.id)
                nt.assert_equals(res.status_code, 400)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.check_for_file_existent_on_export_location')
    @mock.patch.object(ExportData, 'extract_file_information_json_from_source_storage')
    def test_check_export_data_successful(self, mock_class, mock_check_exist):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'

        def side_effect():
            return '', FAKE_DATA_NEW
        mock_class.side_effect = side_effect
        mock_export_data = mock.MagicMock()
        mock_check_exist.return_value = []
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_validate = mock.MagicMock()
                mock_validate.return_value = True
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
                    view = management.CheckExportData()
                    view = setup_view(view, request, data_id=self.export_data.id)
                    view.export_data = self.export_data
                    res = view.get(request, data_id=self.export_data.id)
                    nt.assert_equals(res.status_code, 200)

    def test__dispatch_anonymous(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.anon
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)

    def test__dispatch_not_exist(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=0)
        res = view.dispatch(request)
        nt.assert_equals(res.status_code, 404)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.check_for_file_existent_on_export_location')
    @mock.patch.object(ExportData, 'extract_file_information_json_from_source_storage')
    def test__dispatch_success(self, mock_class, mock_check_exist):
        def side_effect():
            return '', FAKE_DATA_NEW

        mock_class.side_effect = side_effect
        mock_check_exist.return_value = []
        self.export_data.source._id = 'vcu'
        mock_export_data = mock.MagicMock()
        mock_export_data.filter.return_value.first.return_value = self.export_data

        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_validate = mock.MagicMock()
                mock_validate.return_value = True
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
                    request = RequestFactory().get('/fake_path')
                    request.user = self.superuser
                    request.COOKIES = '213919sdasdn823193929'
                    view = management.CheckExportData()
                    view = setup_view(view, request, data_id=self.export_data.id)
                    res = view.dispatch(request)
                    nt.assert_equals(res.status_code, 200)

    def test__test_func_normal_user(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.normal_user
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        view.export_data = self.export_data
        nt.assert_false(view.test_func())

    def test__test_func_super(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data.id)
        view.export_data = self.export_data
        nt.assert_true(view.test_func())

    def test__test_func_admin_has_perrmision(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data_01.id)
        view.export_data = self.export_data_01
        nt.assert_true(view.test_func())

    def test__test_func_admin_not_perrmision(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckExportData()
        view = setup_view(view, request, data_id=self.export_data_02.id)
        view.export_data = self.export_data_02
        nt.assert_false(view.test_func())


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

        self.institution01 = InstitutionFactory(name='inst01')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_01_location = ExportDataLocationFactory(institution_guid=self.institution01._id)
        self.export_data_restore_01 = ExportDataRestoreFactory()
        self.export_data_restore_01.export = self.export_data_01

        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.export_data_02_location = ExportDataLocationFactory(institution_guid=self.institution02._id)
        self.export_data_restore_02 = ExportDataRestoreFactory()
        self.export_data_restore_02.export = self.export_data_02

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

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

        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            view = management.CheckRestoreData()
            view = setup_view(view, request, data_id=export_data.id)
            view.export_data = self.export_data
            view.institution_id = self.institution.id
            view.destination_id = self.export_data.source.id
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

        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            view = management.CheckRestoreData()
            view = setup_view(view, request, data_id=export_data.id)
            view.export_data = self.export_data
            view.institution_id = self.institution.id
            view.destination_id = self.export_data.source.id
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
        mock_export_data.filter.return_value.first.return_value = export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = JsonResponse({'message': ''}, status=400)
            with mock.patch('osf.models.export_data.requests', mock_request):
                view = management.CheckRestoreData()
                view = setup_view(view, request, data_id=export_data.id)
                view.export_data = self.export_data
                view.institution_id = self.institution.id
                view.destination_id = self.export_data.source.id
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

        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            with mock.patch('osf.models.export_data.requests', mock_request):
                view = management.CheckRestoreData()
                view = setup_view(view, request, data_id=self.export_data.id)
                view.export_data = self.export_data
                view.institution_id = self.institution.id
                view.destination_id = self.export_data.source.id
                res = view.get(request, data_id=self.export_data.id)
                nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    @mock.patch.object(ExportDataRestore, 'extract_file_information_json_from_destination_storage')
    def test_check_restore_data__successful(self, mock_extract_file, mock_get_latest_restore):
        def side_effect_export_data():
            return '', FAKE_DATA_NEW

        def side_effect_export_data_restore(destination_id=100):
            return self.export_data_restore

        mock_extract_file.side_effect = side_effect_export_data
        mock_get_latest_restore.side_effect = side_effect_export_data_restore

        mock_export_data = mock.MagicMock()
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_validate = mock.MagicMock()
                mock_validate.return_value = True
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
                    request = RequestFactory().get('/fake_path')
                    request.user = self.user
                    request.COOKIES = '213919sdasdn823193929'
                    request.GET = {'destination_id': 100}
                    view = management.CheckRestoreData()
                    view = setup_view(view, request, data_id=self.export_data.id)
                    view.export_data = self.export_data
                    view.institution_id = self.institution.id
                    view.destination_id = self.export_data.source.id
                    res = view.get(request, data_id=self.export_data.id)

        nt.assert_equals(res.status_code, 200)
        content_data = json.loads(res.content.decode())
        # check quantity
        nt.assert_equal(content_data['ok'] + content_data['ng'], content_data['total'])
        nt.assert_equal(len(content_data['list_file_ng']), content_data['ng'])

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    @mock.patch.object(ExportDataRestore, 'extract_file_information_json_from_destination_storage')
    def test_check_restore_data__successful__when_location_change(self, mock_extract_file, mock_get_latest_restore):
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.GET = {'destination_id': 100}

        # file_id=1~files_len
        files_len = 3
        files_old = [gen_file(i, version_n=5) for i in range(1, files_len + 1, 1)]
        fake_data_json = copy.deepcopy(FAKE_DATA_NEW)
        fake_data_json['files'] = files_old

        def side_effect_export_data():
            return '', fake_data_json

        # simulate the case where the location is changed
        files_new = []
        for file_info in copy.deepcopy(files_old):
            version_list = file_info['version']
            latest_version = version_list[0]
            latest_ver_location = latest_version['location']
            # e.g. re-deploy WB server
            latest_ver_location['host'] = uuid.uuid4().hex[:12],
            # e.g. change only the bucket
            latest_ver_location['bucket'] = 'grdm-ierae-new',
            file_info['location'] = latest_version['location']
            files_new.append(file_info)
        fake_data_json['files'] = files_new

        def side_effect_export_data_restore(destination_id=100):
            return self.export_data_restore

        mock_extract_file.side_effect = side_effect_export_data
        mock_get_latest_restore.side_effect = side_effect_export_data_restore

        mock_export_data = mock.MagicMock()
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200, fake_data_json)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_validate = mock.MagicMock()
                mock_validate.return_value = True
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
                    view = management.CheckRestoreData()
                    view = setup_view(view, request, data_id=self.export_data.id)
                    view.export_data = self.export_data
                    view.institution_id = self.institution.id
                    view.destination_id = self.export_data.source.id
                    res = view.get(request, data_id=self.export_data.id)

        nt.assert_equals(res.status_code, 200)
        content_data = json.loads(res.content.decode())
        # check quantity
        nt.assert_equal(content_data['ng'], 0)
        nt.assert_equal(len(content_data['list_file_ng']), content_data['ng'])
        nt.assert_equal(content_data['ok'], content_data['total'])

    def test__dispatch_anonymous(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.anon
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)

    def test__dispatch_not_exist(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=0)
        res = view.dispatch(request)
        nt.assert_equals(res.status_code, 404)

        # not exist destination_id
        request.GET = {'destination_id': '0'}
        view.request = request
        view = setup_view(view, request, data_id=self.export_data.id)
        res = view.dispatch(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 404)

    def test__dispatch_not_valid(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        request.GET = {'destination_id': 'fake_id'}
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        view.request = request
        res = view.dispatch(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 400)

    @mock.patch.object(ExportData, 'get_latest_restored_data_with_destination_id')
    @mock.patch.object(ExportDataRestore, 'extract_file_information_json_from_destination_storage')
    def test__dispatch_success(self, mock_class_export, mock_class_restore):
        def side_effect_export_data():
            return '', FAKE_DATA_NEW

        def side_effect_export_data_restore(destination_id=100):
            return self.export_data_restore

        mock_class_export.side_effect = side_effect_export_data
        mock_class_restore.side_effect = side_effect_export_data_restore
        mock_export_data = mock.MagicMock()
        self.export_data.source._id = 'vcu'
        mock_export_data.filter.return_value.first.return_value = self.export_data
        with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects', mock_export_data):
            mock_request = mock.MagicMock()
            mock_request.get.return_value = FakeRes(200)
            with mock.patch('osf.models.export_data.requests', mock_request):
                mock_validate = mock.MagicMock()
                mock_validate.return_value = True
                with mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.validate_exported_data', mock_validate):
                    request = RequestFactory().get('/fake_path')
                    request.user = self.superuser
                    request.COOKIES = '213919sdasdn823193929'
                    request.GET = {'destination_id': str(self.region_inst_01.id)}
                    view = management.CheckRestoreData()
                    view = setup_view(view, request, data_id=self.export_data.id)
                    view.request = request
                    res = view.dispatch(request, data_id=self.export_data.id)
        nt.assert_equals(res.status_code, 200)

    def test__test_func_normal_user(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.normal_user
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        view.export_data = self.export_data
        nt.assert_false(view.test_func())

    def test__test_func_super(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data.id)
        view.export_data = self.export_data
        nt.assert_true(view.test_func())

    def test__test_func_admin_has_permission(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data_01.id)
        view.export_data = self.export_data_01
        nt.assert_true(view.test_func())

    def test__test_func_admin_not_permission(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        view = management.CheckRestoreData()
        view = setup_view(view, request, data_id=self.export_data_02.id)
        view.export_data = self.export_data_02
        nt.assert_false(view.test_func())


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

        self.institution01 = InstitutionFactory(name='inst01')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_01_location = ExportDataLocationFactory(institution_guid=self.institution01._id)

        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.export_data_02_location = ExportDataLocationFactory(institution_guid=self.institution02._id)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.read_file_info_from_location')
    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportDataFileCSVView.get_object')
    def test_get(self, mock_get_object, mock_read_file_info):
        mock_get_object.return_value = self.export_data
        mock_read_file_info.return_value = FakeRes(200)
        request = RequestFactory().get('/fake_path')
        request.user = self.user
        view = setup_view(self.view, request)
        res = view.get(request)
        nt.assert_equal(res.status_code, 200)

    def test__test_func_anonymus(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.anon
        view = setup_view(self.view, request)
        nt.assert_false(view.test_func())

    def test__test_func_normal_user(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.normal_user
        view = setup_view(self.view, request)
        nt.assert_false(view.test_func())

    def test__test_func_super_user(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.superuser
        view = setup_view(self.view, request)
        nt.assert_true(view.test_func())

    def test__test_func_admin_has_perrmision(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        view = setup_view(self.view, request)
        nt.assert_true(view.test_func())

    def test__test_func_admin_not_permission(self):
        request = RequestFactory().get('/fake_path')
        self.institution01_admin.affiliated_institutions.clear()
        self.institution01_admin.save()
        request.user = self.institution01_admin
        view = setup_view(self.view, request)
        nt.assert_false(view.test_func())

    def test__test_get_object_success(self):
        request = RequestFactory().get('/fake_path')
        request.user = self.institution01_admin
        view = setup_view(self.view, request, data_id=self.export_data_01.id)
        nt.assert_is_not_none(view.get_object())

    def test__test_get_object_not_permission(self):
        request = RequestFactory().get('/fake_path')
        self.institution01_admin.affiliated_institutions.clear()
        self.institution01_admin.save()
        request.user = self.institution01_admin
        view = setup_view(self.view, request, data_id=self.export_data_02.id)
        with nt.assert_raises(PermissionDenied):
            view.get_object()

    def test__test_get_object_not_exit(self):
        request = RequestFactory().get('/fake_path')
        self.institution01_admin.affiliated_institutions.clear()
        self.institution01_admin.save()
        request.user = self.institution01_admin
        view = setup_view(self.view, request, data_id=0)
        with nt.assert_raises(Http404):
            view.get_object()


@pytest.mark.feature_202210
class TestDeleteExportDataView(AdminTestCase):
    def setUp(self):
        super(TestDeleteExportDataView, self).setUp()
        self.user = AuthUserFactory()
        self.export_data = ExportDataFactory()
        self.institution = InstitutionFactory()
        self.view = management.DeleteExportDataView()

        self.institution01 = InstitutionFactory(name='inst01')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_01_location = ExportDataLocationFactory(institution_guid=self.institution01._id)

        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.export_data_02_location = ExportDataLocationFactory(institution_guid=self.institution02._id)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on',
                         'selected_source_id': '100', 'selected_location_id': '100'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
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

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    def test_delete_permanently_with_super(self, mock_request, mock_export_data):
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on',
                         'selected_source_id': '100', 'selected_location_id': '100',
                         'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
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

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('osf.models.export_data.requests')
    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render_bad_request_response')
    def test_delete_permanently_fail(self, mock_render, mock_request, mock_export_data):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        mock_export_data.filter.return_value = [self.export_data]
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=400)
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '3#', 'delete_permanently': 'on',
                         'selected_source_id': '100', 'selected_location_id': '100'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 400)

    def test_delete_not_permanently(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off',
                         'selected_source_id': '100', 'selected_location_id': '100'}
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
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'selected_source_id': '100',
                         'selected_location_id': '100', 'institution_id': self.institution.id}
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

    def test_delete_anonymous(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.anon
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'institution_id': self.institution.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

    def test_delete_normal_user(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.normal_user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'delete_permanently': 'off', 'institution_id': self.institution.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

    def test_delete_super_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                         'delete_permanently': 'off', 'institution_id': self.institution01.id}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 302)

    def test_delete_super_not_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'

        # list_id_export_data not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # list_id_export_data with multi value not same institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # selected_source_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_02.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # selected_location_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_02_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # institution_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution02.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

    def test_delete_admin_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 302)

    def test_delete_admin_not_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'

        # list_id_export_data not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # list_id_export_data with multi value not same institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # selected_source_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_02.id,
                        'selected_location_id': self.export_data_01_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # selected_location_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_02_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # institution_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution02.id}
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

        # admin not in institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution01.id}
        self.institution01_admin.affiliated_institutions = []
        request.user = self.institution01_admin
        with self.assertRaises(PermissionDenied):
            management.DeleteExportDataView.as_view()(request)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render_bad_request_response')
    def test_delete_with_invalid_request_body(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        # list_id_export_data not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#abc#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution01.id}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # selected_source_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': 'abc',
                        'selected_location_id': self.export_data_01_location.id, 'delete_permanently': 'off',
                        'institution_id': self.institution01.id}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # selected_location_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': 'abc',
                        'delete_permanently': 'off', 'institution_id': self.institution01.id}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # institution_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': 'abc'}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # institution_id is missing value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'delete_permanently': 'off', 'institution_id': None}
        res = management.DeleteExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)


@pytest.mark.feature_202210
class TestRevertExportData(AdminTestCase):
    def setUp(self):
        super(TestRevertExportData, self).setUp()
        self.user = AuthUserFactory()
        self.view = management.RevertExportDataView()
        self.institution = InstitutionFactory()

        self.institution01 = InstitutionFactory(name='inst01')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_01.is_deleted = True
        self.export_data_01.save()
        self.export_data_01_location = ExportDataLocationFactory(institution_guid=self.institution01._id)

        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.export_data_02.is_deleted = True
        self.export_data_02.save()
        self.export_data_02_location = ExportDataLocationFactory(institution_guid=self.institution02._id)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    def test_post(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': '100', 'selected_location_id': '100'}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_not_source(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': None, 'selected_location_id': None}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_super(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': '100',
                        'selected_location_id': '100', 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_post_super_not_source(self):
        request = RequestFactory().post('/fake_path')
        self.user.is_superuser = True
        request.user = self.user
        request.POST = {'list_id_export_data': '1000#', 'selected_source_id': None,
                        'selected_location_id': None, 'institution_id': self.institution.id}
        view = setup_view(self.view, request)
        res = view.post(request)
        nt.assert_equal(res.status_code, 302)

    def test_revert_anonymous(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.anon
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'institution_id': self.institution.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

    def test_revert_normal_user(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.normal_user
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': '4#', 'institution_id': self.institution.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

    def test_revert_super_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'institution_id': self.institution01.id}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 302)

    def test_revert_super_not_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'

        # list_id_export_data not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_02.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # list_id_export_data with multi value not same institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # selected_source_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_02.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # selected_location_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_02_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # institution_id not same institution of other parameter
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution02.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

    def test_revert_admin_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 302)

    def test_revert_admin_not_permission(self):
        request = RequestFactory().post('/fake_path')
        request.user = self.institution01_admin
        request.COOKIES = '213919sdasdn823193929'

        # list_id_export_data not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_02.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # list_id_export_data with multi value not same institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#{self.export_data_02.id}#',
                        'selected_source_id': self.region_inst_01.id, 'selected_location_id': self.export_data_01_location.id,
                        'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # selected_source_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_02.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # selected_location_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_02_location.id, 'institution_id': self.institution01.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # institution_id not same institution of login user
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution02.id}
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

        # admin not in institution
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        self.institution01_admin.affiliated_institutions = []
        request.user = self.institution01_admin
        with self.assertRaises(PermissionDenied):
            management.RevertExportDataView.as_view()(request)

    @mock.patch(f'{MANAGEMENT_EXPORT_DATA_PATH}.render_bad_request_response')
    def test_revert_with_invalid_request_body(self, mock_render):
        mock_render.return_value = HttpResponseBadRequest(content='fake')
        request = RequestFactory().post('/fake_path')
        request.user = self.superuser
        request.COOKIES = '213919sdasdn823193929'
        # list_id_export_data not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#abc#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # selected_source_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': 'abc',
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': self.institution01.id}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # selected_location_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': 'abc', 'institution_id': self.institution01.id}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # institution_id not integer value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': 'abc'}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)

        # institution_id is missing value
        request.POST = {'list_id_export_data': f'{self.export_data_01.id}#', 'selected_source_id': self.region_inst_01.id,
                        'selected_location_id': self.export_data_01_location.id, 'institution_id': None}
        res = management.RevertExportDataView.as_view()(request)
        nt.assert_equal(res.status_code, 400)
