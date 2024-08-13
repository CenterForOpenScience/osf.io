from django.urls import re_path
from admin.osf_groups import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.OSFGroupsListView.as_view(), name='osf_groups_list'),
    re_path(r'^search/$', views.OSFGroupsFormView.as_view(), name='search'),
    re_path(r'^(?P<id>[a-z0-9]+)/$', views.OSFGroupsView.as_view(), name='osf_group'),
]
