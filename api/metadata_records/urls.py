from django.conf.urls import url

from api.metadata_records import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.MetadataRecordCreate.as_view(), name=views.MetadataRecordCreate.view_name),
    url(r'^(?P<metadata_record_id>\w+)/$', views.MetadataRecordDetail.as_view(), name=views.MetadataRecordDetail.view_name),
    url(r'^guid/(?P<guid_id>\w+)/(?P<serializer_name>[\w-]+)$', views.GuidMetadataDownload.as_view(), name=views.GuidMetadataDownload.view_name),
]
