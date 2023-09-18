# -*- coding: utf-8 -*-
import csv
import datetime
import inspect  # noqa
import logging

from django.core.exceptions import SuspiciousOperation
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
)
from osf.models import ExportData, Institution
from website.util import inspect_info  # noqa
from .location import ExportStorageLocationViewBaseView

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
            self.institution = Institution.objects.get(id=institution_id)
            self.institution_guid = self.institution.guid
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

        self.query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id, selected_source_name=selected_source_name)

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

        self.query_set = get_export_data(self.institution_guid, selected_location_id, selected_source_id, deleted=True, selected_source_name=selected_source_name)
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
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id')).first()
        if export_data:
            if not self.is_super_admin:
                source_institution_guid = export_data.source.guid
                source_institution_query = Institution.objects.filter(_id=source_institution_guid)
                if not source_institution_query.exists():
                    self.handle_no_permission()

                source_institution_id = source_institution_query.first().id

                if not self.is_affiliated_institution(source_institution_id):
                    self.handle_no_permission()
            return export_data
        raise Http404(
            'Export data with id {} not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get(self, request, *args, **kwargs):
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id')).first()
        if not self.is_super_admin:
            self.load_institution()
        else:
            if export_data:
                self.institution_guid = export_data.source.guid
                self.institution = Institution.objects.filter(_id=self.institution_guid).first()

        cookie = self.request.user.get_or_create_cookie().decode()
        cookies = self.request.COOKIES

        kwargs.pop('object_list', None)
        self.object_list = []
        self.query_set = []
        export_data = self.get_object()

        source_storages = self.institution.get_institutional_storage()

        # get file_info from location
        response = export_data.read_export_data_from_location(cookies, cookie=cookie)
        status_code = response.status_code
        if status_code != 200:
            raise SuspiciousOperation('Cannot connect to the export data storage location.')
        # validate export_data
        exported_info = response.json()
        check = validate_exported_data(exported_info, schema_filename='export-data-schema.json')
        if not check:
            raise SuspiciousOperation('The export data files are corrupted.')

        # get file_info from location
        response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        status_code = response.status_code
        if status_code != 200:
            raise SuspiciousOperation('Cannot connect to the export data storage location.')
        # validate list_file_info
        file_info = response.json()
        check = validate_exported_data(file_info)
        if not check:
            raise SuspiciousOperation('The export data files are corrupted.')

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

    def post(self, request):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        check_delete_permanently = True if request.POST.get('delete_permanently') == 'on' else False
        list_export_data_delete = request.POST.get('list_id_export_data').split('#')
        list_export_data_delete = list(filter(None, list_export_data_delete))
        if check_delete_permanently:
            for item in ExportData.objects.filter(id__in=list_export_data_delete, is_deleted=True):
                response = item.delete_export_data_folder(cookies, cookie=cookie)
                if response.status_code == 204:
                    item.delete()
                else:
                    raise SuspiciousOperation('Cannot connect to the export data storage location.')
        else:
            ExportData.objects.filter(id__in=list_export_data_delete).update(is_deleted=True)
        selected_source_id = request.POST.get('selected_source_id')
        selected_location_id = request.POST.get('selected_location_id')
        institution_id = request.POST.get('institution_id')
        is_super = self.is_super_admin
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

    def post(self, request):
        list_export_data = request.POST.get('list_id_export_data').split('#')
        list_export_data = list(filter(None, list_export_data))
        if list_export_data:
            ExportData.objects.filter(id__in=list_export_data).update(is_deleted=False)
        selected_source_id = request.POST.get('selected_source_id')
        selected_location_id = request.POST.get('selected_location_id')
        institution_id = request.POST.get('institution_id')
        is_super = self.is_super_admin
        if len(selected_source_id) > 0 and len(selected_location_id) > 0:
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
class ExportDataFileCSVView(RdmPermissionMixin, View):

    def get_object(self, **kwargs):
        export_data = ExportData.objects.filter(id=self.kwargs.get('data_id')).first()
        if export_data:
            if not self.is_super_admin:
                source_institution_guid = export_data.source.guid
                source_institution_query = Institution.objects.filter(_id=source_institution_guid)
                if not source_institution_query.exists():
                    self.handle_no_permission()

                source_institution_id = source_institution_query.first().id

                if not self.is_affiliated_institution(source_institution_id):
                    self.handle_no_permission()
            return export_data
        raise Http404(
            'Export data with id {} not found.'.format(
                self.kwargs.get('data_id')
            ))

    def get(self, *args, **kwargs):
        cookie = self.request.user.get_or_create_cookie().decode()
        cookies = self.request.COOKIES

        export_data = self.get_object()
        # get file_info from location
        response = export_data.read_file_info_from_location(cookies, cookie=cookie)
        status_code = response.status_code
        if status_code != 200:
            raise SuspiciousOperation('Cannot connect to the export data storage location.')
        # validate list_file_info
        file_info = response.json()
        processed_list_file_info = process_data_information(file_info['files'])
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
class CheckExportData(RdmPermissionMixin, View):

    def get(self, request, data_id):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        export_data = ExportData.objects.filter(id=data_id).first()
        if export_data.status != ExportData.STATUS_COMPLETED:
            message = 'Cannot check in this time. The process is {}'.format(export_data.status)
            return JsonResponse({'message': message}, status=400)

        # start check
        export_data.status = ExportData.STATUS_CHECKING
        export_data.last_check = datetime.datetime.now()
        export_data.save()

        # get file information exported
        response = export_data.read_file_info_from_location(cookies, cookie=cookie)
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
        _, storage_file_info = export_data.extract_file_information_json_from_source_storage()
        exported_file_versions = process_data_information(exported_file_info['files'])
        storage_file_versions = process_data_information(storage_file_info['files'])
        exclude_keys = []
        data = count_files_ng_ok(exported_file_versions, storage_file_versions, exclude_keys=exclude_keys)

        # end check
        export_data.status = ExportData.STATUS_COMPLETED
        export_data.save()

        return JsonResponse(data, status=200)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class CheckRestoreData(RdmPermissionMixin, View):

    def get(self, request, data_id):
        cookie = request.user.get_or_create_cookie().decode()
        cookies = request.COOKIES

        export_data = ExportData.objects.filter(id=data_id).first()

        if 'destination_id' in request.GET:
            destination_id = request.GET.get('destination_id')
            restore_data = export_data.get_latest_restored_data_with_destination_id(destination_id)
        else:
            restore_data = export_data.get_latest_restored()

        if restore_data.status != ExportData.STATUS_COMPLETED:
            message = 'Cannot check in this time. The process is {}'.format(restore_data.status)
            return JsonResponse({'message': message}, status=400)

        # start check
        restore_data.status = ExportData.STATUS_CHECKING
        restore_data.last_check = datetime.datetime.now()
        restore_data.save()

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
        exclude_keys = []
        data = count_files_ng_ok(exported_file_versions, storage_file_versions, exclude_keys=exclude_keys)

        # end check
        restore_data.status = ExportData.STATUS_COMPLETED
        restore_data.save()

        return JsonResponse(data, status=200)
