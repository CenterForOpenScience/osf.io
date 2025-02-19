from django.urls import re_path
from admin.files import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.FileSearchView.as_view(), name='search'),
    re_path(r'^(?P<guid>\w+)/$', views.FileView.as_view(), name='file')
]
