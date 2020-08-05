from django.conf.urls import url
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
]
