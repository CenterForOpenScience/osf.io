from django.conf.urls import url

from api.files import views

urlpatterns = [
    url(r'^(?P<file_id>\w+)/$', views.FileDetail.as_view(), name=views.FileDetail.view_name),
    url(r'^(?P<file_id>\w+)/versions/$', views.FileVersionsList.as_view(), name=views.FileVersionsList.view_name),
    url(r'^(?P<file_id>\w+)/versions/(?P<version_id>\w+)/$', views.FileVersionDetail.as_view(), name=views.FileVersionDetail.view_name),
    url(r'^(?P<node_id>\w+)/list/(?P<provider>\w+)(?P<path>/(?:.*/)?)', views.FileList.as_view(), name=views.FileList.view_name),
]
