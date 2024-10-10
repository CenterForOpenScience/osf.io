from django.conf.urls import include, url
from . import views


urlpatterns = [
    url(r'^external_acc_update/(?P<access_token>-?\w+)/$', views.external_acc_update, name='external_acc_update'),
    url(r'^institutional_storage/$', views.InstitutionalStorageView.as_view(), name='institutional_storage'),
    url(r'^institutional_storage/institutions/$', views.InstitutionalStorageListView.as_view(), name='institutional_storage_institutions'),
    url(r'^institutional_storage/institutions/(?P<institution_id>[0-9]+)/$', views.InstitutionalStorageView.as_view(), name='institutional_storage_list'),
    url(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    url(r'^test_connection/(?P<institution_id>[0-9]+)$', views.TestConnectionView.as_view(), name='test_connection'),
    url(r'^save_credentials/(?P<institution_id>[0-9]+)$', views.SaveCredentialsView.as_view(), name='save_credentials'),
    url(r'^credentials/(?P<institution_id>[0-9]+)$', views.FetchCredentialsView.as_view(), name='credentials'),
    url(r'^fetch_temporary_token/(?P<institution_id>[0-9]+)$', views.FetchTemporaryTokenView.as_view(), name='fetch_temporary_token'),
    url(r'^remove_auth_data_temporary/(?P<institution_id>[0-9]+)$', views.RemoveTemporaryAuthData.as_view(), name='remove_auth_data_temporary'),
    url(r'^usermap/(?P<institution_id>[0-9]+)$', views.UserMapView.as_view(), name='usermap'),

    url(r'^export_data/', include('admin.rdm_custom_storage_location.export_data.urls', namespace='export_data')),
]
