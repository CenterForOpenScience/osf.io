from django.urls import re_path
from admin.guids import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.GuidSearchView.as_view(), name='search'),
    # version guids (abcde_v1) are matched too, so the detail view can explain why they are not supported
    re_path(r'^(?P<guid>[a-z0-9]+(?:_v[0-9]+)?)/$', views.GuidDetailView.as_view(), name='detail'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reassign/$', views.GuidReassignView.as_view(), name='reassign'),
]
