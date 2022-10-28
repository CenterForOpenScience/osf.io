from django.conf.urls import url

from api.metadata_records import views

app_name = 'osf'

urlpatterns = [
    url(r'^osfio:(?P<guid_id>\w+)/$', views.MetadataRecordDetail.as_view(), name=views.MetadataRecordDetail.view_name),
    url(r'^osfio:(?P<guid_id>\w+)/(?P<serializer_name>[\w-]+)$', views.GuidMetadataDownload.as_view(), name=views.GuidMetadataDownload.view_name),
]
