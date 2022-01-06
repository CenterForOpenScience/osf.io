from django.conf.urls import include, url

from api.files import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<file_id>\w+)/$', views.FileDetail.as_view(), name=views.FileDetail.view_name),
    url(r'^(?P<file_id>\w+)/versions/$', views.FileVersionsList.as_view(), name=views.FileVersionsList.view_name),
    url(r'^(?P<file_id>\w+)/versions/(?P<version_id>\w+)/$', views.FileVersionDetail.as_view(), name=views.FileVersionDetail.view_name),
    url(r'^(?P<file_id>\w+)/schema_responses/', include('api.file_schema_responses.urls', namespace='file_schema_responses')),
]
