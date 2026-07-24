from django.urls import re_path
from admin.files import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.FileSearchView.as_view(), name='search'),
    re_path(r'^(?P<guid>\w+)/$', views.FileView.as_view(), name='file'),
    re_path(r'^(?P<guid>\w+)/delete/$', views.FileDeleteView.as_view(), name='file-delete'),
    re_path(r'^(?P<guid>\w+)/versions/(?P<version_id>[\w-]+)/delete/$', views.FileVersionDeleteView.as_view(), name='file-version-delete'),
]
