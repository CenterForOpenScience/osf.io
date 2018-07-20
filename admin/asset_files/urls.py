from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.ProviderAssetFileList.as_view(), name='list'),
    url(r'^create/$', views.ProviderAssetFileCreate.as_view(), name='create'),
    url(r'^(?P<asset_id>[0-9]+)/$', views.ProviderAssetFileDetail.as_view(), name='detail'),
    url(r'^(?P<asset_id>[0-9]+)/delete/$', views.ProviderAssetFileDelete.as_view(), name='delete'),
]
