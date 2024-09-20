from django.urls import re_path

from api.cedar_metadata_records import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.CedarMetadataRecordCreate.as_view(), name=views.CedarMetadataRecordCreate.view_name),
    re_path(r'^(?P<record_id>[0-9A-Za-z]+)/metadata_download/$', views.CedarMetadataRecordMetadataDownload.as_view(), name=views.CedarMetadataRecordMetadataDownload.view_name),
    re_path(r'^(?P<record_id>[0-9A-Za-z]+)/$', views.CedarMetadataRecordDetail.as_view(), name=views.CedarMetadataRecordDetail.view_name),
]
