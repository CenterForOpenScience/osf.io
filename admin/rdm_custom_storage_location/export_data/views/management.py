# -*- coding: utf-8 -*-
import csv
import datetime
import inspect  # noqa
import logging

from django.db import transaction
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.urls import reverse
from django.views.generic import ListView

from admin.rdm.utils import RdmPermissionMixin
from admin.rdm_custom_storage_location.export_data.utils import (
    process_data_information,
    validate_exported_data,
    count_files_ng_ok,
    check_for_file_existent_on_export_location,
)
from osf.models import ExportData, Institution, ExportDataLocation, ExportDataRestore
from website.util import inspect_info  # noqa
from .location import ExportStorageLocationViewBaseView
from addons.osfstorage.models import Region
from django.contrib.auth.mixins import UserPassesTestMixin
from admin.rdm.utils import get_institution_id_by_region
from admin.base.utils import render_bad_request_response

logger = logging.getLogger(__name__)


def get_export_data(institution_guid, selected_location_id=None, selected_source_id=None, deleted=False,
                    check_delete=True, selected_source_name=None):
    institution = Institution.load(institution_guid)
    locations = institution.get_allowed_storage_location()
    list_location_id = locations.values_list('id', flat=True)

    source_storages = institution.get_institutional_storage()
    list_source_id = source_storages.values_list('id', flat=True)

    # Get export data following user_institution_guid
    list_export_data = ExportData.objects.filter(
        location_id__in=list_location_id,
        source_id__in=list_source_id,
        status__in=ExportData.EXPORT_DATA_AVAILABLE
    )
    if check_delete:
        list_export_data = list_export_data.filter(is_deleted=deleted)
    if selected_location_id:
        list_export_data = list_export_data.filter(location_id=selected_location_id)
    if selected_source_id:
        list_export_data = list_export_data.filter(source_id=selected_source_id)
    if selected_source_name:
        list_export_data = list_export_data.filter(source_name=selected_source_name)
    list_export_data = list_export_data.order_by('-id')

    list_data = []
    for export_data in list_export_data:
        data = {
            'export_data': export_data,
            'location_name': export_data.location.name,
            'source_id': export_data.source.id,
            'source_name': export_data.source_name if export_data.source_name is not None else ''
        }
        list_data.append(data)
    return list_data


class ExportBaseView(ExportStorageLocationViewBaseView, ListView):
    raise_exception = True
    paginate_by = 10

    def get_queryset(self):
        raise NotImplementedError(
            '{0} is missing the implementation of the get_queryset() method.'.format(self.__class__.__name__)
        )

    def get_context_data(self, **kwargs):
        return super(ExportBaseView, self).get_context_data(**kwargs)

    def load_institution(self):
        institution_id = self.kwargs.get('institution_id')

        if institution_id:
            # superuser admin can access it
            try:
                self.institution = Institution.objects.get(id=institution_id, is_deleted=False)
                self.institution_guid = self.institution.guid
            except Institution.DoesNotExist:
                raise Http404(f'Institution with id {institution_id} not found')
        else:
            # institutional admin access without institution_id -> get from representative_affiliated_institution
            if not institution_id and self.request.user.is_affiliated_institution:
                self.institution = self.request.user.representative_affiliated_institution
                if self.institution:
                    self.institution_guid = self.institution.guid
                    institution_id = self.institution.id

            # skip if institution_id
            if not institution_id and self.is_super_admin:
                self.institution = Institution.objects.first()
                self.institution_guid = self.institution.guid
                institution_id = self.institution.id

        # skip if is_affiliated_institution
        # institutional admin access with invalid institution_id
        if not self.is_super_admin and not self.is_affiliated_institution(institution_id):
            self.handle_no_permission()


class ExportDataListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_list.html'

    def get(self, request, *args, **kwargs):
        if self.is_super_admin and not kwargs.get('institution_id'):
            return redirect(reverse('custom_storage_location:export_data:export_data_list_institutions'))

        self.load_institution()

        locations = self.institution.get_allowed_storage_location()
        selected_location_id = request.GET.get('location_id')
        if not selected_location_id and locations.exists():
            selected_location_id = locations.first().id

        source_storages = self.institution.get_institutional_storage()
        selected_source_id = self.kwargs.get('storage_id', request.GET.get('storage_id'))
        selected_source_name = self.kwargs.get('storage_name', request.GET.get('storage_name'))

        if not selected_source_id and source_storages.exists():
            selected_source_id = source_storages.first().id

        source_storage_list = get_export_data(self.institution_guid)
        source_name_list = [item['source_name'] for item in source_storage_list]
        source_name_list = list(set(filter(None, source_name_list)))
        source_name_list.sort()

        self.query_set = get_export_data(self.institution_guid, selected_location_id,
                                         selected_source_id, selected_source_name=selected_source_name)

        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_name_list': source_name_list,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'selected_source_name': selected_source_name if selected_source_name else '',
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


class ExportDataDeletedListView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_deleted_list.html'

    def get(self, request, *args, **kwargs):
        self.load_institution()

        locations = self.institution.get_allowed_storage_location()
        selected_location_id = request.GET.get('location_id')
        selected_source_name = self.kwargs.get('storage_name', request.GET.get('storage_name'))
        if not selected_location_id and locations.exists():
            selected_location_id = locations.first().id

        source_storages = self.institution.get_institutional_storage()
        selected_source_id = self.kwargs.get('storage_id', request.GET.get('storage_id'))
        if not selected_source_id and source_storages.exists():
            selected_source_id = source_storages.first().id

        source_storage_list = get_export_data(self.institution_guid)
        source_name_list = [item['source_name'] for item in source_storage_list]
        source_name_list = list(set(filter(None, source_name_list)))
        source_name_list.sort()

        self.query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id,
                                          deleted=True, selected_source_name=selected_source_name)
        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)
        context = {
            'institution': self.institution,
            'list_export_data': self.query_set,
            'locations': locations,
            'selected_location_id': int(selected_location_id) if selected_location_id else 0,
            'source_name_list': source_name_list,
            'selected_source_id': int(selected_source_id) if selected_source_id else 0,
            'selected_source_name': selected_source_name if selected_source_name else '',
            'source_id': self.query_set[0]['source_id'] if len(self.query_set) > 0 else 0,
            'page': self.page,
        }
        return render(request, self.template_name, context)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ExportDataInformationView(ExportBaseView):
    template_name = 'rdm_custom_storage_location/export_data_information.html'

    def get_object(self, **kwargs):
        data_id = self.kwargs.get('data_id')
        export_data = ExportData.objects.filter(id=data_id, is_deleted=False).first()
        if export_data:
            if not self.is_super_admin:
                source_institution_guid = export_data.source.guid
                source_institution_query = Institution.objects.filter(_id=source_institution_guid, is_deleted=False)
                if not source_institution_query.exists():
                    self.handle_no_permission()

                source_institution_id = source_institution_query.first().id

                if not self.is_affiliated_institution(source_institution_id):
                    self.handle_no_permission()
            return export_data
        raise Http404(f'Export data with id {data_id} not found.')

    def get(self, request, *args, **kwargs):
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id'), is_deleted=False).first()
        if not self.is_super_admin:
            self.load_institution()
        else:
            if export_data:
                self.institution_guid = export_data.source.guid
                self.institution = Institution.objects.filter(_id=self.institution_guid, is_deleted=False).first()

        cookie = self.request.user.get_or_create_cookie().decode()
        cookies = self.request.COOKIES

        kwargs.pop('object_list', None)
        self.object_list = []
        self.query_set = []
        export_data = self.get_object()

        source_storages = self.institution.get_institutional_storage()

        # get file_info from location
        try:
            response = export_data.read_export_data_from_location(cookies, cookie=cookie)
        except Exception:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=request, error_msgs=message)
        status_code = response.status_code
        if status_code != 200:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=request, error_msgs=message)
        # validate export_data
        exported_info = response.json()
        check = validate_exported_data(exported_info, schema_filename='export-data-schema.json')
        if not check:
            message = 'The export data files are corrupted.'
            return render_bad_request_response(request=request, error_msgs=message)

        # get file_info from location
        try:
            response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        except Exception:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=request, error_msgs=message)
        status_code = response.status_code
        if status_code != 200:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=request, error_msgs=message)
        # validate list_file_info
        file_info = response.json()
        check = validate_exported_data(file_info)
        if not check:
            message = 'The export data files are corrupted.'
            return render_bad_request_response(request=request, error_msgs=message)

        processed_list_file_info = process_data_information(file_info['files'])
        self.object_list = processed_list_file_info
        self.query_set = processed_list_file_info

        self.page_size = self.get_paginate_by(self.query_set)
        _, self.page, self.query_set, _ = self.paginate_queryset(self.query_set, self.page_size)

        context = {
            'institution': self.institution,
            'destination_storages': source_storages,
            'exported_info': exported_info,
            'export_data': export_data,
            'file_versions': self.query_set,
            'page': self.page,
        }
        return render(request, self.template_name, context)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class DeleteExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        institution_id_set = set()
        try:
            selected_source_id = self.request.POST.get('selected_source_id')
            if selected_source_id:
                selected_source_inst = Region.objects.filter(id=int(selected_source_id)).first()
                if selected_source_inst:
                    institution_id_set.add(selected_source_inst.institution.id)
                else:
                    raise Http404(f'The selected source with id {selected_source_id} is not exist')

            institution_id = self.request.POST.get('institution_id')
            if institution_id:
                if not Institution.objects.filter(id=int(institution_id), is_deleted=False).exists():
                    raise Http404(f'The institution with id {institution_id} is not exist')
                institution_id_set.add(int(institution_id))

            selected_location_id = self.request.POST.get('selected_location_id')
            if selected_location_id:
                selected_location = ExportDataLocation.objects.filter(id=selected_location_id).first()
                if selected_location:
                    selected_location_inst = Institution.load(selected_location.institution_guid)
                    if selected_location_inst:
                        institution_id_set.add(selected_location_inst.id)
                else:
                    raise Http404(f'The selected source with id {selected_source_id} is not exist')

            list_export_data = self.request.POST.get('list_id_export_data')
            if list_export_data:
                list_export_data = list(filter(None, list_export_data.split('#')))
                list_export_data = list(map(int, list_export_data))
                institution_guid = ExportData.objects.filter(
                    id__in=list_export_data).values_list('source___id', flat=True)
                institution_guid_set = set(institution_guid)
                if len(institution_guid_set) > 1:
                    return False
                elif len(institution_guid_set) == 1:
                    institution_id_set.add(Institution.load(institution_guid_set.pop()).id)
        except ValueError:
            pass

        if len(institution_id_set) < 1:
            return True
        elif len(institution_id_set) > 1:
            return False
        else:
            return self.has_auth(institution_id_set.pop())

    def post(self, request):
        # Init and validate request body data
        try:
            cookie = request.user.get_or_create_cookie().decode()
            cookies = request.COOKIES
            is_super = self.is_super_admin
            selected_source_id = request.POST.get('selected_source_id')
            if selected_source_id:
                selected_source_id = int(selected_source_id)
            selected_location_id = request.POST.get('selected_location_id')
            if selected_location_id:
                selected_location_id = int(selected_location_id)
            institution_id = request.POST.get('institution_id')
            if is_super and not institution_id:
                message = 'The request missing required institution_id.'
                return render_bad_request_response(request=request, error_msgs=message)
            elif institution_id:
                institution_id = int(institution_id)

            list_export_data_delete = request.POST.get('list_id_export_data')
            if not list_export_data_delete:
                message = 'The request missing list_id_export_data.'
                return render_bad_request_response(request=request, error_msgs=message)
            list_export_data_delete = list(filter(None, list_export_data_delete.split('#')))
            list_export_data_delete = list(map(int, list_export_data_delete))

        except ValueError:
            message = 'The request contain invalid value.'
            return render_bad_request_response(request=request, error_msgs=message)

        # Delete export data
        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        if check_delete_permanently:
            for item in ExportData.objects.filter(id__in=list_export_data_delete, is_deleted=True):
                response = item.delete_export_data_folder(cookies, cookie=cookie)
                if response.status_code == 204:
                    item.delete()
                else:

                    message = 'Cannot connect to the export data storage location.'
                    return render_bad_request_response(request=request, error_msgs=message)
        else:
            ExportData.objects.filter(id__in=list_export_data_delete).update(is_deleted=True)

        if check_delete_permanently:
            if selected_source_id and selected_location_id:
                if is_super:
                    return redirect(reverse('custom_storage_location:export_data:export_data_deleted_list_institution', kwargs={'institution_id': institution_id}) + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
                else:
                    return redirect(reverse('custom_storage_location:export_data:export_data_deleted_list') + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
            else:
                if is_super:
                    return redirect(reverse('custom_storage_location:export_data:export_data_deleted_list_institution', kwargs={'institution_id': institution_id}))
                else:
                    return redirect('custom_storage_location:export_data:export_data_deleted_list')
        else:
            if selected_source_id and selected_location_id:
                if is_super:
                    return redirect(reverse('custom_storage_location:export_data:export_data_list_institution', kwargs={'institution_id': institution_id}) + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
                else:
                    return redirect(reverse('custom_storage_location:export_data:export_data_list') + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
            else:
                if is_super:
                    return redirect(reverse('custom_storage_location:export_data:export_data_list_institution', kwargs={'institution_id': institution_id}))
                else:
                    return redirect('custom_storage_location:export_data:export_data_list')


class RevertExportDataView(ExportStorageLocationViewBaseView, View):
    raise_exception = True

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        institution_id_set = set()
        # Collect institution_id from request body data
        try:
            selected_source_id = self.request.POST.get('selected_source_id')
            if selected_source_id:
                selected_source_inst = Region.objects.filter(id=int(selected_source_id)).first()
                if selected_source_inst:
                    institution_id_set.add(selected_source_inst.institution.id)
                else:
                    raise Http404(f'The selected source with id {selected_source_id} is not exist')

            institution_id = self.request.POST.get('institution_id')
            if institution_id:
                if not Institution.objects.filter(id=int(institution_id), is_deleted=False).exists():
                    raise Http404(f'The institution with id {institution_id} is not exist')
                institution_id_set.add(int(institution_id))

            selected_location_id = self.request.POST.get('selected_location_id')
            if selected_location_id:
                selected_location = ExportDataLocation.objects.filter(id=int(selected_location_id)).first()
                if selected_location:
                    selected_location_inst = Institution.load(selected_location.institution_guid)
                    if selected_location_inst:
                        institution_id_set.add(selected_location_inst.id)
                else:
                    raise Http404(f'The selected location with id {selected_location_id} is not exist')
            list_export_data = self.request.POST.get('list_id_export_data')
            if list_export_data:
                list_export_data = list(filter(None, list_export_data.split('#')))
                list_export_data = list(map(int, list_export_data))
                institution_guid = ExportData.objects.filter(
                    id__in=list_export_data, is_deleted=True).values_list('source___id', flat=True)
                institution_guid_set = set(institution_guid)
                if len(institution_guid_set) > 1:
                    return False
                elif len(institution_guid_set) == 1:
                    institution_id_set.add(Institution.load(institution_guid_set.pop()).id)

        except ValueError:
            pass

        if len(institution_id_set) < 1:
            return True
        elif len(institution_id_set) > 1:
            return False
        else:
            return self.has_auth(institution_id_set.pop())

    def post(self, request):
        # Init and validate request body data
        try:
            is_super = self.is_super_admin
            selected_source_id = request.POST.get('selected_source_id')
            if selected_source_id:
                selected_source_id = int(selected_source_id)
            selected_location_id = request.POST.get('selected_location_id')
            if selected_location_id:
                selected_location_id = int(selected_location_id)
            institution_id = request.POST.get('institution_id')
            if is_super and not institution_id:
                message = 'The request missing required institution_id.'
                return render_bad_request_response(request=request, error_msgs=message)
            elif institution_id:
                institution_id = int(institution_id)
            list_export_data = request.POST.get('list_id_export_data')
            if not list_export_data:
                message = 'The request missing list_id_export_data.'
                return render_bad_request_response(request=request, error_msgs=message)
            list_export_data = list(filter(None, list_export_data.split('#')))
            list_export_data = list(map(int, list_export_data))
        except ValueError:
            message = 'The request contain invalid value.'
            return render_bad_request_response(request=request, error_msgs=message)

        # Revert export data deleted and redirect
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=False)
        if selected_source_id and selected_location_id:
            if is_super:
                return redirect(reverse(
                    'custom_storage_location:export_data:export_data_deleted_list_institution', kwargs={'institution_id': institution_id}) + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
            else:
                return redirect(reverse(
                    'custom_storage_location:export_data:export_data_deleted_list') + f'?storage_id={selected_source_id}&location_id={selected_location_id}')
        else:
            if is_super:
                return redirect(reverse('custom_storage_location:export_data:export_data_deleted_list_institution', kwargs={'institution_id': institution_id}))
            else:
                return redirect('custom_storage_location:export_data:export_data_deleted_list')


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ExportDataFileCSVView(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True

    def test_func(self):
        """ Check user permissions """
        if not self.is_authenticated:
            return False
        user = self.request.user
        return user.is_super_admin or user.is_institutional_admin

    def get_object(self, **kwargs):
        data_id = self.kwargs.get('data_id')
        export_data = ExportData.objects.filter(id=data_id, is_deleted=False).first()
        if export_data:
            if not self.is_super_admin:
                source_institution_guid = export_data.source.guid
                source_institution_query = Institution.objects.filter(_id=source_institution_guid, is_deleted=False)
                if not source_institution_query.exists():
                    self.handle_no_permission()

                source_institution_id = source_institution_query.first().id

                if not self.is_affiliated_institution(source_institution_id):
                    self.handle_no_permission()
            return export_data
        raise Http404(f'Export data with id {data_id} not found.')

    def get(self, *args, **kwargs):
        cookie = self.request.user.get_or_create_cookie().decode()
        cookies = self.request.COOKIES

        export_data = self.get_object()
        # get file_info from location
        try:
            response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        except Exception:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=self.request, error_msgs=message)
        status_code = response.status_code
        if status_code != 200:
            message = 'Cannot connect to the export data storage location.'
            return render_bad_request_response(request=self.request, error_msgs=message)
        # validate list_file_info
        file_info = response.json()
        processed_list_file_info = process_data_information(file_info['files'])
        if self.is_super_admin:
            guid = export_data.source.guid
        else:
            guid = self.request.user.representative_affiliated_institution.guid
        current_datetime = str('{date:%Y-%m-%d-%H%M%S}'.format(date=datetime.datetime.now())).replace('-', '')
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=file_info_{}_{}.csv'.format(guid, current_datetime)
        writer = csv.writer(response)
        writer.writerow(
            ['project_id', 'project_name', 'owner', 'file_id', 'file_path', 'filename', 'versions', 'size', 'stamper'])
        for file in processed_list_file_info:
            writer.writerow([
                file['project']['id'],
                file['project']['name'],
                file['contributor'],
                file['id'],
                file['materialized_path'],
                file['name'],
                file['identifier'],
                str(file['size']) + ' Bytes',
                file.get('timestamp', {}).get('verify_user')
            ])
        return response


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class CheckExportData(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True
    export_data = None
    user_institution_guid = None

    def dispatch(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()

        data_id = self.kwargs.get('data_id')
        self.export_data = ExportData.objects.filter(id=data_id, is_deleted=False).first()
        if not self.export_data:
            message = f'The data_id "{data_id}" is not exist'
            return JsonResponse({'message': message}, status=404)

        return super(CheckExportData, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        """check user permissions"""
        institution_guid = self.export_data.source._id
        user = self.request.user
        if not user.is_superuser and user.is_affiliated_institution:
            institution = user.affiliated_institutions.first()
            self.user_institution_guid = institution.guid

        return user.is_superuser or (user.is_institutional_admin
                                      and self.user_institution_guid == institution_guid)

    def get(self, request, *args, **kwargs):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        if self.export_data.status != ExportData.STATUS_COMPLETED:
            message = f'Cannot check in this time. The process is {self.export_data.status}'
            return JsonResponse({'message': message}, status=400)

        # start check
        self.export_data.status = ExportData.STATUS_CHECKING
        self.export_data.last_check = datetime.datetime.now()
        self.export_data.save()

        try:
            # get file information exported
            response = self.export_data.read_file_info_from_location(cookies, cookie=cookie)
            status_code = response.status_code

            if status_code != 200:
                message = 'Cannot connect to the export data storage location.'
                return JsonResponse({'message': message}, status=400)
            exported_file_info = response.json()
            check = validate_exported_data(exported_file_info)
            if not check:
                message = 'The export data files are corrupted.'
                return JsonResponse({'message': message}, status=400)

            # Get data from current source storage
            _, storage_file_info = self.export_data.extract_file_information_json_from_source_storage()
            exported_file_versions = process_data_information(exported_file_info['files'])
            storage_file_versions = process_data_information(storage_file_info['files'])
            exclude_keys = []
            data = count_files_ng_ok(exported_file_versions, storage_file_versions, exclude_keys=exclude_keys)

            # check file exist in Export location storage
            node_id = self.export_data.EXPORT_DATA_FAKE_NODE_ID
            provider = self.export_data.location.provider_name
            location_id = self.export_data.location.id
            file_path = f'/{self.export_data.export_data_folder_name}/files/'
            file_list = check_for_file_existent_on_export_location(
                exported_file_info, node_id, provider, file_path, location_id, cookies, cookie)
            file_fails_list = data.get('list_file_ng') + file_list
            for file in file_list:
                if not any(d['path'] == file['path'] for d in data.get('list_file_ng')):
                    data['ng'] += 1
                    data['ok'] -= 1
            data['list_file_ng'] = file_fails_list

            return JsonResponse(data, status=200)
        except Exception:
            message = 'Cannot connect to the export data storage location.'
            return JsonResponse({'message': message}, status=400)
        finally:
            # end check
            self.export_data.status = ExportData.STATUS_COMPLETED
            self.export_data.save()


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class CheckRestoreData(RdmPermissionMixin, UserPassesTestMixin, View):
    raise_exception = True
    destination_id = None
    institution_id = None
    export_data = None

    def dispatch(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""
        # login check
        if not self.is_authenticated:
            return self.handle_no_permission()
        try:
            self.destination_id = self.request.GET.get('destination_id')
            if self.destination_id:
                self.institution_id = get_institution_id_by_region(
                    Region.objects.filter(id=int(self.destination_id)).first())
                if not self.institution_id:
                    message = f'The destination_id "{self.destination_id}" is not exist'
                    return JsonResponse({'message': message}, status=404)
            data_id = self.kwargs.get('data_id')
            self.export_data = ExportData.objects.filter(id=data_id, is_deleted=False).first()
            if not self.export_data:
                message = f'The data_id "{data_id}" is not exist'
                return JsonResponse({'message': message}, status=404)

            return super(CheckRestoreData, self).dispatch(request, *args, **kwargs)
        except ValueError:
            message = 'destination_id must be a integer'
            return JsonResponse({'message': message}, status=400)

    def test_func(self):
        """check user permissions"""

        # allowed if superuser or admin
        if not self.is_super_admin and not self.is_institutional_admin:
            return False

        if self.export_data:
            export_data_inst_id = get_institution_id_by_region(self.export_data.source)
        if not export_data_inst_id:
            return True
        elif not self.destination_id:
            return self.has_auth(export_data_inst_id)
        else:
            return (export_data_inst_id == self.institution_id) and self.has_auth(export_data_inst_id)

    def get(self, request, data_id):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        try:
            if 'destination_id' in request.GET:
                restore_data = self.export_data.get_latest_restored_data_with_destination_id(self.destination_id)
            else:
                restore_data = self.export_data.get_latest_restored()
        except ExportDataRestore.DoesNotExist:
            message = f'Cannot check restore data with data_id is {data_id} and destination_id is {self.destination_id}'
            return JsonResponse({'message': message}, status=400)

        if restore_data.status != ExportData.STATUS_COMPLETED:
            message = f'Cannot check in this time. The process is {restore_data.status}'
            return JsonResponse({'message': message}, status=400)

        # start check
        restore_data.status = ExportData.STATUS_CHECKING
        restore_data.last_check = datetime.datetime.now()
        restore_data.save()

        try:
            # get file information exported
            response = restore_data.export.read_file_info_from_location(cookies, cookie=cookie)
            if response.status_code != 200:
                message = 'Cannot connect to the export data storage location.'
                return JsonResponse({'message': message}, status=400)
            exported_file_info = response.json()
            check = validate_exported_data(exported_file_info)
            if not check:
                message = 'The export data files are corrupted.'
                return JsonResponse({'message': message}, status=400)

            # Get data from current destination storage
            _, storage_file_info = restore_data.extract_file_information_json_from_destination_storage()
            exported_file_versions = process_data_information(exported_file_info['files'])
            storage_file_versions = process_data_information(storage_file_info['files'])
            exclude_keys = ['location']
            data = count_files_ng_ok(exported_file_versions, storage_file_versions, exclude_keys=exclude_keys)

            return JsonResponse(data, status=200)
        except Exception:
            message = 'Cannot connect to the export data storage location.'
            return JsonResponse({'message': message}, status=400)
        finally:
            # end check
            restore_data.status = ExportData.STATUS_COMPLETED
            restore_data.save()
