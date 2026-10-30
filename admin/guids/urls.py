from django.urls import re_path
from admin.guids import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.GuidSearchView.as_view(), name='search'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.GuidDetailView.as_view(), name='detail'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reassign/$', views.GuidReassignView.as_view(), name='reassign'),
]
