from django.conf.urls import url

from api.osf_groups import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.OSFGroupList.as_view(), name=views.OSFGroupList.view_name),
    url(r'^(?P<group_id>\w+)/$', views.OSFGroupDetail.as_view(), name=views.OSFGroupDetail.view_name),
    url(r'^(?P<group_id>\w+)/managers/$', views.OSFGroupManagersList.as_view(), name=views.OSFGroupManagersList.view_name),
    url(r'^(?P<group_id>\w+)/members/$', views.OSFGroupMembersList.as_view(), name=views.OSFGroupMembersList.view_name),
]
