from django.conf.urls import url

from api.files import views

urlpatterns = [
    url(r'^(?P<file_id>\w+)/$', views.FileDetail.as_view(), name='file-detail'),
    url(r'^(?P<file_id>\w+)/versions/$', views.FileVersionsList.as_view(), name='file-versions'),
    url(r'^(?P<file_id>\w+)/versions/(?P<version_id>\w+)/$', views.FileVersionDetail.as_view(), name='version-detail'),
]
