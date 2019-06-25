from django.conf.urls import url
from admin.osf_groups import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.OSFGroupsListView.as_view(), name='osf_groups_list'),
    url(r'^search/$', views.OSFGroupsFormView.as_view(), name='search'),
    url(r'^(?P<id>[a-z0-9]+)/$', views.OSFGroupsView.as_view(), name='osf_group'),
]
