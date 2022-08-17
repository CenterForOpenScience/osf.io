from django.conf.urls import url

from . import export_data_views
from . import views


urlpatterns = [
    url(r'^external_acc_update/(?P<access_token>-?\w+)/$', views.external_acc_update, name='external_acc_update'),
    url(r'^institutional_storage/$', views.InstitutionalStorageView.as_view(), name='institutional_storage'),
    url(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    url(r'^test_connection/$', views.TestConnectionView.as_view(), name='test_connection'),
    url(r'^save_credentials/$', views.SaveCredentialsView.as_view(), name='save_credentials'),
    url(r'^credentials/$', views.FetchCredentialsView.as_view(), name='credentials'),
    url(r'^fetch_temporary_token/$', views.FetchTemporaryTokenView.as_view(), name='fetch_temporary_token'),
    url(r'^remove_auth_data_temporary/$', views.RemoveTemporaryAuthData.as_view(), name='remove_auth_data_temporary'),
    url(r'^usermap/$', views.UserMapView.as_view(), name='usermap'),

    # to register export data storage location
    url(r'^export_data/storage_location/$', export_data_views.ExportStorageLocationView.as_view(), name='export_data_storage_location'),
    url(r'^export_data/test_connection/$', views.TestConnectionView.as_view(), name='export_data_test_connection'),
    url(r'^export_data/save_credentials/$', export_data_views.SaveCredentialsView.as_view(), name='export_data_save_credentials'),

    # to manage export data
    url(r'^export_data/institutions/$', export_data_views.ExportDataInstitutionList.as_view(), name='export_data_institutions'),
    url(r'^export_data/institutions/(?P<institution_id>[0-9]+)/storages/$', export_data_views.ExportDataInstitutionalStorages.as_view(),
        name='export_data_institution_storages'),
    # url(r'^export_data/institutions/(?P<institution_id>[0-9]+)/storages/(?P<storage_id>[0-9]+)/$',
    #     export_data_views.ExportDataList.as_view(),
    #     name='export_data_list'),
    url(r'^export_data/institutions/manager/$',
        export_data_views.ExportDataList.as_view(),
        name='export_data_list'),
    # url(r'^export_data/institutions/(?P<institution_id>[0-9]+)/storages/(?P<storage_id>[0-9]+)/deleted/$',
    #     export_data_views.ExportDataDeletedList.as_view(),
    #     name='export_data_deleted_list'),
    url(r'^export_data/institutions/manager/deleted/$',
        export_data_views.ExportDataDeletedList.as_view(),
        name='export_data_deleted_list'),
    url(r'^export_data/(?P<data_id>[0-9]+)/$', export_data_views.ExportDataInformation.as_view(), name='export_data_information'),
    url(r'^delete_export_data/$', export_data_views.DeleteExportData.as_view(), name='delete_export_data'),
    url(r'^revert_export_data/$', export_data_views.RevertExportData.as_view(), name='revert_export_data'),
    url(r'^export_data_csv/$', export_data_views.ExportDataFileCSV.as_view(), name='export_data_csv'),
]
