from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.ProviderAssetFileList.as_view(), name='list'),
    re_path(r'^create/$', views.ProviderAssetFileCreate.as_view(), name='create'),
    re_path(r'^(?P<asset_id>[0-9]+)/$', views.ProviderAssetFileDetail.as_view(), name='detail'),
    re_path(r'^(?P<asset_id>[0-9]+)/delete/$', views.ProviderAssetFileDelete.as_view(), name='delete'),
]
