from django.conf.urls import url

from api.file_schema_responses import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.FileSchemaResponsesList.as_view(), name=views.FileSchemaResponsesList.view_name),
    url(r'^(?P<file_schema_response_id>\w+)/$', views.FileSchemaResponseDetail.as_view(), name=views.FileSchemaResponseDetail.view_name),
    url(r'^(?P<file_schema_response_id>\w+)/download/$', views.FileSchemaResponseDownload.as_view(), name=views.FileSchemaResponseDownload.view_name),
]
