from django.conf.urls import re_path

from api.files import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<file_id>\w+)/$', views.FileDetail.as_view(), name=views.FileDetail.view_name),
    re_path(r'^(?P<file_id>\w+)/versions/$', views.FileVersionsList.as_view(), name=views.FileVersionsList.view_name),
    re_path(r'^(?P<file_id>\w+)/versions/(?P<version_id>\w+)/$', views.FileVersionDetail.as_view(), name=views.FileVersionDetail.view_name),
    re_path(r'^(?P<file_id>\w+)/metadata_records/$', views.FileMetadataRecordsList.as_view(), name=views.FileMetadataRecordsList.view_name),
    re_path(r'^(?P<file_id>\w+)/metadata_records/(?P<record_id>\w+)/$', views.FileMetadataRecordDetail.as_view(), name=views.FileMetadataRecordDetail.view_name),
    re_path(r'^(?P<file_id>\w+)/metadata_records/(?P<record_id>\w+)/download/$', views.FileMetadataRecordDownload.as_view(), name=views.FileMetadataRecordDownload.view_name),
]
