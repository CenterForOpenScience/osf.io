from django.urls import re_path

from api.osf_groups import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.GroupList.as_view(), name=views.GroupList.view_name),
    re_path(r'^(?P<group_id>\w+)/$', views.GroupDetail.as_view(), name=views.GroupDetail.view_name),
    re_path(r'^(?P<group_id>\w+)/members/$', views.GroupMembersList.as_view(), name=views.GroupMembersList.view_name),
    re_path(r'^(?P<group_id>\w+)/members/(?P<user_id>\w+)/$', views.GroupMemberDetail.as_view(), name=views.GroupMemberDetail.view_name),
]
