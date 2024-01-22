from django.urls import re_path

from api.cedar_metadata_records import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.CedarMetadataRecordList.as_view(), name=views.CedarMetadataRecordList.view_name),
    re_path(r'^(?P<record_id>[0-9A-Za-z]+)/$', views.CedarMetadataRecordDetail.as_view(), name=views.CedarMetadataRecordDetail.view_name),
]
