from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^external_acc_update/(?P<access_token>-?\w+)/$', views.external_acc_update, name='external_acc_update'),
    url(r'^institutional_storage/$', views.InstitutionalStorage.as_view(), name='institutional_storage'),
    url(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    url(r'^test_connection$', views.test_connection, name='test_connection'),
    url(r'^save_credentials$', views.save_credentials, name='save_credentials'),
]
