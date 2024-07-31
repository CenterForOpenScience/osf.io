from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionAssetFileList.as_view(), name='list'),
    re_path(r'^create/$', views.InstitutionAssetFileCreate.as_view(), name='create'),
    re_path(r'^(?P<asset_id>[0-9]+)/$', views.InstitutionAssetFileDetail.as_view(), name='detail'),
    re_path(r'^(?P<asset_id>[0-9]+)/delete/$', views.InstitutionAssetFileDelete.as_view(), name='delete'),
]
