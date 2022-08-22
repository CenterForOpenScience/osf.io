# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import location, institutional_storage, management, restore
from ..views import TestConnectionView

urlpatterns = [
    # to register export data storage location
    url(r'^storage_location/$',
        location.ExportStorageLocationView.as_view(),
        name='export_data_storage_location'),
    url(r'^storage_location/(?P<location_id>[0-9]+)/delete/$',
        location.DeleteCredentialsView.as_view(),
        name='export_data_delete_credentials'),
    url(r'^test_connection/$',
        TestConnectionView.as_view(),
        name='export_data_test_connection'),
    url(r'^save_credentials/$',
        location.SaveCredentialsView.as_view(),
        name='export_data_save_credentials'),

    # to manage institutional storage
    url(r'^institutions/$',
        institutional_storage.ExportDataInstitutionListView.as_view(),
        name='export_data_institutions'),
    url(r'^institutions/(?P<institution_id>[0-9]+)/storages/$',
        institutional_storage.ExportDataInstitutionalStorageListView.as_view(),
        name='export_data_institutional_storage'),

    # to manage export data
    url(r'^institutions/(?P<institution_id>[0-9]+)/storages/(?P<storage_id>[0-9]+)/$',
        management.ExportDataListView.as_view(),
        name='export_data_institutional_storage_list'),
    url(r'^institutions/(?P<institution_id>[0-9]+)/storages/(?P<storage_id>[0-9]+)/deleted/$',
        management.ExportDataDeletedListView.as_view(),
        name='export_data_institutional_storage_deleted_list'),
    url(r'^$',
        management.ExportDataListView.as_view(),
        name='export_data_list'),
    url(r'^deleted/$',
        management.ExportDataDeletedListView.as_view(),
        name='export_data_deleted_list'),
    url(r'^(?P<data_id>[0-9]+)/$',
        management.ExportDataInformationView.as_view(),
        name='export_data_information'),
    url(r'^delete/$',
        management.DeleteExportDataView.as_view(),
        name='export_data_delete'),
    url(r'^revert/$',
        management.RevertExportDataView.as_view(),
        name='export_data_revert'),
    url(r'^output_csv/$',
        management.ExportDataFileCSVView.as_view(),
        name='export_data_output_csv'),

    # to manage restore export data storage
    url(r'^(?P<export_id>[0-9]+)/restore_export_data$',
        restore.ExportDataRestore.as_view(), name='export_data_restore'),
    url(r'^(?P<export_id>[0-9]+)/task_status$',
        restore.ExportDataRestoreTaskStatus.as_view(), name='export_data_restore_task_status'),
]
